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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# -------------------- داده‌ها -------------------- #

ads: Dict[int, Dict[str, Any]] = {}          # آگهی‌های تایید شده
pending_ads: Dict[int, Dict[str, Any]] = {}  # آگهی‌های در انتظار تأیید
user_state: Dict[int, str] = {}              # وضعیت مرحله هر کاربر
temp_data: Dict[int, Dict[str, Any]] = {}    # دادهٔ موقت ثبت آگهی
next_ad_id: int = 1                          # شماره آگهی بعدی

# -------------------- منوها -------------------- #

def user_menu():
    return ReplyKeyboardMarkup(
        [["ثبت آگهی موتور", "لیست آگهی‌ها"], ["تماس با پشتیبانی"]],
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        [["ثبت آگهی موتور", "لیست آگهی‌ها"], ["آگهی‌های در انتظار تأیید", "تماس با پشتیبانی"]],
        resize_keyboard=True
    )

# -------------------- اعتبارسنجی -------------------- #

def is_valid_price(t):
    return t.isdigit() and int(t) > 0

def is_valid_phone(t):
    return t.isdigit() and len(t) == 11

# -------------------- شروع -------------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid == OWNER_ID:
        await update.message.reply_text("سلام مدیر عزیز👑", reply_markup=admin_menu())
    else:
        await update.message.reply_text("سلام موتوریاز عزیز🔥", reply_markup=user_menu())

# -------------------- پشتیبانی -------------------- #

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📞 پشتیبانی فروش:\n"
        f"شماره تماس: {SUPPORT_PHONE}\n"
        f"شماره کارت: {CARD_NUMBER}\n"
        "برای هماهنگی تماس یا واتساپ."
    )
    await update.message.reply_text(text)

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
            InlineKeyboardButton("✔ تأیید", callback_data=f"approve_{ad_id}"),
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

# -------------------- ثبت آگهی -------------------- #

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = "province"
    temp_data[uid] = {"photos": []}
    await update.message.reply_text("استان موتور را بنویس:")

# -------------------- لیست آگهی‌ها -------------------- #

async def list_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not ads:
        await update.message.reply_text("هیچ آگهی تایید شده‌ای وجود ندارد.")
        return

    for ad_id, ad in ads.items():
        caption = (
            f"#{ad_id}\n"
            f"{ad['province']} - {ad['city']}\n"
            f"{ad['motor_type']} | {ad['model']}\n"
            f"سال: {ad['year']} | کارکرد: {ad['km']} km\n"
            f"رنگ: {ad['color']} | تصادف: {ad['accident']} | سند: {ad['document']}\n"
            f"بیمه: {ad['insurance']} ماه\n"
            f"قیمت: {ad['price']} ریال\n"
            f"تماس: {ad['phone']}"
        )

        # دکمه حذف برای صاحب آگهی
        if ad["owner_id"] == uid:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑 حذف آگهی من", callback_data=f"mydelete_{ad_id}")]
            ])
        else:
            kb = None

        await update.message.reply_photo(
            photo=ad["photos"][0],
            caption=caption,
            reply_markup=kb
        )

# -------------------- لیست آگهی‌های در انتظار تأیید -------------------- #

async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        await update.message.reply_text("این بخش فقط برای مدیر است.")
        return

    if not pending_ads:
        await update.message.reply_text("هیچ آگهی در انتظار تأیید وجود ندارد.")
        return

    for ad_id, ad in pending_ads.items():
        caption = (
            f"#{ad_id}\n"
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
                InlineKeyboardButton("✔ تأیید", callback_data=f"approve_{ad_id}"),
                InlineKeyboardButton("❌ حذف", callback_data=f"delete_{ad_id}")
            ]
        ])

        await update.message.reply_photo(
            photo=ad["photos"][0],
            caption=caption,
            reply_markup=buttons
        )

# -------------------- عکس -------------------- #

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message

    # مرحله عکس‌های آگهی
    if uid in user_state and user_state[uid] == "photos":
        temp_data[uid]["photos"].append(msg.photo[-1].file_id)
        await msg.reply_text("عکس اضافه شد. اگر تمام شد بنویس: تمام")
        return

    # مرحله رسید پرداخت
    if uid in user_state and user_state[uid].startswith("payment_"):
        ad_id = int(user_state[uid].split("_")[1])
        await msg.reply_text("رسید دریافت شد. آگهی برای مدیر ارسال شد.")
        await send_to_admin(context, ad_id, pending_ads[ad_id])
        del user_state[uid]
        del temp_data[uid]
        return

    await msg.reply_text("❌ عکس فقط در مرحله ثبت آگهی یا ارسال رسید مجاز است.")

