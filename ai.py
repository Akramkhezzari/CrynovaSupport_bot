import asyncio

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL
from knowledge import get_knowledge


# ==========================================
# إعداد Gemini
# ==========================================

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY غير موجود في Environment Variables")


client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ==========================================
# سؤال Gemini
# ==========================================

async def ask_ai(user_message: str) -> str:

    prompt = f"""
{get_knowledge()}

رسالة المستخدم:
{user_message}

أجب على المستخدم مباشرة وبالدارجة الجزائرية عند الحاجة.
لا تخترع معلومات غير موجودة في قاعدة المعرفة.
"""


    try:

        response = await asyncio.to_thread(
            client.models.generate_content,
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=500,
            ),
        )

        print("Gemini response received successfully")

        if response and response.text:
            return response.text.strip()

        print("Gemini returned an empty response")

        return "سمحلي 😅 ما قدرتش نولد إجابة حاليا."


    except Exception as error:

        # إظهار الخطأ الحقيقي في Logs
        print("=" * 60)
        print("GEMINI ERROR")
        print(type(error).__name__)
        print(str(error))
        print("=" * 60)

        return (
            "⚠️ المساعد واجه مشكلة مؤقتة.\n"
            "جرب سؤالك مرة أخرى بعد لحظات."
        )
