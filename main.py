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
# RATE LIMITER
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

            # إذا تجاوز المستخدم الحد
            if len(queue) >= self.max_requests:

                return False

            queue.append(now)

            return True


# =========================================================
# USER MESSAGE MANAGER
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
# SAFE REPLY
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

    await safe_reply(
        update,
        message
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
        "• ما نعطيوش معلومات غير مؤكدة.\n"
        "• المساعد مخصص لمواضيع Crynova.\n\n"

        "🤖 المساعد موجود باش يعاونك."
    )

    await safe_reply(
        update,
        message
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

    await safe_reply(
        update,
        "🟢 Crynova AI خدام حاليًا.\n\n"
        "🤖 المساعد جاهز لمساعدتك في الأمور المتعلقة بالمنصة."
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

        # الأدمن ما نطبقوش عليه الحذف
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
        # DELETE MESSAGE
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

        message = (
            update.message.text.strip()
        )

        if not message:
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
                "استنى شوية وعاود جرب."
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

            except Exception as error:

                logger.exception(
                    "AI request failed | user=%s | chat=%s | error=%s",
                    user_id,
                    chat_id,
                    error
                )

                answer = (
                    "⚠️ صرات مشكلة مؤقتة مع المساعد.\n\n"
                    "عاود المحاولة بعد لحظات."
                )

            # =============================================
            # SEND ANSWER
            # =============================================

            await safe_reply(
                update,
                answer
            )

    except asyncio.CancelledError:

        raise

    except Exception:

        # خطأ في مستخدم واحد لا يوقف البوت
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
    # TEXT MESSAGES
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
    # IMPORTANT
    # =====================================================
    #
    # لا نستعمل:
    #
    # application.job_queue.run_repeating(...)
    #
    # لأن JobQueue غير مفعلة في إعدادات
    # python-telegram-bot الحالية.
    #
    # الـRateLimiter ينظف الطلبات القديمة
    # تلقائيًا عند وصول طلب جديد.
    #
    # =====================================================

    return application


# =========================================================
# RUN BOT
# =========================================================

async def run_bot():

    # =====================================================
    # ENVIRONMENT
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
    # AUTO RESTART
    # =====================================================

    restart_delay = 10

    while True:

        application = None

        try:

            logger.info(
                "Starting Crynova AI Bot..."
            )

            # =================================================
            # BUILD
            # =================================================

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
            # START POLLING
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

                # إذا توقف updater لأي سبب
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
            # STOP UPDATER
            # =================================================

            if application:

                try:

                    if (
                        application.updater
                        and application.updater.running
                    ):

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
    # TELEGRAM BOT
    # =====================================================

    asyncio.run(
        run_bot()
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()
