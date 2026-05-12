"""
Aplicación: Casos de uso para gestión de jugadores.
Orquestan lógica de negocio usando entidades del dominio.
"""

from dataclasses import dataclass
from typing import Optional

from src.domain import (
    BattleAlreadyExistsError,
    Player,
    PlayerAlreadyExistsError,
    PlayerNotFoundError,
    PlayerRepository,
)


@dataclass
class RegisterPlayerResult:
    """Resultado del caso de uso de registro."""

    success: bool
    player: Optional[Player] = None
    error: Optional[str] = None


@dataclass
class GetPlayerResult:
    """Resultado del caso de uso de obtención de jugador."""

    found: bool
    player: Optional[Player] = None


class RegisterPlayer:
    """Caso de uso: Registra un nuevo jugador."""

    def __init__(self, player_repository: PlayerRepository):
        self.player_repository = player_repository

    def execute(
        self, telegram_id: int, username: str
    ) -> RegisterPlayerResult:
        """
        Registra un jugador si no existe.
        Si ya existe, retorna el jugador existente.
        """
        # Verificar si ya existe por telegram_id
        existing = self.player_repository.get_by_telegram_id(telegram_id)
        if existing:
            return RegisterPlayerResult(
                success=True,
                player=existing,
                error=None,
            )

        # Crear nuevo jugador
        player = Player(telegram_id=telegram_id, username=username)
        self.player_repository.save(player)

        return RegisterPlayerResult(success=True, player=player, error=None)


class GetPlayer:
    """Caso de uso: Obtiene un jugador por ID o Telegram ID."""

    def __init__(self, player_repository: PlayerRepository):
        self.player_repository = player_repository

    def by_id(self, player_id: str) -> GetPlayerResult:
        """Obtiene jugador por ID interno."""
        player = self.player_repository.get_by_id(player_id)
        if not player:
            return GetPlayerResult(found=False, player=None)
        return GetPlayerResult(found=True, player=player)

    def by_telegram_id(self, telegram_id: int) -> GetPlayerResult:
        """Obtiene jugador por Telegram ID."""
        player = self.player_repository.get_by_telegram_id(telegram_id)
        if not player:
            return GetPlayerResult(found=False, player=None)
        return GetPlayerResult(found=True, player=player)


class GetRanking:
    """Caso de uso: Obtiene ranking de jugadores."""

    def __init__(self, player_repository: PlayerRepository):
        self.player_repository = player_repository

    def execute(self, limit: int = 10) -> list[Player]:
        """Retorna top jugadores ordenados por ranking score."""
        return self.player_repository.get_ranking(limit=limit)


class UpdatePlayerStats:
    """Caso de uso: Actualiza estadísticas de jugador (persiste cambios)."""

    def __init__(self, player_repository: PlayerRepository):
        self.player_repository = player_repository

    def execute(self, player: Player) -> None:
        """Persiste los cambios en las estadísticas del jugador."""
        self.player_repository.save(player)
