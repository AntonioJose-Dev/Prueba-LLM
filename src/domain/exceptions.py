"""
Dominio: Excepciones específicas del dominio.
"""


class DomainError(Exception):
    """Excepción base para errores del dominio."""

    pass


class PlayerNotFoundError(DomainError):
    """El jugador especificado no existe."""

    def __init__(self, player_id: str):
        super().__init__(f"Player not found: {player_id}")
        self.player_id = player_id


class PlayerAlreadyExistsError(DomainError):
    """El jugador ya está registrado."""

    def __init__(self, telegram_id: int):
        super().__init__(f"Player already exists with telegram_id: {telegram_id}")
        self.telegram_id = telegram_id


class BattleNotFoundError(DomainError):
    """La batalla especificada no existe."""

    def __init__(self, battle_id: str):
        super().__init__(f"Battle not found: {battle_id}")
        self.battle_id = battle_id


class BattleAlreadyExistsError(DomainError):
    """Ya existe una batalla activa para este jugador."""

    def __init__(self, player_id: str):
        super().__init__(f"Player already in an active battle: {player_id}")
        self.player_id = player_id


class BattleInvalidStateError(DomainError):
    """La batalla no está en el estado esperado para la operación."""

    def __init__(self, battle_id: str, expected_state: str, actual_state: str):
        super().__init__(
            f"Battle {battle_id} is in state {actual_state}, expected {expected_state}"
        )
        self.battle_id = battle_id
        self.expected_state = expected_state
        self.actual_state = actual_state


class BattleInvalidActionError(DomainError):
    """La acción solicitada no es válida en el contexto actual."""

    def __init__(self, player_id: str, reason: str):
        super().__init__(f"Invalid action for player {player_id}: {reason}")
        self.player_id = player_id
        self.reason = reason
