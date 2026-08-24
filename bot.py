import logging
from telegram import (
    Update, ReplyKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

# ---------------- تنظیمات ---------------- #
TOKEN = "8868906040:AAHFEcVX4u6Nh-K2AJG_9KDIix3PENqA4sc"
OWNER_ID = 8474856910
SUPPORT_PHONE = "+989910065071"
CARD_NUMBER = "6037998216767839"
CHANNEL_USERNAME = "persian_motor"   # یوزرنیم کانال

logging.basicConfig(level=logging.INFO)

# ---------------- دیتابیس ---------------- #
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

# ---------------- چک عضویت کانال (فقط پیشنهاد، نه اجباری) ---------------- #
async def suggest_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", update.effective_user.id)
        if member.status not in ["member", "administrator", "creator"]:
            await update.message.reply_text(
                f"برای دیدن همه آگهی‌ها و عکس‌ها، بهتره عضو کانال بشی:\nhttps://t.me/{CHANNEL_USERNAME}"
            )
    except:
        pass

# ---------------- قوانین ---------------- #
def rules():
    return (
        "📜 قوانین ربات موتور:\n\n"
        "💰 هزینه ثبت هر آگهی: ۷,۰۰۰,۰۰۰ ریال\n"
        "📌 آگهی تا زمان فروش فعال می‌ماند\n"
        "❌ عکس شخصی، سلفی، شماره موبایل روی عکس ممنوع\n"
        "❌ آگهی غیرمرتبط حذف می‌شود\n"
        "✅ اعضا می‌توانند دوستانشان را به کانال و ربات اضافه کنند.\n"
    )

# ---------------- شروع ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await suggest_join(update, context)

    if uid == OWNER_ID:
        await update.message.reply_text("سلام مدیر عزیز 👑", reply_markup=admin_menu())
    else:
        await update.message.reply_text(rules(), reply_markup=user_menu())

# ---------------- تماس با پشتیبانی ---------------- #
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"📞 پشتیبانی:\n"
        f"شماره تماس: {SUPPORT_PHONE}\n"
        f"شماره کارت: {CARD_NUMBER}\n"
        f"برای هماهنگی، تماس یا واتساپ."
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
    uid = update.effective_user.id
    user_state[uid] = "province"
    temp_data[uid] = {"photos": []}
    await update.message.reply_text("استان:")

# ---------------- دستیار هوشمند ---------------- #
async def assistant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = "assistant"
    await update.message.reply_text(
        "🤖 دستیار فعال شد.\n"
        "مدل موتور و قیمت پیشنهادی را بنویس.\n"
        "مثال: آپاچی 180، 120000000"
    )

def smart_price(model, price):
    model = model.lower()

    if "هوندا" in model or "125" in model:
        if price < 45000000: return "💬 قیمت خیلی پایین است."
        if price > 150000000: return "💬 قیمت خیلی بالاست."
        return "💬 قیمت منطقی است."

    if "آپاچی" in model or "apache" in model or "180" in model:
        if price < 90000000: return "💬 قیمت پایین است."
        if price > 230000000: return "💬 قیمت بالاست."
        return "💬 قیمت منطقی است."

    if "پالس" in model or "bajaj" in model:
        if price < 70000000: return "💬 قیمت پایین است."
        if price > 200000000: return "💬 قیمت بالاست."
        return "💬 قیمت مناسب است."

    return "💬 مدل موتور ناشناس است."

async def handle_assistant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    try:
        parts = text.split("،")
        model = parts[0].strip()
        price = int("".join(ch for ch in parts[1] if ch.isdigit()))
    except:
        await update.message.reply_text("❗ مثال صحیح: آپاچی 180، 120000000")
        return

    result = smart_price(model, price)

    if uid == OWNER_ID:
        await update.message.reply_text(result, reply_markup=admin_menu())
    else:
        await update.message.reply_text(result, reply_markup=user_menu())

    del user_state[uid]

# ---------------- هندل پیام‌ها ---------------- #
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message

    # عکس‌ها فقط در مرحلهٔ ثبت آگهی مجازند
    if msg.photo:
        if uid in user_state and user_state[uid] == "photos":
            photo_id = msg.photo[-1].file_id
            temp_data[uid]["photos"].append(photo_id)
            await msg.reply_text("✅ عکس اضافه شد. اگر عکس دیگری داری، بفرست؛ اگر تمام شد، بنویس: تمام")
            return
        else:
            await msg.reply_text("❌ عکس فقط در مرحلهٔ ثبت آگهی موتور مجاز است.")
            return

    text = msg.text

    if uid not in user_state:
        return

    step = user_state[uid]

    # دستیار
    if step == "assistant":
        await handle_assistant(update, context)
        return

    # ثبت آگهی مرحله‌ای
    if step == "province":
        temp_data[uid]["province"] = text
        user_state[uid] = "city"
        await msg.reply_text("شهر:")
        return

    if step == "city":
        temp_data[uid]["city"] = text
        user_state[uid] = "model"
        await msg.reply_text("مدل موتور:")
        return

    if step == "model":
        temp_data[uid]["model"] = text
        user_state[uid] = "price"
        await msg.reply_text("قیمت:")
        return

    if step == "price":
        temp_data[uid]["price"] = text
        user_state[uid] = "phone"
        await msg.reply_text("شماره تماس:")
        return

    if step == "phone":
        temp_data[uid]["phone"] = text
        user_state[uid] = "photos"
        await msg.reply_text("حالا عکس‌های موتور را بفرست.\nهرچقدر عکس داری بفرست.\nاگر تمام شد، بنویس: تمام")
        return

    if step == "photos":
        if text.strip() == "تمام":
            global next_ad_id
            pending_ads[next_ad_id] = temp_data[uid]

            await msg.reply_text(
                f"آگهی #{next_ad_id} ثبت شد و منتظر تأیید مدیر است.",
                reply_markup=user_menu()
            )

            ad = temp_data[uid]
            admin_msg = (
                f"🔔 آگهی جدید:\n\n"
                f"#{next_ad_id}\n"
                f"{ad['province']} - {ad['city']}\n"
                f"{ad['model']} - {ad['price']}\n"
                f"تماس: {ad['phone']}\n"
                f"تعداد عکس: {len(ad['photos'])}"
            )
            await context.bot.send_message(OWNER_ID, admin_msg)

            next_ad_id += 1
            del user_state[uid]
            del temp_data[uid]
            return
        else:
            await msg.reply_text("اگر عکس دیگری نداری، بنویس: تمام")
            return

    # تأیید آگهی
    if step == "approve":
        if uid != OWNER_ID:
            await msg.reply_text("فقط مدیر.", reply_markup=user_menu())
            del user_state[uid]
            return

        try:
            ad_id = int(text)
            if ad_id in pending_ads:
                ads[ad_id] = pending_ads[ad_id]
                ad = ads[ad_id]

                # ارسال آگهی کامل به کانال (متن + عکس‌ها)
                caption = (
                    f"آگهی #{ad_id}\n"
                    f"{ad['province']} - {ad['city']}\n"
                    f"{ad['model']} - {ad['price']}\n"
                    f"تماس: {ad['phone']}"
                )

                if ad["photos"]:
                    media = [InputMediaPhoto(photo_id, caption=caption if i == 0 else "") 
                             for i, photo_id in enumerate(ad["photos"])]
                    await context.bot.send_media_group(chat_id=f"@{CHANNEL_USERNAME}", media=media)
                else:
                    await context.bot.send_message(chat_id=f"@{CHANNEL_USERNAME}", text=caption)

                await msg.reply_text(f"آگهی #{ad_id} تأیید و در کانال منتشر شد ✅", reply_markup=admin_menu())
                del pending_ads[ad_id]
            else:
                await msg.reply_text("آگهی در انتظار تأیید نیست.", reply_markup=admin_menu())
        except:
            await msg.reply_text("شماره آگهی نامعتبر است.", reply_markup=admin_menu())

        del user_state[uid]
        return

    # حذف آگهی
    if step == "delete":
        if uid != OWNER_ID:
            await msg.reply_text("فقط مدیر.", reply_markup=user_menu())
            del user_state[uid]
            return

        try:
            ad_id = int(text)
            if ad_id in ads:
                del ads[ad_id]
                await msg.reply_text(f"آگهی #{ad_id} حذف شد.", reply_markup=admin_menu())
            else:
                await msg.reply_text("آگهی پیدا نشد.", reply_markup=admin_menu())
        except:
            await msg.reply_text("شماره آگهی نامعتبر است.", reply_markup=admin_menu())

        del user_state[uid]
        return

# ---------------- لیست آگهی‌های تأیید شده ---------------- #
async def list_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ads:
        await update.message.reply_text(
            "هیچ آگهی تأیید شده‌ای نیست.",
            reply_markup=admin_menu() if update.effective_user.id == OWNER_ID else user_menu()
        )
        return

    text = ""
    for ad_id, ad in ads.items():
        text += f"#{ad_id}\n{ad['province']} - {ad['city']}\n{ad['model']} - {ad['price']}\nتماس: {ad['phone']}\n\n"

    if update.effective_user.id == OWNER_ID:
        await update.message.reply_text(text, reply_markup=admin_menu())
    else:
        await update.message.reply_text(text, reply_markup=user_menu())

# ---------------- آگهی‌های در انتظار تأیید ---------------- #
async def pending_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("فقط مدیر.", reply_markup=user_menu())
        return

    if not pending_ads:
        await update.message.reply_text("هیچ آگهی در انتظار نیست.", reply_markup=admin_menu())
        return

    text = ""
    for ad_id, ad in pending_ads.items():
        text += f"#{ad_id}\n{ad['province']} - {ad['city']}\n{ad['model']} - {ad['price']}\nتماس: {ad['phone']}\nتعداد عکس: {len(ad['photos'])}\n\n"

    await update.message.reply_text(text, reply_markup=admin_menu())

# ---------------- تأیید آگهی ---------------- #
async def start_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("فقط مدیر.", reply_markup=user_menu())
        return

    uid = update.effective_user.id
    user_state[uid] = "approve"
    await update.message.reply_text("شماره آگهی برای تأیید:", reply_markup=admin_menu())

# ---------------- حذف آگهی ---------------- #
async def start_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("فقط مدیر.", reply_markup=user_menu())
        return

    uid = update.effective_user.id
    user_state[uid] = "delete"
    await update.message.reply_text("شماره آگهی برای حذف:", reply_markup=admin_menu())

# ---------------- جستجو ---------------- #
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = "search"
    await update.message.reply_text("عبارت مورد نظر (استان، شهر، مدل یا قیمت):")

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    query = text.lower()
    results = []

    for ad_id, ad in ads.items():
        if (query in ad["province"].lower() or
            query in ad["city"].lower() or
            query in ad["model"].lower() or
            query in ad["price"].lower()):
            results.append((ad_id, ad))

    if not results:
        await update.message.reply_text(
            "چیزی پیدا نشد.",
            reply_markup=admin_menu() if uid == OWNER_ID else user_menu()
        )
    else:
        msg = ""
        for ad_id, ad in results:
            msg += (
                f"#{ad_id}\n"
                f"{ad['province']} - {ad['city']}\n"
                f"{ad['model']} - {ad['price']}\n"
                f"تماس: {ad['phone']}\n\n"
            )
        await update.message.reply_text(
            msg,
            reply_markup=admin_menu() if uid == OWNER_ID else user_menu()
        )

    del user_state[uid]

# ---------------- اجرای ربات ---------------- #
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", get_id))

    app.add_handler(MessageHandler(filters.Regex("^ثبت آگهی موتور$"), new_ad))
    app.add_handler(MessageHandler(filters.Regex("^لیست آگهی‌ها$"), list_ads))
    app.add_handler(MessageHandler(filters.Regex("^آگهی‌های در انتظار تأیید$"), pending_list))
    app.add_handler(MessageHandler(filters.Regex("^جستجو$"), search))
    app.add_handler(MessageHandler(filters.Regex("^تماس با پشتیبانی$"), support))
    app.add_handler(MessageHandler(filters.Regex("^دستیار هوشمند$"), assistant))
    app.add_handler(MessageHandler(filters.Regex("^تأیید آگهی$"), start_approve))
    app.add_handler(MessageHandler(filters.Regex("^حذف آگهی$"), start_delete))

    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
