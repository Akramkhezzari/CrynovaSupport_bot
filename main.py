import asyncio
import json
import logging
import os
import re
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.constants import ChatType
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from ai import ask_ai


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("crynova-ai")


# =========================================================
# روابط البوت والقناة (محدثة)
# =========================================================

BOT_LINK = "https://t.me/Crynova_bot"
CHANNEL_LINK = "https://t.me/Crynova_dz"


# =========================================================
# تحميل FAQ
# =========================================================

FAQ_DATA = None

def load_faq():
    global FAQ_DATA
    try:
        with open("faq.json", "r", encoding="utf-8") as f:
            FAQ_DATA = json.load(f)
        logger.info("✅ تم تحميل faq.json بنجاح")
    except Exception as e:
        logger.error(f"❌ فشل تحميل faq.json: {e}")
        FAQ_DATA = {
            "topics": [],
            "default_response": "🤔 مافهمت سؤالك بزاف. تقدر تسألني على المواضيع المتوفرة."
        }


def get_faq_response(user_message: str):
    if not FAQ_DATA:
        return None
    user_message_lower = user_message.lower()
    for topic in FAQ_DATA.get("topics", []):
        for keyword in topic.get("keywords", []):
            if keyword in user_message_lower:
                return topic.get("response", "")
    return None


ALLOWED_DOMAINS = {
    "crynova.app",
    "www.crynova.app",
    "t.me",
    "telegram.me",
}

INSULT_WORDS = {
    "كلب", "حمار", "غبي", "غبية", "تافه", "تافهة",
    "كذاب", "كذابة", "كذابين", "نصاب", "نصابة", "نصابين",
}

COMPLAINT_WORDS = {
    "نصب", "نصاب", "نصابة", "سرق", "سرقة", "احتيال",
    "مشكل", "مشكلة", "شكوى", "ما رجعليش", "ما وصلنيش",
    "خسرت", "فلوسي",
}

warnings = defaultdict(int)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(b"Crynova AI Bot is running!")

    def log_message(self, format, *args):
        return


def start_web_server():
    port = int(os.getenv("PORT", "10000"))
    while True:
        try:
            server = HTTPServer(("0.0.0.0", port), HealthHandler)
            logger.info("Health server started on port %s", port)
            server.serve_forever()
        except Exception as e:
            logger.exception("Health server error: %s", e)
            time.sleep(5)


URL_PATTERN = re.compile(
    r"(?i)\b(https?://[^\s]+|www\.[^\s]+|t\.me/[^\s]+|telegram\.me/[^\s]+)"
)

def extract_urls(text: str):
    if not text:
        return []
    return URL_PATTERN.findall(text)

def clean_url(url: str):
    return url.rstrip(".,!?;:)]}>\"'")

def get_domain(url: str):
    url = clean_url(url).lower()
    if url.startswith("https://"):
        url = url[8:]
    elif url.startswith("http://"):
        url = url[7:]
    elif url.startswith("www."):
        url = url[4:]
    return url.split("/")[0].split(":")[0]

def contains_external_link(text: str):
    for raw_url in extract_urls(text):
        if get_domain(raw_url) not in ALLOWED_DOMAINS:
            return True
    return False


def contains_insult(text: str):
    if not text:
        return False
    normalized = text.lower().replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    for word in INSULT_WORDS:
        if word in normalized:
            return True
    return False


def contains_complaint(text: str):
    if not text:
        return False
    for word in COMPLAINT_WORDS:
        if word in text.lower():
            return True
    return False


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_user:
        return False
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id
        )
        return member.status in ("administrator", "creator")
    except TelegramError as e:
        logger.warning("Admin check failed: %s", e)
        return False


async def delete_message(update: Update, reason: str):
    try:
        await update.message.delete()
        logger.info("Message deleted. Reason: %s", reason)
        return True
    except (Forbidden, BadRequest, TelegramError) as e:
        logger.warning("Delete error: %s", e)
        return False


async def warn_user(update: Update, reason: str):
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    warnings[user_id] += 1
    count = warnings[user_id]

    if count == 1:
        msg = f"⚠️ خويا، نبهتك برك.\n\nالسبب: {reason}\n\nخلي النقاش محترم، وإذا عندك مشكل مع المنصة اشرح المشكل ونعاونك."
    elif count == 2:
        msg = "⚠️ هذا ثاني تنبيه ليك.\nإذا عندك شكوى أو مشكل في Crynova اكتب التفاصيل بدون سب أو إهانة."
    else:
        msg = "🚫 راك تجاوزت عدد التنبيهات المسموح به.\nخلي النقاش محترم."

    try:
        await update.effective_chat.send_message(msg)
    except TelegramError as e:
        logger.warning("Could not send warning: %s", e)


async def moderate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return False
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return False
    if await is_admin(update, context):
        return False

    text = update.message.text

    if contains_external_link(text):
        if await delete_message(update, "external link"):
            await warn_user(update, "إرسال رابط خارجي داخل المجموعة")
        return True

    if contains_insult(text):
        if await delete_message(update, "insult"):
            await warn_user(update, "استعمال كلام مسيء أو إهانة")
        return True

    if contains_complaint(text):
        logger.info("Possible complaint from %s", update.effective_user.id)
        return False

    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    name = update.effective_user.first_name or "صديقي"
    await update.message.reply_text(
        f"👋 مرحبا {name}!\n\n"
        "أنا المساعد الذكي الرسمي تاع Crynova 🤖\n\n"
        "نقدر نعاونك في:\n"
        "💰 معلومات المنصة\n"
        "🎁 الإحالات والمكافآت\n"
        "📊 نشاط الحساب\n"
        "🚀 طريقة استعمال المنصة\n"
        "❓ الأسئلة والمشاكل\n\n"
        "🔗 روابط مهمة:\n"
        f"🤖 البوت: {BOT_LINK}\n"
        f"📢 القناة: {CHANNEL_LINK}\n\n"
        "اكتبلي سؤالك ونعاونك."
    )


async def channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📢 قناة Crynova الرسمية:\n{CHANNEL_LINK}")


async def bot_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🤖 بوت Crynova:\n{BOT_LINK}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    if await moderate_message(update, context):
        return

    user_message = update.message.text.strip()
    if not user_message:
        return

    faq_reply = get_faq_response(user_message)
    if faq_reply:
        await update.message.reply_text(faq_reply)
        return

    try:
        await update.message.chat.send_action(action="typing")
        response = await ask_ai(user_message)
        if not response:
            response = "سمحلي 😅 ما قدرتش نجاوبك حاليا.\nعاود جرب بعد شوية."
        await update.message.reply_text(response)
    except Exception as e:
        logger.exception("AI error: %s", e)
        await update.message.reply_text("⚠️ صرات مشكلة مؤقتة.\nعاود جرب بعد شوية.")


async def run_bot():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN غير موجود.")

    load_faq()

    while True:
        app = None
        try:
            app = Application.builder().token(token).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("channel", channel))
            app.add_handler(CommandHandler("bot", bot_link))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

            await app.initialize()
            await app.start()
            await app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)

            logger.info("Crynova AI Bot is ONLINE ✅")
            while True:
                await asyncio.sleep(30)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("Bot crashed: %s", e)
            await asyncio.sleep(10)
        finally:
            if app:
                try:
                    if app.updater:
                        await app.updater.stop()
                except:
                    pass
                try:
                    await app.stop()
                except:
                    pass
                try:
                    await app.shutdown()
                except:
                    pass


def main():
    logger.info("Starting Crynova AI service...")
    threading.Thread(target=start_web_server, daemon=True).start()
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
