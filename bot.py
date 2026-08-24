import logging
from telegram import (
    Update, ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes,
    filters
)

# ---------------- تنظیمات ---------------- #
TOKEN = "8868906040:AAHFEcVX4u6Nh-K2AJG_9KDIix3PENqA4sc"
OWNER_ID = 8474856910
SUPPORT_PHONE = "+989910065071"
CARD_NUMBER = "6037998216767839"
CHANNEL_USERNAME = "persian_motor"  # یوزرنیم کانال کانال خودت

logging.basicConfig(level=logging.INFO)

# ---------------- دیتابیس ساده ---------------- #
ads = {}            # آگهی‌های تأیید شده
pending_ads = {}    # آگهی‌های در انتظار تأیید
user_state = {}
temp_data = {}
next_ad_id = 1

# ---------------- منوها ---------------- #
def user_menu():
    kb = [
        ["ثبت آگهی موتور", "لیست آگهی‌ها"],
        ["جستجو", "تماس با پشتیبانی"],
        ["دستیار هوشمند"]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def admin_menu():
    kb = [
        ["ثبت آگهی موتور", "لیست آگهی‌ها"],
        ["آگهی‌های در انتظار تأیید", "جستجو"],
        ["حذف آگهی", "تأیید آگهی"],
        ["تماس با پشتیبانی", "دستیار هوشمند"]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# ---------------- چک عضویت کانال ---------------- #
async def is_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", update.effective_user.id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

# ---------------- قوانین (فقط برای مشتری) ---------------- #
async def rules_text() -> str:
    return (
        "📜 قوانین ربات موتور:\n\n"
        "✅ هزینه ثبت هر آگهی موتور: ۷,۰۰۰,۰۰۰ ریال\n"
        "✅ آگهی تا زمان فروش موتور فعال می‌ماند.\n"
        "✅ فقط عکس و اطلاعات موتور مجاز است.\n"
        "❌ عکس شخصی، سلفی، شماره موبایل روی عکس و هر چیز غیرمرتبط ممنوع است.\n"
        "❌ در صورت تخلف، آگهی بدون بازگشت وجه حذف می‌شود.\n"
    )

# ---------------- شروع ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "سلام 👋\n"
        "به ربات خرید و فروش موتور خوش آمدید.\n\n"
        "هزینه ثبت هر آگهی: ۷,۰۰۰,۰۰۰ ریال.\n"
        "آگهی تا زمان فروش موتور فعال می‌ماند.\n\n"
        "با منوی زیر کار را شروع کنید."
    )
    if update.effective_user.id == OWNER_ID:
        await update.message.reply_text(text, reply_markup=admin_menu())
    else:
        await update.message.reply_text(await rules_text(), reply_markup=user_menu())

# ---------------- تماس با پشتیبانی ---------------- #
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"📞 پشتیبانی:\n"
        f"شماره تماس: {SUPPORT_PHONE}\n"
        f"شماره کارت: {CARD_NUMBER}\n"
        f"برای هماهنگی و پرداخت، با این شماره در واتساپ یا تماس مستقیم در ارتباط باشید."
    )
    if update.effective_user.id == OWNER_ID:
        await update.message.reply_text(text, reply_markup=admin_menu())
    else:
        await update.message.reply_text(text, reply_markup=user_menu())

# ---------------- دستور /id ---------------- #
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"ایدی شما: {user_id}")

# ---------------- ثبت آگهی ---------------- #
async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        await update.message.reply_text(
            f"برای ثبت آگهی باید عضو کانال شوید:\nhttps://t.me/{CHANNEL_USERNAME}"
        )
        return

    uid = update.effective_user.id
    user_state[uid] = "province"
    temp_data[uid] = {}
    await update.message.reply_text("استان را وارد کن:")

# ---------------- دستیار قیمت ساده ---------------- #
def price_hint(model: str, price_text: str) -> str:
    try:
        p = int("".join(ch for ch in price_text if ch.isdigit()))
    except:
        return "❗ فرمت قیمت نامعتبر است، لطفاً عددی وارد کنید."

    model = model.lower()
    if "هوندا" in model:
        if p < 50000000:
            return "💬 قیمت برای هوندا خیلی پایین به نظر می‌رسد."
        elif p > 200000000:
            return "💬 قیمت برای هوندا بالاتر از حد معمول است."
        else:
            return "💬 قیمت هوندا در بازهٔ منطقی است."
    if "آپاچی" in model or "apache" in model:
        if p < 80000000:
            return "💬 قیمت برای آپاچی کمی پایین است."
        elif p > 250000000:
            return "💬 قیمت برای آپاچی بالاست."
        else:
            return "💬 قیمت آپاچی قابل قبول است."
    return "💬 قیمت وارد شده بررسی شد؛ در صورت نیاز با پشتیبانی مشورت کنید."

