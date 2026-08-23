const { Telegraf, Markup } = require('telegraf');
const express = require('express');

// ============================================================
// 1. متغيرات البيئة
// ============================================================
const BOT_TOKEN = process.env.BOT_TOKEN;
const WEBHOOK_URL = process.env.WEBHOOK_URL;
const PORT = process.env.PORT || 3000;

if (!BOT_TOKEN) {
  console.error('❌ لم يتم تعيين BOT_TOKEN في متغيرات البيئة');
  process.exit(1);
}

if (!WEBHOOK_URL) {
  console.error('❌ لم يتم تعيين WEBHOOK_URL في متغيرات البيئة');
  console.log('⚠️  سيتم استخدام long polling كبديل');
}

// ============================================================
// 2. إنشاء البوت
// ============================================================
const bot = new Telegraf(BOT_TOKEN);

// ============================================================
// 3. رسالة الترحيب
// ============================================================
const WELCOME_MESSAGE = `💜 مرحبًا بك في دعم Crynova

👋 كيف يمكننا مساعدتك اليوم؟

✍️ أرسل استفسارك أو مشكلتك بالتفصيل، وسيقوم فريق الدعم بمساعدتك.

💰 استثمار • 💸 سحب وإيداع • 🎁 مكافآت • 👤 حسابك • 📊 المستويات

⏱️ يرجى الانتظار حتى يتم الرد عليك وعدم إرسال نفس الرسالة عدة مرات

Crynova Support 💜`;

// ============================================================
// 4. الأوامر
// ============================================================

// أمر /start
bot.start(async (ctx) => {
  try {
    const keyboard = Markup.inlineKeyboard([
      [Markup.button.url('🛎️ خدمة العملاء', 'https://t.me/CrynovaSupport_bot/support')],
      [
        Markup.button.url('📢 القناة الرسمية', 'https://t.me/Crynova_dz'),
        Markup.button.url('💬 فتح الدردشة', 'https://t.me/CrynovaChat')
      ]
    ]);

    await ctx.reply(WELCOME_MESSAGE, keyboard);
    console.log(`✅ تم إرسال رسالة الترحيب للمستخدم: ${ctx.from.id}`);
  } catch (error) {
    console.error('❌ فشل إرسال رسالة الترحيب:', error);
  }
});

// أمر /help
bot.help((ctx) => {
  ctx.reply('🆘 للتواصل مع الدعم، استخدم الأزرار أعلاه أو أرسل رسالتك وسنرد عليك في أقرب وقت.');
});

// الرد على أي رسالة نصية أخرى
bot.on('text', async (ctx) => {
  if (ctx.message.text.startsWith('/')) return;

  try {
    await ctx.reply('✅ تم استلام رسالتك، سيتم الرد عليك قريباً من قبل فريق الدعم.');
    console.log(`📩 رسالة من ${ctx.from.id}: ${ctx.message.text}`);
  } catch (error) {
    console.error('❌ فشل الرد على الرسالة:', error);
  }
});

// ============================================================
// 5. إعداد Webhook أو Long Polling
// ============================================================

if (WEBHOOK_URL) {
  // ---------- استخدام Webhook ----------
  const app = express();
  app.use(express.json());

  // نقطة نهاية الويب هوك
  app.post('/webhook', (req, res) => {
    bot.handleUpdate(req.body, res);
  });

  // نقطة نهاية للتحقق من صحة الخادم
  app.get('/', (req, res) => {
    res.send('✅ بوت Crynova Support يعمل عبر Webhook');
  });

  // تشغيل الخادم مع ربطه بـ 0.0.0.0 والمنفذ المحدد
  app.listen(PORT, '0.0.0.0', async () => {
    console.log(`🚀 خادم Express يعمل على المنفذ ${PORT}`);

    try {
      // تعيين الويب هوك
      await bot.telegram.setWebhook(`${WEBHOOK_URL}/webhook`);
      console.log(`✅ تم تعيين Webhook: ${WEBHOOK_URL}/webhook`);
    } catch (err) {
      console.error('❌ فشل تعيين Webhook:', err);
    }
  });

} else {
  // ---------- استخدام Long Polling (بديل) ----------
  console.log('⚠️  WEBHOOK_URL غير مضبوط، سيتم استخدام Long Polling');

  bot.launch()
    .then(() => {
      console.log('🚀 بوت Crynova Support يعمل عبر Long Polling');
    })
    .catch((err) => {
      console.error('❌ فشل تشغيل البوت:', err);
      process.exit(1);
    });

  // إيقاف التشغيل بشكل نظيف
  process.once('SIGINT', () => bot.stop('SIGINT'));
  process.once('SIGTERM', () => bot.stop('SIGTERM'));
}
