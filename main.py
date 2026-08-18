import asyncio
import logging
import threading
import time
from collections import defaultdict, deque
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
# HEALTH SERVER - RENDER
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

        server = None

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

        finally:

            if server:

                try:
                    server.server_close()
                except Exception:
                    pass


# =========================================================
# RUNTIME RATE LIMITER
# =========================================================

class UserRateLimiter:

    def __init__(
        self,
        max_requests=8,
        window_seconds=60
    ):

        self.max_requests = max_requests
        self.window_seconds = window_seconds

        self.requests = defaultdict(deque)

        self.lock = asyncio.Lock()

    async def allowed(
        self,
        user_id: int
    ) -> bool:

        now = time.monotonic()

        async with self.lock:

            queue = self.requests[user_id]

            # حذف الطلبات القديمة
            while queue:

                if (
                    now - queue[0]
                    > self.window_seconds
                ):

                    queue.popleft()

                else:

                    break

            # تجاوز الحد
            if len(queue) >= self.max_requests:

                return False

            queue.append(now)

            return True

    async def cleanup(self):

        now = time.monotonic()

        async with self.lock:

            empty_users = []

            for user_id, queue in self.requests.items():

                while queue:

                    if (
                        now - queue[0]
                        > self.window_seconds
                    ):

                        queue.popleft()

                    else:

                        break

                if not queue:

                    empty_users.append(
                        user_id
                    )

            for user_id in empty_users:

                self.requests.pop(
                    user_id,
                    None
                )


# =========================================================
# USER MESSAGE LOCK
# =========================================================

class UserMessageManager:

    def __init__(self):

        self.locks = defaultdict(
            asyncio.Lock
        )

    def get_lock(
        self,
        user_id: int,
        chat_id: int
    ):

        return self.locks[
            (chat_id, user_id)
        ]


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

    except Exception:

        logger.exception(
            "Admin check failed"
        )

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
# GET RATE LIMITER
# =========================================================

def get_rate_limiter(
    context: ContextTypes.DEFAULT_TYPE
) -> UserRateLimiter:

    return context.application.bot_data[
        "rate_limiter"
    ]


# =========================================================
# GET USER MANAGER
# =========================================================

def get_user_manager(
    context: ContextTypes.DEFAULT_TYPE
) -> UserMessageManager:

    return context.application.bot_data[
        "user_manager"
    ]


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
        "• ما نعطيوش معلومات غير مؤكدة على الحسابات أو الأموال.\n"
        "• المساعد مخصص لمواضيع Crynova فقط.\n\n"

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
            "🟢 Crynova AI خدام حاليًا.\n\n"
            "🤖 المساعد جاهز لمساعدتك في الأمور المتعلقة بالمنصة."
        )

    except TelegramError:

        logger.exception(
            "Could not send status"
        )


# =========================================================
# SEND SAFE MESSAGE
# =========================================================

async def safe_reply(
    update: Update,
    text: str
):

    if not update.message:
        return

    try:

        await update.message.reply_text(
            text
        )

    except TelegramError:

        logger.exception(
            "Could not send Telegram reply"
        )

    except Exception:

        logger.exception(
            "Unexpected reply error"
        )


# =========================================================
# MODERATION
# =========================================================

async def moderate_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> bool:

    if not update.message:
        return False

    if not update.effective_chat:
        return False

    if update.effective_chat.type not in (
        ChatType.GROUP,
        ChatType.SUPERGROUP
    ):
        return False

    try:

        admin = await is_admin(
            update,
            context
        )

        if admin:
            return False

        moderator = get_moderator(
            context
        )

        result = moderator.inspect(
            update.message.text
        )

        if not result.delete:
            return False

        # =================================================
        # DELETE
        # =================================================

        try:

            await update.message.delete()

            logger.info(
                "Message deleted by moderation | chat=%s | user=%s",
                update.effective_chat.id,
                update.effective_user.id
                if update.effective_user
                else 0
            )

        except TelegramError:

            logger.warning(
                "Could not delete moderated message",
                exc_info=True
            )

        # =================================================
        # WARNING
        # =================================================

        if result.warning:

            try:

                await update.effective_chat.send_message(
                    result.warning
                )

            except TelegramError:

                logger.warning(
                    "Could not send moderation warning"
                )

        return True

    except Exception:

        logger.exception(
            "Moderation failed"
        )

        # إذا moderation نفسها فشلت،
        # ما نوقفوش البوت كامل.
        return False