# ---------------- دستیار هوشمند (ساده و متنی) ---------------- #
async def assistant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = "assistant"
    await update.message.reply_text(
        "🤖 دستیار هوشمند فعال شد.\n"
        "مدل موتور و قیمت تقریبی را بنویس تا نظر بدهم.\n"
        "مثال: هوندا 125، قیمت 120000000"
    )

# ---------------- هندل پیام‌ها ---------------- #
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # جلوگیری از عکس و فایل برای آگهی
    if update.message.photo or update.message.document:
        await update.message.reply_text(
            "❌ ارسال عکس یا فایل در این بخش مجاز نیست.\n"
            "لطفاً فقط اطلاعات متنی موتور را وارد کنید."
        )
        return

    text = update.message.text
    if uid not in user_state:
        return

    step = user_state[uid]

    # دستیار هوشمند
    if step == "assistant":
        parts = text.split("،")
        if len(parts) < 2:
            await update.message.reply_text(
                "لطفاً به این شکل بنویس:\nمدل موتور، قیمت\nمثال: هوندا 125، 120000000"
            )
            return
        model = parts[0]
        price_text = parts[1]
        hint = price_hint(model, price_text)
        if uid == OWNER_ID:
            await update.message.reply_text(hint, reply_markup=admin_menu())
        else:
            await update.message.reply_text(hint, reply_markup=user_menu())
        del user_state[uid]
        return

    if step == "province":
        temp_data[uid]["province"] = text
        user_state[uid] = "city"
        await update.message.reply_text("شهر را وارد کن:")
        return

    if step == "city":
        temp_data[uid]["city"] = text
        user_state[uid] = "model"
        await update.message.reply_text("مدل موتور (مثلاً هوندا، آپاچی، ...):")
        return

    if step == "model":
        temp_data[uid]["model"] = text
        user_state[uid] = "price"
        await update.message.reply_text("قیمت (مثلاً 120000000):")
        return

    if step == "price":
        temp_data[uid]["price"] = text
        hint = price_hint(temp_data[uid]["model"], text)
        await update.message.reply_text(hint)
        user_state[uid] = "phone"
        await update.message.reply_text("شماره تماس خودت را وارد کن:")
        return

    if step == "phone":
        temp_data[uid]["phone"] = text

        global next_ad_id, pending_ads
        pending_ads[next_ad_id] = temp_data[uid]

        msg = (
            f"آگهی #{next_ad_id} ثبت شد ✅\n"
            f"بعد از تأیید مدیر، در لیست آگهی‌ها نمایش داده می‌شود.\n"
            f"هزینه آگهی: ۷,۰۰۰,۰۰۰ ریال."
        )
        if uid == OWNER_ID:
            await update.message.reply_text(msg, reply_markup=admin_menu())
        else:
            await update.message.reply_text(msg, reply_markup=user_menu())

        ad = temp_data[uid]
        admin_msg = (
            f"🔔 آگهی جدید در انتظار تأیید:\n\n"
            f"آگهی #{next_ad_id}\n"
            f"استان: {ad['province']}\n"
            f"شهر: {ad['city']}\n"
            f"مدل: {ad['model']}\n"
            f"قیمت: {ad['price']}\n"
            f"تماس: {ad['phone']}\n\n"
            f"برای تأیید، در ربات روی /admin → «آگهی‌های در انتظار تأیید» → «تأیید آگهی» بزن و شماره آگهی را وارد کن."
        )
        try:
            await context.bot.send_message(chat_id=OWNER_ID, text=admin_msg)
        except Exception as e:
            logging.error(f"خطا در ارسال پیام به مدیر: {e}")

        next_ad_id += 1
        del user_state[uid]
        del temp_data[uid]
        return

    if step == "search":
        query = text.lower()
        results = []

        for ad_id, ad in ads.items():
            if (query in ad["province"].lower() or
                query in ad["city"].lower() or
                query in ad["model"].lower() or
                query in ad["price"].lower()):
                results.append((ad_id, ad))

        if not results:
            if uid == OWNER_ID:
                await update.message.reply_text("چیزی پیدا نشد.", reply_markup=admin_menu())
            else:
                await update.message.reply_text("چیزی پیدا نشد.", reply_markup=user_menu())
        else:
            msg = ""
            for ad_id, ad in results:
                msg += (
                    f"آگهی #{ad_id}\n"
                    f"{ad['province']} - {ad['city']}\n"
                    f"{ad['model']} - قیمت: {ad['price']}\n"
                    f"تماس: {ad['phone']}\n\n"
                )
            if uid == OWNER_ID:
                await update.message.reply_text(msg, reply_markup=admin_menu())
            else:
                await update.message.reply_text(msg, reply_markup=user_menu())

        del user_state[uid]
        return

    if step == "approve_waiting":
        if uid != OWNER_ID:
            await update.message.reply_text("این بخش فقط برای مدیر است.", reply_markup=user_menu())
            del user_state[uid]
            return

        try:
            ad_id = int(text)
            if ad_id in pending_ads:
                ads[ad_id] = pending_ads[ad_id]
                del pending_ads[ad_id]
                await update.message.reply_text(f"آگهی #{ad_id} تأیید شد ✅", reply_markup=admin_menu())
            else:
                await update.message.reply_text("آگهی در انتظار تأیید نیست.", reply_markup=admin_menu())
        except:
            await update.message.reply_text("شماره آگهی نامعتبر است.", reply_markup=admin_menu())

        del user_state[uid]
        return

    if step == "delete_waiting":
        if uid != OWNER_ID:
            await update.message.reply_text("این بخش فقط برای مدیر است.", reply_markup=user_menu())
            del user_state[uid]
            return

        try:
            ad_id = int(text)
            if ad_id in ads:
                del ads[ad_id]
                await update.message.reply_text(f"آگهی #{ad_id} حذف شد.", reply_markup=admin_menu())
            else:
                await update.message.reply_text("آگهی پیدا نشد.", reply_markup=admin_menu())
        except:
            await update.message.reply_text("شماره آگهی نامعتبر است.", reply_markup=admin_menu())

        del user_state[uid]
        return

