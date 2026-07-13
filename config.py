from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Config:
    token: str
    staff_group_id: int
    database_dir: Path
    legacy_data_path: Path | None
    start_balance: float = 1000.0
    license_prices: dict[str, float] | None = None

    @classmethod
    def from_env(cls) -> "Config":
        token = os.getenv("BOT_TOKEN", "").strip()
        staff_group_id = int(os.getenv("STAFF_GROUP_ID", "0"))
        database_dir = Path(os.getenv("DATABASE_DIR", "database"))
        legacy_env = os.getenv("LEGACY_DATA_PATH", "").strip()
        legacy_path = Path(legacy_env) if legacy_env else None
        return cls(
            token=token,
            staff_group_id=staff_group_id,
            database_dir=database_dir,
            legacy_data_path=legacy_path,
            license_prices={
                "car": 5000.0,
                "truck": 7500.0,
                "motorcycle": 3500.0,
                "weapon": 15000.0,
                "fishing": 2500.0,
                "hunting": 8000.0,
            },
        )


config = Config.from_env()
