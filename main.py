import asyncio
import logging
import os
import threading
import time
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

logger = logging.getLogger("crynova-ai")


# ==========================================
# Health Server - Render
# ==========================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        self.wfile.write(
            b"Crynova AI Bot is running!"
        )

    def log_message(self, format, *args):
        return


def start_web_server():

    port = int(os.getenv("PORT", "10000"))

    while True:
        try:

            server = HTTPServer(
                ("0.0.0.0", port),
                HealthHandler
            )

            logger.info(
                "Health server started on port %s",
                port
            )

            server.serve_forever()

        except Exception as error:

            logger.error(
                "Health server error: %s",
                error
            )

            time.sleep(5)


# ==========================================
# /start
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        if not update.message:
            return

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

        await update.message.reply_text(
            message
        )

    except Exception as error:

        logger.exception(
            "Start handler error: %s",
            error
        )


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

        # إظهار الكتابة
        try:

            await update.message.chat.send_action(
                action="typing"
            )

        except Exception as error:

            logger.warning(
                "Typing action failed: %s",
                error
            )

        # الاتصال بـ Gemini
        response = await ask_ai(
            user_message
        )

        if not response:

            response = (
                "سمحلي 😅\n"
                "ما قدرتش نولد إجابة حاليا.\n"
                "عاود المحاولة بعد شوية."
            )

        # إرسال الرد
        await update.message.reply_text(
            response
        )

    except Exception as error:

        logger.exception(
            "Message handler error: %s",
            error
        )

        # نحاول نرسل رسالة خطأ للمستخدم
        try:

            await update.message.reply_text(
                "⚠️ صرات مشكلة مؤقتة.\n"
                "المساعد راه يحاول يعاود الاتصال، "
                "جرب بعد لحظات."
            )

        except Exception as send_error:

            logger.error(
                "Could not send error message: %s",
                send_error
            )


# ==========================================
# تشغيل Telegram
# ==========================================

async def run_bot():

    token = os.getenv(
        "TELEGRAM_BOT_TOKEN"
    )

    if not token:

        raise ValueError(
            "TELEGRAM_BOT_TOKEN غير موجود."
        )

    while True:

        application = None

        try:

            logger.info(
                "Starting Crynova Telegram Bot..."
            )

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

            # الرسائل النصية
            application.add_handler(
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_message
                )
            )

            # تشغيل التطبيق
            await application.initialize()

            await application.start()

            await application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=False
            )

            logger.info(
                "Crynova AI Bot is ONLINE ✅"
            )

            # إبقاء البوت يعمل
            while True:

                await asyncio.sleep(30)

        except asyncio.CancelledError:

            logger.info(
                "Bot task cancelled."
            )

            raise

        except Exception as error:

            logger.exception(
                "Telegram bot crashed: %s",
                error
            )

            logger.info(
                "Restarting bot in 10 seconds..."
            )

            await asyncio.sleep(10)

        finally:

            if application:

                try:

                    if application.updater:

                        await application.updater.stop()

                except Exception as error:

                    logger.warning(
                        "Updater stop error: %s",
                        error
                    )

                try:

                    await application.stop()

                except Exception as error:

                    logger.warning(
                        "Application stop error: %s",
                        error
                    )

                try:

                    await application.shutdown()

                except Exception as error:

                    logger.warning(
                        "Application shutdown error: %s",
                        error
                    )


# ==========================================
# Main
# ==========================================

def main():

    logger.info(
        "Starting Crynova AI service..."
    )

    # تشغيل Health Server في Thread
    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()

    # تشغيل Telegram مع إعادة المحاولة
    asyncio.run(
        run_bot()
    )


# ==========================================
# Start
# ==========================================

if __name__ == "__main__":
    main()
