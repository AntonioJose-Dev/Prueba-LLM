"""
Infraestructura: Implementación SQLite de repositorios.
Sin lógica de negocio. Solo persistencia.
"""

import sqlite3
from pathlib import Path
from typing import Optional

from src.domain.models import Battle, BattleResult, BattleStatus, Player
from src.domain.repositories import BattleRepository, PlayerRepository


class SQLitePlayerRepository(PlayerRepository):
    """Implementación SQLite para persistencia de jugadores."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Inicializa la tabla de jugadores."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                id TEXT PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT NOT NULL,
                created_at TEXT NOT NULL,
                victories INTEGER DEFAULT 0,
                defeats INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                current_hp INTEGER DEFAULT 100,
                max_hp INTEGER DEFAULT 100,
                attack_power INTEGER DEFAULT 15,
                defense_power INTEGER DEFAULT 10,
                special_charge INTEGER DEFAULT 0,
                max_special_charge INTEGER DEFAULT 3,
                is_defending INTEGER DEFAULT 0
            )
            """
        )
        conn.commit()
        conn.close()

    def _player_to_row(self, player: Player) -> tuple:
        """Convierte entidad Player a tupla para SQLite."""
        return (
            player.id,
            player.telegram_id,
            player.username,
            player.created_at.isoformat(),
            player.victories,
            player.defeats,
            player.draws,
            player.current_hp,
            player.max_hp,
            player.attack_power,
            player.defense_power,
            player.special_charge,
            player.max_special_charge,
            1 if player.is_defending else 0,
        )

    def _row_to_player(self, row: tuple) -> Player:
        """Convierte fila de SQLite a entidad Player."""
        return Player(
            id=row[0],
            telegram_id=row[1],
            username=row[2],
            created_at=__import__("datetime").datetime.fromisoformat(row[3]),
            victories=row[4],
            defeats=row[5],
            draws=row[6],
            current_hp=row[7],
            max_hp=row[8],
            attack_power=row[9],
            defense_power=row[10],
            special_charge=row[11],
            max_special_charge=row[12],
            is_defending=bool(row[13]),
        )

    def get_by_id(self, player_id: str) -> Optional[Player]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        row = cursor.fetchone()
        conn.close()
        return self._row_to_player(row) if row else None

    def get_by_telegram_id(self, telegram_id: int) -> Optional[Player]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM players WHERE telegram_id = ?", (telegram_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return self._row_to_player(row) if row else None

    def save(self, player: Player) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO players 
            (id, telegram_id, username, created_at, victories, defeats, draws,
             current_hp, max_hp, attack_power, defense_power, special_charge,
             max_special_charge, is_defending)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._player_to_row(player),
        )
        conn.commit()
        conn.close()

    def get_all(self) -> list[Player]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players")
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_player(row) for row in rows]

    def get_ranking(self, limit: int = 10) -> list[Player]:
        """Ordena por victorias - derrotas DESC."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM players 
            ORDER BY (victories - defeats) DESC, victories DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_player(row) for row in rows]


class SQLiteBattleRepository(BattleRepository):
    """Implementación SQLite para persistencia de batallas."""

    def __init__(self, db_path: str, player_repository: Optional[SQLitePlayerRepository] = None):
        self.db_path = db_path
        self.player_repository = player_repository
        self._init_db()

    def _init_db(self) -> None:
        """Inicializa la tabla de batallas."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS battles (
                id TEXT PRIMARY KEY,
                player1_id TEXT NOT NULL,
                player2_id TEXT NOT NULL,
                status TEXT NOT NULL,
                current_turn INTEGER DEFAULT 0,
                turn_order TEXT,
                results TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()

    def _battle_to_row(self, battle: Battle) -> tuple:
        """Convierte entidad Battle a tupla para SQLite."""
        import json

        return (
            battle.id,
            battle.player1_id,
            battle.player2_id,
            battle.status.value,
            battle.current_turn,
            json.dumps(battle.turn_order),
            json.dumps(
                {k: v.value for k, v in battle.results.items()}
                if battle.results
                else {}
            ),
            __import__("datetime").datetime.utcnow().isoformat(),
        )

    def _row_to_battle(self, row: tuple) -> Battle:
        """Convierte fila de SQLite a entidad Battle."""
        import json

        battle = Battle(
            id=row[0],
            player1_id=row[1],
            player2_id=row[2],
            status=BattleStatus(row[3]),
            current_turn=row[4],
            turn_order=json.loads(row[5]) if row[5] else [],
            results={
                k: BattleResult(v) for k, v in json.loads(row[6]).items()
            }
            if row[6]
            else {},
        )
        
        # Cargar jugadores si el repositorio está disponible
        if self.player_repository:
            battle.player1 = self.player_repository.get_by_id(battle.player1_id)
            battle.player2 = self.player_repository.get_by_id(battle.player2_id)
        
        return battle

    def get_by_id(self, battle_id: str) -> Optional[Battle]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM battles WHERE id = ?", (battle_id,))
        row = cursor.fetchone()
        conn.close()
        return self._row_to_battle(row) if row else None

    def save(self, battle: Battle) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO battles 
            (id, player1_id, player2_id, status, current_turn, turn_order, results, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._battle_to_row(battle),
        )
        conn.commit()
        conn.close()

    def get_active_battle_for_player(self, player_id: str) -> Optional[Battle]:
        """Busca batalla IN_PROGRESS o PENDING donde participe el jugador."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM battles 
            WHERE (player1_id = ? OR player2_id = ?)
            AND status IN (?, ?)
            """,
            (player_id, player_id, BattleStatus.PENDING.value, BattleStatus.IN_PROGRESS.value),
        )
        row = cursor.fetchone()
        conn.close()
        return self._row_to_battle(row) if row else None
