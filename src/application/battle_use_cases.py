"""
Aplicación: Casos de uso para gestión de batallas.
Orquestan lógica de negocio usando entidades del dominio.
"""

from dataclasses import dataclass
from typing import Optional

from src.domain import (
    Battle,
    BattleAction,
    BattleAlreadyExistsError,
    BattleInvalidActionError,
    BattleInvalidStateError,
    BattleNotFoundError,
    BattleRepository,
    BattleStatus,
    Player,
    PlayerRepository,
    TurnResult,
)


@dataclass
class CreateBattleResult:
    """Resultado del caso de uso de creación de batalla."""

    success: bool
    battle: Optional[Battle] = None
    error: Optional[str] = None


@dataclass
class BattleActionRequest:
    """Solicitud de acción en batalla."""

    battle_id: str
    player_id: str
    action_type: str  # "attack", "defend", "special", "flee"


@dataclass
class ExecuteTurnResult:
    """Resultado de ejecución de turno."""

    success: bool
    turn_result: Optional[TurnResult] = None
    error: Optional[str] = None


class CreateBattle:
    """Caso de uso: Crea una batalla PvP entre dos jugadores."""

    def __init__(
        self,
        battle_repository: BattleRepository,
        player_repository: PlayerRepository,
    ):
        self.battle_repository = battle_repository
        self.player_repository = player_repository

    def execute(
        self, challenger_id: str, opponent_id: str
    ) -> CreateBattleResult:
        """
        Crea una nueva batalla entre dos jugadores.
        Valida que ambos existan y no estén ya en batalla activa.
        """
        # Validar que los jugadores existen
        challenger = self.player_repository.get_by_id(challenger_id)
        if not challenger:
            return CreateBattleResult(
                success=False,
                battle=None,
                error=f"Challenger not found: {challenger_id}",
            )

        opponent = self.player_repository.get_by_id(opponent_id)
        if not opponent:
            return CreateBattleResult(
                success=False,
                battle=None,
                error=f"Opponent not found: {opponent_id}",
            )

        # Validar que no estén ya en batalla activa
        existing_challenger = self.battle_repository.get_active_battle_for_player(
            challenger_id
        )
        if existing_challenger:
            return CreateBattleResult(
                success=False,
                battle=None,
                error=f"Challenger already in active battle: {existing_challenger.id}",
            )

        existing_opponent = self.battle_repository.get_active_battle_for_player(
            opponent_id
        )
        if existing_opponent:
            return CreateBattleResult(
                success=False,
                battle=None,
                error=f"Opponent already in active battle: {existing_opponent.id}",
            )

        # Crear batalla
        battle = Battle(
            player1_id=challenger_id,
            player2_id=opponent_id,
            player1=challenger,
            player2=opponent,
        )

        self.battle_repository.save(battle)

        return CreateBattleResult(success=True, battle=battle, error=None)


class StartBattle:
    """Caso de uso: Inicia una batalla pendiente."""

    def __init__(self, battle_repository: BattleRepository):
        self.battle_repository = battle_repository

    def execute(self, battle_id: str) -> ExecuteTurnResult:
        """Inicia la batalla y prepara el primer turno."""
        battle = self.battle_repository.get_by_id(battle_id)
        if not battle:
            return ExecuteTurnResult(
                success=False,
                turn_result=None,
                error=f"Battle not found: {battle_id}",
            )

        try:
            battle.start()
            self.battle_repository.save(battle)
            return ExecuteTurnResult(
                success=True,
                turn_result=None,
                error=None,
            )
        except ValueError as e:
            return ExecuteTurnResult(
                success=False,
                turn_result=None,
                error=str(e),
            )


