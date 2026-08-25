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

# -------------------- تنظیمات امن -------------------- #

TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
SUPPORT_PHONE = os.getenv("SUPPORT_PHONE", "")
CARD_NUMBER = os.getenv("CARD_NUMBER", "")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "")

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

def user_menu() -> ReplyKeyboardMarkup:
    kb = [
        ["ثبت آگهی موتور", "لیست آگهی‌ها"],
        ["جستجو پیشرفته", "تماس با پشتیبانی"],
        ["دستیار هوشمند"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    kb = [
        ["ثبت آگهی موتور", "لیست آگهی‌ها"],
        ["آگهی‌های در انتظار تأیید", "جستجو پیشرفته"],
        ["دستیار هوشمند"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# -------------------- اعتبارسنجی‌های ساده -------------------- #

def is_valid_price(t: str) -> bool:
    return t.isdigit() and int(t) > 0


def is_valid_phone(t: str) -> bool:
    return t.isdigit() and len(t) == 11

# -------------------- شروع -------------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if uid == OWNER_ID:
        await update.message.reply_text(
            "سلام مدیر عزیز👑\nبه پنل مدیریت ربات موتور خوش آمدید.",
            reply_markup=admin_menu(),
        )
    else:
        await update.message.reply_text(
            "سلام موتوریاز عزیز🔥\nبه بزرگترین ربات خرید و فروش موتور خوش آمدی!",
            reply_markup=user_menu(),
        )

# -------------------- تماس با پشتیبانی -------------------- #

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if uid == OWNER_ID:
        await update.message.reply_text(
            "شما مدیر هستید، بخش پشتیبانی برای مشتری‌هاست.",
            reply_markup=admin_menu(),
        )
        return

    text = (
        "📞 پشتیبانی فروش:\n"
        f"شماره تماس: {SUPPORT_PHONE}\n"
        f"شماره کارت: {CARD_NUMBER}\n"
        "برای هماهنگی تماس یا واتساپ."
    )
    await update.message.reply_text(text, reply_markup=user_menu())

# -------------------- دستور /id -------------------- #

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"ایدی عددی شما: {update.effective_user.id}"
    )

# -------------------- ارسال آگهی برای مدیر -------------------- #

async def send_ad_to_admin(
    context: ContextTypes.DEFAULT_TYPE,
    ad_id: int,
    ad: Dict[str, Any],
) -> None:
    caption = (
        f"🔔 آگهی جدید:\n"
        f"#{ad_id}\n"
        f"{ad['province']} - {ad['city']}\n"
        f"{ad['motor_type']} | {ad['model']}\n"
        f"سال: {ad['year']} | کارکرد: {ad['km']} km\n"
        f"رنگ: {ad['color']} | تصادف: {ad['accident']} | سند: {ad['document']}\n"
        f"بیمه: {ad['insurance']} ماه\n"
        f"قیمت: {ad['price']} ریال\n"
        f"تماس: {ad['phone']}\n"
        f"تعداد عکس: {len(ad['photos'])}"
    )

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✔ تأیید", callback_data=f"approve_{ad_id}"
                ),
                InlineKeyboardButton(
                    "❌ حذف", callback_data=f"delete_{ad_id}"
                ),
            ]
        ]
    )

    if ad["photos"]:
        await context.bot.send_media_group(
            chat_id=OWNER_ID,
            media=[
                InputMediaPhoto(media=pid)
                for pid in ad["photos"]
            ],
        )
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=caption,
            reply_markup=buttons,
        )
    else:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=caption,
            reply_markup=buttons,
        )

# -------------------- ثبت آگهی -------------------- #

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    user_state[uid] = "province"
    temp_data[uid] = {"photos": []}
    await update.message.reply_text("استان موتور را بنویس:")

# -------------------- لیست آگهی‌های تایید شده -------------------- #

