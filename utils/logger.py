from __future__ import annotations

from typing import Any

from utils.database import Database


def log_action(database: Database, actor_id: int | None, action: str, **meta: Any) -> None:
    database.add_log(actor_id, action, meta)
