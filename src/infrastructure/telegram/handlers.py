"""
Infraestructura: Handlers de Telegram.
Sin lógica de negocio. Solo delegan a casos de uso y formatean respuestas.
"""

from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from src.application.battle_use_cases import (
    CreateBattle,
    ExecuteBattleTurn,
    FleeBattle,
    GetBattle,
    StartBattle,
)
from src.application.player_use_cases import GetPlayer, GetRanking, RegisterPlayer
from src.domain.models import ActionType, BattleAction


class TelegramHandlers:
    """Handlers para comandos de Telegram."""

    def __init__(
        self,
        register_player: RegisterPlayer,
        get_player: GetPlayer,
        get_ranking: GetRanking,
        create_battle: CreateBattle,
        start_battle: StartBattle,
        execute_turn: ExecuteBattleTurn,
        flee_battle: FleeBattle,
        get_battle: GetBattle,
    ):
        self.register_player = register_player
        self.get_player = get_player
        self.get_ranking = get_ranking
        self.create_battle = create_battle
        self.start_battle = start_battle
        self.execute_turn = execute_turn
        self.flee_battle = flee_battle
        self.get_battle = get_battle

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Registra al usuario."""
        if not update.effective_user or not update.effective_message:
            return

        telegram_id = update.effective_user.id
        username = update.effective_user.username or str(telegram_id)

        result = self.register_player.execute(telegram_id, username)

        if result.success and result.player:
            await update.effective_message.reply_text(
                f"¡Bienvenido, {result.player.username}!\n"
                f"Has sido registrado en el sistema de combate espiritual.\n"
                f"Usa /batalla @usuario para desafiar a alguien."
            )

    async def perfil(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /perfil - Muestra estadísticas del jugador."""
        if not update.effective_user or not update.effective_message:
            return

        telegram_id = update.effective_user.id
        result = self.get_player.by_telegram_id(telegram_id)

        if not result.found or not result.player:
            await update.effective_message.reply_text(
                "No estás registrado. Usa /start primero."
            )
            return

        player = result.player
        stats = (
            f"📊 Perfil de {player.username}\n\n"
            f"🏆 Victorias: {player.victories}\n"
            f"💀 Derrotas: {player.defeats}\n"
            f"🤝 Empates: {player.draws}\n"
            f"📈 Ranking Score: {player.ranking_score}\n"
            f"🎯 Win Rate: {player.win_rate:.1f}%\n"
            f"❤️ HP: {player.current_hp}/{player.max_hp}\n"
            f"⚔️ Ataque: {player.attack_power}\n"
            f"🛡️ Defensa: {player.defense_power}\n"
            f"✨ Carga Especial: {player.special_charge}/{player.max_special_charge}"
        )

        await update.effective_message.reply_text(stats)

    async def ranking(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /ranking - Muestra top jugadores."""
        if not update.effective_message:
            return

        players = self.get_ranking.execute(limit=10)

        if not players:
            await update.effective_message.reply_text(
                "Aún no hay jugadores registrados."
            )
            return

        lines = ["🏆 Ranking de Combatientes 🏆\n"]
        for i, player in enumerate(players, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📍"
            lines.append(
                f"{medal} {i}. {player.username} - "
                f"Score: {player.ranking_score} "
                f"(V:{player.victories} D:{player.defeats})"
            )

        await update.effective_message.reply_text("\n".join(lines))

    async def batalla(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Comando /batalla @usuario - Desafía a otro jugador."""
        if (
            not update.effective_user
            or not update.effective_message
            or not context.args
        ):
            await update.effective_message.reply_text(
                "Uso: /batalla @usuario_a_desafiar"
            )
            return

        challenger_telegram_id = update.effective_user.id
        opponent_username = context.args[0].lstrip("@")

        # Obtener challenger
        challenger_result = self.get_player.by_telegram_id(challenger_telegram_id)
        if not challenger_result.found or not challenger_result.player:
            await update.effective_message.reply_text(
                "Debes registrarte con /start antes de batalar."
            )
            return
        challenger = challenger_result.player

        # Buscar oponente por username (necesitamos iterar todos los jugadores)
        # En producción esto sería más eficiente con un índice
        from src.domain.repositories import PlayerRepository

        # Obtenemos el repositorio desde el caso de uso
        player_repo: PlayerRepository = self.get_player.player_repository  # type: ignore
        all_players = player_repo.get_all()
        opponent = None
        for p in all_players:
            if p.username.lower() == opponent_username.lower():
                opponent = p
                break

        if not opponent:
            await update.effective_message.reply_text(
                f"Jugador @{opponent_username} no encontrado."
            )
            return

        if opponent.id == challenger.id:
            await update.effective_message.reply_text(
                "No puedes batalar contra ti mismo."
            )
            return

        # Crear batalla
        result = self.create_battle.execute(challenger.id, opponent.id)

        if not result.success or not result.battle:
            await update.effective_message.reply_text(
                f"No se pudo crear la batalla: {result.error}"
            )
            return

        battle = result.battle

        # Iniciar batalla automáticamente
        start_result = self.start_battle.execute(battle.id)
        if not start_result.success:
            await update.effective_message.reply_text(
                f"Error al iniciar batalla: {start_result.error}"
            )
            return

        # Guardar ID de batalla en contexto para seguimiento
        if context.chat_data is not None:
            context.chat_data["active_battle_id"] = battle.id

        await update.effective_message.reply_text(
            f"⚔️ ¡Batalla iniciada entre {challenger.username} y {opponent.username}!\n\n"
            f"Esperando acciones de ambos jugadores.\n"
            f"Usa:\n"
            f"/atacar @oponente\n"
            f"/defender\n"
            f"/especial @oponente\n"
            f"/huir"
        )

    async def atacar(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Comando /atacar @oponente - Acción de ataque."""
        await self._process_action(
            update, context, ActionType.ATTACK, require_target=True
        )

    async def defender(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Comando /defender - Acción de defensa."""
        await self._process_action(update, context, ActionType.DEFEND)

    async def especial(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Comando /especial @oponente - Habilidad especial."""
        await self._process_action(
            update, context, ActionType.SPECIAL, require_target=True
        )

    async def huir(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /huir - Abandonar batalla."""
        if not update.effective_user or not update.effective_message:
            return

        telegram_id = update.effective_user.id
        player_result = self.get_player.by_telegram_id(telegram_id)

        if not player_result.found or not player_result.player:
            await update.effective_message.reply_text("No estás registrado.")
            return

        player = player_result.player
        battle = self.get_battle.active_for_player(player.id)

        if not battle:
            await update.effective_message.reply_text(
                "No estás en ninguna batalla activa."
            )
            return

        result = self.flee_battle.execute(battle.id, player.id)

        if not result.success or not result.turn_result:
            await update.effective_message.reply_text(
                f"Error al huir: {result.error}"
            )
            return

        for msg in result.turn_result.messages:
            await update.effective_message.reply_text(msg)

        # Limpiar contexto
        if context.chat_data is not None:
            context.chat_data.pop("active_battle_id", None)

    async def _process_action(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        action_type: ActionType,
        require_target: bool = False,
    ):
        """Procesa una acción de batalla genérica."""
        if not update.effective_user or not update.effective_message:
            return

        telegram_id = update.effective_user.id

        # Obtener jugador
        player_result = self.get_player.by_telegram_id(telegram_id)
        if not player_result.found or not player_result.player:
            await update.effective_message.reply_text(
                "Debes registrarte con /start primero."
            )
            return

        player = player_result.player

        # Obtener batalla activa
        battle = self.get_battle.active_for_player(player.id)
        if not battle:
            await update.effective_message.reply_text(
                "No estás en ninguna batalla activa. Usa /batalla @usuario."
            )
            return

        if battle.status.value != "in_progress":
            await update.effective_message.reply_text(
                "Esta batalla aún no ha comenzado o ya terminó."
            )
            return

        # Determinar objetivo
        target_player = None
        if require_target:
            if not context.args:
                await update.effective_message.reply_text(
                    f"Este comando requiere un objetivo. Uso: /{action_type.value} @oponente"
                )
                return

            opponent_username = context.args[0].lstrip("@")
            opponent = battle.get_opponent(player.id)
            if opponent and opponent.username.lower() == opponent_username.lower():
                target_player = opponent
            else:
                await update.effective_message.reply_text(
                    "Objetivo inválido. Debe ser tu oponente en esta batalla."
                )
                return

        # Crear acción
        action = BattleAction(
            player_id=player.id,
            action_type=action_type,
            target_player_id=target_player.id if target_player else None,
        )

        # Ejecutar turno
        result = self.execute_turn.execute(battle.id, [action])

        if not result.success:
            await update.effective_message.reply_text(f"Error: {result.error}")
            return

        if not result.turn_result:
            await update.effective_message.reply_text("No se pudo ejecutar el turno.")
            return

        turn_result = result.turn_result

        # Mostrar mensajes del turno
        for msg in turn_result.messages:
            await update.effective_message.reply_text(msg)

        # Si la batalla terminó, limpiar contexto
        if turn_result.battle_ended:
            if context.chat_data is not None:
                context.chat_data.pop("active_battle_id", None)

            if turn_result.winner_id:
                winner = battle.get_player_by_id(turn_result.winner_id)
                if winner:
                    await update.effective_message.reply_text(
                        f"🏆 ¡{winner.username} ha ganado la batalla!"
                    )
            else:
                await update.effective_message.reply_text("¡La batalla terminó en empate!")


def create_handlers(
    player_repo,
    battle_repo,
) -> TelegramHandlers:
    """Factory para crear handlers con todas las dependencias inyectadas."""
    from src.application.battle_use_cases import (
        CreateBattle,
        ExecuteBattleTurn,
        FleeBattle,
        GetBattle,
        StartBattle,
    )
    from src.application.player_use_cases import GetPlayer, GetRanking, RegisterPlayer

    register_player = RegisterPlayer(player_repo)
    get_player = GetPlayer(player_repo)
    get_ranking = GetRanking(player_repo)
    create_battle = CreateBattle(battle_repo, player_repo)
    start_battle = StartBattle(battle_repo)
    execute_turn = ExecuteBattleTurn(battle_repo, player_repo)
    flee_battle = FleeBattle(battle_repo, player_repo)
    get_battle = GetBattle(battle_repo)

    return TelegramHandlers(
        register_player=register_player,
        get_player=get_player,
        get_ranking=get_ranking,
        create_battle=create_battle,
        start_battle=start_battle,
        execute_turn=execute_turn,
        flee_battle=flee_battle,
        get_battle=get_battle,
    )
