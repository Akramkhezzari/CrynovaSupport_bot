import re
import logging
from dataclasses import dataclass
from urllib.parse import urlparse

from config import settings


logger = logging.getLogger("crynova.moderation")


# =========================================================
# الروابط
# =========================================================

URL_PATTERN = re.compile(
    r"(?i)"
    r"(?:"
    r"https?://[^\s<>()]+"
    r"|www\.[^\s<>()]+"
    r"|t\.me/[^\s<>()]+"
    r"|telegram\.me/[^\s<>()]+"
    r")"
)


# =========================================================
# كلمات الإهانة
# =========================================================
#
# هذه قائمة أولية.
# تقدر تزيد كلمات خاصة بالمجموعة لاحقًا.
#

INSULT_WORDS = {
    "كلب",
    "كلبة",
    "حمار",
    "حمارة",
    "غبي",
    "غبية",
    "تافه",
    "تافهة",
    "كذاب",
    "كذابة",
    "كذابين",
    "حقير",
    "حقيرة",
    "وسخ",
    "وسخة",
}


# =========================================================
# كلمات الشكاوى
# =========================================================
#
# مهم:
# هذه الكلمات لا تؤدي للحذف وحدها.
#
# مثال:
# "عندي مشكلة، ما وصلنيش السحب"
#
# هذه شكوى، وليس سبًا.
#

COMPLAINT_WORDS = {
    "نصب",
    "نصاب",
    "نصابة",
    "احتيال",
    "سرقة",
    "سرق",
    "سرقولي",
    "فلوسي",
    "خسرت",
    "ما وصلنيش",
    "ما وصلني",
    "مشكلة",
    "مشكل",
    "شكوى",
    "شكايتي",
    "السحب",
    "ما قدرتش نسحب",
}


# =========================================================
# النتيجة
# =========================================================

@dataclass
class ModerationResult:

    delete: bool = False

    warning: str | None = None

    reason: str | None = None

    complaint: bool = False


# =========================================================
# محرك الحماية
# =========================================================

