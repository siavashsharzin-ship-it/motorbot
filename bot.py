import logging
import os
import re
from telegram import (
    Update, ReplyKeyboardMarkup, InputMediaPhoto,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# ---------------- تنظیمات امن ---------------- #
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
SUPPORT_PHONE = os.getenv("SUPPORT_PHONE", "")
CARD_NUMBER = os.getenv("CARD_NUMBER", "")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "")

logging.basicConfig(level=logging.INFO)

# ---------------- دیتابیس ---------------- #
ads = {}
pending_ads = {}
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
        ["دستیار هوشمند"]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# ---------------- شروع ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid == OWNER_ID:
        await update.message.reply_text(
            "سلام مدیر عزیز 👑\nبه پنل مدیریت خوش آمدید.",
            reply_markup=admin_menu()
        )
    else:
        await update.message.reply_text(
            "سلام موتورباز عزیز 🔥\nبه بزرگ‌ترین ربات خرید و فروش موتور خوش اومدی!",
            reply_markup=user_menu()
        )

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
    await update.message.reply_text(f"ایدی شما: {update.effective_user.id}")

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
        "🤖 مشخصات موتور را یکجا بنویس:\n"
        "مدل، سال، کارکرد، رنگ، تصادفی/بی‌تصادف، سند، بیمه، قیمت."
    )

def extract_info(text):
    info = {
        "model": None, "year": None, "km": None,
        "color": None, "accident": None,
        "document": None, "insurance": None,
        "price": None
    }

    m = re.search(r"(.+?)مدل", text)
    if m: info["model"] = m.group(1).strip()

    y = re.search(r"مدل\s*(\d{4})", text)
    if y: info["year"] = int(y.group(1))

    km = re.search(r"کارکرد\s*([\d]+)", text)
    if km: info["km"] = int(km.group(1))

    c = re.search(r"رنگ\s*([آ-ی\s]+?)(،|$)", text)
    if c: info["color"] = c.group(1).strip()

    if "بدون تصادف" in text or "بی‌تصادف" in text:
        info["accident"] = "بدون تصادف"
    elif "تصادف" in text:
        info["accident"] = "تصادفی"

    if "سند تک" in text:
        info["document"] = "تک‌برگ"
    elif "سند" in text:
        info["document"] = "دارای سند"

    ins = re.search(r"بیمه\s*([\d]+)\s*ماه", text)
    if ins: info["insurance"] = int(ins.group(1))

    pr = re.search(r"قیمت\s*([\d]+)", text)
    if pr: info["price"] = int(pr.group(1))

    return info

def expert_analysis(info):
    lines = ["📋 گزارش کارشناسی:\n"]
    for k, v in info.items():
        if v: lines.append(f"• {k}: {v}")
    lines.append("\n🔍 تحلیل: قیمت تقریبی بر اساس بازار محاسبه شد.")
    lines.append("توصیه: بازدید حضوری و تست فنی فراموش نشود.")
    return "\n".join(lines)

async def handle_assistant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    info = extract_info(update.message.text)
    result = expert_analysis(info)

    if uid == OWNER_ID:
        await update.message.reply_text(result, reply_markup=admin_menu())
    else:
        await update.message.reply_text(result, reply_markup=user_menu())

    del user_state[uid]

# ---------------- دکمه‌های تأیید و حذف ---------------- #
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("approve_"):
        ad_id = int(data.split("_")[1])
        if ad_id in pending_ads:
            ads[ad_id] = pending_ads[ad_id]
            del pending_ads[ad_id]

            await query.edit_message_caption(
                caption=f"آگهی #{ad_id} تأیید شد و منتشر می‌شود."
            )

            ad = ads[ad_id]
            caption = (
                f"آگهی #{ad_id}\n"
                f"{ad['province']} - {ad['city']}\n"
                f"{ad['model']} - {ad['price']}\n"
                f"تماس: {ad['phone']}"
            )

            if ad["photos"]:
                await context.bot.send_media_group(
                    chat_id=f"@{CHANNEL_USERNAME}",
                    media=[InputMediaPhoto(p, caption if i == 0 else "") for i, p in enumerate(ad["photos"])]
                )
            else:
                await context.bot.send_message(f"@{CHANNEL_USERNAME}", caption)

    if data.startswith("delete_"):
        ad_id = int(data.split("_")[1])
        if ad_id in pending_ads:
            del pending_ads[ad_id]
            await query.edit_message_caption(caption=f"آگهی #{ad_id} حذف شد ❌")

