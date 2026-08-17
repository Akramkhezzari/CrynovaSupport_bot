import os
import google.generativeai as genai
import logging

logger = logging.getLogger("crynova-ai")

# تهيئة Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("⚠️ GEMINI_API_KEY غير موجودة في المتغيرات البيئية")


async def ask_ai(prompt: str) -> str | None:
    """إرسال سؤال إلى Gemini والعودة بالرد."""
    if not GEMINI_API_KEY:
        return "❌ مفتاح Gemini غير موجود. يرجى إعداده في متغيرات البيئة."

    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
        return None
    except Exception as e:
        logger.exception(f"Gemini error: {e}")
        return None
