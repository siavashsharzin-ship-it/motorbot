import logging
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, CallbackQueryHandler, filters
)

# ------------------ تنظیمات واقعی ------------------
TOKEN = "8868906040:AAHbcnGXFW5diAhe8DnR6-6JKBa-NRlWYpE"
ADMIN_ID = 1                     # آیدی عددی تلگرام خودت را اینجا بگذار
CARD_NUMBER = "6037998216767839"
SUPPORT_PHONE = "+989910065071"

logging.basicConfig(level=logging.INFO)

# ------------------ دیتابیس ساده ------------------
ads = {}
user_state = {}
temp_data = {}
next_ad_id = 1

# ------------------ کیبورد اصلی ------------------
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("ثبت آگهی موتور")],
            [KeyboardButton("لیست آگهی‌ها")],
            [KeyboardButton("ثبت امضای الکترونیک خریدار")],
        ],
        resize_keyboard=True
    )

# ------------------ شروع ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = None
    temp_data[uid] = {}
    await update.message.reply_text(
        "سلام، ربات خرید و فروش موتور فعال شد 🏍️\n"
        f"پشتیبانی: {SUPPORT_PHONE}",
        reply_markup=get_main_keyboard()
    )

# ------------------ شروع ثبت آگهی ------------------
async def start_new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = "ad_province"
    temp_data[uid] = {}
    await update.message.reply_text("استان را وارد کن:")

# ------------------ هندلر متن ------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    state = user_state.get(uid)

    if text == "ثبت آگهی موتور":
        await start_new_ad(update, context)
        return
    if text == "لیست آگهی‌ها":
        await list_ads(update, context)
        return
    if text == "ثبت امضای الکترونیک خریدار":
        await start_buyer_signature(update, context)
        return

    if state == "ad_province":
        temp_data[uid]["province"] = text
        user_state[uid] = "ad_city"
        await update.message.reply_text("شهر:")

    elif state == "ad_city":
        temp_data[uid]["city"] = text
        user_state[uid] = "ad_model"
        await update.message.reply_text("مدل موتور:")

    elif state == "ad_model":
        temp_data[uid]["model"] = text
        user_state[uid] = "ad_year"
        await update.message.reply_text("سال ساخت:")

    elif state == "ad_year":
        temp_data[uid]["year"] = text
        user_state[uid] = "ad_km"
        await update.message.reply_text("کارکرد (کیلومتر):")

    elif state == "ad_km":
        temp_data[uid]["km"] = text
        user_state[uid] = "ad_price"
        await update.message.reply_text("قیمت پیشنهادی:")

    elif state == "ad_price":
        temp_data[uid]["price"] = text
        user_state[uid] = "ad_desc"
        await update.message.reply_text("توضیحات:")

    elif state == "ad_desc":
        temp_data[uid]["desc"] = text
        user_state[uid] = "ad_signature_name"
        await update.message.reply_text("نام فروشنده:")

    elif state == "ad_signature_name":
        temp_data[uid]["seller_name"] = text
        user_state[uid] = "ad_signature_national"
        await update.message.reply_text("کد ملی فروشنده:")

    elif state == "ad_signature_national":
        temp_data[uid]["seller_national"] = text
        user_state[uid] = "ad_signature_text"
        await update.message.reply_text("متن امضای فروشنده:")

    elif state == "ad_signature_text":
        temp_data[uid]["seller_signature"] = text
        user_state[uid] = "ad_photo_front"
        await update.message.reply_text("عکس موتور از روبه‌رو را ارسال کن:")

    else:
        await update.message.reply_text("از دکمه‌ها استفاده کن.")

# ------------------ عکس‌ها ------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    state = user_state.get(uid)
    file_id = update.message.photo[-1].file_id

    if state == "ad_photo_front":
        temp_data[uid]["photo_front"] = file_id
        user_state[uid] = "ad_photo_side"
        await update.message.reply_text("عکس موتور از بغل:")

    elif state == "ad_photo_side":
        temp_data[uid]["photo_side"] = file_id
        user_state[uid] = "ad_photo_back"
        await update.message.reply_text("عکس موتور از عقب:")

    elif state == "ad_photo_back":
        temp_data[uid]["photo_back"] = file_id
        await finalize_ad(update, context)

    else:
        await update.message.reply_text("در مرحله ثبت عکس نیستی.")

# ------------------ نهایی‌سازی آگهی ------------------
async def finalize_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_ad_id
    uid = update.effective_user.id
    data = temp_data[uid]
    ad_id = next_ad_id
    next_ad_id += 1

    ads[ad_id] = {
        "id": ad_id,
        "owner_id": uid,
        "province": data["province"],
        "city": data["city"],
        "model": data["model"],
        "year": data["year"],
        "km": data["km"],
        "price": data["price"],
        "desc": data["desc"],
        "seller_name": data["seller_name"],
        "seller_national": data["seller_national"],
        "seller_signature": data["seller_signature"],
        "photo_front": data["photo_front"],
        "photo_side": data["photo_side"],
        "photo_back": data["photo_back"],
        "paid": False,
        "buyer_signature": None,
    }

    user_state[uid] = None
    temp_data[uid] = {}

    await update.message.reply_text(
        f"آگهی #{ad_id} ثبت شد.\n"
        f"هزینه آگهی: ۷,۰۰۰,۰۰۰ ریال\n"
        f"واریز به کارت: {CARD_NUMBER}\n"
        f"بعد از واریز، رسید را برای ادمین ارسال کن.\n"
        f"پشتیبانی: {SUPPORT_PHONE}",
        reply_markup=get_main_keyboard()
    )

