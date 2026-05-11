# web3_teacher_bot

Production-ready MVP Discord bot for Web3 education, crypto market lookups, charts, news, newsletters, price alerts, and Live Market Pulse.

All market-related responses include: "Educational information only. Not financial advice."

## Purpose

Futurenomics Bot is a private Discord assistant for Web3 communities. Its purpose is to make crypto education easier to access inside the place where the community already talks: Discord.

The bot is built around five practical jobs:

- Teach beginners Web3 concepts through lessons, glossary terms, quizzes, and a roadmap.
- Help users inspect market data without turning that data into trading advice.
- Generate simple charts for visual learning and market context.
- Collect crypto/Web3 news from RSS feeds and Google Custom Search fallback.
- Automate recurring community updates through newsletters, alerts, and Live Market Pulse.

The bot should be treated as an educational guide, not a signal provider. Market data can help users learn how prices, volume, volatility, and news interact, but every output must stay neutral and include the required disclaimer.

## Theory

The bot follows a service-first backend design. Discord commands are intentionally thin: they validate input, call a service, handle errors, log usage, and return a user-friendly response. The deeper work lives in services such as `binance_service.py`, `news_service.py`, `newsletter_service.py`, `alert_service.py`, and `market_pulse_service.py`.

This design keeps the bot easier to maintain:

- Cogs answer Discord interactions.
- Services own business logic.
- The database layer owns SQLite reads/writes.
- Scheduled tasks run background automation.
- Utility modules standardize embeds, formatting, validation, time handling, and logging.

The system is also defensive by design. If Binance, RSS feeds, Google Search, chart generation, Discord channel lookup, or SQLite operations fail, the bot should log the issue and return a clean message instead of crashing.

## Working Flow

At runtime, the bot works like this:

1. `bot.py` starts and loads environment variables from `.env`.
2. Logging is configured for both console output and `logs/bot.log`.
3. SQLite initializes automatically from `database/schema.sql`.
4. Seed data loads beginner lessons, glossary terms, and starter quiz content.
5. All cogs listed in `config.py` are loaded.
6. Slash commands are synced globally and directly to guilds for faster command visibility.
7. Background tasks start for newsletters, market snapshots, alerts, and Live Market Pulse.
8. Users interact through Discord slash commands.
9. Commands call services, services fetch/store data, and responses are returned as Discord embeds or files.
10. Command usage and automated send attempts are stored in SQLite logs.

Example command flow:

```text
User runs /price BTCUSDT
-> market_commands.py validates the symbol
-> binance_service.py calls Binance public API
-> embed_builder.py formats a market embed
-> command_logs stores the command result
-> Discord receives the response with the disclaimer
```

Example newsletter flow:

```text
Admin runs /set_newsletter_channel in the target channel
-> guilds.newsletter_channel_id is saved
User or admin runs /send_newsletter_now
-> newsletter_commands.py reads the configured channel
-> newsletter_service.py builds the newsletter
-> bot sends the embed to the configured channel
-> newsletters table stores send status
```

Example Live Market Pulse flow:

```text
Admin configures channel, coins, price interval, and chart interval
-> market_pulse_settings stores the guild configuration
market_pulse_task.py wakes every minute
-> active guild settings are checked
-> interval rules decide whether to send
-> market_pulse_service.py builds the price embed
-> optional charts are generated every 5+ minutes
-> market_pulse_logs stores success or failure
```

## Features

- Discord slash commands with `discord.py`
- SQLite database with automatic first-run initialization
- Binance public market data
- Candlestick chart generation with pandas, matplotlib, and mplfinance
- RSS-first crypto news service with Google Custom Search fallback structure
- Daily newsletter service and scheduled task skeletons
- Live Market Pulse with configurable channel, symbols, update interval, and chart interval
- User profiles, glossary, lessons, roadmap, quizzes, alerts, admin commands
- File and console logging to `logs/bot.log`
- Basic pytest suite

## Setup

1. Create a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy environment variables:

```bash
copy .env.example .env
```

4. Edit `.env` and set `DISCORD_BOT_TOKEN`.

## Create a Discord Bot Token

1. Go to the Discord Developer Portal.
2. Create an application.
3. Open the Bot section and create a bot.
4. Copy the bot token into `.env`.
5. In OAuth2 URL Generator, select `bot` and `applications.commands`.
6. Add permissions needed by your server, then invite the bot.

## Environment Variables

- `DISCORD_BOT_TOKEN`: required
- `BINANCE_API_KEY`, `BINANCE_SECRET_KEY`: optional for this MVP because public endpoints are used
- `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_ENGINE_ID`: Google Custom Search fallback for news
- `DATABASE_PATH`: defaults to `database/web3_teacher_bot.db`
- `NEWSLETTER_HOUR`, `NEWSLETTER_MINUTE`, `TIMEZONE`: daily newsletter schedule
- `ADMIN_USER_IDS`: comma-separated Discord user IDs

## Run

```bash
python bot.py
```

The database initializes and seed data loads automatically on first run.

## Useful Commands

- `/help`
- `/learn bitcoin`
- `/glossary Wallet`
- `/roadmap`
- `/price BTCUSDT`
- `/market ETH`
- `/chart BTCUSDT 1h`
- `/news crypto`
- `/alert BTCUSDT above 70000`
- `/myalerts`
- `/set_newsletter_channel`
- `/send_newsletter_now`
- `/set_market_pulse_channel`
- `/start_market_pulse`
- `/market_pulse_now`

## Live Market Pulse

Live Market Pulse automatically posts Futurenomics crypto market updates into a configured Discord channel. It is designed for private community education: fast price updates, slower chart updates, and no trading advice.

Example admin setup flow:

```text
/set_market_pulse_channel #live-market-pulse
/set_market_pulse_coins BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT
/set_market_pulse_interval 1
/set_market_pulse_chart_interval 5
/start_market_pulse
```

Admin commands:

- `/set_market_pulse_channel channel`: choose where pulse updates are posted
- `/start_market_pulse`: enable automatic updates for the server
- `/stop_market_pulse`: disable automatic updates
- `/set_market_pulse_coins symbols`: save comma-separated Binance symbols
- `/set_market_pulse_interval minutes`: set price update interval, minimum 1 minute
- `/set_market_pulse_chart_interval minutes`: set chart interval, minimum 5 minutes
- `/market_pulse_now`: send one pulse update immediately

Price updates can run every 1 minute. Chart updates should run every 5 minutes or more because chart generation is heavier. By default, chart posting is limited to 3 symbols per cycle.

Every Live Market Pulse post includes: "Educational information only. Not financial advice."

## Tests

```bash
pytest
```

## Directory Structure

The project follows a service-first layout:

- `bot.py`: Discord startup, cogs, scheduled tasks
- `config.py`: environment config
- `database/`: SQLite schema, helpers, seed data
- `services/`: Binance, charts, education, news, newsletters, alerts, users, market pulse
- `cogs/`: thin Discord command handlers
- `tasks/`: scheduled jobs
- `utils/`: embeds, validators, logging, formatting, time helpers
- `data/`: markdown lessons, glossary, roadmap
- `tests/`: pytest coverage

## Security Notes

Never commit `.env`, bot tokens, private keys, seed phrases, or exchange credentials. Keep admin IDs explicit in `.env`. The bot reads public Binance data by default and does not need trading permissions.

## Disclaimer

This bot is for education and community learning. It does not provide financial advice, investment recommendations, or trading signals.
