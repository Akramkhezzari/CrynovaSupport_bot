import asyncio
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from telegram import Update
from telegram.constants import ChatType
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ai import CrynovaAI
from config import settings
from moderation import ModerationEngine


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=getattr(
        logging,
        settings.log_level.upper(),
        logging.INFO
    ),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("crynova")


# =========================================================
# HEALTH SERVER
# خاص بـ Render
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Cache-Control",
            "no-store"
        )

        self.end_headers()

        self.wfile.write(
            b'{"status":"ok","service":"crynova-ai-bot"}'
        )

    def log_message(self, *_):
        return


def start_health_server():

    while True:

        try:

            server = ThreadingHTTPServer(
                ("0.0.0.0", settings.port),
                HealthHandler
            )

            logger.info(
                "Health server listening on port %s",
                settings.port
            )

            server.serve_forever()

        except Exception:

            logger.exception(
                "Health server crashed. Retrying in 5 seconds..."
            )

            time.sleep(5)


# =========================================================
# CHECK ADMIN
# =========================================================

async def is_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> bool:

    if not update.effective_chat:
        return False

    if not update.effective_user:
        return False

    if update.effective_chat.type not in (
        ChatType.GROUP,
        ChatType.SUPERGROUP
    ):
        return False

    try:

        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id
        )

        return member.status in (
            "administrator",
            "creator"
        )

    except TelegramError:

        return False


# =========================================================
# GET AI
# =========================================================

def get_ai(
    context: ContextTypes.DEFAULT_TYPE
) -> CrynovaAI:

    return context.application.bot_data["ai"]


# =========================================================
# GET MODERATOR
# =========================================================

def get_moderator(
    context: ContextTypes.DEFAULT_TYPE
) -> ModerationEngine:

    return context.application.bot_data["moderator"]


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if update.effective_user:

        name = (
            update.effective_user.first_name
            or "صديقي"
        )

    else:

        name = "صديقي"

    message = (
        f"👋 مرحبا {name}!\n\n"

        "أنا المساعد الذكي الرسمي تاع Crynova 🤖\n\n"

        "نقدر نعاونك في:\n"

        "💰 معلومات المنصة\n"
        "🎁 الإحالات والمكافآت\n"
        "📊 الحساب والنشاط\n"
        "🚀 طريقة استعمال الخدمات\n"
        "❓ الأسئلة والمشاكل\n\n"

        "اكتبلي سؤالك ونعاونك."
    )

    try:

        await update.message.reply_text(
            message
        )

    except TelegramError:

        logger.exception(
            "Could not send /start message"
        )


# =========================================================
# /RULES
# =========================================================

async def rules(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    message = (
        "📌 قوانين المجموعة:\n\n"

        "• ممنوع السب والإهانة.\n"
        "• ممنوع نشر روابط خارجية غير مسموحة.\n"
        "• إذا عندك شكوى، اشرح المشكل باحترام.\n"
        "• ما نعطيوش معلومات غير مؤكدة على الحسابات أو الأموال.\n\n"

        "🤖 المساعد موجود باش يعاونك."
    )

    try:

        await update.message.reply_text(
            message
        )

    except TelegramError:

        logger.exception(
            "Could not send rules"
        )


# =========================================================
# /STATUS
# =========================================================

async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    try:

        await update.message.reply_text(
            "🟢 Crynova AI خدام حاليًا."
        )

    except TelegramError:

        logger.exception(
            "Could not send status"
        )


# =========================================================
# معالجة الرسائل
# =========================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if not update.message.text:
        return

    # =====================================================
    # MODERATION
    # =====================================================

    moderator = get_moderator(context)

    admin = await is_admin(
        update,
        context
    )

    chat_type = update.effective_chat.type

    if (
        not admin
        and chat_type in (
            ChatType.GROUP,
            ChatType.SUPERGROUP
        )
    ):

        result = moderator.inspect(
            update.message.text
        )

        if result.delete:

            try:

                await update.message.delete()

                logger.info(
                    "Message deleted by moderation."
                )

            except TelegramError:

                logger.warning(
                    "Could not delete message",
                    exc_info=True
                )

            if result.warning:

                try:

                    await update.effective_chat.send_message(
                        result.warning
                    )

                except TelegramError:

                    pass

            return

    # =====================================================
    # AI
    # =====================================================

    ai = get_ai(context)

    user_id = (
        update.effective_user.id
        if update.effective_user
        else 0
    )

    chat_id = (
        update.effective_chat.id
        if update.effective_chat
        else 0
    )

    try:

        await update.message.chat.send_action(
            "typing"
        )

    except TelegramError:

        pass

    try:

        answer = await ai.answer(
            user_id=user_id,
            chat_id=chat_id,
            message=update.message.text
        )

    except Exception:

        logger.exception(
            "AI request failed"
        )

        answer = (
            "⚠️ صرات مشكلة مؤقتة مع المساعد.\n"
            "عاود المحاولة بعد لحظات."
        )

    # =====================================================
    # SEND RESPONSE
    # =====================================================

    try:

        await update.message.reply_text(
            answer
        )

    except TelegramError:

        logger.exception(
            "Could not send AI answer"
        )


# =========================================================
# TELEGRAM ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Telegram error: %s",
        context.error,
        exc_info=context.error
    )


