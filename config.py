import os
from dataclasses import dataclass


def env_bool(name: str, default: bool = False) -> bool:
    """
    تحويل Environment Variable إلى True / False.
    """

    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@dataclass(frozen=True)
class Settings:
    # =====================================================
    # TELEGRAM
    # =====================================================

    telegram_token: str = os.getenv(
        "TELEGRAM_BOT_TOKEN",
        ""
    )

    # =====================================================
    # GEMINI
    # =====================================================

    gemini_api_key: str = os.getenv(
        "GEMINI_API_KEY",
        ""
    )

    gemini_model: str = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.5-flash-lite"
    )

    # =====================================================
    # RENDER
    # =====================================================

    port: int = int(
        os.getenv(
            "PORT",
            "10000"
        )
    )

    # =====================================================
    # LOGGING
    # =====================================================

    log_level: str = os.getenv(
        "LOG_LEVEL",
        "INFO"
    )

    # =====================================================
    # AI MEMORY
    # =====================================================

    # عدد الرسائل التي يحتفظ بها البوت
    # لكل مستخدم / محادثة.
    max_history: int = int(
        os.getenv(
            "MAX_HISTORY",
            "8"
        )
    )

    # =====================================================
    # GEMINI TIMEOUT
    # =====================================================

    ai_timeout: int = int(
        os.getenv(
            "AI_TIMEOUT",
            "45"
        )
    )

    # =====================================================
    # MESSAGE LIMIT
    # =====================================================

    max_message_length: int = int(
        os.getenv(
            "MAX_MESSAGE_LENGTH",
            "3500"
        )
    )

    # =====================================================
    # MODERATION
    # =====================================================

    moderation_enabled: bool = env_bool(
        "MODERATION_ENABLED",
        True
    )


# =========================================================
# SETTINGS INSTANCE
# =========================================================

settings = Settings()
