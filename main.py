import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from ai import ask_ai


# ==========================================
# Logging
# ==========================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ==========================================
# Web Server
# Render يحتاج Port مفتوح
# ==========================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

        self.wfile.write(
            b"Crynova AI Bot is running!"
        )

    def log_message(self, format, *args):
        return


def start_web_server():

    port = int(os.environ.get("PORT", 10000))

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    logger.info(
        f"Health server running on port {port}"
    )

    server.serve_forever()


# ==========================================
# /start
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    name = (
        user.first_name
        if user and user.first_name
        else "صديقي"
    )

    message = (
        f"👋 مرحبا {name}!\n\n"
        "أنا المساعد الذكي الرسمي لمنصة Crynova 🤖\n\n"
        "نقدر نعاونك في:\n"
        "💰 معلومات المنصة\n"
        "🎁 المكافآت والإحالات\n"
        "📊 متابعة النشاط\n"
        "🚀 كيفية استعمال الخدمات\n\n"
        "اكتبلي سؤالك ونعاونك."
    )

    await update.message.reply_text(message)


# ==========================================
# استقبال الرسائل
# ==========================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if not update.message.text:
        return

    user_message = update.message.text.strip()

    if not user_message:
        return

    try:

        await update.message.chat.send_action(
            "typing"
        )

        response = await ask_ai(
            user_message
        )

        if not response:

            response = (
                "سمحلي 😅\n"
                "ما قدرتش نجاوبك حاليا."
            )

        await update.message.reply_text(
            response
        )

    except Exception as error:

        logger.error(
            f"Message error: {error}"
        )

        await update.message.reply_text(
            "⚠️ صرات مشكلة مؤقتة مع المساعد.\n"
            "عاود المحاولة بعد لحظات."
        )


# ==========================================
# تشغيل البوت
# ==========================================

def main():

    token = os.getenv(
        "TELEGRAM_BOT_TOKEN"
    )

    if not token:

        raise ValueError(
            "TELEGRAM_BOT_TOKEN غير موجود."
        )

    # تشغيل Web Server في Thread مستقل
    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()

    # إنشاء Telegram Application
    application = (
        Application
        .builder()
        .token(token)
        .build()
    )

    # /start
    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # الرسائل
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    logger.info(
        "Crynova AI Bot is starting..."
    )

    # تشغيل Telegram
    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ==========================================
# Start
# ==========================================

if __name__ == "__main__":
    main()