class ExecuteBattleTurn:
    """Caso de uso: Ejecuta un turno de batalla con las acciones de los jugadores."""

    def __init__(
        self,
        battle_repository: BattleRepository,
        player_repository: PlayerRepository,
    ):
        self.battle_repository = battle_repository
        self.player_repository = player_repository

    def execute(
        self, battle_id: str, actions: list[BattleAction]
    ) -> ExecuteTurnResult:
        """
        Ejecuta un turno con las acciones proporcionadas.
        Persiste los cambios en jugadores y batalla.
        """
        battle = self.battle_repository.get_by_id(battle_id)
        if not battle:
            return ExecuteTurnResult(
                success=False,
                turn_result=None,
                error=f"Battle not found: {battle_id}",
            )

        if battle.status != BattleStatus.IN_PROGRESS:
            return ExecuteTurnResult(
                success=False,
                turn_result=None,
                error=f"Battle is not in progress (status: {battle.status.value})",
            )

        # Validar que las acciones sean válidas
        validation_error = self._validate_actions(battle, actions)
        if validation_error:
            return ExecuteTurnResult(
                success=False,
                turn_result=None,
                error=validation_error,
            )

        # Ejecutar turno
        turn_result = battle.execute_turn(actions)

        # Persistir cambios en jugadores
        for player in battle.participants:
            self.player_repository.save(player)

        # Persistir batalla (especialmente si terminó)
        self.battle_repository.save(battle)

        return ExecuteTurnResult(
            success=True,
            turn_result=turn_result,
            error=None,
        )

    def _validate_actions(
        self, battle: Battle, actions: list[BattleAction]
    ) -> Optional[str]:
        """Valida que las acciones sean válidas para el estado actual."""
        player_ids_in_action = set()

        for action in actions:
            # Verificar que el jugador está en la batalla
            player = battle.get_player_by_id(action.player_id)
            if not player:
                return f"Player {action.player_id} is not in this battle"

            # Verificar que el jugador está vivo
            if not player.is_alive():
                return f"Player {action.player_id} is not alive"

            # Verificar que no haya acciones duplicadas
            if action.player_id in player_ids_in_action:
                return f"Multiple actions for player {action.player_id}"
            player_ids_in_action.add(action.player_id)

            # Validaciones específicas por tipo de acción
            if action.action_type.value == "special":
                if player.special_charge < 1:
                    return f"Player {player.username} doesn't have special charge"

        return None


class FleeBattle:
    """Caso de uso: Un jugador huye de la batalla."""

    def __init__(
        self,
        battle_repository: BattleRepository,
        player_repository: PlayerRepository,
    ):
        self.battle_repository = battle_repository
        self.player_repository = player_repository

    def execute(self, battle_id: str, player_id: str) -> ExecuteTurnResult:
        """Un jugador huye de la batalla, perdiendo automáticamente."""
        battle = self.battle_repository.get_by_id(battle_id)
        if not battle:
            return ExecuteTurnResult(
                success=False,
                turn_result=None,
                error=f"Battle not found: {battle_id}",
            )

        if battle.status != BattleStatus.IN_PROGRESS:
            return ExecuteTurnResult(
                success=False,
                turn_result=None,
                error=f"Battle is not in progress (status: {battle.status.value})",
            )

        player = battle.get_player_by_id(player_id)
        if not player:
            return ExecuteTurnResult(
                success=False,
                turn_result=None,
                error=f"Player {player_id} is not in this battle",
            )

        turn_result = battle.player_flees(player_id)

        # Persistir cambios
        for p in battle.participants:
            self.player_repository.save(p)
        self.battle_repository.save(battle)

        return ExecuteTurnResult(
            success=True,
            turn_result=turn_result,
            error=None,
        )


class GetBattle:
    """Caso de uso: Obtiene información de una batalla."""

    def __init__(self, battle_repository: BattleRepository):
        self.battle_repository = battle_repository

    def by_id(self, battle_id: str) -> Optional[Battle]:
        """Obtiene una batalla por ID."""
        return self.battle_repository.get_by_id(battle_id)

    def active_for_player(self, player_id: str) -> Optional[Battle]:
        """Obtiene la batalla activa de un jugador."""
        return self.battle_repository.get_active_battle_for_player(player_id)
