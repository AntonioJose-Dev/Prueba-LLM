"""
Dominio: Exporta todas las entidades y contratos del dominio.
"""

from src.domain.exceptions import (
    BattleAlreadyExistsError,
    BattleInvalidActionError,
    BattleInvalidStateError,
    BattleNotFoundError,
    DomainError,
    PlayerAlreadyExistsError,
    PlayerNotFoundError,
)
from src.domain.models import (
    ActionType,
    Battle,
    BattleAction,
    BattleResult,
    BattleStatus,
    Player,
    TurnResult,
)
from src.domain.repositories import BattleRepository, PlayerRepository

__all__ = [
    # Modelos
    "Player",
    "Battle",
    "BattleAction",
    "TurnResult",
    "ActionType",
    "BattleStatus",
    "BattleResult",
    # Excepciones
    "DomainError",
    "PlayerNotFoundError",
    "PlayerAlreadyExistsError",
    "BattleNotFoundError",
    "BattleAlreadyExistsError",
    "BattleInvalidStateError",
    "BattleInvalidActionError",
    # Repositorios (contratos)
    "PlayerRepository",
    "BattleRepository",
]
