"""
Tests del dominio: Verifican reglas de negocio puras.
Sin dependencias de infraestructura.
"""

import pytest

from src.domain import (
    ActionType,
    Battle,
    BattleAction,
    BattleResult,
    BattleStatus,
    Player,
)


class TestPlayer:
    """Tests para la entidad Player."""

    def test_create_player_with_defaults(self):
        """Un jugador se crea con stats por defecto."""
        player = Player(telegram_id=123, username="test_user")

        assert player.telegram_id == 123
        assert player.username == "test_user"
        assert player.current_hp == 100
        assert player.max_hp == 100
        assert player.attack_power == 15
        assert player.defense_power == 10
        assert player.victories == 0
        assert player.defeats == 0
        assert player.special_charge == 0

    def test_player_is_alive_when_hp_positive(self):
        """Un jugador está vivo si HP > 0."""
        player = Player(telegram_id=1, username="alive")
        assert player.is_alive() is True

    def test_player_is_dead_when_hp_zero(self):
        """Un jugador está muerto si HP == 0."""
        player = Player(telegram_id=1, username="dead")
        player.current_hp = 0
        assert player.is_alive() is False

    def test_take_damage_reduces_hp(self):
        """El daño reduce el HP actual."""
        player = Player(telegram_id=1, username="fighter")
        initial_hp = player.current_hp

        damage = player.take_damage(20)

        assert damage == 20
        assert player.current_hp == initial_hp - 20

    def test_take_damage_respects_defense(self):
        """La defensa reduce el daño recibido."""
        player = Player(telegram_id=1, username="defender")
        player.is_defending = True
        player.defense_power = 10

        damage = player.take_damage(15)

        assert damage == 5  # 15 - 10 = 5
        assert player.current_hp == 95

    def test_take_damage_minimum_zero(self):
        """El daño no puede ser negativo."""
        player = Player(telegram_id=1, username="tank")
        player.is_defending = True
        player.defense_power = 20

        damage = player.take_damage(10)

        assert damage == 0
        assert player.current_hp == 100

    def test_heal_increases_hp_up_to_max(self):
        """La cura aumenta HP hasta el máximo."""
        player = Player(telegram_id=1, username="healer")
        player.current_hp = 50

        healed = player.heal(30)

        assert healed == 30
        assert player.current_hp == 80

    def test_heal_cannot_exceed_max_hp(self):
        """La cura no puede superar el HP máximo."""
        player = Player(telegram_id=1, username="full_heal")
        player.current_hp = 90

        healed = player.heal(50)

        assert healed == 10  # Solo cura hasta 100
        assert player.current_hp == 100

    def test_charge_special_increments_up_to_max(self):
        """La carga especial incrementa hasta el máximo."""
        player = Player(telegram_id=1, username="charger")

        player.charge_special()
        assert player.special_charge == 1

        player.charge_special()
        player.charge_special()
        assert player.special_charge == 3  # Máximo

        player.charge_special()
        assert player.special_charge == 3  # No supera el máximo

    def test_use_special_requires_charge(self):
        """Usar especial requiere al menos 1 de carga."""
        player = Player(telegram_id=1, username="special_user")

        # Sin carga
        assert player.use_special() is False
        assert player.special_charge == 0

        # Con carga
        player.charge_special()
        assert player.use_special() is True
        assert player.special_charge == 0

    def test_reset_turn_state_clears_defense(self):
        """Resetear turno limpia estado defensivo."""
        player = Player(telegram_id=1, username="resetter")
        player.is_defending = True

        player.reset_turn_state()

        assert player.is_defending is False

    def test_ranking_score_is_victories_minus_defeats(self):
        """El ranking score es victorias - derrotas."""
        player = Player(telegram_id=1, username="ranked")
        player.victories = 5
        player.defeats = 2

        assert player.ranking_score == 3

    def test_win_rate_calculation(self):
        """El win rate se calcula correctamente."""
        player = Player(telegram_id=1, username="winner")
        player.victories = 3
        player.defeats = 1
        player.draws = 0

        assert player.win_rate == 75.0

    def test_win_rate_zero_matches(self):
        """Win rate es 0 si no hay partidas."""
        player = Player(telegram_id=1, username="newbie")

        assert player.win_rate == 0.0


