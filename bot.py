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

# -------------------- دیتابیس ساده -------------------- #

ads: Dict[int, Dict[str, Any]] = {}         # آگهی‌های تایید شده
pending_ads: Dict[int, Dict[str, Any]] = {} # آگهی‌های در انتظار پرداخت/تایید
sold_ads: Dict[int, Dict[str, Any]] = {}    # آگهی‌های فروخته شده
user_state: Dict[int, str] = {}             # مرحلهٔ کاربر
temp_data: Dict[int, Dict[str, Any]] = {}   # دادهٔ موقت ثبت آگهی
next_ad_id: int = 1                         # شماره آگهی

# -------------------- منو مشتری -------------------- #

def user_menu():
    return ReplyKeyboardMarkup(
        [
            ["ثبت آگهی موتور"],
            ["لیست آگهی‌های فروشندگان"],
            ["شماره پشتیبانی"],
        ],
        resize_keyboard=True
    )

# -------------------- منو مدیر -------------------- #

def admin_menu():
    return ReplyKeyboardMarkup(
        [
            ["ثبت آگهی‌ها"],
            ["لیست آگهی‌ها"],
            ["لیست انتظار"],
            ["لیست فروش"],
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
        "• مبلغ ۷۰۰۰۰۰۰ ریال باید واریز شود تا آگهی شما ثبت شود (به جز مدیر).\n"
        "• آگهی تا زمان فروش موتور بدون محدودیت زمانی در ربات می‌ماند.\n"
        "• پس از ثبت آگهی، مدیر بررسی و تایید می‌کند.\n"
    )

    if uid == OWNER_ID:
        await update.message.reply_text(welcome, reply_markup=admin_menu())
    else:
        await update.message.reply_text(welcome, reply_markup=user_menu())

# -------------------- پشتیبانی -------------------- #

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📞 شماره پشتیبانی:\n{SUPPORT_PHONE}\n\nشماره کارت:\n{CARD_NUMBER}"
    )

# -------------------- ثبت آگهی -------------------- #

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = "province"
    temp_data[uid] = {"photos": []}
    await update.message.reply_text("استان را بنویس:")

# -------------------- ارسال آگهی برای مدیر -------------------- #

async def send_to_admin(context: ContextTypes.DEFAULT_TYPE, ad_id: int, ad: Dict[str, Any]):
    caption = (
        f"🔔 آگهی جدید #{ad_id}\n"
        f"{ad['province']} - {ad['city']}\n"
        f"{ad['motor_type']} | {ad['model']}\n"
        f"سال: {ad['year']} | کارکرد: {ad['km']} km\n"
        f"قیمت: {ad['price']} ریال\n"
        f"تماس: {ad['phone']}"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✔ تایید", callback_data=f"approve_{ad_id}"),
            InlineKeyboardButton("🗑 حذف", callback_data=f"delete_{ad_id}"),
            InlineKeyboardButton("✅ فروخته شد", callback_data=f"sold_{ad_id}"),
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
            f"قیمت: {ad['price']} ریال\n"
            f"تماس: {ad['phone']}"
        )

        if uid == OWNER_ID:
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🗑 حذف", callback_data=f"delad_{ad_id}"),
                    InlineKeyboardButton("✅ فروخته شد", callback_data=f"sold_{ad_id}"),
                ]
            ])
            await update.message.reply_photo(
                photo=ad["photos"][0],
                caption=caption,
                reply_markup=buttons
            )
        else:
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
        await update.message.reply_text("هیچ آگهی در انتظار پرداخت یا تایید نیست.")
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
                InlineKeyboardButton("🗑 حذف", callback_data=f"delete_{ad_id}"),
            ]
        ])

        await update.message.reply_photo(
            photo=ad["photos"][0],
            caption=caption,
            reply_markup=buttons
        )

async def list_sold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        await update.message.reply_text("لیست فروش فقط برای مدیر است.")
        return

    if not sold_ads:
        await update.message.reply_text("هیچ موتوری فروخته نشده.")
        return

    for ad_id, ad in sold_ads.items():
        caption = f"فروخته شده: #{ad_id} - {ad['model']}"
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 حذف", callback_data=f"delsold_{ad_id}")]
        ])
        await update.message.reply_text(caption, reply_markup=buttons)

# -------------------- عکس -------------------- #

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message

    # مرحله ثبت عکس
    if uid in user_state and user_state[uid] == "photos":
        temp_data[uid]["photos"].append(msg.photo[-1].file_id)
        await msg.reply_text("عکس اضافه شد. اگر تمام شد بنویس: تمام")
        return

    # مرحله رسید پرداخت
    if uid in user_state and user_state[uid].startswith("waitpay_"):
        ad_id = int(user_state[uid].split("_")[1])
        await msg.reply_text("رسید دریافت شد. آگهی برای مدیر ارسال شد.")
        await send_to_admin(context, ad_id, pending_ads[ad_id])
        del user_state[uid]
        return

    await msg.reply_text("❌ عکس فقط در مرحله ثبت آگهی یا ارسال رسید مجاز است.")

