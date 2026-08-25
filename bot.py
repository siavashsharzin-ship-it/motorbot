import logging
import os
import re
from typing import Dict, Any, List

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
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

MOTOR_TYPES: List[str] = [
    "اسکوتر",
    "اسپرت",
    "تریل",
    "کراس",
    "کلاسیک",
    "بایک",
    "سفری",
    "شهری",
]

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

# -------------------- اعتبارسنجی -------------------- #

def is_valid_text(t: str, min_len: int = 3) -> bool:
    t = t.strip()
    if len(t) < min_len:
        return False
    if not re.match(r"^[A-Za-zآ-ی0-9\s]+$", t):
        return False
    parts = t.split()
    if len(parts) == 1 and len(parts[0]) < 3:
        return False
    return True


def is_valid_price(t: str) -> bool:
    return t.isdigit() and int(t) > 0


def is_valid_phone(t: str) -> bool:
    return t.isdigit() and len(t) == 11


def is_valid_year(t: str) -> bool:
    return t.isdigit() and 1300 <= int(t) <= 1500


def is_valid_km(t: str) -> bool:
    return t.isdigit() and int(t) >= 0


def normalize_motor_type(t: str) -> str:
    t = t.strip()
    for mt in MOTOR_TYPES:
        if mt in t:
            return mt
    return t

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
        f"{ad['model']} ({ad['motor_type']})\n"
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

    await context.bot.send_photo(
        chat_id=OWNER_ID,
        photo=ad["photos"][0],
        caption=caption,
        reply_markup=buttons,
    )

# -------------------- ثبت آگهی -------------------- #

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    user_state[uid] = "province"
    temp_data[uid] = {"photos": []}
    await update.message.reply_text("استان موتور:")

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
            f"{ad['model']} ({ad['motor_type']})\n"
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
            f"{ad['model']} ({ad['motor_type']})\n"
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

# -------------------- جستجو پیشرفته -------------------- #

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
    if f.get("color") and f["color"] not in ad["color"]:
        return False
    if f.get("accident") and f["accident"] != ad["accident"]:
        return False
    if f.get("document") and f["document"] != ad["document"]:
        return False
    if f.get("insurance_min") and ad["insurance"] < f["insurance_min"]:
        return False
    return True


