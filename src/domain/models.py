"""
Dominio: Entidades y reglas de negocio del bot de combate espiritual.
Sin dependencias externas. Sin lógica de infraestructura.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


class ActionType(Enum):
    """Acciones disponibles en combate."""
    ATTACK = "attack"
    DEFEND = "defend"
    SPECIAL = "special"
    FLEE = "flee"


class BattleStatus(Enum):
    """Estados posibles de una batalla."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class BattleResult(Enum):
    """Resultado final para un participante."""
    VICTORY = "victory"
    DEFEAT = "defeat"
    FLED = "fled"
    DRAW = "draw"


@dataclass
class Player:
    """Entidad raíz: Jugador con perfil y estadísticas."""
    telegram_id: int
    username: str
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Estadísticas de combate
    victories: int = 0
    defeats: int = 0
    draws: int = 0
    
    # Estado actual
    current_hp: int = 100
    max_hp: int = 100
    attack_power: int = 15
    defense_power: int = 10
    special_charge: int = 0
    max_special_charge: int = 3
    is_defending: bool = False
    
    @property
    def total_matches(self) -> int:
        return self.victories + self.defeats + self.draws
    
    @property
    def win_rate(self) -> float:
        if self.total_matches == 0:
            return 0.0
        return (self.victories / self.total_matches) * 100
    
    @property
    def ranking_score(self) -> int:
        """Puntuación para ranking: victorias - derrotas."""
        return self.victories - self.defeats
    
    def is_alive(self) -> bool:
        return self.current_hp > 0
    
    def take_damage(self, amount: int) -> int:
        """Aplica daño y retorna el daño real recibido."""
        actual_damage = max(0, amount - (self.defense_power if self.is_defending else 0))
        self.current_hp = max(0, self.current_hp - actual_damage)
        return actual_damage
    
    def heal(self, amount: int) -> int:
        """Cura HP y retorna la cantidad real curada."""
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp - old_hp
    
    def charge_special(self) -> None:
        """Incrementa la carga de habilidad especial."""
        self.special_charge = min(self.max_special_charge, self.special_charge + 1)
    
    def use_special(self) -> bool:
        """Intenta usar habilidad especial. Retorna True si fue exitoso."""
        if self.special_charge >= 1:
            self.special_charge -= 1
            return True
        return False
    
    def reset_turn_state(self) -> None:
        """Reseta estados temporales al inicio de cada turno."""
        self.is_defending = False
    
    def record_victory(self) -> None:
        self.victories += 1
    
    def record_defeat(self) -> None:
        self.defeats += 1
    
    def record_draw(self) -> None:
        self.draws += 1


@dataclass
class BattleAction:
    """Acción ejecutada por un jugador en un turno."""
    player_id: str
    action_type: ActionType
    target_player_id: Optional[str] = None


@dataclass
class TurnResult:
    """Resultado de un turno de batalla."""
    turn_number: int
    actions: list[BattleAction]
    damage_dealt: dict[str, int]  # player_id -> damage
    messages: list[str]
    battle_ended: bool = False
    winner_id: Optional[str] = None


