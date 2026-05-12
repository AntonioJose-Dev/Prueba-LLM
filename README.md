# Bot de Combate Espiritual

Bot de Telegram para batallas PvP por turnos con arquitectura limpia.

## Estructura del Proyecto

```
src/
├── domain/                 # Entidades y reglas de negocio
│   ├── models.py          # Player, Battle, ActionType, etc.
│   ├── repositories.py    # Contratos abstractos
│   └── exceptions.py      # Excepciones específicas
│
├── application/            # Casos de uso
│   ├── player_use_cases.py    # Registro, ranking, perfil
│   └── battle_use_cases.py    # Crear, iniciar, ejecutar turnos
│
├── infrastructure/         # Implementaciones concretas
│   ├── db/
│   │   ├── init.py            # Factory de repositorios
│   │   └── sqlite_repositories.py  # SQLite implementation
│   └── telegram/
│       └── handlers.py        # Handlers de Telegram
│
└── main.py               # Punto de entrada del bot
```

## Comandos Disponibles

- `/start` - Registrarse en el sistema
- `/perfil` - Ver estadísticas personales
- `/ranking` - Ver top 10 jugadores
- `/batalla @usuario` - Desafiar a otro jugador
- `/atacar @oponente` - Atacar al oponente
- `/defender` - Ponerse en posición defensiva
- `/especial @oponente` - Usar habilidad especial (requiere carga)
- `/huir` - Abandonar la batalla

## Acciones de Combate

| Acción | Efecto | Carga Especial |
|--------|--------|----------------|
| Atacar | Daño = attack_power | +1 |
| Defender | Reduce daño en defense_power | +1 |
| Especial | Daño doble + cura 50% | -1 |
| Huir | Pierdes automáticamente | - |

## Configuración

1. Obtén un token de bot en [@BotFather](https://t.me/BotFather)
2. Exporta la variable de entorno:
   ```bash
   export TELEGRAM_BOT_TOKEN="tu_token_aqui"
   ```
3. Ejecuta el bot:
   ```bash
   python -m src.main
   ```

## Dependencias

```bash
pip install python-telegram-bot
```

## Arquitectura

El proyecto sigue **Clean Architecture**:

- **Domain**: Sin dependencias externas. Contiene las entidades y reglas de negocio puras.
- **Application**: Casos de uso que orquestan la lógica. Dependen solo del dominio.
- **Infrastructure**: Implementaciones concretas (SQLite, Telegram). Dependen de las capas superiores.

Los handlers de Telegram **no contienen lógica de negocio**, solo delegan a casos de uso y formatean respuestas.

## Testing

Ejecutar tests del dominio:
```bash
python -m pytest tests/
```

Verificar integración:
```bash
python -c "from src.infrastructure import create_repositories; print('OK')"
```
