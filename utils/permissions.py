from __future__ import annotations

from aiogram.types import Message, User

from config import Config
from utils.database import Database


SYSTEM_OWNER_IDS = {8548608434}


def is_staff_group(message: Message, config: Config) -> bool:
    return config.staff_group_id != 0 and message.chat.id == config.staff_group_id


def is_owner(user: User | None, database: Database) -> bool:
    if not user:
        return False
    admins = database.read("admins")
    return user.id in SYSTEM_OWNER_IDS or user.id in admins.get("owners", [])


def is_staff_member(user: User | None, database: Database) -> bool:
    if not user:
        return False
    admins = database.read("admins")
    profile = database.get_user(user.id)
    roles = [str(role).lower() for role in profile.get("roles", [])] if profile else []
    role_ids = set(admins.get("owners", [])) | set(admins.get("admins", [])) | set(admins.get("moderators", [])) | set(admins.get("ids", []))
    role_words = ("владел", "owner", "админ", "admin", "модер", "moderator")
    return user.id in SYSTEM_OWNER_IDS or user.id in role_ids or any(any(word in role for word in role_words) for role in roles)


def is_admin(user: User | None, database: Database) -> bool:
    if not user:
        return False
    admins = database.read("admins")
    profile = database.get_user(user.id)
    roles = profile.get("roles", []) if profile else []
    admin_ids = set(admins.get("owners", [])) | set(admins.get("admins", [])) | set(admins.get("ids", []))
    return user.id in SYSTEM_OWNER_IDS or user.id in admin_ids or any("админ" in str(role).lower() or "admin" in str(role).lower() for role in roles)