@dataclass
class Battle:
    """Entidad raíz: Batalla PvP entre jugadores."""
    id: str = field(default_factory=lambda: str(uuid4()))
    player1_id: str = ""
    player2_id: str = ""
    status: BattleStatus = BattleStatus.PENDING
    current_turn: int = 0
    turn_order: list[str] = field(default_factory=list)
    results: dict[str, BattleResult] = field(default_factory=dict)
    
    # Referencias a jugadores (se llenan desde aplicación)
    player1: Optional[Player] = None
    player2: Optional[Player] = None
    
    @property
    def participants(self) -> list[Player]:
        """Retorna lista de jugadores participantes."""
        participants = []
        if self.player1:
            participants.append(self.player1)
        if self.player2:
            participants.append(self.player2)
        return participants
    
    @property
    def opponent_ids(self) -> dict[str, str]:
        """Mapea player_id a opponent_id."""
        return {
            self.player1_id: self.player2_id,
            self.player2_id: self.player1_id,
        }
    
    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        if self.player1 and self.player1.id == player_id:
            return self.player1
        if self.player2 and self.player2.id == player_id:
            return self.player2
        return None
    
    def get_opponent(self, player_id: str) -> Optional[Player]:
        opponent_id = self.opponent_ids.get(player_id)
        if not opponent_id:
            return None
        return self.get_player_by_id(opponent_id)
    
    def start(self) -> None:
        """Inicia la batalla y determina orden de turnos."""
        if self.status != BattleStatus.PENDING:
            raise ValueError("Battle already started")
        
        if not self.player1 or not self.player2:
            raise ValueError("Missing players")
        
        self.status = BattleStatus.IN_PROGRESS
        self.current_turn = 1
        
        # Orden aleatorio simple basado en IDs (determinístico para testing)
        ids = [self.player1_id, self.player2_id]
        self.turn_order = sorted(ids)
        
        self.player1.reset_turn_state()
        self.player2.reset_turn_state()
    
    def execute_turn(self, actions: list[BattleAction]) -> TurnResult:
        """Ejecuta un turno con las acciones de los jugadores."""
        if self.status != BattleStatus.IN_PROGRESS:
            raise ValueError("Battle is not in progress")
        
        messages = []
        damage_dealt: dict[str, int] = {}
        
        # Procesar cada acción (el estado defensivo persiste durante este loop)
        for action in actions:
            attacker = self.get_player_by_id(action.player_id)
            if not attacker:
                continue
            
            defender = None
            if action.target_player_id:
                defender = self.get_player_by_id(action.target_player_id)
            
            result = self._execute_action(attacker, defender, action.action_type)
            if result["message"]:
                messages.append(result["message"])
            if result["damage"] > 0 and result["target_id"]:
                damage_dealt[result["target_id"]] = damage_dealt.get(result["target_id"], 0) + result["damage"]
        
        # Verificar si la batalla terminó
        battle_ended = False
        winner_id = None
        
        if self.player1 and not self.player1.is_alive():
            battle_ended = True
            winner_id = self.player2_id if self.player2 and self.player2.is_alive() else None
        elif self.player2 and not self.player2.is_alive():
            battle_ended = True
            winner_id = self.player1_id if self.player1 and self.player1.is_alive() else None
        
        # Resetear estados para próximo turno (solo si no terminó)
        if not battle_ended:
            for player in self.participants:
                player.reset_turn_state()
            self.current_turn += 1
        
        # Determinar resultado final si terminó
        if battle_ended:
            self._resolve_results(winner_id)
        
        return TurnResult(
            turn_number=self.current_turn,
            actions=actions,
            damage_dealt=damage_dealt,
            messages=messages,
            battle_ended=battle_ended,
            winner_id=winner_id,
        )
    
    def _execute_action(
        self,
        attacker: Player,
        defender: Optional[Player],
        action_type: ActionType,
    ) -> dict:
        """Ejecuta una acción y retorna resultado."""
        result = {"message": "", "damage": 0, "target_id": None}
        
        if action_type == ActionType.ATTACK:
            if not defender:
                result["message"] = f"{attacker.username} ataca pero no hay oponente."
                return result
            
            damage = attacker.attack_power
            actual_damage = defender.take_damage(damage)
            result["damage"] = actual_damage
            result["target_id"] = defender.id
            result["message"] = (
                f"{attacker.username} ataca a {defender.username} "
                f"por {actual_damage} de daño. "
                f"HP restante: {defender.current_hp}/{defender.max_hp}"
            )
            attacker.charge_special()
        
        elif action_type == ActionType.DEFEND:
            attacker.is_defending = True
            result["message"] = f"{attacker.username} se pone en posición defensiva."
            attacker.charge_special()
        
        elif action_type == ActionType.SPECIAL:
            if not defender:
                result["message"] = f"{attacker.username} intenta usar especial pero no hay oponente."
                return result
            
            if not attacker.use_special():
                result["message"] = (
                    f"{attacker.username} intenta usar especial pero no tiene carga suficiente. "
                    f"Carga actual: {attacker.special_charge}/{attacker.max_special_charge}"
                )
                return result
            
            # Habilidad especial: daño doble + cura del 50% del daño
            base_damage = attacker.attack_power * 2
            actual_damage = defender.take_damage(base_damage)
            
            heal_amount = actual_damage // 2
            attacker.heal(heal_amount)
            
            result["damage"] = actual_damage
            result["target_id"] = defender.id
            result["message"] = (
                f"¡{attacker.username} usa HABILIDAD ESPECIAL! "
                f"Inflige {actual_damage} de daño a {defender.username} "
                f"y se cura {heal_amount} HP. "
                f"HP enemigo: {defender.current_hp}/{defender.max_hp}, "
                f"HP propio: {attacker.current_hp}/{attacker.max_hp}"
            )
        
        elif action_type == ActionType.FLEE:
            result["message"] = f"{attacker.username} intenta huir de la batalla."
            # Huir se procesa al nivel de batalla, no aquí
            result["damage"] = 0
        
        return result
    
    def _resolve_results(self, winner_id: Optional[str]) -> None:
        """Resuelve los resultados de la batalla y actualiza estadísticas."""
        self.status = BattleStatus.FINISHED
        
        if not winner_id:
            # Empate
            self.results[self.player1_id] = BattleResult.DRAW
            self.results[self.player2_id] = BattleResult.DRAW
            if self.player1:
                self.player1.record_draw()
            if self.player2:
                self.player2.record_draw()
        else:
            # Hay ganador
            loser_id = self.player2_id if winner_id == self.player1_id else self.player1_id
            
            self.results[winner_id] = BattleResult.VICTORY
            self.results[loser_id] = BattleResult.DEFEAT
            
            winner = self.get_player_by_id(winner_id)
            loser = self.get_player_by_id(loser_id)
            
            if winner:
                winner.record_victory()
            if loser:
                loser.record_defeat()
    
    def player_flees(self, player_id: str) -> TurnResult:
        """Un jugador huye de la batalla."""
        fleeing_player = self.get_player_by_id(player_id)
        opponent = self.get_opponent(player_id)
        
        messages = []
        if fleeing_player:
            messages.append(f"{fleeing_player.username} ha huido de la batalla.")
        
        if opponent:
            messages.append(f"{opponent.username} gana por retirada del oponente.")
        
        # El que huye pierde, el oponente gana
        self.status = BattleStatus.FINISHED
        self.results[player_id] = BattleResult.FLED
        if opponent:
            self.results[opponent.id] = BattleResult.VICTORY
            opponent.record_victory()
        if fleeing_player:
            fleeing_player.record_defeat()
        
        return TurnResult(
            turn_number=self.current_turn,
            actions=[],
            damage_dealt={},
            messages=messages,
            battle_ended=True,
            winner_id=opponent.id if opponent else None,
        )
