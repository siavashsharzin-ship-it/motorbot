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

# ---------------- تنظیمات ----------------
TOKEN = "8868906040:AAHbcnGXFW5diAhe8DnR6-6JKBa-NRlWYpE"
OWNER_ID = 8474856910
SUPPORT_PHONE = "+989910065071"
CARD_NUMBER = "6037998216767839"

logging.basicConfig(level=logging.INFO)

# ---------------- دیتابیس ساده ----------------
ads = {}
user_state = {}
temp_data = {}
next_ad_id = 1

# ---------------- دستور /id ----------------
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"ایدی شما: {user_id}")

# ---------------- شروع ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        ["ثبت آگهی موتور"],
        ["لیست آگهی‌ها"],
        ["پنل مدیریت"]
    ]
    await update.message.reply_text(
        "سلام، ربات خرید و فروش موتور فعال شد 🏍",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

# ---------------- ثبت آگهی ----------------
async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_ad_id

    user_state[update.effective_user.id] = "province"
    temp_data[update.effective_user.id] = {}

    await update.message.reply_text("استان را وارد کن:")
    return

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid not in user_state:
        return

    step = user_state[uid]
    text = update.message.text

    if step == "province":
        temp_data[uid]["province"] = text
        user_state[uid] = "city"
        await update.message.reply_text("شهر را وارد کن:")
        return

    if step == "city":
        temp_data[uid]["city"] = text
        user_state[uid] = "model"
        await update.message.reply_text("مدل موتور:")
        return

    if step == "model":
        temp_data[uid]["model"] = text
        user_state[uid] = "price"
        await update.message.reply_text("قیمت:")
        return

    if step == "price":
        temp_data[uid]["price"] = text
        user_state[uid] = "phone"
        await update.message.reply_text("شماره تماس:")
        return

    if step == "phone":
        temp_data[uid]["phone"] = text

        global next_ad_id
        ads[next_ad_id] = temp_data[uid]
        await update.message.reply_text(f"آگهی #{next_ad_id} ثبت شد ✅")

        next_ad_id += 1
        del user_state[uid]
        del temp_data[uid]
        return

# ---------------- لیست آگهی‌ها ----------------
async def list_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ads:
        await update.message.reply_text("هیچ آگهی‌ای ثبت نشده.")
        return

    text = ""
    for ad_id, ad in ads.items():
        text += f"آگهی #{ad_id}\n"
        text += f"{ad['province']} - {ad['city']}\n"
        text += f"{ad['model']} - قیمت: {ad['price']}\n"
        text += f"تماس: {ad['phone']}\n\n"

    await update.message.reply_text(text)

# ---------------- پنل مدیریت ----------------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("شما مدیر نیستید.")
        return

    kb = [
        ["لیست آگهی‌ها"],
        ["حذف آگهی"]
    ]

    await update.message.reply_text(
        "پنل مدیریت فعال شد:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

# ---------------- حذف آگهی ----------------
async def delete_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("شما مدیر نیستید.")
        return

    try:
        ad_id = int(update.message.text)
        if ad_id in ads:
            del ads[ad_id]
            await update.message.reply_text(f"آگهی #{ad_id} حذف شد.")
        else:
            await update.message.reply_text("آگهی پیدا نشد.")
    except:
        await update.message.reply_text("شماره آگهی نامعتبر است.")

# ---------------- اجرای ربات ----------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", get_id))

    app.add_handler(MessageHandler(filters.Regex("^ثبت آگهی موتور$"), new_ad))
    app.add_handler(MessageHandler(filters.Regex("^لیست آگهی‌ها$"), list_ads))
    app.add_handler(MessageHandler(filters.Regex("^پنل مدیریت$"), admin_panel))
    app.add_handler(MessageHandler(filters.Regex("^[0-9]+$"), delete_ad))

    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()