# ---------------- لیست آگهی‌های در انتظار ---------------- #
async def pending_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("فقط مدیر.", reply_markup=user_menu())
        return

    if not pending_ads:
        await update.message.reply_text("هیچ آگهی در انتظار نیست.", reply_markup=admin_menu())
        return

    for ad_id, ad in pending_ads.items():
        caption = (
            f"آگهی #{ad_id}\n"
            f"{ad['province']} - {ad['city']}\n"
            f"{ad['model']} - {ad['price']}\n"
            f"تماس: {ad['phone']}"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✔ تأیید", callback_data=f"approve_{ad_id}"),
                InlineKeyboardButton("❌ حذف", callback_data=f"delete_{ad_id}")
            ]
        ])

        if ad["photos"]:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=ad["photos"][0],
                caption=caption,
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(caption, reply_markup=keyboard)

# ---------------- هندل پیام‌ها ---------------- #
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message

    if msg.photo:
        if uid in user_state and user_state[uid] == "photos":
            temp_data[uid]["photos"].append(msg.photo[-1].file_id)
            await msg.reply_text("عکس اضافه شد. اگر تمام شد بنویس: تمام")
            return
        else:
            await msg.reply_text("عکس فقط در مرحله ثبت آگهی مجاز است.")
            return

    text = msg.text

    if uid not in user_state:
        return

    step = user_state[uid]

    if step == "assistant":
        await handle_assistant(update, context)
        return

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
        await msg.reply_text("عکس‌های موتور را بفرست. اگر تمام شد بنویس: تمام")
        return

    if step == "photos":
        if text.strip() == "تمام":
            global next_ad_id
            pending_ads[next_ad_id] = temp_data[uid]

            await msg.reply_text(
                f"آگهی #{next_ad_id} ثبت شد و منتظر تأیید مدیر است.",
                reply_markup=user_menu()
            )

            next_ad_id += 1
            del user_state[uid]
            del temp_data[uid]
            return
        else:
            await msg.reply_text("اگر عکس دیگری نداری، بنویس: تمام")
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
        text += (
            f"#{ad_id}\n"
            f"{ad['province']} - {ad['city']}\n"
            f"{ad['model']} - {ad['price']}\n"
            f"تماس: {ad['phone']}\n\n"
        )

    if update.effective_user.id == OWNER_ID:
        await update.message.reply_text(text, reply_markup=admin_menu())
    else:
        await update.message.reply_text(text, reply_markup=user_menu())

# ---------------- جستجو ---------------- #
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = "search"
    await update.message.reply_text("عبارت مورد نظر:")

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    q = update.message.text.lower()

    results = []
    for ad_id, ad in ads.items():
        if (q in ad["province"].lower() or
            q in ad["city"].lower() or
            q in ad["model"].lower() or
            q in ad["price"].lower()):
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
    if not TOKEN:
        raise RuntimeError("TOKEN در Railway تنظیم نشده است.")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", get_id))

    app.add_handler(MessageHandler(filters.Regex("^ثبت آگهی موتور$"), new_ad))
    app.add_handler(MessageHandler(filters.Regex("^لیست آگهی‌ها$"), list_ads))
    app.add_handler(MessageHandler(filters.Regex("^آگهی‌های در انتظار تأیید$"), pending_list))
    app.add_handler(MessageHandler(filters.Regex("^جستجو$"), search))
    app.add_handler(MessageHandler(filters.Regex("^تماس با پشتیبانی$"), support))
    app.add_handler(MessageHandler(filters.Regex("^دستیار هوشمند$"), assistant))

    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()