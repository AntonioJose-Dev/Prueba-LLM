"""
Dominio: Interfaces de repositorios (contratos).
Definen qué métodos deben implementar los repositorios de infraestructura.
Sin implementación concreta aquí.
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.models import Battle, Player


class PlayerRepository(ABC):
    """Contrato para persistencia de jugadores."""

    @abstractmethod
    def get_by_id(self, player_id: str) -> Optional[Player]:
        """Obtiene un jugador por su ID interno."""
        pass

    @abstractmethod
    def get_by_telegram_id(self, telegram_id: int) -> Optional[Player]:
        """Obtiene un jugador por su ID de Telegram."""
        pass

    @abstractmethod
    def save(self, player: Player) -> None:
        """Crea o actualiza un jugador."""
        pass

    @abstractmethod
    def get_all(self) -> list[Player]:
        """Retorna todos los jugadores."""
        pass

    @abstractmethod
    def get_ranking(self, limit: int = 10) -> list[Player]:
        """Retorna top jugadores ordenados por ranking score."""
        pass


class BattleRepository(ABC):
    """Contrato para persistencia de batallas."""

    @abstractmethod
    def get_by_id(self, battle_id: str) -> Optional[Battle]:
        """Obtiene una batalla por su ID."""
        pass

    @abstractmethod
    def save(self, battle: Battle) -> None:
        """Crea o actualiza una batalla."""
        pass

    @abstractmethod
    def get_active_battle_for_player(self, player_id: str) -> Optional[Battle]:
        """Busca batalla activa donde participe el jugador."""
        pass