class ModerationEngine:

    def __init__(self):

        # =================================================
        # النطاقات المسموحة
        # =================================================

        self.allowed_domains = {
            "crynova.app",
            "www.crynova.app",

            "t.me",
            "telegram.me",
        }

        # =================================================
        # نطاقات إضافية من Environment Variables
        #
        # مثال:
        #
        # ALLOWED_DOMAINS=crynova.com,crynova.net
        # =================================================

        extra_domains = (
            __import__("os")
            .getenv(
                "ALLOWED_DOMAINS",
                ""
            )
        )

        if extra_domains:

            for domain in extra_domains.split(","):

                domain = domain.strip().lower()

                if domain:

                    self.allowed_domains.add(
                        domain
                    )

        logger.info(
            "Moderation initialized with %s allowed domains",
            len(self.allowed_domains)
        )

    # =====================================================
    # NORMALIZE TEXT
    # =====================================================

    @staticmethod
    def normalize(
        text: str
    ) -> str:

        if not text:
            return ""

        text = text.lower()

        # توحيد بعض الحروف العربية
        text = (
            text
            .replace("أ", "ا")
            .replace("إ", "ا")
            .replace("آ", "ا")
            .replace("ة", "ه")
            .replace("ى", "ي")
        )

        # إزالة بعض الرموز المتكررة
        text = re.sub(
            r"[ـ_]+",
            "",
            text
        )

        return text

    # =====================================================
    # استخراج الروابط
    # =====================================================

    def extract_urls(
        self,
        text: str
    ) -> list[str]:

        if not text:
            return []

        urls = URL_PATTERN.findall(
            text
        )

        cleaned = []

        for url in urls:

            url = url.strip()

            # إزالة علامات الترقيم من النهاية
            url = url.rstrip(
                ".,!?;:)]}>\"'"
            )

            if url:

                cleaned.append(
                    url
                )

        return cleaned

    # =====================================================
    # DOMAIN
    # =====================================================

    def get_domain(
        self,
        url: str
    ) -> str:

        if not url:
            return ""

        url = url.strip()

        # إذا كان الرابط بدون scheme
        if not url.startswith(
            (
                "http://",
                "https://"
            )
        ):

            url = "https://" + url

        try:

            parsed = urlparse(
                url
            )

            domain = (
                parsed.netloc
                .lower()
                .split("@")[-1]
                .split(":")[0]
            )

            return domain

        except Exception:

            return ""

    # =====================================================
    # CHECK DOMAIN
    # =====================================================

    def is_allowed_domain(
        self,
        domain: str
    ) -> bool:

        if not domain:
            return False

        domain = domain.lower()

        # نفس النطاق
        if domain in self.allowed_domains:
            return True

        # السماح بالنطاقات الفرعية
        for allowed in self.allowed_domains:

            if domain.endswith(
                "." + allowed
            ):

                return True

        return False

    # =====================================================
    # EXTERNAL LINK
    # =====================================================

    def contains_external_link(
        self,
        text: str
    ) -> bool:

        if not settings.moderation_enabled:
            return False

        urls = self.extract_urls(
            text
        )

        if not urls:
            return False

        for url in urls:

            domain = self.get_domain(
                url
            )

            if not self.is_allowed_domain(
                domain
            ):

                logger.info(
                    "External URL detected: %s",
                    domain
                )

                return True

        return False

    # =====================================================
    # INSULT
    # =====================================================

    def contains_insult(
        self,
        text: str
    ) -> bool:

        if not text:
            return False

        normalized = self.normalize(
            text
        )

        # تحويل بعض علامات الترقيم إلى مسافات
        normalized = re.sub(
            r"[^\w\u0600-\u06FF]+",
            " ",
            normalized
        )

        words = set(
            normalized.split()
        )

        for insult in INSULT_WORDS:

            insult_normalized = (
                self.normalize(
                    insult
                )
            )

            if (
                insult_normalized in words
            ):

                return True

        return False

    # =====================================================
    # COMPLAINT
    # =====================================================

    def contains_complaint(
        self,
        text: str
    ) -> bool:

        if not text:
            return False

        normalized = self.normalize(
            text
        )

        for word in COMPLAINT_WORDS:

            if (
                self.normalize(word)
                in normalized
            ):

                return True

        return False

    # =====================================================
    # تحليل الرسالة
    # =====================================================

    def inspect(
        self,
        text: str
    ) -> ModerationResult:

        if not settings.moderation_enabled:

            return ModerationResult(
                delete=False
            )

        if not text:

            return ModerationResult(
                delete=False
            )

        # =================================================
        # 1. الروابط الخارجية
        # =================================================

        if self.contains_external_link(
            text
        ):

            return ModerationResult(

                delete=True,

                reason="external_link",

                warning=(
                    "⚠️ الرسالة تحذفت لأن الروابط "
                    "الخارجية غير مسموحة هنا.\n\n"
                    "استعمل فقط الروابط الرسمية "
                    "المسموحة تاع Crynova."
                )
            )

        # =================================================
        # 2. الإهانات
        # =================================================

        if self.contains_insult(
            text
        ):

            return ModerationResult(

                delete=True,

                reason="insult",

                warning=(
                    "⚠️ الرسالة تحذفت بسبب الإهانة.\n\n"
                    "إذا عندك مشكل مع Crynova، "
                    "اشرح المشكل بلا سب ونعاونك."
                )
            )

        # =================================================
        # 3. الشكوى
        # =================================================
        #
        # لا نحذفها.
        #

        if self.contains_complaint(
            text
        ):

            logger.info(
                "Complaint detected but preserved."
            )

            return ModerationResult(

                delete=False,

                complaint=True,

                reason="complaint"
            )

        # =================================================
        # 4. رسالة عادية
        # =================================================

        return ModerationResult(
            delete=False
        )
