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
TOKEN = "8868906040:AAHbcnGXFW5diAhe8DnR6-6JKBa-NRlWYpE"
OWNER_ID = 8474856910
SUPPORT_PHONE = "+989910065071"
CARD_NUMBER = "6037998216767839"

logging.basicConfig(level=logging.INFO)

# ---------------- دیتابیس ساده ---------------- #
ads = {}            # آگهی‌های تأیید شده
pending_ads = {}    # آگهی‌های در انتظار تأیید
user_state = {}
temp_data = {}
next_ad_id = 1

# ---------------- دستور /id ---------------- #
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"ایدی شما: {user_id}")

# ---------------- منوی اصلی (برای همه) ---------------- #
def main_menu():
    kb = [
        ["ثبت آگهی موتور"],
        ["لیست آگهی‌ها"],
        ["جستجو"],
        ["تماس با پشتیبانی"],
        ["پنل مدیریت"]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# ---------------- شروع ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\nربات خرید و فروش موتور فعال است.\nاز منوی زیر گزینه مورد نظر را انتخاب کنید:",
        reply_markup=main_menu()
    )

# ---------------- تماس با پشتیبانی ---------------- #
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"📞 پشتیبانی:\n"
        f"شماره تماس: {SUPPORT_PHONE}\n"
        f"شماره کارت: {CARD_NUMBER}\n"
        f"برای هماهنگی و پرداخت، با این شماره در واتساپ یا تماس مستقیم در ارتباط باشید."
    )
    await update.message.reply_text(text)