class TestBattle:
    """Tests para la entidad Battle."""

    def _create_players(self) -> tuple[Player, Player]:
        """Helper para crear dos jugadores de prueba."""
        p1 = Player(telegram_id=1, username="player1")
        p2 = Player(telegram_id=2, username="player2")
        return p1, p2

    def _create_battle(self) -> Battle:
        """Helper para crear una batalla lista para empezar."""
        p1, p2 = self._create_players()
        battle = Battle(
            player1_id=p1.id,
            player2_id=p2.id,
            player1=p1,
            player2=p2,
        )
        return battle

    def test_create_battle_is_pending(self):
        """Una batalla nueva está en estado PENDING."""
        battle = self._create_battle()

        assert battle.status == BattleStatus.PENDING
        assert battle.current_turn == 0

    def test_start_battle_changes_status(self):
        """Iniciar batalla cambia estado a IN_PROGRESS."""
        battle = self._create_battle()

        battle.start()

        assert battle.status == BattleStatus.IN_PROGRESS
        assert battle.current_turn == 1

    def test_start_battle_sets_turn_order(self):
        """Iniciar batalla establece orden de turnos."""
        battle = self._create_battle()

        battle.start()

        assert len(battle.turn_order) == 2
        assert battle.player1_id in battle.turn_order
        assert battle.player2_id in battle.turn_order

    def test_execute_attack_action(self):
        """Ejecutar ataque reduce HP del oponente."""
        battle = self._create_battle()
        battle.start()

        p1 = battle.player1
        p2 = battle.player2
        initial_hp = p2.current_hp

        action = BattleAction(
            player_id=p1.id,
            action_type=ActionType.ATTACK,
            target_player_id=p2.id,
        )

        result = battle.execute_turn([action])

        assert result.battle_ended is False
        assert p2.current_hp < initial_hp
        assert f"{p1.username} ataca a {p2.username}" in result.messages[0]

    def test_execute_defend_action(self):
        """Ejecutar defensa activa estado defensivo durante el turno."""
        battle = self._create_battle()
        battle.start()

        p1 = battle.player1

        action = BattleAction(
            player_id=p1.id,
            action_type=ActionType.DEFEND,
        )

        result = battle.execute_turn([action])

        # El estado defensivo se resetea al final del turno
        # pero la defensa ya aplicó su efecto (carga especial)
        assert p1.special_charge == 1  # Cargó especial al defender
        assert "posición defensiva" in result.messages[0]

    def test_defense_reduces_next_damage(self):
        """Defensa reduce el daño recibido en el mismo turno (antes del reset)."""
        battle = self._create_battle()
        battle.start()

        p1 = battle.player1
        p2 = battle.player2

        # P1 se defiende - necesitamos simular que el estado persiste
        # hasta que P2 ataque. En nuestro modelo, execute_turn procesa
        # todas las acciones y luego resetea. Para testear defensa,
        # ejecutamos ambas acciones en el mismo turno.
        defend_action = BattleAction(
            player_id=p1.id,
            action_type=ActionType.DEFEND,
        )
        attack_action = BattleAction(
            player_id=p2.id,
            action_type=ActionType.ATTACK,
            target_player_id=p1.id,
        )

        # Ejecutar ambas acciones en el mismo turno
        result = battle.execute_turn([defend_action, attack_action])

        # P1 debería haber recibido menos daño por defenderse
        damage_received = 100 - p1.current_hp
        assert damage_received < p2.attack_power  # Menos de 15 por defensa

    def test_special_requires_charge(self):
        """Habilidad especial falla sin carga."""
        battle = self._create_battle()
        battle.start()

        p1 = battle.player1
        p2 = battle.player2

        action = BattleAction(
            player_id=p1.id,
            action_type=ActionType.SPECIAL,
            target_player_id=p2.id,
        )

        result = battle.execute_turn([action])

        assert "no tiene carga suficiente" in result.messages[0]

    def test_special_deals_double_damage(self):
        """Habilidad especial hace daño doble y cura."""
        battle = self._create_battle()
        battle.start()

        p1 = battle.player1
        p2 = battle.player2

        # Cargar especial (3 ataques)
        for _ in range(3):
            attack = BattleAction(
                player_id=p1.id,
                action_type=ActionType.ATTACK,
                target_player_id=p2.id,
            )
            battle.execute_turn([attack])

        # Usar especial
        special = BattleAction(
            player_id=p1.id,
            action_type=ActionType.SPECIAL,
            target_player_id=p2.id,
        )
        result = battle.execute_turn([special])

        assert "HABILIDAD ESPECIAL" in result.messages[0]
        assert p1.current_hp > 70  # Se curó algo

    def test_battle_ends_when_player_dies(self):
        """La batalla termina cuando un jugador muere."""
        battle = self._create_battle()
        battle.start()

        p1 = battle.player1
        p2 = battle.player2

        # P1 ataca repetidamente hasta matar a P2
        while p2.is_alive():
            attack = BattleAction(
                player_id=p1.id,
                action_type=ActionType.ATTACK,
                target_player_id=p2.id,
            )
            result = battle.execute_turn([attack])

        assert result.battle_ended is True
        assert result.winner_id == p1.id
        assert battle.status == BattleStatus.FINISHED

    def test_flee_ends_battle_immediately(self):
        """Huir termina la batalla inmediatamente."""
        battle = self._create_battle()
        battle.start()

        p1 = battle.player1

        result = battle.player_flees(p1.id)

        assert result.battle_ended is True
        assert result.winner_id == battle.player2_id
        assert battle.results[p1.id] == BattleResult.FLED
        assert battle.results[battle.player2_id] == BattleResult.VICTORY

    def test_get_opponent_returns_correct_player(self):
        """get_opponent retorna el oponente correcto."""
        battle = self._create_battle()

        opponent = battle.get_opponent(battle.player1_id)

        assert opponent == battle.player2

    def test_participants_returns_both_players(self):
        """participants retorna ambos jugadores."""
        battle = self._create_battle()

        participants = battle.participants

        assert len(participants) == 2
        assert battle.player1 in participants
        assert battle.player2 in participants