# -------------------- متن -------------------- #

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message
    text = msg.text.strip()

    # اگر وسط ثبت آگهی هست → منو کار نکند
    if uid in user_state:
        st = user_state[uid]

        if st == "province":
            temp_data[uid]["province"] = text
            user_state[uid] = "city"
            await msg.reply_text("شهر را بنویس:")
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
            if not text.isdigit():
                await msg.reply_text("سال ساخت باید عدد باشد.")
                return
            temp_data[uid]["year"] = int(text)
            user_state[uid] = "km"
            await msg.reply_text("کارکرد را بنویس:")
            return

        if st == "km":
            if not text.isdigit():
                await msg.reply_text("کارکرد باید عدد باشد.")
                return
            temp_data[uid]["km"] = int(text)
            user_state[uid] = "price"
            await msg.reply_text("قیمت را بنویس:")
            return

        if st == "price":
            if not text.isdigit():
                await msg.reply_text("قیمت باید عدد باشد.")
                return
            temp_data[uid]["price"] = int(text)
            user_state[uid] = "phone"
            await msg.reply_text("شماره تماس را بنویس:")
            return

        if st == "phone":
            temp_data[uid]["phone"] = text
            user_state[uid] = "photos"
            await msg.reply_text("عکس‌های موتور را بفرست. اگر تمام شد بنویس: تمام")
            return

        if st == "photos":
            if text == "تمام":
                global next_ad_id
                ad_id = next_ad_id
                next_ad_id += 1

                # مدیر → رایگان
                if uid == OWNER_ID:
                    ads[ad_id] = {
                        **temp_data[uid],
                        "owner_id": uid,
                    }
                    await msg.reply_text(f"آگهی #{ad_id} ثبت شد و در لیست آگهی‌ها قرار گرفت.")
                    del user_state[uid]
                    return

                # مشتری → نیاز به پرداخت
                pending_ads[ad_id] = {
                    **temp_data[uid],
                    "owner_id": uid,
                }

                await msg.reply_text(
                    f"برای ثبت آگهی #{ad_id} مبلغ ۷۰۰۰۰۰۰ ریال را به کارت زیر واریز کنید:\n"
                    f"{CARD_NUMBER}\n\n"
                    "پس از پرداخت، رسید را به صورت عکس ارسال کنید."
                )

                user_state[uid] = f"waitpay_{ad_id}"
                return

            else:
                await msg.reply_text("اگر عکس دیگری نداری بنویس: تمام")
                return

    # دستورات مشتری
    if uid != OWNER_ID:
        if text == "ثبت آگهی موتور":
            await new_ad(update, context)
        elif text == "لیست آگهی‌های فروشندگان":
            await list_ads(update, context)
        elif text == "شماره پشتیبانی":
            await support(update, context)
        else:
            await msg.reply_text("دستور نامعتبر است.")
        return

    # دستورات مدیر
    if uid == OWNER_ID:
        if text == "ثبت آگهی موتور":
            await new_ad(update, context)
        elif text == "لیست آگهی‌ها":
            await list_ads(update, context)
        elif text == "لیست انتظار":
            await list_pending(update, context)
        elif text == "لیست فروش":
            await list_sold(update, context)
        else:
            await msg.reply_text("دستور نامعتبر است.")
        return

# -------------------- دکمه‌ها -------------------- #

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # تایید از pending → ads
    if data.startswith("approve_"):
        ad_id = int(data.split("_")[1])
        if ad_id in pending_ads:
            ads[ad_id] = pending_ads[ad_id]
            del pending_ads[ad_id]
            await query.edit_message_text(f"آگهی #{ad_id} تایید شد و در لیست آگهی‌ها قرار گرفت.")
        return

    # حذف از pending
    if data.startswith("delete_"):
        ad_id = int(data.split("_")[1])
        if ad_id in pending_ads:
            del pending_ads[ad_id]
            await query.edit_message_text(f"آگهی #{ad_id} حذف شد.")
        return

    # فروخته شد از ads → sold_ads
    if data.startswith("sold_"):
        ad_id = int(data.split("_")[1])
        if ad_id in ads:
            sold_ads[ad_id] = ads[ad_id]
            del ads[ad_id]
            await query.edit_message_text(f"آگهی #{ad_id} به عنوان فروخته‌شده ثبت شد.")
        return

    # حذف آگهی از ads
    if data.startswith("delad_"):
        ad_id = int(data.split("_")[1])
        if ad_id in ads:
            del ads[ad_id]
            await query.edit_message_text(f"آگهی #{ad_id} حذف شد.")
        return

    # حذف از sold_ads
    if data.startswith("delsold_"):
        ad_id = int(data.split("_")[1])
        if ad_id in sold_ads:
            del sold_ads[ad_id]
            await query.edit_message_text(f"آگهی #{ad_id} از لیست فروش حذف شد.")
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