# ---------------- لیست آگهی‌های تأیید شده ---------------- #
async def list_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ads:
        if update.effective_user.id == OWNER_ID:
            await update.message.reply_text("هیچ آگهی تأیید شده‌ای وجود ندارد.", reply_markup=admin_menu())
        else:
            await update.message.reply_text("هیچ آگهی تأیید شده‌ای وجود ندارد.", reply_markup=user_menu())
        return

    text = ""
    for ad_id, ad in ads.items():
        text += f"آگهی #{ad_id}\n"
        text += f"{ad['province']} - {ad['city']}\n"
        text += f"{ad['model']} - قیمت: {ad['price']}\n"
        text += f"تماس: {ad['phone']}\n\n"

    if update.effective_user.id == OWNER_ID:
        await update.message.reply_text(text, reply_markup=admin_menu())
    else:
        await update.message.reply_text(text, reply_markup=user_menu())

# ---------------- آگهی‌های در انتظار تأیید ---------------- #
async def pending_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("این بخش فقط برای مدیر است.", reply_markup=user_menu())
        return

    if not pending_ads:
        await update.message.reply_text("هیچ آگهی در انتظار تأیید نیست.", reply_markup=admin_menu())
        return

    text = ""
    for ad_id, ad in pending_ads.items():
        text += f"آگهی #{ad_id}\n"
        text += f"{ad['province']} - {ad['city']}\n"
        text += f"{ad['model']} - قیمت: {ad['price']}\n"
        text += f"تماس: {ad['phone']}\n\n"

    await update.message.reply_text(text, reply_markup=admin_menu())

# ---------------- شروع تأیید آگهی ---------------- #
async def start_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("این بخش فقط برای مدیر است.", reply_markup=user_menu())
        return

    uid = update.effective_user.id
    user_state[uid] = "approve_waiting"
    await update.message.reply_text("شماره آگهی را برای تأیید وارد کنید:", reply_markup=admin_menu())

# ---------------- شروع حذف آگهی ---------------- #
async def start_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("این بخش فقط برای مدیر است.", reply_markup=user_menu())
        return

    uid = update.effective_user.id
    user_state[uid] = "delete_waiting"
    await update.message.reply_text("شماره آگهی را برای حذف وارد کنید:", reply_markup=admin_menu())

# ---------------- جستجو ---------------- #
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = "search"
    await update.message.reply_text(
        "عبارت مورد نظر را وارد کنید (استان، شهر، مدل یا قیمت):"
    )

# ---------------- پنل مدیریت (فقط مدیر) ---------------- #
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("این بخش فقط برای مدیر است.", reply_markup=user_menu())
        return

    await update.message.reply_text(
        "پنل مدیریت فعال شد:",
        reply_markup=admin_menu()
    )

# ---------------- اجرای ربات ---------------- #
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(CommandHandler("admin", admin_panel))

    app.add_handler(MessageHandler(filters.Regex("^ثبت آگهی موتور$"), new_ad))
    app.add_handler(MessageHandler(filters.Regex("^لیست آگهی‌ها$"), list_ads))
    app.add_handler(MessageHandler(filters.Regex("^آگهی‌های در انتظار تأیید$"), pending_list))
    app.add_handler(MessageHandler(filters.Regex("^جستجو$"), search))
    app.add_handler(MessageHandler(filters.Regex("^تماس با پشتیبانی$"), support))
    app.add_handler(MessageHandler(filters.Regex("^دستیار هوشمند$"), assistant))

    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