# ------------------ لیست آگهی‌ها ------------------
async def list_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ads:
        await update.message.reply_text("هیچ آگهی‌ای ثبت نشده.")
        return

    msg = "🏍️ لیست آگهی‌ها:\n"
    for ad in ads.values():
        msg += (
            f"\n#{ad['id']} - {ad['model']} | {ad['year']} | {ad['km']} km\n"
            f"{ad['province']} / {ad['city']}\n"
            f"قیمت: {ad['price']} ریال\n"
            f"پرداخت: {'تأیید شده' if ad['paid'] else 'در انتظار'}\n"
        )

    await update.message.reply_text(msg)

    await update.message.reply_text(
        "برای مشاهده جزئیات:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("جزئیات آگهی‌ها", callback_data="show_ads_detail")]
        ])
    )

# ------------------ جزئیات آگهی‌ها ------------------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_ads_detail":
        for ad in ads.values():
            text = (
                f"آگهی #{ad['id']}\n"
                f"مدل: {ad['model']}\n"
                f"سال: {ad['year']}\n"
                f"کارکرد: {ad['km']} km\n"
                f"{ad['province']} / {ad['city']}\n"
                f"قیمت: {ad['price']} ریال\n"
                f"توضیحات: {ad['desc']}\n"
                f"فروشنده: {ad['seller_name']} ({ad['seller_national']})\n"
                f"امضا: {ad['seller_signature']}\n"
                f"پرداخت: {'تأیید شده' if ad['paid'] else 'در انتظار'}\n"
            )
            await query.message.reply_text(text)

            if ad["paid"]:
                await context.bot.send_photo(query.message.chat_id, ad["photo_front"], caption="نمای جلو")
                await context.bot.send_photo(query.message.chat_id, ad["photo_side"], caption="نمای بغل")
                await context.bot.send_photo(query.message.chat_id, ad["photo_back"], caption="نمای عقب")
            else:
                await query.message.reply_text("پرداخت تأیید نشده؛ عکس‌ها نمایش داده نمی‌شود.")

# ------------------ امضای خریدار ------------------
async def start_buyer_signature(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = "buyer_ad_id"
    temp_data[uid] = {}
    await update.message.reply_text("شماره آگهی:")

async def handle_buyer_signature_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    state = user_state.get(uid)

    if state == "buyer_ad_id":
        try:
            ad_id = int(text)
        except:
            await update.message.reply_text("عدد وارد کن.")
            return
        if ad_id not in ads:
            await update.message.reply_text("آگهی وجود ندارد.")
            return
        temp_data[uid]["ad_id"] = ad_id
        user_state[uid] = "buyer_name"
        await update.message.reply_text("نام خریدار:")

    elif state == "buyer_name":
        temp_data[uid]["buyer_name"] = text
        user_state[uid] = "buyer_national"
        await update.message.reply_text("کد ملی خریدار:")

    elif state == "buyer_national":
        temp_data[uid]["buyer_national"] = text
        user_state[uid] = "buyer_signature_text"
        await update.message.reply_text("متن امضای خریدار:")

    elif state == "buyer_signature_text":
        ad_id = temp_data[uid]["ad_id"]
        ads[ad_id]["buyer_signature"] = {
            "name": temp_data[uid]["buyer_name"],
            "national": temp_data[uid]["buyer_national"],
            "text": text,
        }
        user_state[uid] = None
        temp_data[uid] = {}
        await update.message.reply_text("امضای خریدار ثبت شد.", reply_markup=get_main_keyboard())

    else:
        await handle_text(update, context)

# ------------------ ادمین: تأیید پرداخت ------------------
async def admin_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("فقط ادمین.")
        return

    parts = update.message.text.split()
    if len(parts) != 2:
        await update.message.reply_text("فرمت:\n/confirm_ad <id>")
        return

    try:
        ad_id = int(parts[1])
    except:
        await update.message.reply_text("عدد وارد کن.")
        return

    if ad_id not in ads:
        await update.message.reply_text("آگهی وجود ندارد.")
        return

    ads[ad_id]["paid"] = True
    await update.message.reply_text(f"پرداخت آگهی #{ad_id} تأیید شد.")

    owner = ads[ad_id]["owner_id"]
    await context.bot.send_message(owner, f"پرداخت آگهی #{ad_id} تأیید شد. عکس‌ها فعال شدند.")

# ------------------ اجرای ربات ------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("confirm_ad", admin_confirm))
app.add_handler(CallbackQueryHandler(callback_handler))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buyer_signature_text))

app.run_polling()
