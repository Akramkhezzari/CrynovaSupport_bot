import os


# ==============================
# Telegram
# ==============================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# ==============================
# Gemini
# ==============================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# الموديل المستخدم
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash-lite"
)


# ==============================
# إعدادات البوت
# ==============================

BOT_NAME = "Crynova AI"

LANGUAGE = "ar-DZ"


# ==============================
# التحقق من الإعدادات
# ==============================

def validate_config():

    missing = []

    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")

    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")

    if missing:
        raise ValueError(
            "المتغيرات التالية غير موجودة: "
            + ", ".join(missing)
        )
