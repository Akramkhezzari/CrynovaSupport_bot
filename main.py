import logging
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from ai import ask_ai


# ==============================
# إعداد التسجيل
# ==============================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ==============================
# أمر /start
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    name = user.first_name if user and user.first_name else "صديقي"

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


# ==============================
# استقبال الرسائل
# ==============================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return

    user_message = update.message.text.strip()

    if not user_message:
        return

    try:
        # إرسال السؤال إلى الذكاء الاصطناعي
        response = await ask_ai(user_message)

        if not response:
            response = (
                "سمحلي، ما قدرتش نجاوبك حاليا 😅\n"
                "عاود جرب بعد لحظات."
            )

        await update.message.reply_text(response)

    except Exception as error:
        logger.error("AI error: %s", error)

        await update.message.reply_text(
            "⚠️ صرات مشكلة مؤقتة في المساعد.\n"
            "عاود المحاولة بعد شوية."
        )


# ==============================
# تشغيل البوت
# ==============================

def main():

    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN غير موجود في متغيرات البيئة."
        )

    application = Application.builder().token(token).build()

    # الأوامر
    application.add_handler(
        CommandHandler("start", start)
    )

    # الرسائل النصية
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    logger.info("Crynova AI Bot is starting...")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ==============================
# نقطة البداية
# ==============================

if __name__ == "__main__":
    main()
