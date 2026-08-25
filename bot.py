import logging
import os
from typing import Dict, Any

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# -------------------- تنظیمات -------------------- #

TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
SUPPORT_PHONE = os.getenv("SUPPORT_PHONE", "")
CARD_NUMBER = os.getenv("CARD_NUMBER", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- دیتابیس -------------------- #

ads = {}             # آگهی‌های تایید شده
pending_ads = {}     # آگهی‌های در انتظار تایید
sold_ads = {}        # آگهی‌های فروخته شده
deleted_ads = {}     # آگهی‌های حذف شده
user_state = {}      # مرحلهٔ کاربر
temp_data = {}       # دادهٔ موقت
next_ad_id = 1       # شماره آگهی

# -------------------- منو -------------------- #

def user_menu():
    return ReplyKeyboardMarkup(
        [
            ["ثبت آگهی موتور", "لیست آگهی‌ها"],
            ["لیست فروش", "لیست انتظار"],
            ["تماس با پشتیبانی"]
        ],
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        [
            ["آگهی‌های در انتظار تایید", "لیست آگهی‌ها"],
            ["لیست فروش", "لیست حذف‌شده‌ها"],
            ["تماس با پشتیبانی"]
        ],
        resize_keyboard=True
    )

# -------------------- /id -------------------- #

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"ایدی عددی شما: {update.effective_user.id}")

# -------------------- شروع -------------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    welcome = (
        "سلام موتورباز عزیز🔥\n"
        "به بزرگترین ربات خرید و فروش موتورسیکلت ایران خوش آمدید.\n\n"
        "📌 قوانین:\n"
        "• مبلغ ۷۰۰۰۰۰۰ ریال باید واریز شود تا آگهی شما ثبت شود.\n"
        "• آگهی شما تا زمان فروش موتور بدون محدودیت زمانی در ربات باقی می‌ماند.\n"
        "• پس از ثبت آگهی، مدیر بررسی و تایید می‌کند.\n"
    )

    if uid == OWNER_ID:
        await update.message.reply_text(welcome, reply_markup=admin_menu())
    else:
        await update.message.reply_text(welcome, reply_markup=user_menu())

# -------------------- پشتیبانی -------------------- #

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📞 پشتیبانی فروش:\n"
        f"شماره تماس: {SUPPORT_PHONE}\n"
        f"شماره کارت: {CARD_NUMBER}\n"
        "برای هماهنگی تماس یا واتساپ."
    )
    await update.message.reply_text(text)

# -------------------- ثبت آگهی -------------------- #

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = "province"
    temp_data[uid] = {"photos": []}
    await update.message.reply_text("استان موتور را بنویس:")

# -------------------- ارسال آگهی برای مدیر -------------------- #

async def send_to_admin(context, ad_id, ad):
    caption = (
        f"🔔 آگهی جدید #{ad_id}\n"
        f"{ad['province']} - {ad['city']}\n"
        f"{ad['motor_type']} | {ad['model']}\n"
        f"سال: {ad['year']} | کارکرد: {ad['km']} km\n"
        f"رنگ: {ad['color']} | تصادف: {ad['accident']} | سند: {ad['document']}\n"
        f"بیمه: {ad['insurance']} ماه\n"
        f"قیمت: {ad['price']} ریال\n"
        f"تماس: {ad['phone']}"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✔ تایید", callback_data=f"approve_{ad_id}"),
            InlineKeyboardButton("❌ حذف", callback_data=f"delete_{ad_id}")
        ]
    ])

    await context.bot.send_media_group(
        chat_id=OWNER_ID,
        media=[InputMediaPhoto(p) for p in ad["photos"]]
    )

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=caption,
        reply_markup=buttons
    )

# -------------------- لیست‌ها -------------------- #

async def list_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ads:
        await update.message.reply_text("هیچ آگهی تایید شده‌ای وجود ندارد.")
        return

    for ad_id, ad in ads.items():
        caption = (
            f"#{ad_id}\n"
            f"{ad['province']} - {ad['city']}\n"
            f"{ad['motor_type']} | {ad['model']}\n"
            f"سال: {ad['year']} | کارکرد: {ad['km']} km\n"
            f"قیمت: {ad['price']} ریال\n"
            f"تماس: {ad['phone']}"
        )

        await update.message.reply_photo(
            photo=ad["photos"][0],
            caption=caption
        )

async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        await update.message.reply_text("این بخش فقط برای مدیر است.")
        return

    if not pending_ads:
        await update.message.reply_text("هیچ آگهی در انتظار تایید نیست.")
        return

    for ad_id, ad in pending_ads.items():
        caption = (
            f"#{ad_id}\n"
            f"{ad['province']} - {ad['city']}\n"
            f"{ad['motor_type']} | {ad['model']}\n"
            f"سال: {ad['year']} | کارکرد: {ad['km']} km\n"
            f"قیمت: {ad['price']} ریال\n"
            f"تماس: {ad['phone']}"
        )

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✔ تایید", callback_data=f"approve_{ad_id}"),
                InlineKeyboardButton("❌ حذف", callback_data=f"delete_{ad_id}")
            ]
        ])

        await update.message.reply_photo(
            photo=ad["photos"][0],
            caption=caption,
            reply_markup=buttons
        )