# -------------------- متن -------------------- #

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message
    text = msg.text.strip()

    # مراحل ثبت آگهی
    if uid in user_state:
        st = user_state[uid]

        if st == "province":
            temp_data[uid]["province"] = text
            user_state[uid] = "city"
            await msg.reply_text("شهر موتور را بنویس:")
            return

        if st == "city":
            temp_data[uid]["city"] = text
            user_state[uid] = "motor_type"
            await msg.reply_text("نوع موتور را بنویس:")
            return

        if st == "motor_type":
            temp_data[uid]["motor_type"] = text
            user_state[uid] = "model"
            await msg.reply_text("مدل موتور را بنویس:")
            return

        if st == "model":
            temp_data[uid]["model"] = text
            user_state[uid] = "year"
            await msg.reply_text("سال ساخت را بنویس:")
            return

        if st == "year":
            temp_data[uid]["year"] = int(text) if text.isdigit() else 0
            user_state[uid] = "km"
            await msg.reply_text("کارکرد را بنویس:")
            return

        if st == "km":
            temp_data[uid]["km"] = int(text) if text.isdigit() else 0
            user_state[uid] = "color"
            await msg.reply_text("رنگ موتور را بنویس:")
            return

        if st == "color":
            temp_data[uid]["color"] = text
            user_state[uid] = "accident"
            await msg.reply_text("وضعیت تصادف را بنویس:")
            return

        if st == "accident":
            temp_data[uid]["accident"] = text
            user_state[uid] = "document"
            await msg.reply_text("وضعیت سند را بنویس:")
            return

        if st == "document":
            temp_data[uid]["document"] = text
            user_state[uid] = "insurance"
            await msg.reply_text("بیمه را بنویس:")
            return

        if st == "insurance":
            temp_data[uid]["insurance"] = int(text) if text.isdigit() else 0
            user_state[uid] = "price"
            await msg.reply_text("قیمت را بنویس (عدد):")
            return

        if st == "price":
            if not is_valid_price(text):
                await msg.reply_text("❌ قیمت باید عدد باشد.")
                return
            temp_data[uid]["price"] = text
            user_state[uid] = "phone"
            await msg.reply_text("شماره تماس را بنویس:")
            return

        if st == "phone":
            if not is_valid_phone(text):
                await msg.reply_text("❌ شماره تماس باید 11 رقم باشد.")
                return
            temp_data[uid]["phone"] = text
            user_state[uid] = "photos"
            await msg.reply_text("عکس‌های موتور را بفرست. اگر تمام شد بنویس: تمام")
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

                # پیام نهایی به مشتری با دکمه‌ها
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 ثبت برای خریداران", callback_data=f"user_publish_{ad_id}")],
                    [InlineKeyboardButton("🗑 حذف آگهی", callback_data=f"user_delete_{ad_id}")]
                ])

                await msg.reply_text(
                    f"آگهی #{ad_id} آماده است.\nبرای ثبت در لیست خریداران روی دکمه بزن.",
                    reply_markup=buttons
                )

                del user_state[uid]
                return

            else:
                await msg.reply_text("اگر عکس دیگری نداری بنویس: تمام")
                return

    # دستورات اصلی
    if text == "ثبت آگهی موتور":
        await new_ad(update, context)
    elif text == "لیست آگهی‌ها":
        await list_ads(update, context)
    elif text == "آگهی‌های در انتظار تأیید":
        await list_pending(update, context)
    elif text == "تماس با پشتیبانی":
        await support(update, context)
    else:
        await msg.reply_text("دستور نامعتبر است.")

# -------------------- دکمه‌ها -------------------- #

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # مشتری: ثبت برای خریداران
    if data.startswith("user_publish_"):
        ad_id = int(data.split("_")[2])
        await query.edit_message_text("آگهی برای مدیر ارسال شد. منتظر تأیید باشید.")
        await send_to_admin(context, ad_id, pending_ads[ad_id])
        return

    # مشتری: حذف آگهی
    if data.startswith("user_delete_"):
        ad_id = int(data.split("_")[2])
        if ad_id in pending_ads:
            del pending_ads[ad_id]
        await query.edit_message_text("آگهی حذف شد.")
        return

    # مدیر: تأیید
    if data.startswith("approve_"):
        ad_id = int(data.split("_")[1])
        ads[ad_id] = pending_ads[ad_id]
        del pending_ads[ad_id]
        await query.edit_message_text(f"آگهی #{ad_id} ✔ تأیید شد.")
        return

    # مدیر: حذف
    if data.startswith("delete_"):
        ad_id = int(data.split("_")[1])
        del pending_ads[ad_id]
        await query.edit_message_text(f"آگهی #{ad_id} ❌ حذف شد.")
        return

    # صاحب آگهی: حذف آگهی تایید شده
    if data.startswith("mydelete_"):
        ad_id = int(data.split("_")[1])
        del ads[ad_id]
        await query.edit_message_text("آگهی شما حذف شد.")
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