from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]


class Database:
    def __init__(self, root: Path, legacy_data_path: Path | None, start_balance: float) -> None:
        self.root = root
        self.legacy_data_path = legacy_data_path
        self.start_balance = start_balance
        self.backups = self.root / "backups"
        self.files = {
            "users": self.root / "users.json",
            "transactions": self.root / "transactions.json",
            "checks": self.root / "checks.json",
            "inventory": self.root / "inventory.json",
            "treasury": self.root / "treasury.json",
            "casino": self.root / "casino.json",
            "licenses": self.root / "licenses.json",
            "admins": self.root / "admins.json",
            "logs": self.root / "logs.json",
            "settings": self.root / "settings.json",
        }

    def bootstrap(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.backups.mkdir(parents=True, exist_ok=True)
        defaults: dict[str, Any] = {
            "users": {},
            "transactions": [],
            "checks": {},
            "inventory": {},
            "treasury": {"balance": 0.0, "mayor_id": None, "donations": []},
            "casino": {"games": []},
            "licenses": {},
            "admins": {"owners": [8548608434], "admins": [], "moderators": [], "ids": []},
            "logs": [],
            "settings": {"schema_version": 2, "legacy_migrated": False},
        }
        for name, path in self.files.items():
            if not path.exists():
                self.write(name, defaults[name], backup=False)
        self.ensure_admin_schema()
        self.migrate_legacy_if_needed()

    def ensure_admin_schema(self) -> None:
        admins = self.read("admins")
        changed = False
        for key in ("owners", "admins", "moderators", "ids"):
            if key not in admins or not isinstance(admins[key], list):
                admins[key] = []
                changed = True
        if 8548608434 not in admins["owners"]:
            admins["owners"].append(8548608434)
            changed = True
        if changed:
            self.write("admins", admins)

    def read(self, name: str) -> Any:
        path = self.files[name]
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError):
            return {} if name not in {"transactions", "logs"} else []

    def write(self, name: str, data: Any, backup: bool = True) -> None:
        path = self.files[name]
        if backup and path.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            shutil.copy2(path, self.backups / f"{name}-{stamp}.json")
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        tmp.replace(path)

    def now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_user(self, telegram_id: int) -> JsonDict | None:
        return self.read("users").get(str(telegram_id))

    def upsert_user(self, telegram_id: int, username: str | None, name: str | None) -> JsonDict:
        users = self.read("users")
        key = str(telegram_id)
        user = users.get(key)
        if not user:
            user = {
                "telegram_id": telegram_id,
                "username": username or "",
                "name": name or "Игрок",
                "passport": self.make_passport(telegram_id),
                "balances": {"RUB": self.start_balance, "USD": 0.0, "EUR": 0.0},
                "roles": [],
                "status": {"banned": False, "wanted": False, "alive": True},
                "stats": {
                    "transfers": 0,
                    "received": 0.0,
                    "spent": 0.0,
                    "casino_wins": 0,
                    "casino_losses": 0,
                    "donated": 0.0,
                },
                "created_at": self.now(),
                "last_menu_message_id": None,
            }
        else:
            user["username"] = username or user.get("username", "")
            user["name"] = name or user.get("name", "Игрок")
        users[key] = user
        self.write("users", users)
        self.ensure_user_files(telegram_id)
        return user

    def ensure_user_files(self, telegram_id: int) -> None:
        key = str(telegram_id)
        inventory = self.read("inventory")
        licenses = self.read("licenses")
        inventory.setdefault(key, [])
        licenses.setdefault(key, {})
        self.write("inventory", inventory)
        self.write("licenses", licenses)

    def update_user(self, telegram_id: int, data: JsonDict) -> None:
        users = self.read("users")
        users[str(telegram_id)] = data
        self.write("users", users)

    def find_users(self, query: str) -> list[JsonDict]:
        query_clean = query.strip().lower().removeprefix("@")
        if not query_clean:
            return []
        result = []
        for user in self.read("users").values():
            fields = [
                str(user.get("telegram_id", "")),
                str(user.get("passport", "")),
                str(user.get("username", "")).lower(),
                str(user.get("name", "")).lower(),
            ]
            if any(query_clean in field for field in fields):
                result.append(user)
        return result[:10]

    def transfer(self, sender_id: int, receiver_id: int, amount: float) -> bool:
        users = self.read("users")
        sender = users.get(str(sender_id))
        receiver = users.get(str(receiver_id))
        if not sender or not receiver or amount <= 0:
            return False
        if sender["balances"]["RUB"] < amount:
            return False
        sender["balances"]["RUB"] -= amount
        receiver["balances"]["RUB"] += amount
        sender["stats"]["spent"] += amount
        sender["stats"]["transfers"] += 1
        receiver["stats"]["received"] += amount
        receiver["stats"]["transfers"] += 1
        users[str(sender_id)] = sender
        users[str(receiver_id)] = receiver
        self.write("users", users)
        self.add_transaction("transfer", sender_id, receiver_id, amount, {})
        return True

    def add_transaction(self, kind: str, from_id: int | None, to_id: int | None, amount: float, meta: JsonDict) -> None:
        transactions = self.read("transactions")
        transactions.append({
            "id": len(transactions) + 1,
            "kind": kind,
            "from_id": from_id,
            "to_id": to_id,
            "amount": amount,
            "meta": meta,
            "created_at": self.now(),
        })
        self.write("transactions", transactions)

    def add_log(self, actor_id: int | None, action: str, meta: JsonDict) -> None:
        logs = self.read("logs")
        logs.append({
            "id": len(logs) + 1,
            "actor_id": actor_id,
            "action": action,
            "meta": meta,
            "created_at": self.now(),
        })
        self.write("logs", logs)

    def donate_to_treasury(self, telegram_id: int, amount: float, reason: str) -> bool:
        users = self.read("users")
        user = users.get(str(telegram_id))
        if not user or amount <= 0 or user["balances"]["RUB"] < amount:
            return False
        user["balances"]["RUB"] -= amount
        user["stats"]["spent"] += amount
        user["stats"]["donated"] += amount
        users[str(telegram_id)] = user
        treasury = self.read("treasury")
        treasury["balance"] = float(treasury.get("balance", 0.0)) + amount
        treasury.setdefault("donations", []).append({
            "telegram_id": telegram_id,
            "amount": amount,
            "reason": reason,
            "created_at": self.now(),
        })
        self.write("users", users)
        self.write("treasury", treasury)
        self.add_transaction("treasury", telegram_id, None, amount, {"reason": reason})
        return True

    def issue_license(self, telegram_id: int, license_id: str) -> None:
        licenses = self.read("licenses")
        user_licenses = licenses.setdefault(str(telegram_id), {})
        user_licenses[license_id] = {"active": True, "issued_at": self.now()}
        self.write("licenses", licenses)
        self.add_log(telegram_id, "license_issued", {"license": license_id})

    def has_license(self, telegram_id: int, license_id: str) -> bool:
        user_licenses = self.read("licenses").get(str(telegram_id), {})
        return bool(user_licenses.get(license_id, {}).get("active"))

    def make_passport(self, telegram_id: int) -> str:
        return f"ZB-{str(telegram_id)[-6:].zfill(6)}"

    def migrate_legacy_if_needed(self) -> None:
        settings = self.read("settings")
        users = self.read("users")
        if settings.get("legacy_migrated") or users:
            return
        legacy_path = self.find_legacy_path()
        if not legacy_path:
            return
        with legacy_path.open("r", encoding="utf-8") as file:
            legacy = json.load(file)
        admins = self.read("admins")
        for raw_id, payload in legacy.items():
            telegram_id = int(raw_id)
            roles = payload.get("roles", [])
            stats = payload.get("stats", {})
            users[raw_id] = {
                "telegram_id": telegram_id,
                "username": payload.get("username", ""),
                "name": payload.get("first_name") or payload.get("name") or "Игрок",
                "passport": self.make_passport(telegram_id),
                "balances": {
                    "RUB": float(payload.get("balance", self.start_balance)),
                    "USD": float(payload.get("currencies", {}).get("USD", 0.0)),
                    "EUR": float(payload.get("currencies", {}).get("EUR", 0.0)),
                },
                "roles": roles,
                "status": {"banned": False, "wanted": False, "alive": True},
                "stats": {
                    "transfers": int(stats.get("transactions", 0)),
                    "received": float(stats.get("received", 0.0)),
                    "spent": float(stats.get("spent", 0.0)),
                    "casino_wins": 0,
                    "casino_losses": 0,
                    "donated": 0.0,
                },
                "created_at": self.now(),
                "last_menu_message_id": None,
            }
            if any("админ" in str(role).lower() or "admin" in str(role).lower() for role in roles):
                admins.setdefault("ids", []).append(telegram_id)
        self.write("users", users)
        self.write("admins", admins)
        for raw_id in legacy:
            self.ensure_user_files(int(raw_id))
        settings["legacy_migrated"] = True
        settings["legacy_source"] = str(legacy_path)
        self.write("settings", settings)
        self.add_log(None, "legacy_migrated", {"source": str(legacy_path), "users": len(legacy)})

    def find_legacy_path(self) -> Path | None:
        candidates = [
            self.legacy_data_path,
            Path("data.json"),
            self.root / "data.json",
            Path.home() / "Downloads" / "data.json",
        ]
        for candidate in candidates:
            if candidate and candidate.exists():
                return candidate
        return None