# =========================================================
# HANDLE MESSAGE
# =========================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        if not update.message:
            return

        if not update.message.text:
            return

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

        message = (
            update.message.text.strip()
        )

        if not message:
            return

        # =================================================
        # MODERATION
        # =================================================

        deleted = await moderate_message(
            update,
            context
        )

        if deleted:
            return

        # =================================================
        # RATE LIMIT
        # =================================================

        limiter = get_rate_limiter(
            context
        )

        allowed = await limiter.allowed(
            user_id
        )

        if not allowed:

            await safe_reply(
                update,
                "⏳ خويا راك تبعت بسرعة شوية 😅\n"
                "استنى لحظات وعاود جرب."
            )

            return

        # =================================================
        # USER LOCK
        # =================================================

        manager = get_user_manager(
            context
        )

        lock = manager.get_lock(
            user_id,
            chat_id
        )

        # =================================================
        # PROCESS USER MESSAGE
        # =================================================

        async with lock:

            # =============================================
            # TYPING
            # =============================================

            try:

                await update.message.chat.send_action(
                    "typing"
                )

            except TelegramError:

                pass

            # =============================================
            # AI
            # =============================================

            ai = get_ai(
                context
            )

            try:

                answer = await ai.answer(
                    user_id=user_id,
                    chat_id=chat_id,
                    message=message
                )

            except asyncio.CancelledError:

                raise

            except Exception:

                logger.exception(
                    "AI request failed | user=%s | chat=%s",
                    user_id,
                    chat_id
                )

                answer = (
                    "⚠️ صرات مشكلة مؤقتة مع المساعد.\n\n"
                    "عاود المحاولة بعد لحظات."
                )

            # =============================================
            # RESPONSE
            # =============================================

            await safe_reply(
                update,
                answer
            )

    except asyncio.CancelledError:

        raise

    except Exception:

        # مهم جدًا:
        # أي خطأ غير متوقع داخل مستخدم واحد
        # ما يقتلش الـTelegram polling.
        logger.exception(
            "Unhandled message processing error"
        )


# =========================================================
# TELEGRAM ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    error = context.error

    logger.error(
        "Telegram error: %s",
        error,
        exc_info=error
    )


# =========================================================
# RATE LIMIT CLEANUP
# =========================================================

async def rate_limit_cleanup(
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        limiter = get_rate_limiter(
            context
        )

        await limiter.cleanup()

    except Exception:

        logger.exception(
            "Rate limiter cleanup failed"
        )


# =========================================================
# BUILD APPLICATION
# =========================================================

def build_application():

    application = (
        Application
        .builder()
        .token(
            settings.telegram_token
        )
        .concurrent_updates(
            32
        )
        .build()
    )

    # =====================================================
    # SERVICES
    # =====================================================

    application.bot_data["ai"] = (
        CrynovaAI()
    )

    application.bot_data["moderator"] = (
        ModerationEngine()
    )

    application.bot_data["rate_limiter"] = (
        UserRateLimiter(
            max_requests=8,
            window_seconds=60
        )
    )

    application.bot_data["user_manager"] = (
        UserMessageManager()
    )

    # =====================================================
    # COMMANDS
    # =====================================================

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

    # =====================================================
    # TEXT
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_message
        )
    )

    # =====================================================
    # ERROR HANDLER
    # =====================================================

    application.add_error_handler(
        error_handler
    )

    # =====================================================
    # CLEANUP JOB
    # =====================================================

    application.job_queue.run_repeating(
        rate_limit_cleanup,
        interval=300,
        first=300
    )

    return application


# =========================================================
# RUN BOT
# =========================================================

async def run_bot():

    # =====================================================
    # ENVIRONMENT CHECK
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
    # RESTART LOOP
    # =====================================================

    restart_delay = 10

    while True:

        application = None

        try:

            logger.info(
                "Starting Crynova AI Bot..."
            )

            application = build_application()

            # =================================================
            # INITIALIZE
            # =================================================

            await application.initialize()

            # =================================================
            # START
            # =================================================

            await application.start()

            # =================================================
            # POLLING
            # =================================================

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

                # نتأكد أن updater مازال شغال
                if (
                    application.updater
                    and not application.updater.running
                ):

                    logger.warning(
                        "Telegram updater stopped unexpectedly."
                    )

                    break

        except asyncio.CancelledError:

            logger.info(
                "Bot task cancelled."
            )

            raise

        except Exception as error:

            logger.exception(
                "Bot process failed: %s",
                error
            )

            logger.info(
                "Restarting bot in %s seconds...",
                restart_delay
            )

            await asyncio.sleep(
                restart_delay
            )

        finally:

            # =================================================
            # STOP POLLING
            # =================================================

            if application:

                try:

                    if application.updater:

                        if application.updater.running:

                            await application.updater.stop()

                except Exception:

                    logger.exception(
                        "Error while stopping updater"
                    )

                # =============================================
                # STOP APPLICATION
                # =============================================

                try:

                    if application.running:

                        await application.stop()

                except Exception:

                    logger.exception(
                        "Error while stopping application"
                    )

                # =============================================
                # SHUTDOWN
                # =============================================

                try:

                    await application.shutdown()

                except Exception:

                    logger.exception(
                        "Error while shutting down application"
                    )


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
    # TELEGRAM
    # =====================================================

    asyncio.run(
        run_bot()
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()