async def list_ads(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if not ads:
        await update.message.reply_text(
            "هیچ آگهی تایید شده‌ای وجود ندارد.",
            reply_markup=admin_menu() if uid == OWNER_ID else user_menu(),
        )
        return

    text = ""
    for ad_id, ad in ads.items():
        text += (
            f"#{ad_id}\n"
            f"{ad['province']} - {ad['city']}\n"
            f"{ad['motor_type']} | {ad['model']}\n"
            f"سال: {ad['year']} | کارکرد: {ad['km']} km\n"
            f"رنگ: {ad['color']} | تصادف: {ad['accident']} | سند: {ad['document']}\n"
            f"بیمه: {ad['insurance']} ماه\n"
            f"قیمت: {ad['price']} ریال\n"
            f"تماس: {ad['phone']}\n\n"
        )

    await update.message.reply_text(
        text,
        reply_markup=admin_menu() if uid == OWNER_ID else user_menu(),
    )

# -------------------- لیست آگهی‌های در انتظار تأیید -------------------- #

async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if uid != OWNER_ID:
        await update.message.reply_text(
            "این بخش فقط برای مدیر است.",
            reply_markup=user_menu(),
        )
        return

    if not pending_ads:
        await update.message.reply_text(
            "هیچ آگهی در انتظار تأیید وجود ندارد.",
            reply_markup=admin_menu(),
        )
        return

    text = ""
    for ad_id, ad in pending_ads.items():
        text += (
            f"#{ad_id}\n"
            f"{ad['province']} - {ad['city']}\n"
            f"{ad['motor_type']} | {ad['model']}\n"
            f"سال: {ad['year']} | کارکرد: {ad['km']} km\n"
            f"رنگ: {ad['color']} | تصادف: {ad['accident']} | سند: {ad['document']}\n"
            f"بیمه: {ad['insurance']} ماه\n"
            f"قیمت: {ad['price']} ریال\n"
            f"تماس: {ad['phone']}\n\n"
        )

    await update.message.reply_text(
        text,
        reply_markup=admin_menu(),
    )

# -------------------- جستجو پیشرفته (حرفه‌ای) -------------------- #

def match_filters(ad: Dict[str, Any], f: Dict[str, Any]) -> bool:
    if f.get("province") and f["province"] not in ad["province"]:
        return False
    if f.get("city") and f["city"] not in ad["city"]:
        return False
    if f.get("motor_type") and f["motor_type"] not in ad["motor_type"]:
        return False
    if f.get("model") and f["model"] not in ad["model"]:
        return False
    if f.get("year_min") and ad["year"] < f["year_min"]:
        return False
    if f.get("year_max") and ad["year"] > f["year_max"]:
        return False
    price_int = int(ad["price"])
    if f.get("price_min") and price_int < f["price_min"]:
        return False
    if f.get("price_max") and price_int > f["price_max"]:
        return False
    if f.get("km_min") and ad["km"] < f["km_min"]:
        return False
    if f.get("km_max") and ad["km"] > f["km_max"]:
        return False
    if f.get("color") and f["color"] not in ad["color"]:
        return False
    if f.get("accident") and f["accident"] not in ad["accident"]:
        return False
    if f.get("document") and f["document"] not in ad["document"]:
        return False
    if f.get("insurance_min") and ad["insurance"] < f["insurance_min"]:
        return False
    return True


async def search_advanced(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    text = update.message.text.strip()

    if text == "جستجو پیشرفته":
        user_state[uid] = "search_province"
        temp_data[uid] = {"filters": {}}
        await update.message.reply_text(
            "🔍 جستجو پیشرفته:\nاستان مورد نظر را بنویس (یا خالی بگذار):",
            reply_markup=admin_menu() if uid == OWNER_ID else user_menu(),
        )
        return

    if uid not in user_state or not user_state[uid].startswith("search_"):
        return

    st = user_state[uid]
    f = temp_data[uid]["filters"]

    def empty_to_none(t: str) -> str | None:
        return t if t else None

    if st == "search_province":
        if text:
            f["province"] = text
        user_state[uid] = "search_city"
        await update.message.reply_text("شهر مورد نظر را بنویس (یا خالی بگذار):")
        return

    if st == "search_city":
        if text:
            f["city"] = text
        user_state[uid] = "search_motor_type"
        await update.message.reply_text("نوع موتور را بنویس (یا خالی بگذار):")
        return

    if st == "search_motor_type":
        if text:
            f["motor_type"] = text
        user_state[uid] = "search_model"
        await update.message.reply_text("مدل موتور را بنویس (یا خالی بگذار):")
        return

    if st == "search_model":
        if text:
            f["model"] = text
        user_state[uid] = "search_year_min"
        await update.message.reply_text("حداقل سال ساخت (مثلاً 1395 یا خالی):")
        return

    if st == "search_year_min":
        if text:
            if text.isdigit():
                f["year_min"] = int(text)
            else:
                await update.message.reply_text("سال باید عدد باشد یا خالی.")
                return
        user_state[uid] = "search_year_max"
        await update.message.reply_text("حداکثر سال ساخت (مثلاً 1403 یا خالی):")
        return

    if st == "search_year_max":
        if text:
            if text.isdigit():
                f["year_max"] = int(text)
            else:
                await update.message.reply_text("سال باید عدد باشد یا خالی.")
                return
        user_state[uid] = "search_km_min"
        await update.message.reply_text("حداقل کارکرد (km، عدد یا خالی):")
        return

    if st == "search_km_min":
        if text:
            if text.isdigit():
                f["km_min"] = int(text)
            else:
                await update.message.reply_text("کارکرد باید عدد باشد یا خالی.")
                return
        user_state[uid] = "search_km_max"
        await update.message.reply_text("حداکثر کارکرد (km، عدد یا خالی):")
        return

    if st == "search_km_max":
        if text:
            if text.isdigit():
                f["km_max"] = int(text)
            else:
                await update.message.reply_text("کارکرد باید عدد باشد یا خالی.")
                return
        user_state[uid] = "search_price_min"
        await update.message.reply_text("حداقل قیمت (ریال، عدد یا خالی):")
        return

    if st == "search_price_min":
        if text:
            if is_valid_price(text):
                f["price_min"] = int(text)
            else:
                await update.message.reply_text("قیمت باید عدد مثبت باشد یا خالی.")
                return
        user_state[uid] = "search_price_max"
        await update.message.reply_text("حداکثر قیمت (ریال، عدد یا خالی):")
        return

    if st == "search_price_max":
        if text:
            if is_valid_price(text):
                f["price_max"] = int(text)
            else:
                await update.message.reply_text("قیمت باید عدد مثبت باشد یا خالی.")
                return
        user_state[uid] = "search_color"
        await update.message.reply_text("رنگ (مثلاً مشکی، یا خالی):")
        return

    if st == "search_color":
        if text:
            f["color"] = text
        user_state[uid] = "search_accident"
        await update.message.reply_text("وضعیت تصادف (مثلاً بی‌تصادف، یا خالی):")
        return

    if st == "search_accident":
        if text:
            f["accident"] = text
        user_state[uid] = "search_document"
        await update.message.reply_text("وضعیت سند (مثلاً تک‌برگ، یا خالی):")
        return

    if st == "search_document":
        if text:
            f["document"] = text
        user_state[uid] = "search_insurance_min"
        await update.message.reply_text("حداقل بیمه (ماه، عدد یا خالی):")
        return

    if st == "search_insurance_min":
        if text:
            if text.isdigit():
                f["insurance_min"] = int(text)
            else:
                await update.message.reply_text("بیمه باید عدد باشد یا خالی.")
                return

        result = ""
        for ad_id, ad in ads.items():
            if match_filters(ad, f):
                result += (
                    f"#{ad_id}\n"
                    f"{ad['province']} - {ad['city']}\n"
                    f"{ad['motor_type']} | {ad['model']}\n"
                    f"سال: {ad['year']} | کارکرد: {ad['km']} km\n"
                    f"رنگ: {ad['color']} | تصادف: {ad['accident']} | سند: {ad['document']}\n"
                    f"بیمه: {ad['insurance']} ماه\n"
                    f"قیمت: {ad['price']} ریال\n"
                    f"تماس: {ad['phone']}\n\n"
                )

        if not result:
            await update.message.reply_text(
                "هیچ آگهی مطابق فیلترها پیدا نشد.",
                reply_markup=admin_menu() if uid == OWNER_ID else user_menu(),
            )
        else:
            await update.message.reply_text(
                result,
                reply_markup=admin_menu() if uid == OWNER_ID else user_menu(),
            )

        del user_state[uid]
        del temp_data[uid]
        return

# -------------------- دستیار هوشمند (ساده) -------------------- #

async def assistant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    text = update.message.text.strip()

    if text == "دستیار هوشمند":
        user_state[uid] = "assistant"
        await update.message.reply_text(
            "متن توضیحات موتور را بفرست (هرچه دوست داری بنویس):",
            reply_markup=admin_menu() if uid == OWNER_ID else user_menu(),
        )
        return

    if uid in user_state and user_state[uid] == "assistant":
        await update.message.reply_text(
            "✅ توضیحات دریافت شد.\nاین نسخه فقط ثبت آگهی و فیلتر حرفه‌ای دارد.",
            reply_markup=admin_menu() if uid == OWNER_ID else user_menu(),
        )
        del user_state[uid]
        return

# -------------------- هندل عکس -------------------- #

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    msg = update.message

    if uid in user_state and user_state[uid] == "photos":
        photo_id = msg.photo[-1].file_id
        temp_data[uid]["photos"].append(photo_id)
        await msg.reply_text(
            "✅ عکس اضافه شد. اگر عکس دیگری داری، بفرست؛ اگر تمام شد، بنویس: تمام"
        )
    elif uid in user_state and user_state[uid].startswith("payment_"):
        ad_id = int(user_state[uid].split("_")[1])
        await msg.reply_text(
            "✅ رسید دریافت شد. آگهی برای مدیر ارسال شد.",
            reply_markup=user_menu() if uid != OWNER_ID else admin_menu(),
        )
        await send_ad_to_admin(context, ad_id, pending_ads[ad_id])
        del user_state[uid]
        del temp_data[uid]
    else:
        await msg.reply_text("❌ عکس فقط در مرحله ثبت آگهی موتور یا ارسال رسید مجاز است.")

# -------------------- هندل متن -------------------- #

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    msg = update.message
    text = msg.text.strip()

    if text == "جستجو پیشرفته" or (
        uid in user_state and user_state[uid].startswith("search_")
    ):
        await search_advanced(update, context)
        return

    if text == "دستیار هوشمند" or (
        uid in user_state and user_state[uid] == "assistant"
    ):
        await assistant(update, context)
        return

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
            await msg.reply_text("نوع موتور را بنویس (مثلاً اسکوتر، آپاچی، هوندا و ...):")
            return

        if st == "motor_type":
            temp_data[uid]["motor_type"] = text
            user_state[uid] = "model"
            await msg.reply_text("مدل موتور را بنویس:")
            return

        if st == "model":
            temp_data[uid]["model"] = text
            user_state[uid] = "year"
            await msg.reply_text("سال ساخت را بنویس (مثلاً 1398):")
            return

        if st == "year":
            temp_data[uid]["year"] = text if text else "نامشخص"
            user_state[uid] = "km"
            await msg.reply_text("کارکرد را بنویس (به کیلومتر، مثلاً 25000):")
            return

        if st == "km":
            temp_data[uid]["km"] = int(text) if text.isdigit() else 0
            user_state[uid] = "color"
            await msg.reply_text("رنگ موتور را بنویس:")
            return

        if st == "color":
            temp_data[uid]["color"] = text
            user_state[uid] = "accident"
            await msg.reply_text("وضعیت تصادف را بنویس (مثلاً بی‌تصادف، تصادفی و ...):")
            return

        if st == "accident":
            temp_data[uid]["accident"] = text
            user_state[uid] = "document"
            await msg.reply_text("وضعیت سند را بنویس (مثلاً تک‌برگ، قولنامه و ...):")
            return

        if st == "document":
            temp_data[uid]["document"] = text
            user_state[uid] = "insurance"
            await msg.reply_text("بیمه را بنویس (مثلاً 12 ماه، یا بدون بیمه):")
            return

        if st == "insurance":
            temp_data[uid]["insurance"] = int(text) if text.isdigit() else 0
            user_state[uid] = "price"
            await msg.reply_text("قیمت را بنویس (به ریال، فقط عدد):")
            return

        if st == "price":
            if not is_valid_price(text):
                await msg.reply_text("❌ قیمت باید عدد مثبت باشد.")
                return
            temp_data[uid]["price"] = text
            user_state[uid] = "phone"
            await msg.reply_text("شماره تماس را بنویس (11 رقم):")
            return

        if st == "phone":
            if not is_valid_phone(text):
                await msg.reply_text("❌ شماره تماس باید 11 رقم باشد.")
                return
            temp_data[uid]["phone"] = text
            user_state[uid] = "photos"
            await msg.reply_text(
                "حالا عکس‌های موتور را بفرست. حداقل یک عکس لازم است.\nاگر تمام شد، بنویس: تمام"
            )
            return

        if st == "photos":
            if text == "تمام":
                if len(temp_data[uid]["photos"]) < 1:
                    await msg.reply_text("❌ حداقل یک عکس لازم است.")
                    return

                global next_ad_id
                ad_id = next_ad_id
                next_ad_id += 1

                pending_ads[ad_id] = {
                    "province": temp_data[uid]["province"],
                    "city": temp_data[uid]["city"],
                    "motor_type": temp_data[uid]["motor_type"],
                    "model": temp_data[uid]["model"],
                    "year": int(temp_data[uid]["year"]) if str(temp_data[uid]["year"]).isdigit() else 0,
                    "km": temp_data[uid]["km"],
                    "color": temp_data[uid]["color"],
                    "accident": temp_data[uid]["accident"],
                    "document": temp_data[uid]["document"],
                    "insurance": temp_data[uid]["insurance"],
                    "price": temp_data[uid]["price"],
                    "phone": temp_data[uid]["phone"],
                    "photos": temp_data[uid]["photos"],
                    "owner_id": uid,
                }

                await msg.reply_text(
                    f"برای ثبت نهایی آگهی #{ad_id}، مبلغ ۷۰۰۰۰۰۰ ریال را به شماره کارت زیر واریز کن:\n{CARD_NUMBER}\n\nپس از واریز، عکس رسید را ارسال کن.",
                    reply_markup=user_menu()
                    if uid != OWNER_ID
                    else admin_menu(),
                )

                user_state[uid] = f"payment_{ad_id}"
                return
            else:
                await msg.reply_text("اگر عکس دیگری نداری، بنویس: تمام")
                return

        if st.startswith("payment_"):
            await msg.reply_text("❌ لطفاً عکس رسید واریز را ارسال کن.")
            return

    if text == "ثبت آگهی موتور":
        await new_ad(update, context)
    elif text == "لیست آگهی‌ها":
        await list_ads(update, context)
    elif text == "آگهی‌های در انتظار تأیید":
        await list_pending(update, context)
    elif text == "تماس با پشتیبانی":
        await support(update, context)
    elif text == "جستجو پیشرفته":
        await search_advanced(update, context)
    elif text == "دستیار هوشمند":
        await assistant(update, context)
    else:
        await msg.reply_text(
            "دستور نامعتبر است.",
            reply_markup=admin_menu() if uid == OWNER_ID else user_menu(),
        )

# -------------------- دکمه‌های تایید و حذف -------------------- #

async def callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("approve_"):
        ad_id = int(data.split("_")[1])
        if ad_id in pending_ads:
            ads[ad_id] = pending_ads[ad_id]
            del pending_ads[ad_id]
            await query.edit_message_text(
                text=f"آگهی #{ad_id} ✔ تأیید شد.",
            )
        else:
            await query.edit_message_text("آگهی یافت نشد یا قبلاً رسیدگی شده است.")

    elif data.startswith("delete_"):
        ad_id = int(data.split("_")[1])
        if ad_id in pending_ads:
            del pending_ads[ad_id]
            await query.edit_message_text(
                text=f"آگهی #{ad_id} ❌ حذف شد.",
            )
        else:
            await query.edit_message_text("آگهی یافت نشد یا قبلاً حذف شده است.")

# -------------------- اجرا -------------------- #

def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", get_id))

    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    app.run_polling()


if __name__ == "__main__":
    main()