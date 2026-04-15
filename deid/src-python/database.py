from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class DatabaseManager:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS name_pool (
                name  TEXT NOT NULL,
                theme TEXT NOT NULL DEFAULT 'default',
                PRIMARY KEY (name, theme)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS config (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reversible_mapping (
                seed          TEXT NOT NULL,
                entity_type   TEXT NOT NULL,
                original_value TEXT NOT NULL,
                mapped_value  TEXT NOT NULL,
                created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (seed, entity_type, mapped_value)
            )
            """
        )
        self.connection.commit()

    def seed_if_empty(
        self, config_values: dict[str, Any], initial_name_pool: dict[str, list[str]]
    ) -> None:
        cursor = self.connection.cursor()
        config_count = cursor.execute("SELECT COUNT(*) AS c FROM config").fetchone()["c"]
        pool_count = cursor.execute("SELECT COUNT(*) AS c FROM name_pool").fetchone()["c"]
        if config_count > 0 or pool_count > 0:
            return

        cursor.executemany(
            "INSERT INTO config (key, value) VALUES (?, ?)",
            [(key, json.dumps(value)) for key, value in config_values.items()],
        )

        rows: list[tuple[str, str]] = []
        for theme, names in initial_name_pool.items():
            for name in names:
                rows.append((name, theme))
        cursor.executemany("INSERT INTO name_pool (name, theme) VALUES (?, ?)", rows)
        self.connection.commit()

    def get_config(self) -> dict[str, Any]:
        cursor = self.connection.cursor()
        rows = cursor.execute("SELECT key, value FROM config").fetchall()
        config: dict[str, Any] = {}
        for row in rows:
            config[row["key"]] = json.loads(row["value"])
        return config

    def update_config(self, key: str, value: Any) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO config (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, json.dumps(value)),
        )
        self.connection.commit()

    def list_themes(self) -> list[str]:
        cursor = self.connection.cursor()
        rows = cursor.execute("SELECT DISTINCT theme FROM name_pool ORDER BY theme ASC")
        return [row["theme"] for row in rows]

    def theme_exists(self, theme: str) -> bool:
        cursor = self.connection.cursor()
        row = cursor.execute(
            "SELECT 1 FROM name_pool WHERE theme = ? LIMIT 1", (theme,)
        ).fetchone()
        return row is not None

    def get_name_pool(self, theme: str) -> list[str]:
        cursor = self.connection.cursor()
        rows = cursor.execute(
            "SELECT name FROM name_pool WHERE theme = ? ORDER BY name ASC", (theme,)
        ).fetchall()
        return [row["name"] for row in rows]

    def replace_theme_pool(self, theme: str, names: list[str]) -> None:
        cleaned_names = list(dict.fromkeys(name.strip() for name in names if name and name.strip()))
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM name_pool WHERE theme = ?", (theme,))
        if cleaned_names:
            cursor.executemany(
                "INSERT INTO name_pool (name, theme) VALUES (?, ?)",
                [(name, theme) for name in cleaned_names],
            )
        self.connection.commit()

    def ensure_theme_pool(self, theme: str, names: list[str]) -> None:
        if self.theme_exists(theme):
            return
        cleaned_names = list(dict.fromkeys(name.strip() for name in names if name and name.strip()))
        if not cleaned_names:
            return
        cursor = self.connection.cursor()
        cursor.executemany(
            "INSERT INTO name_pool (name, theme) VALUES (?, ?)",
            [(name, theme) for name in cleaned_names],
        )
        self.connection.commit()

    def replace_config_all(self, config_values: dict[str, Any]) -> None:
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM config")
        cursor.executemany(
            "INSERT INTO config (key, value) VALUES (?, ?)",
            [(key, json.dumps(value)) for key, value in config_values.items()],
        )
        self.connection.commit()

    def upsert_reversible_mappings(
        self, seed: str, rows: list[tuple[str, str, str]]
    ) -> None:
        if not rows:
            return
        cursor = self.connection.cursor()
        cursor.executemany(
            """
            INSERT OR IGNORE INTO reversible_mapping (seed, entity_type, original_value, mapped_value)
            VALUES (?, ?, ?, ?)
            """,
            [(seed, entity_type, original_value, mapped_value) for entity_type, original_value, mapped_value in rows],
        )
        self.connection.commit()

    def list_reversible_mappings(
        self, seed: str, entity_types: list[str] | None = None
    ) -> list[dict[str, str]]:
        cursor = self.connection.cursor()
        if entity_types:
            placeholders = ",".join("?" for _ in entity_types)
            query = (
                "SELECT entity_type, original_value, mapped_value FROM reversible_mapping "
                f"WHERE seed = ? AND entity_type IN ({placeholders}) "
                "ORDER BY LENGTH(mapped_value) DESC, mapped_value DESC"
            )
            params: tuple[Any, ...] = (seed, *entity_types)
            result = cursor.execute(query, params)
        else:
            result = cursor.execute(
                """
                SELECT entity_type, original_value, mapped_value
                FROM reversible_mapping
                WHERE seed = ?
                ORDER BY LENGTH(mapped_value) DESC, mapped_value DESC
                """,
                (seed,),
            )
        return [
            {
                "entity_type": str(row["entity_type"]),
                "original_value": str(row["original_value"]),
                "mapped_value": str(row["mapped_value"]),
            }
            for row in result.fetchall()
        ]

    def clear_reversible_mappings(self) -> None:
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM reversible_mapping")
        self.connection.commit()

    def purge_reversible_mappings_older_than(self, days: int) -> int:
        cursor = self.connection.cursor()
        row = cursor.execute(
            """
            SELECT COUNT(*) AS c
            FROM reversible_mapping
            WHERE datetime(created_at) < datetime('now', ?)
            """,
            (f"-{int(days)} days",),
        ).fetchone()
        delete_count = int(row["c"]) if row is not None else 0
        cursor.execute(
            """
            DELETE FROM reversible_mapping
            WHERE datetime(created_at) < datetime('now', ?)
            """,
            (f"-{int(days)} days",),
        )
        self.connection.commit()
        return delete_count

    def replace_all_theme_pools(self, themed_names: dict[str, list[str]]) -> None:
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM name_pool")
        rows: list[tuple[str, str]] = []
        for theme, names in themed_names.items():
            for name in names:
                cleaned = str(name).strip()
                if cleaned:
                    rows.append((cleaned, str(theme)))
        if rows:
            cursor.executemany("INSERT INTO name_pool (name, theme) VALUES (?, ?)", rows)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
