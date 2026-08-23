const { Telegraf } = require('telegraf');

// الحصول على توكن البوت من متغيرات البيئة
const BOT_TOKEN = process.env.BOT_TOKEN;
if (!BOT_TOKEN) {
  console.error('❌ لم يتم تعيين BOT_TOKEN في متغيرات البيئة');
  process.exit(1);
}

// إنشاء البوت
const bot = new Telegraf(BOT_TOKEN);

// رسالة الترحيب المطلوبة
const WELCOME_MESSAGE = `💜 مرحبًا بك في دعم Crynova

👋 كيف يمكننا مساعدتك اليوم؟

✍️ أرسل استفسارك أو مشكلتك بالتفصيل، وسيقوم فريق الدعم بمساعدتك.

💰 استثمار • 💸 سحب وإيداع • 🎁 مكافآت • 👤 حسابك • 📊 المستويات

⏱️ يرجى الانتظار حتى يتم الرد عليك وعدم إرسال نفس الرسالة عدة مرات

Crynova Support 💜`;

// أمر /start
bot.start(async (ctx) => {
  try {
    await ctx.reply(WELCOME_MESSAGE);
    console.log(`✅ تم إرسال رسالة الترحيب للمستخدم: ${ctx.from.id}`);
  } catch (error) {
    console.error('❌ فشل إرسال رسالة الترحيب:', error);
  }
});

// أمر /help (اختياري)
bot.help((ctx) => {
  ctx.reply('🆘 للتواصل مع الدعم، أرسل رسالتك وسنرد عليك في أقرب وقت.');
});

// الرد على أي رسالة نصية أخرى
bot.on('text', async (ctx) => {
  // تجاهل الأوامر التي تبدأ بـ / حتى لا نتداخل مع الأوامر الأخرى
  if (ctx.message.text.startsWith('/')) return;

  try {
    // يمكن إرسال رد تلقائي للمستخدم بأنه سيتم الرد عليه
    await ctx.reply('✅ تم استلام رسالتك، سيتم الرد عليك قريباً من قبل فريق الدعم.');
    console.log(`📩 رسالة من ${ctx.from.id}: ${ctx.message.text}`);
  } catch (error) {
    console.error('❌ فشل الرد على الرسالة:', error);
  }
});

// تشغيل البوت (باستخدام long polling)
bot.launch()
  .then(() => {
    console.log('🚀 بوت Crynova Support يعمل الآن...');
  })
  .catch((err) => {
    console.error('❌ فشل تشغيل البوت:', err);
    process.exit(1);
  });

// إيقاف التشغيل بشكل نظيف عند إنهاء العملية
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