# ---------------- ثبت آگهی ---------------- #
async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = "province"
    temp_data[uid] = {}
    await update.message.reply_text("استان را وارد کن:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    # اگر در هیچ مرحله‌ای نیست، پیام را نادیده بگیر
    if uid not in user_state:
        return

    step = user_state[uid]

    # ثبت آگهی مرحله‌ای
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
        await update.message.reply_text("قیمت (مثلاً 120 میلیون):")
        return

    if step == "price":
        temp_data[uid]["price"] = text
        user_state[uid] = "phone"
        await update.message.reply_text("شماره تماس خودت را وارد کن:")
        return

    if step == "phone":
        temp_data[uid]["phone"] = text

        global next_ad_id, pending_ads
        pending_ads[next_ad_id] = temp_data[uid]

        # پیام برای کاربر
        await update.message.reply_text(
            f"آگهی #{next_ad_id} ثبت شد ✅\n"
            f"بعد از تأیید مدیر، در لیست آگهی‌ها نمایش داده می‌شود.",
            reply_markup=main_menu()
        )

        # نوتیفیکیشن فوری برای مدیر
        ad = temp_data[uid]
        admin_msg = (
            f"🔔 آگهی جدید در انتظار تأیید:\n\n"
            f"آگهی #{next_ad_id}\n"
            f"استان: {ad['province']}\n"
            f"شهر: {ad['city']}\n"
            f"مدل: {ad['model']}\n"
            f"قیمت: {ad['price']}\n"
            f"تماس: {ad['phone']}\n\n"
            f"برای تأیید، در ربات روی «پنل مدیریت» → «آگهی‌های در انتظار تأیید» → «تأیید آگهی» بزن و شماره آگهی را وارد کن."
        )
        try:
            await context.bot.send_message(chat_id=OWNER_ID, text=admin_msg)
        except Exception as e:
            logging.error(f"خطا در ارسال پیام به مدیر: {e}")

        next_ad_id += 1
        del user_state[uid]
        del temp_data[uid]
        return

    # جستجو
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
            await update.message.reply_text("چیزی پیدا نشد.", reply_markup=main_menu())
        else:
            msg = ""
            for ad_id, ad in results:
                msg += (
                    f"آگهی #{ad_id}\n"
                    f"{ad['province']} - {ad['city']}\n"
                    f"{ad['model']} - قیمت: {ad['price']}\n"
                    f"تماس: {ad['phone']}\n\n"
                )
            await update.message.reply_text(msg, reply_markup=main_menu())

        del user_state[uid]
        return

    # تأیید آگهی (وارد کردن شماره)
    if step == "approve_waiting":
        if uid != OWNER_ID:
            await update.message.reply_text("این بخش فقط برای مدیر است.", reply_markup=main_menu())
            del user_state[uid]
            return

        try:
            ad_id = int(text)
            if ad_id in pending_ads:
                ads[ad_id] = pending_ads[ad_id]
                del pending_ads[ad_id]
                await update.message.reply_text(f"آگهی #{ad_id} تأیید شد ✅", reply_markup=main_menu())
            else:
                await update.message.reply_text("آگهی در انتظار تأیید نیست.", reply_markup=main_menu())
        except:
            await update.message.reply_text("شماره آگهی نامعتبر است.", reply_markup=main_menu())

        del user_state[uid]
        return

    # حذف آگهی (وارد کردن شماره)
    if step == "delete_waiting":
        if uid != OWNER_ID:
            await update.message.reply_text("این بخش فقط برای مدیر است.", reply_markup=main_menu())
            del user_state[uid]
            return

        try:
            ad_id = int(text)
            if ad_id in ads:
                del ads[ad_id]
                await update.message.reply_text(f"آگهی #{ad_id} حذف شد.", reply_markup=main_menu())
            else:
                await update.message.reply_text("آگهی پیدا نشد.", reply_markup=main_menu())
        except:
            await update.message.reply_text("شماره آگهی نامعتبر است.", reply_markup=main_menu())

        del user_state[uid]
        return

# ---------------- لیست آگهی‌های تأیید شده ---------------- #
async def list_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ads:
        await update.message.reply_text("هیچ آگهی تأیید شده‌ای وجود ندارد.", reply_markup=main_menu())
        return

    text = ""
    for ad_id, ad in ads.items():
        text += f"آگهی #{ad_id}\n"
        text += f"{ad['province']} - {ad['city']}\n"
        text += f"{ad['model']} - قیمت: {ad['price']}\n"
        text += f"تماس: {ad['phone']}\n\n"

    await update.message.reply_text(text, reply_markup=main_menu())

# ---------------- آگهی‌های در انتظار تأیید ---------------- #
async def pending_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("این بخش فقط برای مدیر است.", reply_markup=main_menu())
        return

    if not pending_ads:
        await update.message.reply_text("هیچ آگهی در انتظار تأیید نیست.", reply_markup=main_menu())
        return

    text = ""
    for ad_id, ad in pending_ads.items():
        text += f"آگهی #{ad_id}\n"
        text += f"{ad['province']} - {ad['city']}\n"
        text += f"{ad['model']} - قیمت: {ad['price']}\n"
        text += f"تماس: {ad['phone']}\n\n"

    await update.message.reply_text(text, reply_markup=main_menu())

# ---------------- شروع تأیید آگهی ---------------- #
async def start_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("این بخش فقط برای مدیر است.", reply_markup=main_menu())
        return

    uid = update.effective_user.id
    user_state[uid] = "approve_waiting"
    await update.message.reply_text("شماره آگهی را برای تأیید وارد کنید:")

# ---------------- شروع حذف آگهی ---------------- #
async def start_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("این بخش فقط برای مدیر است.", reply_markup=main_menu())
        return

    uid = update.effective_user.id
    user_state[uid] = "delete_waiting"
    await update.message.reply_text("شماره آگهی را برای حذف وارد کنید:")

# ---------------- جستجو ---------------- #
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = "search"
    await update.message.reply_text(
        "عبارت مورد نظر را وارد کنید (استان، شهر، مدل یا قیمت):"
    )

# ---------------- پنل مدیریت ---------------- #
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("این بخش فقط برای مدیر است.", reply_markup=main_menu())
        return

    kb = [
        ["لیست آگهی‌ها"],
        ["آگهی‌های در انتظار تأیید"],
        ["حذف آگهی", "تأیید آگهی"],
        ["جستجو"],
        ["تماس با پشتیبانی"]
    ]

    await update.message.reply_text(
        "پنل مدیریت فعال شد:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

# ---------------- اجرای ربات ---------------- #
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", get_id))

    app.add_handler(MessageHandler(filters.Regex("^ثبت آگهی موتور$"), new_ad))
    app.add_handler(MessageHandler(filters.Regex("^لیست آگهی‌ها$"), list_ads))
    app.add_handler(MessageHandler(filters.Regex("^پنل مدیریت$"), admin_panel))
    app.add_handler(MessageHandler(filters.Regex("^آگهی‌های در انتظار تأیید$"), pending_list))
    app.add_handler(MessageHandler(filters.Regex("^جستجو$"), search))
    app.add_handler(MessageHandler(filters.Regex("^تماس با پشتیبانی$"), support))

    app.add_handler(MessageHandler(filters.Regex("^تأیید آگهی$"), start_approve))
    app.add_handler(MessageHandler(filters.Regex("^حذف آگهی$"), start_delete))

    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
