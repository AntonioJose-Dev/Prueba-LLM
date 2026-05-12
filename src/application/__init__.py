"""
Aplicación: Exporta todos los casos de uso.
"""

from src.application.battle_use_cases import (
    BattleActionRequest,
    CreateBattle,
    CreateBattleResult,
    ExecuteBattleTurn,
    ExecuteTurnResult,
    FleeBattle,
    GetBattle,
    StartBattle,
)
from src.application.player_use_cases import (
    GetPlayer,
    GetPlayerResult,
    GetRanking,
    RegisterPlayer,
    RegisterPlayerResult,
    UpdatePlayerStats,
)

__all__ = [
    # Jugadores
    "RegisterPlayer",
    "RegisterPlayerResult",
    "GetPlayer",
    "GetPlayerResult",
    "GetRanking",
    "UpdatePlayerStats",
    # Batallas
    "CreateBattle",
    "CreateBattleResult",
    "StartBattle",
    "ExecuteBattleTurn",
    "ExecuteTurnResult",
    "FleeBattle",
    "GetBattle",
    "BattleActionRequest",
]
