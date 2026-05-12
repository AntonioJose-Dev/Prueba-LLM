"""
Bot principal de Telegram para Combate Espiritual.
Punto de entrada de la aplicación.
"""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler

from src.infrastructure import create_repositories, create_handlers

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def create_bot_app(token: str):
    """Crea y configura la aplicación del bot."""
    # Inicializar repositorios
    player_repo, battle_repo = create_repositories()

    # Crear handlers con dependencias inyectadas
    handlers = create_handlers(player_repo, battle_repo)

    # Crear aplicación
    app = Application.builder().token(token).build()

    # Registrar comandos
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("perfil", handlers.perfil))
    app.add_handler(CommandHandler("ranking", handlers.ranking))
    app.add_handler(CommandHandler("batalla", handlers.batalla))
    app.add_handler(CommandHandler("atacar", handlers.atacar))
    app.add_handler(CommandHandler("defender", handlers.defender))
    app.add_handler(CommandHandler("especial", handlers.especial))
    app.add_handler(CommandHandler("huir", handlers.huir))

    logger.info("Bot configurado exitosamente.")
    return app


def main():
    """Punto de entrada principal."""
    import os

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN no está configurado en el entorno.")
        return

    app = create_bot_app(token)
    logger.info("Iniciando bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
