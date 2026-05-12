"""Infraestructura: Inicialización de base de datos y dependencias."""

from pathlib import Path

from src.infrastructure.db.sqlite_repositories import (
    SQLiteBattleRepository,
    SQLitePlayerRepository,
)


def get_db_path() -> str:
    """Retorna la ruta absoluta a la base de datos SQLite."""
    return str(Path(__file__).parent.parent.parent.parent / "spiritual_battle.db")


def create_repositories(db_path: str | None = None):
    """Factory para crear repositorios con la misma DB path."""
    if db_path is None:
        db_path = get_db_path()
    
    player_repo = SQLitePlayerRepository(db_path)
    battle_repo = SQLiteBattleRepository(db_path, player_repo)
    
    return player_repo, battle_repo
