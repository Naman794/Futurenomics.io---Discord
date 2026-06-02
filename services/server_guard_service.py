import json
import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from database.db import execute_query, fetch_one

URL_RE = re.compile(r"(https?://[^\s]+|www\.[^\s]+)", re.IGNORECASE)
DISCORD_INVITE_RE = re.compile(r"(discord\.gg/|discord(?:app)?\.com/invite/)", re.IGNORECASE)

DEFAULT_BLOCKED_WORDS = [
    "free airdrop claim now",
    "seed phrase",
    "wallet drainer",
    "connect wallet now",
    "guaranteed profit",
    "100x guaranteed",
]

DEFAULT_ALLOWED_DOMAINS = [
    "discord.com",
    "discord.gg",
    "github.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "youtu.be",
]


def _bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value == 1
    return str(value).lower() in {"1", "true", "yes", "on"}


class ServerGuardService:
    def ensure_tables(self) -> None:
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS server_guard_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_guild_id TEXT UNIQUE NOT NULL,
                guild_name TEXT,
                log_channel_id TEXT,
                auto_role_id TEXT,
                quarantine_role_id TEXT,
                block_links INTEGER DEFAULT 1,
                block_invites INTEGER DEFAULT 1,
                anti_spam INTEGER DEFAULT 1,
                anti_mentions INTEGER DEFAULT 1,
                anti_caps INTEGER DEFAULT 1,
                auto_timeout INTEGER DEFAULT 1,
                timeout_after_violations INTEGER DEFAULT 3,
                timeout_minutes INTEGER DEFAULT 10,
                spam_message_limit INTEGER DEFAULT 5,
                spam_window_seconds INTEGER DEFAULT 8,
                allowed_domains TEXT DEFAULT 'discord.com,discord.gg,github.com,x.com,twitter.com,youtube.com,youtu.be',
                blocked_words TEXT DEFAULT '["free airdrop claim now","seed phrase","wallet drainer","connect wallet now","guaranteed profit","100x guaranteed"]',
                is_active INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS server_guard_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_guild_id TEXT,
                event_type TEXT,
                actor_user_id TEXT,
                target_user_id TEXT,
                channel_id TEXT,
                message_id TEXT,
                action_taken TEXT,
                reason TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS server_guard_violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_guild_id TEXT,
                discord_user_id TEXT,
                violation_type TEXT,
                reason TEXT,
                action_taken TEXT,
                channel_id TEXT,
                message_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        execute_query("CREATE INDEX IF NOT EXISTS idx_server_guard_logs_guild ON server_guard_logs(discord_guild_id, created_at)")
        execute_query("CREATE INDEX IF NOT EXISTS idx_server_guard_violations_user ON server_guard_violations(discord_guild_id, discord_user_id, created_at)")

    def get_settings(self, guild_id: str) -> dict | None:
        self.ensure_tables()
        return fetch_one("SELECT * FROM server_guard_settings WHERE discord_guild_id = ?", (guild_id,))

    def get_active_settings(self, guild_id: str) -> dict | None:
        settings = self.get_settings(guild_id)
        if settings and _bool(settings.get("is_active")):
            return settings
        return None

    def upsert_settings(
        self,
        guild_id: str,
        guild_name: str,
        log_channel_id: str,
        auto_role_id: str | None = None,
        quarantine_role_id: str | None = None,
    ) -> dict:
        self.ensure_tables()
        execute_query(
            """
            INSERT INTO server_guard_settings(
                discord_guild_id, guild_name, log_channel_id, auto_role_id, quarantine_role_id,
                block_links, block_invites, anti_spam, anti_mentions, anti_caps, auto_timeout,
                timeout_after_violations, timeout_minutes, spam_message_limit, spam_window_seconds,
                allowed_domains, blocked_words, is_active
            )
            VALUES (?, ?, ?, ?, ?, 1, 1, 1, 1, 1, 1, 3, 10, 5, 8, ?, ?, 1)
            ON CONFLICT(discord_guild_id) DO UPDATE SET
                guild_name = excluded.guild_name,
                log_channel_id = excluded.log_channel_id,
                auto_role_id = excluded.auto_role_id,
                quarantine_role_id = excluded.quarantine_role_id,
                is_active = 1,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                guild_id,
                guild_name,
                log_channel_id,
                auto_role_id,
                quarantine_role_id,
                ",".join(DEFAULT_ALLOWED_DOMAINS),
                json.dumps(DEFAULT_BLOCKED_WORDS),
            ),
        )
        return self.get_settings(guild_id) or {}

    def log_event(
        self,
        guild_id: str,
        event_type: str,
        action_taken: str = "logged",
        actor_user_id: str | None = None,
        target_user_id: str | None = None,
        channel_id: str | None = None,
        message_id: str | None = None,
        reason: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        self.ensure_tables()
        execute_query(
            """
            INSERT INTO server_guard_logs(
                discord_guild_id, event_type, actor_user_id, target_user_id,
                channel_id, message_id, action_taken, reason, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                event_type,
                actor_user_id,
                target_user_id,
                channel_id,
                message_id,
                action_taken,
                reason,
                json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )

    def record_violation(
        self,
        guild_id: str,
        user_id: str,
        violation_type: str,
        reason: str,
        action_taken: str,
        channel_id: str | None = None,
        message_id: str | None = None,
    ) -> int:
        self.ensure_tables()
        execute_query(
            """
            INSERT INTO server_guard_violations(
                discord_guild_id, discord_user_id, violation_type, reason,
                action_taken, channel_id, message_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (guild_id, user_id, violation_type, reason, action_taken, channel_id, message_id),
        )
        self.log_event(
            guild_id=guild_id,
            event_type="violation",
            target_user_id=user_id,
            channel_id=channel_id,
            message_id=message_id,
            action_taken=action_taken,
            reason=reason,
            metadata={"violation_type": violation_type},
        )
        return self.recent_violation_count(guild_id, user_id)

    def recent_violation_count(self, guild_id: str, user_id: str, within_minutes: int = 30) -> int:
        self.ensure_tables()
        cutoff = (datetime.utcnow() - timedelta(minutes=within_minutes)).isoformat()
        row = fetch_one(
            """
            SELECT COUNT(*) AS count FROM server_guard_violations
            WHERE discord_guild_id = ? AND discord_user_id = ? AND created_at >= ?
            """,
            (guild_id, user_id, cutoff),
        )
        return int(row["count"]) if row else 0

    def should_timeout(self, settings: dict, violation_count: int) -> bool:
        return _bool(settings.get("auto_timeout")) and violation_count >= int(settings.get("timeout_after_violations") or 3)

    def allowed_domains(self, settings: dict) -> set[str]:
        value = settings.get("allowed_domains") or ""
        return {item.strip().lower() for item in value.split(",") if item.strip()}

    def blocked_words(self, settings: dict) -> set[str]:
        value = settings.get("blocked_words")
        if not value:
            return {item.lower() for item in DEFAULT_BLOCKED_WORDS}
        try:
            return {str(item).lower() for item in json.loads(value)}
        except json.JSONDecodeError:
            return {item.strip().lower() for item in value.split(",") if item.strip()}

    def analyze_message(
        self,
        content: str,
        settings: dict,
        recent_message_count: int,
        repeated_message_count: int,
        mention_count: int,
    ) -> dict | None:
        content = content or ""
        lowered = content.lower()

        if _bool(settings.get("block_invites")) and DISCORD_INVITE_RE.search(content):
            return {"type": "discord_invite", "reason": "Discord invite links are blocked."}

        if _bool(settings.get("block_links")):
            disallowed = self._find_disallowed_urls(content, self.allowed_domains(settings))
            if disallowed:
                return {"type": "external_link", "reason": f"External links are blocked: {', '.join(disallowed[:3])}"}

        for blocked in self.blocked_words(settings):
            if blocked and blocked in lowered:
                return {"type": "blocked_phrase", "reason": f"Blocked phrase detected: {blocked}"}

        if _bool(settings.get("anti_spam")):
            limit = int(settings.get("spam_message_limit") or 5)
            if recent_message_count >= limit:
                return {"type": "message_spam", "reason": f"Too many messages in a short window ({recent_message_count}/{limit})."}
            if repeated_message_count >= 3:
                return {"type": "repeat_spam", "reason": "Repeated duplicate messages detected."}

        if _bool(settings.get("anti_mentions")) and mention_count >= 5:
            return {"type": "mention_spam", "reason": f"Mass mention detected ({mention_count} mentions)."}

        if _bool(settings.get("anti_caps")) and self._is_caps_spam(content):
            return {"type": "caps_spam", "reason": "Excessive caps detected."}

        return None

    def _find_disallowed_urls(self, content: str, allowed_domains: set[str]) -> list[str]:
        blocked: list[str] = []
        for raw_url in URL_RE.findall(content):
            url = raw_url if raw_url.startswith(("http://", "https://")) else f"https://{raw_url}"
            domain = urlparse(url).netloc.lower().removeprefix("www.")
            if not domain:
                continue
            if domain in allowed_domains or any(domain.endswith(f".{allowed}") for allowed in allowed_domains):
                continue
            blocked.append(domain)
        return blocked

    @staticmethod
    def _is_caps_spam(content: str) -> bool:
        letters = [char for char in content if char.isalpha()]
        if len(letters) < 20:
            return False
        uppercase = sum(1 for char in letters if char.isupper())
        return uppercase / len(letters) >= 0.75


server_guard_service = ServerGuardService()
