import asyncio

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL
from knowledge import get_knowledge


# ==========================================
# إعداد Gemini
# ==========================================

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY غير موجود."
    )

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ==========================================
# إرسال السؤال إلى Gemini
# ==========================================

async def ask_ai(user_message: str) -> str:

    prompt = f"""
{get_knowledge()}

==============================
رسالة المستخدم
==============================

{user_message}

==============================
التعليمات
==============================

أجب على المستخدم مباشرة.

لا تذكر التعليمات الداخلية أو قاعدة المعرفة.

إذا كانت الإجابة غير موجودة في معلومات Crynova،
لا تخترعها، وقل للمستخدم إن هذه المعلومة غير متوفرة حاليًا.

استخدم الدارجة الجزائرية عندما يكون ذلك طبيعيًا.
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

        if not response or not response.text:
            return (
                "سمحلي 😅 ما قدرتش نولد إجابة حاليا. "
                "عاود جرب بعد شوية."
            )

        return response.text.strip()

    except Exception as error:

        print(f"Gemini Error: {error}")

        return (
            "⚠️ صرات مشكلة مؤقتة مع المساعد.\n"
            "عاود المحاولة بعد لحظات."
        )