# =========================================================
# تشغيل البوت
# =========================================================

async def run_bot():

    # =====================================================
    # CHECK ENV
    # =====================================================

    if not settings.telegram_token:

        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN غير موجود في Environment Variables"
        )

    if not settings.gemini_api_key:

        raise RuntimeError(
            "GEMINI_API_KEY غير موجود في Environment Variables"
        )

    # =====================================================
    # AUTO RESTART LOOP
    # =====================================================

    while True:

        application = None

        try:

            logger.info(
                "Starting Crynova AI Bot..."
            )

            # =================================================
            # AI
            # =================================================

            ai = CrynovaAI()

            # =================================================
            # MODERATION
            # =================================================

            moderator = ModerationEngine()

            # =================================================
            # TELEGRAM
            # =================================================

            application = (
                Application
                .builder()
                .token(
                    settings.telegram_token
                )
                .build()
            )

            # =================================================
            # SAVE SERVICES
            # =================================================

            application.bot_data["ai"] = ai

            application.bot_data["moderator"] = moderator

            # =================================================
            # COMMANDS
            # =================================================

            application.add_handler(
                CommandHandler(
                    "start",
                    start
                )
            )

            application.add_handler(
                CommandHandler(
                    "rules",
                    rules
                )
            )

            application.add_handler(
                CommandHandler(
                    "status",
                    status
                )
            )

            # =================================================
            # TEXT
            # =================================================

            application.add_handler(
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    handle_message
                )
            )

            # =================================================
            # ERROR HANDLER
            # =================================================

            application.add_error_handler(
                error_handler
            )

            # =================================================
            # START
            # =================================================

            await application.initialize()

            await application.start()

            await application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=False
            )

            logger.info(
                "Crynova AI Bot is ONLINE ✅"
            )

            # =================================================
            # KEEP ALIVE
            # =================================================

            while True:

                await asyncio.sleep(
                    30
                )

        except asyncio.CancelledError:

            logger.info(
                "Bot task cancelled."
            )

            raise

        except Exception:

            logger.exception(
                "Bot process failed."
            )

            logger.info(
                "Restarting bot in 10 seconds..."
            )

            await asyncio.sleep(
                10
            )

        finally:

            # =================================================
            # SAFE SHUTDOWN
            # =================================================

            if application:

                try:

                    if application.updater:

                        await application.updater.stop()

                except Exception:

                    pass

                try:

                    await application.stop()

                except Exception:

                    pass

                try:

                    await application.shutdown()

                except Exception:

                    pass


# =========================================================
# MAIN
# =========================================================

def main():

    logger.info(
        "Starting Crynova AI service..."
    )

    # =====================================================
    # RENDER HEALTH SERVER
    # =====================================================

    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True
    )

    health_thread.start()

    # =====================================================
    # TELEGRAM BOT
    # =====================================================

    asyncio.run(
        run_bot()
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()