async def list_sold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not sold_ads:
        await update.message.reply_text("هیچ موتوری فروخته نشده.")
        return

    for ad_id, ad in sold_ads.items():
        await update.message.reply_text(f"فروخته شده: #{ad_id} - {ad['model']}")

async def list_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not deleted_ads:
        await update.message.reply_text("هیچ آگهی حذف نشده.")
        return

    for ad_id, ad in deleted_ads.items():
        await update.message.reply_text(f"حذف شده: #{ad_id} - {ad['model']}")

# -------------------- عکس -------------------- #

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid in user_state and user_state[uid] == "photos":
        temp_data[uid]["photos"].append(update.message.photo[-1].file_id)
        await update.message.reply_text("عکس اضافه شد. اگر تمام شد بنویس: تمام")
        return

    await update.message.reply_text("❌ عکس فقط در مرحله ثبت آگهی مجاز است.")

# -------------------- متن -------------------- #

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()

    if uid in user_state:
        st = user_state[uid]

        if st == "province":
            temp_data[uid]["province"] = text
            user_state[uid] = "city"
            await update.message.reply_text("شهر موتور را بنویس:")
            return

        if st == "city":
            temp_data[uid]["city"] = text
            user_state[uid] = "motor_type"
            await update.message.reply_text("نوع موتور را بنویس:")
            return

        if st == "motor_type":
            temp_data[uid]["motor_type"] = text
            user_state[uid] = "model"
            await update.message.reply_text("مدل موتور را بنویس:")
            return

        if st == "model":
            temp_data[uid]["model"] = text
            user_state[uid] = "year"
            await update.message.reply_text("سال ساخت را بنویس:")
            return

        if st == "year":
            temp_data[uid]["year"] = int(text) if text.isdigit() else 0
            user_state[uid] = "km"
            await update.message.reply_text("کارکرد را بنویس:")
            return

        if st == "km":
            temp_data[uid]["km"] = int(text) if text.isdigit() else 0
            user_state[uid] = "color"
            await update.message.reply_text("رنگ موتور را بنویس:")
            return

        if st == "color":
            temp_data[uid]["color"] = text
            user_state[uid] = "accident"
            await update.message.reply_text("وضعیت تصادف را بنویس:")
            return

        if st == "accident":
            temp_data[uid]["accident"] = text
            user_state[uid] = "document"
            await update.message.reply_text("وضعیت سند را بنویس:")
            return

        if st == "document":
            temp_data[uid]["document"] = text
            user_state[uid] = "insurance"
            await update.message.reply_text("بیمه را بنویس:")
            return

        if st == "insurance":
            temp_data[uid]["insurance"] = int(text) if text.isdigit() else 0
            user_state[uid] = "price"
            await update.message.reply_text("قیمت را بنویس:")
            return

        if st == "price":
            temp_data[uid]["price"] = text
            user_state[uid] = "phone"
            await update.message.reply_text("شماره تماس را بنویس:")
            return

        if st == "phone":
            temp_data[uid]["phone"] = text
            user_state[uid] = "photos"
            await update.message.reply_text("عکس‌های موتور را بفرست. اگر تمام شد بنویس: تمام")
            return

        if st == "photos":
            if text == "تمام":
                global next_ad_id
                ad_id = next_ad_id
                next_ad_id += 1

                pending_ads[ad_id] = {
                    **temp_data[uid],
                    "owner_id": uid
                }

                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 ارسال به مدیر (پس از پرداخت)", callback_data=f"payfirst_{ad_id}")]
                ])

                await update.message.reply_text(
                    f"برای ثبت آگهی #{ad_id} مبلغ ۷۰۰۰۰۰۰ ریال را به کارت زیر واریز کنید:\n{CARD_NUMBER}\n\nپس از پرداخت، دکمهٔ ارسال فعال می‌شود.",
                    reply_markup=buttons
                )

                del user_state[uid]
                return

            else:
                await update.message.reply_text("اگر عکس دیگری نداری بنویس: تمام")
                return

    # دستورات اصلی
    if text == "ثبت آگهی موتور":
        await new_ad(update, context)
    elif text == "لیست آگهی‌ها":
        await list_ads(update, context)
    elif text == "لیست فروش":
        await list_sold(update, context)
    elif text == "لیست انتظار":
        await list_pending(update, context)
    elif text == "لیست حذف‌شده‌ها":
        await list_deleted(update, context)
    elif text == "تماس با پشتیبانی":
        await support(update, context)
    else:
        await update.message.reply_text("دستور نامعتبر است.")

# -------------------- دکمه‌ها -------------------- #

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("payfirst_"):
        ad_id = int(data.split("_")[1])
        await query.edit_message_text(
            "پس از پرداخت، رسید را برای مدیر ارسال کنید.\n"
            "مدیر پس از تایید پرداخت، آگهی را ثبت می‌کند."
        )
        return

    if data.startswith("approve_"):
        ad_id = int(data.split("_")[1])
        ads[ad_id] = pending_ads[ad_id]
        del pending_ads[ad_id]
        await query.edit_message_text(f"آگهی #{ad_id} تایید شد.")
        return

    if data.startswith("delete_"):
        ad_id = int(data.split("_")[1])
        deleted_ads[ad_id] = pending_ads[ad_id]
        del pending_ads[ad_id]
        await query.edit_message_text(f"آگهی #{ad_id} حذف شد.")
        return

# -------------------- اجرا -------------------- #

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", get_id))

    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()

if __name__ == "__main__":
    main()