async def search_advanced(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    text = update.message.text.strip()

    if text == "جستجو پیشرفته":
        user_state[uid] = "search_filters_province"
        temp_data[uid] = {"filters": {}}
        await update.message.reply_text(
            "🔍 جستجو پیشرفته:\nاستان مورد نظر را بنویس (یا بنویس: رد):",
            reply_markup=admin_menu() if uid == OWNER_ID else user_menu(),
        )
        return

    if uid not in user_state or not user_state[uid].startswith("search_filters"):
        return

    st = user_state[uid]
    f = temp_data[uid]["filters"]

    if st == "search_filters_province":
        if text != "رد":
            f["province"] = text
        user_state[uid] = "search_filters_city"
        await update.message.reply_text("شهر مورد نظر را بنویس (یا بنویس: رد):")
        return

    if st == "search_filters_city":
        if text != "رد":
            f["city"] = text
        user_state[uid] = "search_filters_motor_type"
        await update.message.reply_text(
            "نوع موتور (اسکوتر، اسپرت، تریل، کراس، کلاسیک، بایک، سفری، شهری یا رد):"
        )
        return

    if st == "search_filters_motor_type":
        if text != "رد":
            f["motor_type"] = normalize_motor_type(text)
        user_state[uid] = "search_filters_model"
        await update.message.reply_text("مدل موتور (یا بنویس: رد):")
        return

    if st == "search_filters_model":
        if text != "رد":
            f["model"] = text
        user_state[uid] = "search_filters_year_min"
        await update.message.reply_text("حداقل سال ساخت (مثلاً 1395 یا رد):")
        return

    if st == "search_filters_year_min":
        if text != "رد":
            if is_valid_year(text):
                f["year_min"] = int(text)
            else:
                await update.message.reply_text("سال نامعتبر است، دوباره بنویس یا رد:")
                return
        user_state[uid] = "search_filters_year_max"
        await update.message.reply_text("حداکثر سال ساخت (مثلاً 1403 یا رد):")
        return

    if st == "search_filters_year_max":
        if text != "رد":
            if is_valid_year(text):
                f["year_max"] = int(text)
            else:
                await update.message.reply_text("سال نامعتبر است، دوباره بنویس یا رد:")
                return
        user_state[uid] = "search_filters_price_min"
        await update.message.reply_text("حداقل قیمت (به ریال، یا رد):")
        return

    if st == "search_filters_price_min":
        if text != "رد":
            if is_valid_price(text):
                f["price_min"] = int(text)
            else:
                await update.message.reply_text("قیمت نامعتبر است، دوباره بنویس یا رد:")
                return
        user_state[uid] = "search_filters_price_max"
        await update.message.reply_text("حداکثر قیمت (به ریال، یا رد):")
        return

    if st == "search_filters_price_max":
        if text != "رد":
            if is_valid_price(text):
                f["price_max"] = int(text)
            else:
                await update.message.reply_text("قیمت نامعتبر است، دوباره بنویس یا رد:")
                return
        user_state[uid] = "search_filters_color"
        await update.message.reply_text("رنگ (مثلاً مشکی، یا رد):")
        return

    if st == "search_filters_color":
        if text != "رد":
            f["color"] = text
        user_state[uid] = "search_filters_accident"
        await update.message.reply_text("وضعیت تصادف (بی‌تصادف / تصادفی / رد):")
        return

    if st == "search_filters_accident":
        if text != "رد":
            if text in ["بی‌تصادف", "تصادفی"]:
                f["accident"] = text
            else:
                await update.message.reply_text("فقط بی‌تصادف یا تصادفی یا رد:")
                return
        user_state[uid] = "search_filters_document"
        await update.message.reply_text("وضعیت سند (تک‌برگ / دارای سند / رد):")
        return

    if st == "search_filters_document":
        if text != "رد":
            if text in ["تک‌برگ", "دارای سند"]:
                f["document"] = text
            else:
                await update.message.reply_text("فقط تک‌برگ یا دارای سند یا رد:")
                return
        user_state[uid] = "search_filters_insurance_min"
        await update.message.reply_text("حداقل بیمه (ماه، عدد یا رد):")
        return

    if st == "search_filters_insurance_min":
        if text != "رد":
            if text.isdigit():
                f["insurance_min"] = int(text)
            else:
                await update.message.reply_text("فقط عدد یا رد:")
                return

        result = ""
        for ad_id, ad in ads.items():
            if match_filters(ad, f):
                result += (
                    f"#{ad_id}\n"
                    f"{ad['province']} - {ad['city']}\n"
                    f"{ad['model']} ({ad['motor_type']})\n"
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

# -------------------- دستیار هوشمند -------------------- #

def extract_info(text: str) -> Dict[str, Any]:
    info: Dict[str, Any] = {}

    m_color = re.search(r"رنگ\s*([آ-یA-Za-z0-9]+)", text)
    if m_color:
        info["color"] = m_color.group(1).strip()
    else:
        info["color"] = "نامشخص"

    if "بدون تصادف" in text or "بی‌تصادف" in text:
        info["accident"] = "بی‌تصادف"
    elif "تصادف" in text:
        info["accident"] = "تصادفی"
    else:
        info["accident"] = "نامشخص"

    if "سند تک‌برگ" in text or "سند تک برگ" in text:
        info["document"] = "تک‌برگ"
    elif "سند" in text:
        info["document"] = "دارای سند"
    else:
        info["document"] = "نامشخص"

    m_ins = re.search(r"بیمه\s*([\d]+)\s*ماه", text)
    if m_ins:
        info["insurance"] = int(m_ins.group(1))
    else:
        info["insurance"] = None

    m_price = re.search(r"قیمت\s*([\d]+)", text)
    if m_price:
        info["price"] = int(m_price.group(1))
    else:
        info["price"] = None

    return info


def expert_analysis(info: Dict[str, Any]) -> str:
    accident = info.get("accident")
    document = info.get("document")
    insurance = info.get("insurance")
    price = info.get("price")

    lines: List[str] = []
    lines.append("🔧 گزارش کارشناسی هوشمند موتور:\n")

    if accident == "بی‌تصادف":
        lines.append("✅ موتور بدون سابقه تصادف اعلام شده است.")
    elif accident == "تصادفی":
        lines.append("⚠ موتور دارای سابقه تصادف است، نیاز به بررسی دقیق شاسی و فریم دارد.")
    else:
        lines.append("ℹ وضعیت تصادف موتور در متن مشخص نشده است.")

    if document == "تک‌برگ":
        lines.append("✅ سند تک‌برگ، وضعیت حقوقی موتور را شفاف‌تر می‌کند.")
    elif document == "دارای سند":
        lines.append("✅ وجود سند نکته مثبت است، توصیه می‌شود تطبیق پلاک و شماره موتور انجام شود.")
    else:
        lines.append("ℹ وضعیت سند موتور در متن مشخص نشده است.")

    if insurance is not None:
        if insurance >= 6:
            lines.append("✅ بیمه باقیمانده مناسب است و هزینه اولیه خریدار را کاهش می‌دهد.")
        else:
            lines.append("⚠ بیمه کم، هزینه اضافی برای خریدار ایجاد می‌کند.")
    else:
        lines.append("ℹ وضعیت بیمه در متن ذکر نشده است.")

    lines.append("\n✅ جمع‌بندی کارشناسی:")
    if price is not None and accident != "تصادفی":
        lines.append(
            "در صورت تایید سلامت فنی موتور (انجین، جلو‌بندی، سیستم ترمز) و عدم نشتی روغن، این قیمت می‌تواند قابل قبول باشد."
        )
    else:
        lines.append(
            "توصیه می‌شود پیش از خرید، بازدید حضوری و تست فنی کامل انجام شود."
        )

    return "\n".join(lines)


async def assistant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    text = update.message.text.strip()

    if text == "دستیار هوشمند":
        user_state[uid] = "assistant"
        await update.message.reply_text(
            "متن توضیحات موتور را بفرست (رنگ، بیمه، سند، قیمت، تصادف و ...):",
            reply_markup=admin_menu() if uid == OWNER_ID else user_menu(),
        )
        return

    if uid in user_state and user_state[uid] == "assistant":
        info = extract_info(text)
        result = expert_analysis(info)

        await update.message.reply_text(
            result,
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
    else:
        await msg.reply_text("❌ عکس فقط در مرحله ثبت آگهی موتور مجاز است.")

# -------------------- هندل متن -------------------- #

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    msg = update.message
    text = msg.text.strip()

    if text == "جستجو پیشرفته" or (
        uid in user_state and user_state[uid].startswith("search_filters")
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
            if not is_valid_text(text):
                await msg.reply_text("❌ نام استان نامعتبر است.")
                return
            temp_data[uid]["province"] = text
            user_state[uid] = "city"
            await msg.reply_text("شهر:")
            return

        if st == "city":
            if not is_valid_text(text):
                await msg.reply_text("❌ نام شهر نامعتبر است.")
                return
            temp_data[uid]["city"] = text
            user_state[uid] = "motor_type"
            await msg.reply_text(
                "نوع موتور (اسکوتر، اسپرت، تریل، کراس، کلاسیک، بایک، سفری، شهری یا مدل خاص):"
            )
            return

        if st == "motor_type":
            temp_data[uid]["motor_type"] = normalize_motor_type(text)
            user_state[uid] = "model"
            await msg.reply_text("مدل موتور:")
            return

        if st == "model":
            if not is_valid_text(text, min_len=4):
                await msg.reply_text(
                    "❌ مدل نامعتبر است.\nمثال: «هوندا کلیک 150» یا «آپاچی 180»."
                )
                return
            temp_data[uid]["model"] = text
            user_state[uid] = "year"
            await msg.reply_text("سال ساخت (مثلاً 1398):")
            return

        if st == "year":
            if not is_valid_year(text):
                await msg.reply_text("❌ سال ساخت نامعتبر است.")
                return
            temp_data[uid]["year"] = int(text)
            user_state[uid] = "km"
            await msg.reply_text("کارکرد (به کیلومتر، فقط عدد):")
            return

        if st == "km":
            if not is_valid_km(text):
                await msg.reply_text("❌ کارکرد نامعتبر است.")
                return
            temp_data[uid]["km"] = int(text)
            user_state[uid] = "color"
            await msg.reply_text("رنگ موتور:")
            return

        if st == "color":
            if not is_valid_text(text, min_len=2):
                await msg.reply_text("❌ رنگ نامعتبر است.")
                return
            temp_data[uid]["color"] = text
            user_state[uid] = "accident"
            kb = ReplyKeyboardMarkup(
                [["بی‌تصادف", "تصادفی"]],
                resize_keyboard=True
            )
            await msg.reply_text("وضعیت تصادف را انتخاب کن:", reply_markup=kb)
            return

        if st == "accident":
            t = text.replace(" ", "")
            if any(x in t for x in ["بیتصادف", "بدونتصادف", "بی‌تصادف"]):
                temp_data[uid]["accident"] = "بی‌تصادف"
            elif "تصادف" in t:
                temp_data[uid]["accident"] = "تصادفی"
            else:
                await msg.reply_text(
                    "❌ وضعیت تصادف نامشخص است.\nبنویس: «بی‌تصادف» یا «بدون تصادف» یا «تصادفی»."
                )
                return
            user_state[uid] = "document"
            await msg.reply_text("وضعیت سند (تک‌برگ / دارای سند):")
            return

        if st == "document":
            if text not in ["تک‌برگ", "دارای سند"]:
                await msg.reply_text("❌ فقط تک‌برگ یا دارای سند.")
                return
            temp_data[uid]["document"] = text
            user_state[uid] = "insurance"
            await msg.reply_text("بیمه (ماه، فقط عدد):")
            return

        if st == "insurance":
            if not text.isdigit():
                await msg.reply_text("❌ بیمه باید عدد باشد.")
                return
            temp_data[uid]["insurance"] = int(text)
            user_state[uid] = "price"
            await msg.reply_text("قیمت (به ریال، فقط عدد):")
            return

        if st == "price":
            if not is_valid_price(text):
                await msg.reply_text("❌ قیمت باید عدد مثبت باشد.")
                return
            temp_data[uid]["price"] = text
            user_state[uid] = "phone"
            await msg.reply_text("شماره تماس (11 رقم):")
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
                    "year": temp_data[uid]["year"],
                    "km": temp_data[uid]["km"],
                    "color": temp_data[uid]["color"],
                    "accident": temp_data[uid]["accident"],
                    "document": temp_data[uid]["document"],
                    "insurance": temp_data[uid]["insurance"],
                    "price": temp_data[uid]["price"],
                    "phone": temp_data[uid]["phone"],
                    "photos": temp_data[uid]["photos"],
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
            ad_id = int(st.split("_")[1])
            if msg.photo:
                await msg.reply_text(
                    "✅ رسید دریافت شد. آگهی برای مدیر ارسال شد.",
                    reply_markup=user_menu()
                    if uid != OWNER_ID
                    else admin_menu(),
                )
                await send_ad_to_admin(context, ad_id, pending_ads[ad_id])
                del user_state[uid]
                del temp_data[uid]
                return
            else:
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
            await query.edit_message_caption(
                caption=f"آگهی #{ad_id} ✔ تأیید شد.",
            )
        else:
            await query.edit_message_text("آگهی یافت نشد یا قبلاً رسیدگی شده است.")

    elif data.startswith("delete_"):
        ad_id = int(data.split("_")[1])
        if ad_id in pending_ads:
            del pending_ads[ad_id]
            await query.edit_message_caption(
                caption=f"آگهی #{ad_id} ❌ حذف شد.",
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