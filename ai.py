import asyncio
import logging
from collections import defaultdict, deque

from google import genai
from google.genai import types

from config import settings
from knowledge import build_knowledge_text


logger = logging.getLogger("crynova.ai")


class CrynovaAI:

    def __init__(self):

        # =====================================================
        # GEMINI CLIENT
        # =====================================================

        self.client = genai.Client(
            api_key=settings.gemini_api_key
        )

        # =====================================================
        # MEMORY
        # =====================================================

        # ذاكرة قصيرة لكل مستخدم داخل كل محادثة
        #
        # key:
        # (chat_id, user_id)
        #
        # value:
        # آخر الرسائل
        self.history = defaultdict(
            lambda: deque(
                maxlen=settings.max_history
            )
        )

        # =====================================================
        # KNOWLEDGE
        # =====================================================

        self.knowledge = build_knowledge_text()

    # =========================================================
    # بناء Prompt
    # =========================================================

    def build_prompt(
        self,
        user_message: str,
        user_id: int,
        chat_id: int
    ) -> str:

        key = (
            chat_id,
            user_id
        )

        history = self.history[key]

        # تحويل الذاكرة إلى نص
        if history:

            history_text = "\n".join(
                f"{role}: {message}"
                for role, message in history
            )

        else:

            history_text = (
                "لا توجد محادثة سابقة."
            )

        # =====================================================
        # PROMPT
        # =====================================================

        prompt = f"""
أنت Crynova AI 🤖

أنت المساعد الذكي الرسمي لمنصة Crynova.

مهمتك هي مساعدة المستخدمين وشرح خدمات المنصة
والإجابة على الأسئلة المتعلقة بها بطريقة واضحة
ومحترمة وبالدارجة الجزائرية.

━━━━━━━━━━━━━━━━━━━━
🇩🇿 أسلوب الكلام
━━━━━━━━━━━━━━━━━━━━

- اهدر بالدارجة الجزائرية.
- خليك طبيعي وكأنك مساعد جزائري حقيقي.
- استعمل كلمات سهلة ومفهومة.
- ما تستعملش فصحى ثقيلة إلا إذا المستخدم طلبها.
- ما تكثرش الكلام بدون سبب.
- إذا السؤال يحتاج شرح، قسم الإجابة إلى خطوات.
- استعمل الإيموجي باعتدال.

مثال:

"إيه خويا 👍
باش تديرها، روح أولًا لـ...
ومن بعد اضغط على...
إذا حبيت نشرحلك خطوة بخطوة نقولك."

━━━━━━━━━━━━━━━━━━━━
🧠 قواعد الذكاء
━━━━━━━━━━━━━━━━━━━━

1. افهم السؤال قبل الإجابة.

2. إذا المستخدم يسقسي سؤال بسيط:
   جاوب مباشرة.

3. إذا المستخدم ما فهمش:
   عاود اشرح بطريقة أبسط.

4. إذا المستخدم طلب مثال:
   أعطه مثال واضح.

5. إذا المستخدم يسقسي عن المنصة:
   اعتمد على قاعدة المعرفة الموجودة أدناه.

6. ممنوع اختراع معلومات غير موجودة.

7. ممنوع اختراع:
   - أسعار
   - أرباح
   - مكافآت
   - نسب
   - شروط
   - مواعيد
   - أرصدة
   - معاملات
   - بيانات حسابات

8. إذا المعلومة غير موجودة:
   قل بصراحة:

   "المعلومة هذي ما عنديش عليها تأكيد حاليًا،
   الأفضل تتأكد من المنصة أو الدعم."

9. لا تطلب من المستخدم:
   - كلمة المرور
   - رمز Telegram
   - رمز التحقق
   - مفتاح API
   - المفتاح الخاص
   - معلومات سرية

10. لا تدعي أنك تستطيع الوصول إلى حساب المستخدم
    إلا إذا كان هناك Backend فعلي يوفر هذه البيانات.

━━━━━━━━━━━━━━━━━━━━
🛡️ الشكاوى
━━━━━━━━━━━━━━━━━━━━

إذا قال المستخدم:

"المنصة نصابة"

أو:

"خسرت فلوسي"

أو:

"ما وصلنيش السحب"

لا تهاجمه ولا تسكته.

رد بطريقة مهنية مثل:

"إذا عندك مشكل في المعاملة، نقدر نعاونك نفهم وين راه المشكل.
قولّي واش صرا بالضبط والخدمة اللي كنت تستعملها،
ونشوفو الخطوة المناسبة."

ممنوع اعتبار الشكوى دليلًا على صحة أو خطأ المنصة.

━━━━━━━━━━━━━━━━━━━━
🚫 الإهانات
━━━━━━━━━━━━━━━━━━━━

إذا المستخدم يسبك أو يسب أشخاصًا:

لا ترد بالسب.

قل مثلًا:

"خلينا بلا سب خويا 😅
إذا عندك مشكل قولي واش صرا ونحاولو نلقاو الحل."

━━━━━━━━━━━━━━━━━━━━
🎯 نطاق المساعد
━━━━━━━━━━━━━━━━━━━━

الأولوية:

1. Crynova
2. خدمات Crynova
3. الحساب
4. الإحالات
5. المكافآت
6. طريقة استعمال المنصة
7. المشاكل المتعلقة بالمنصة
8. الدعم والتوجيه

إذا السؤال خارج المنصة:

"نقدر نعاونك أكثر في الأمور المتعلقة بـ Crynova والمنصة."

━━━━━━━━━━━━━━━━━━━━
📚 قاعدة معرفة Crynova
━━━━━━━━━━━━━━━━━━━━

{self.knowledge}

━━━━━━━━━━━━━━━━━━━━
💬 المحادثة السابقة
━━━━━━━━━━━━━━━━━━━━

{history_text}

━━━━━━━━━━━━━━━━━━━━
👤 بيانات الجلسة
━━━━━━━━━━━━━━━━━━━━

User ID:
{user_id}

Chat ID:
{chat_id}

━━━━━━━━━━━━━━━━━━━━
📩 رسالة المستخدم
━━━━━━━━━━━━━━━━━━━━

{user_message}

━━━━━━━━━━━━━━━━━━━━
🤖 المطلوب
━━━━━━━━━━━━━━━━━━━━

جاوب المستخدم الآن.

خليك واضح، ذكي، مختصر قدر الإمكان،
وبالدارجة الجزائرية.

لا تقل إنك Gemini.

أنت:
Crynova AI 🤖
""".strip()

        return prompt

    # =========================================================
    # Gemini Request
    # =========================================================

    async def generate(
        self,
        prompt: str
    ):

        response = await asyncio.wait_for(

            self.client.aio.models.generate_content(

                model=settings.gemini_model,

                contents=prompt,

                config=types.GenerateContentConfig(

                    temperature=0.3,

                    max_output_tokens=700,

                ),
            ),

            timeout=settings.ai_timeout
        )

        return response

    # =========================================================
    # Answer
    # =========================================================

    async def answer(
        self,
        user_id: int,
        chat_id: int,
        message: str
    ) -> str:

        # =====================================================
        # LIMIT MESSAGE
        # =====================================================

        if len(message) > settings.max_message_length:

            message = message[
                :settings.max_message_length
            ]

        # =====================================================
        # MEMORY KEY
        # =====================================================

        key = (
            chat_id,
            user_id
        )

        # =====================================================
        # BUILD PROMPT
        # =====================================================

        prompt = self.build_prompt(
            user_message=message,
            user_id=user_id,
            chat_id=chat_id
        )

        # =====================================================
        # RETRY SYSTEM
        # =====================================================

        last_error = None

        for attempt in range(3):

            try:

                logger.info(
                    "Gemini request attempt %s/3",
                    attempt + 1
                )

                response = await self.generate(
                    prompt
                )

                # =================================================
                # GET TEXT
                # =================================================

                text = (
                    response.text
                    if response
                    else ""
                )

                text = (
                    text.strip()
                    if text
                    else ""
                )

                # =================================================
                # EMPTY RESPONSE
                # =================================================

                if not text:

                    raise RuntimeError(
                        "Gemini returned empty response"
                    )

                # =================================================
                # SAVE MEMORY
                # =================================================

                self.history[key].append(
                    (
                        "المستخدم",
                        message
                    )
                )

                self.history[key].append(
                    (
                        "Crynova AI",
                        text
                    )
                )

                logger.info(
                    "Gemini response received successfully"
                )

                return text

            # =====================================================
            # ERROR
            # =====================================================

            except asyncio.TimeoutError as error:

                last_error = error

                logger.warning(
                    "Gemini timeout. Attempt %s/3",
                    attempt + 1
                )

            except Exception as error:

                last_error = error

                logger.warning(
                    "Gemini error. Attempt %s/3: %s",
                    attempt + 1,
                    error
                )

            # =====================================================
            # WAIT BEFORE RETRY
            # =====================================================

            if attempt < 2:

                wait_time = 2 ** attempt

                logger.info(
                    "Retrying Gemini in %s seconds...",
                    wait_time
                )

                await asyncio.sleep(
                    wait_time
                )

        # =====================================================
        # ALL ATTEMPTS FAILED
        # =====================================================

        logger.error(
            "Gemini failed after all attempts: %s",
            last_error
        )

        raise RuntimeError(
            "Gemini temporarily unavailable"
        )
