from services.server_guard_service import ServerGuardService


BASE_SETTINGS = {
    "block_links": 1,
    "block_invites": 1,
    "anti_spam": 1,
    "anti_mentions": 1,
    "anti_caps": 1,
    "allowed_domains": "discord.com,github.com,youtube.com",
    "blocked_words": '["seed phrase","wallet drainer"]',
    "spam_message_limit": 5,
}


def test_blocks_discord_invites():
    service = ServerGuardService()
    result = service.analyze_message("join discord.gg/scam", BASE_SETTINGS, 1, 1, 0)
    assert result["type"] == "discord_invite"


def test_blocks_external_links_except_allowed_domains():
    service = ServerGuardService()
    result = service.analyze_message("go to https://scam.example", BASE_SETTINGS, 1, 1, 0)
    assert result["type"] == "external_link"

    allowed = service.analyze_message("check https://github.com/Naman794", BASE_SETTINGS, 1, 1, 0)
    assert allowed is None


def test_detects_repeat_spam_and_caps():
    service = ServerGuardService()
    repeat = service.analyze_message("same", BASE_SETTINGS, 2, 3, 0)
    assert repeat["type"] == "repeat_spam"

    caps = service.analyze_message("THIS IS A VERY LOUD SPAM MESSAGE", BASE_SETTINGS, 1, 1, 0)
    assert caps["type"] == "caps_spam"


def test_detects_mass_mentions_and_blocked_phrases():
    service = ServerGuardService()
    mention = service.analyze_message("hello everyone", BASE_SETTINGS, 1, 1, 5)
    assert mention["type"] == "mention_spam"

    phrase = service.analyze_message("share your seed phrase", BASE_SETTINGS, 1, 1, 0)
    assert phrase["type"] == "blocked_phrase"
