CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_user_id TEXT UNIQUE NOT NULL,
    username TEXT,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    experience_level TEXT DEFAULT 'beginner',
    preferred_topics TEXT,
    is_admin INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS guilds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_guild_id TEXT UNIQUE NOT NULL,
    guild_name TEXT,
    default_channel_id TEXT,
    newsletter_channel_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    category TEXT,
    level TEXT DEFAULT 'beginner',
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS glossary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT UNIQUE NOT NULL,
    definition TEXT NOT NULL,
    category TEXT,
    example TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quizzes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER,
    question TEXT NOT NULL,
    option_a TEXT,
    option_b TEXT,
    option_c TEXT,
    option_d TEXT,
    correct_option TEXT NOT NULL,
    explanation TEXT,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id)
);

CREATE TABLE IF NOT EXISTS market_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    price REAL,
    price_change_percent REAL,
    volume REAL,
    high_24h REAL,
    low_24h REAL,
    source TEXT DEFAULT 'binance',
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_user_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    condition_type TEXT NOT NULL,
    target_price REAL NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    triggered_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    source TEXT,
    url TEXT UNIQUE,
    summary TEXT,
    category TEXT,
    published_at TIMESTAMP,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS newsletters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT,
    channel_id TEXT,
    title TEXT,
    content TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'sent'
);

CREATE TABLE IF NOT EXISTS newsletter_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_guild_id TEXT,
    discord_user_id TEXT,
    channel_id TEXT,
    subscription_type TEXT DEFAULT 'daily',
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS command_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_user_id TEXT,
    guild_id TEXT,
    command_name TEXT,
    command_input TEXT,
    response_status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_pulse_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_guild_id TEXT UNIQUE NOT NULL,
    channel_id TEXT,
    symbols TEXT DEFAULT 'BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT',
    update_interval_minutes INTEGER DEFAULT 1,
    chart_interval_minutes INTEGER DEFAULT 5,
    is_active INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_pulse_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_guild_id TEXT,
    channel_id TEXT,
    symbols TEXT,
    status TEXT,
    error_message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
