import asyncio
import logging
from collections import defaultdict, deque

from google import genai
from google.genai import types

from config import settings
from knowledge import (
    build_knowledge_text,
    is_platform_question,
    get_best_answer,
    OUT_OF_SCOPE_RESPONSE,
)


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

        self.history = defaultdict(
            lambda: deque(
                maxlen=settings.max_history
            )
        )

        # =====================================================
        # KNOWLEDGE
        # =====================================================

        self.knowledge = build_knowledge_text()

        # =====================================================
        # CONCURRENCY
        # =====================================================

        # أقصى عدد طلبات Gemini في نفس الوقت.
        #
        # مهم:
        # إذا 20 شخص يهدروا في نفس اللحظة،
        # ما نبعثوش 20 طلب دفعة واحدة.
        self.gemini_semaphore = asyncio.Semaphore(5)

        # =====================================================
        # USER LOCKS
        # =====================================================

        # كل مستخدم يقدر تكون عنده محادثته الخاصة.
        #
        # هذا يمنع رسالتين من نفس المستخدم من الدخول
        # على نفس الذاكرة في نفس اللحظة.
        self.user_locks = defaultdict(asyncio.Lock)

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

        if history:

            history_text = "\n".join(
                f"{role}: {message}"
                for role, message in history
            )

        else:

            history_text = (
                "لا توجد محادثة سابقة."
            )

        prompt = f"""
أنت Crynova AI 🤖

أنت المساعد الذكي الرسمي لمنصة Crynova.

مهمتك الوحيدة هي مساعدة المستخدمين في الأمور
المتعلقة بمنصة Crynova.

━━━━━━━━━━━━━━━━━━━━
🇩🇿 أسلوب الكلام
━━━━━━━━━━━━━━━━━━━━

- اهدر بالدارجة الجزائرية.
- خليك طبيعي ومحترم.
- استعمل كلمات بسيطة.
- ما تستعملش فصحى ثقيلة إلا إذا المستخدم طلبها.
- جاوب مباشرة.
- إذا السؤال يحتاج شرح، قسمه إلى خطوات.
- استعمل الإيموجي باعتدال.
- لا تكرر نفس الكلام بلا سبب.

━━━━━━━━━━━━━━━━━━━━
🎯 نطاق المساعد
━━━━━━━━━━━━━━━━━━━━

المواضيع المسموحة:

- Crynova
- الحساب
- تسجيل الدخول
- الإحالات
- المكافآت
- النشاط
- الخدمات الرسمية
- المشاكل المتعلقة بالمنصة
- الدعم
- الأمان
- الشكاوى المتعلقة بالمنصة

إذا كان السؤال خارج Crynova:

لا تجيب عن الموضوع الخارجي.

قل فقط:

"نقدر نعاونك غير في الأمور المتعلقة بـ Crynova 🤖
إذا عندك سؤال على الحساب، الإحالات، المكافآت أو أي خدمة
داخل المنصة قولّي ونعاونك."

━━━━━━━━━━━━━━━━━━━━
🧠 قاعدة المعرفة
━━━━━━━━━━━━━━━━━━━━

المعلومات التالية هي المصدر الأساسي للمعلومات:

{self.knowledge}

ممنوع اختراع معلومات غير موجودة في قاعدة المعرفة.

ممنوع اختراع:

- أسعار
- نسب
- أرباح
- مكافآت
- شروط
- أوقات
- أرصدة
- معاملات
- بيانات المستخدمين

إذا المعلومة غير موجودة:

قل:

"المعلومة هذي ما عنديش عليها تأكيد حاليًا،
الأفضل تتأكد من المنصة أو الدعم الرسمي."

━━━━━━━━━━━━━━━━━━━━
🔐 الخصوصية
━━━━━━━━━━━━━━━━━━━━

لا تطلب أبدًا:

- كلمة السر
- رمز التحقق
- Telegram code
- API key
- Private key
- معلومات سرية

ولا تدعي أنك تشوف حساب المستخدم
أو رصيده أو معاملاته إلا إذا كان Backend
رسمي يرسل هذه البيانات.

━━━━━━━━━━━━━━━━━━━━
🛡️ الشكاوى
━━━━━━━━━━━━━━━━━━━━

إذا المستخدم قال:

"المنصة نصابة"

"خسرت فلوسي"

"السحب ما وصلنيش"

"عندي مشكل"

لا تهاجمه ولا تحذف شكواه ولا تعتبر كلامه
حقيقة مؤكدة.

رد باحترام:

"فهمتك خويا 👍
إذا عندك مشكل مع المنصة، اشرحلي واش صرا
ونحاول نوجهك للخطوة المناسبة."

━━━━━━━━━━━━━━━━━━━━
🚫 الإهانات
━━━━━━━━━━━━━━━━━━━━

إذا المستخدم سب:

لا تسبه.

قل:

"خلينا بلا سب خويا 😅
إذا عندك مشكل قولي واش صرا ونحاولو نلقاو الحل."

━━━━━━━━━━━━━━━━━━━━
💬 الذاكرة
━━━━━━━━━━━━━━━━━━━━

استعمل المحادثة السابقة لفهم السياق فقط.

لا تعتبر معلومات الذاكرة حقيقة رسمية
إذا كانت تتعارض مع قاعدة المعرفة.

━━━━━━━━━━━━━━━━━━━━
📚 المحادثة السابقة
━━━━━━━━━━━━━━━━━━━━

{history_text}

━━━━━━━━━━━━━━━━━━━━
👤 معلومات الجلسة
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

خليك واضح، طبيعي، مختصر،
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

        # =====================================================
        # حماية من كثرة الطلبات
        # =====================================================

        async with self.gemini_semaphore:

            response = await asyncio.wait_for(

                self.client.aio.models.generate_content(

                    model=settings.gemini_model,

                    contents=prompt,

                    config=types.GenerateContentConfig(

                        temperature=0.3,

                        max_output_tokens=700,

                        # منع Automatic Function Calling
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            disable=True
                        ),
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
        # تنظيف الرسالة
        # =====================================================

        message = (
            message or ""
        ).strip()

        if not message:

            return (
                "قولّي واش حاب تعرف على Crynova 🤖"
            )

        # =====================================================
        # LIMIT MESSAGE
        # =====================================================

        if len(message) > settings.max_message_length:

            message = message[
                :settings.max_message_length
            ]

        # =====================================================
        # OUT OF SCOPE FILTER
        # =====================================================

        if not is_platform_question(message):

            return OUT_OF_SCOPE_RESPONSE

        # =====================================================
        # MEMORY KEY
        # =====================================================

        key = (
            chat_id,
            user_id
        )

        # =====================================================
        # USER LOCK
        # =====================================================

        lock = self.user_locks[key]

        async with lock:

            # =================================================
            # DIRECT KNOWLEDGE ANSWER
            # =================================================

            direct_answer = get_best_answer(
                message
            )

            # -------------------------------------------------
            # ملاحظة:
            #
            # ما نرجعوش دائمًا الإجابة المباشرة.
            #
            # نخلي Gemini يشرحها إذا السؤال يحتاج
            # سياق أو شرح إضافي.
            # -------------------------------------------------

            prompt = self.build_prompt(
                user_message=message,
                user_id=user_id,
                chat_id=chat_id
            )

            # =================================================
            # RETRY
            # =================================================

            last_error = None

            for attempt in range(3):

                try:

                    logger.info(
                        "Gemini request attempt %s/3 | user=%s | chat=%s",
                        attempt + 1,
                        user_id,
                        chat_id
                    )

                    response = await self.generate(
                        prompt
                    )

                    # =========================================
                    # GET TEXT
                    # =========================================

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

                    # =========================================
                    # EMPTY RESPONSE
                    # =========================================

                    if not text:

                        # إذا Gemini رجع فارغ،
                        # نستعمل إجابة قاعدة المعرفة
                        if direct_answer:

                            text = direct_answer

                        else:

                            raise RuntimeError(
                                "Gemini returned empty response"
                            )

                    # =========================================
                    # SAVE USER MESSAGE
                    # =========================================

                    self.history[key].append(
                        (
                            "المستخدم",
                            message
                        )
                    )

                    # =========================================
                    # SAVE AI RESPONSE
                    # =========================================

                    self.history[key].append(
                        (
                            "Crynova AI",
                            text
                        )
                    )

                    logger.info(
                        "Gemini response received successfully | user=%s",
                        user_id
                    )

                    return text

                # =============================================
                # TIMEOUT
                # =============================================

                except asyncio.TimeoutError as error:

                    last_error = error

                    logger.warning(
                        "Gemini timeout | attempt=%s/3 | user=%s",
                        attempt + 1,
                        user_id
                    )

                # =============================================
                # OTHER ERRORS
                # =============================================

                except Exception as error:

                    last_error = error

                    logger.warning(
                        "Gemini error | attempt=%s/3 | user=%s | %s",
                        attempt + 1,
                        user_id,
                        error
                    )

                    # -----------------------------------------
                    # AUTH ERROR
                    # -----------------------------------------

                    error_text = str(
                        error
                    ).lower()

                    if (
                        "401" in error_text
                        or "unauthenticated" in error_text
                        or "authentication" in error_text
                    ):

                        logger.error(
                            "Gemini authentication error. "
                            "Check GEMINI_API_KEY."
                        )

                        break

                # =============================================
                # RETRY DELAY
                # =============================================

                if attempt < 2:

                    wait_time = 2 ** attempt

                    logger.info(
                        "Retrying Gemini in %s seconds...",
                        wait_time
                    )

                    await asyncio.sleep(
                        wait_time
                    )

            # =================================================
            # FALLBACK
            # =================================================

            logger.error(
                "Gemini failed after all attempts: %s",
                last_error
            )

            # إذا عندنا إجابة موثوقة من قاعدة المعرفة،
            # نرجعها بدل ما نرسل Error للمستخدم.
            if direct_answer:

                self.history[key].append(
                    (
                        "المستخدم",
                        message
                    )
                )

                self.history[key].append(
                    (
                        "Crynova AI",
                        direct_answer
                    )
                )

                return direct_answer

            # =================================================
            # FINAL FALLBACK
            # =================================================

            return (
                "سمحلي خويا، المساعد الذكي راهو مشغول "
                "شوية حاليًا 😅\n\n"
                "عاود جرب بعد لحظات، وما تحتاجش تعاود "
                "تبعت نفس الرسالة بزاف مرات."
            )
