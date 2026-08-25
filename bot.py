import logging
import os
import re
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
pending_ads: Dict[int, Dict[str, Any]] = {}  # آگهی‌های در انتظار تایید
user_state: Dict[int, str] = {}              # وضعیت مرحله هر کاربر
temp_data: Dict[int, Dict[str, Any]] = {}    # دادهٔ موقت ثبت آگهی
next_ad_id: int = 1                          # شماره آگهی بعدی


# -------------------- منوها -------------------- #

def user_menu() -> ReplyKeyboardMarkup:
    kb = [
        ["ثبت آگهی موتور", "لیست آگهی‌ها"],
        ["جستجو", "تماس با پشتیبانی"],
        ["دستیار هوشمند"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    kb = [
        ["ثبت آگهی موتور", "لیست آگهی‌ها"],
        ["آگهی‌های در انتظار تأیید", "جستجو"],
        ["دستیار هوشمند"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


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


# -------------------- ثبت آگهی -------------------- #

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    user_state[uid] = "province"
    temp_data[uid] = {"photos": []}
    await update.message.reply_text("استان موتور:")


# -------------------- ارسال آگهی برای مدیر -------------------- #

async def send_ad_to_admin(
    context: ContextTypes.DEFAULT_TYPE,
    ad_id: int,
    ad_data: Dict[str, Any],
) -> None:
    caption = (
        f"🔔 آگهی جدید:\n"
        f"#{ad_id}\n"
        f"{ad_data['province']} - {ad_data['city']}\n"
        f"{ad_data['model']} - {ad_data['price']}\n"
        f"تماس: {ad_data['phone']}\n"
        f"تعداد عکس: {len(ad_data['photos'])}"
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

    if ad_data["photos"]:
        await context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=ad_data["photos"][0],
            caption=caption,
            reply_markup=buttons,
        )
    else:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=caption,
            reply_markup=buttons,
        )


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
            f"{ad['model']} - {ad['price']}\n"
            f"تماس: {ad['phone']}\n\n"
        )

    await update.message.reply_text(
        text,
        reply_markup=admin_menu() if uid == OWNER_ID else user_menu(),
    )


# -------------------- لیست آگهی‌های در انتظار تأیید (فقط مدیر) -------------------- #

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

    for ad_id, ad in pending_ads.items():
        caption = (
            f"🔔 آگهی در انتظار تأیید:\n"
            f"#{ad_id}\n"
            f"{ad['province']} - {ad['city']}\n"
            f"{ad['model']} - {ad['price']}\n"
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
            await update.message.reply_media_group(
                media=[
                    InputMediaPhoto(
                        media=ad["photos"][0],
                        caption=caption,
                    )
                ]
            )
            # دکمه‌ها را جداگانه روی پیام آخر می‌گذاریم
            await update.message.reply_text(
                f"آگهی #{ad_id}",
                reply_markup=buttons,
            )
        else:
            await update.message.reply_text(
                caption,
                reply_markup=buttons,
            )


# -------------------- جستجو -------------------- #

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    query = update.message.text.strip()

    # اگر از منو آمده، از کاربر بخواه متن جستجو را بفرستد
    if query == "جستجو":
        await update.message.reply_text(
            "عبارت جستجو را بفرست (مثلاً: تهران، هوندا، 1403):",
            reply_markup=admin_menu() if uid == OWNER_ID else user_menu(),
        )
        user_state[uid] = "search"
        return

    if uid in user_state and user_state[uid] == "search":
        result = ""
        for ad_id, ad in ads.items():
            text_block = (
                f"{ad['province']} {ad['city']} "
                f"{ad['model']} {ad['price']} {ad['phone']}"
            )
            if query in text_block:
                result += (
                    f"#{ad_id}\n"
                    f"{ad['province']} - {ad['city']}\n"
                    f"{ad['model']} - {ad['price']}\n"
                    f"تماس: {ad['phone']}\n\n"
                )

        if not result:
            await update.message.reply_text(
                "هیچ آگهی مطابق جستجو پیدا نشد.",
                reply_markup=admin_menu() if uid == OWNER_ID else user_menu(),
            )
        else:
            await update.message.reply_text(
                result,
                reply_markup=admin_menu() if uid == OWNER_ID else user_menu(),
            )

        del user_state[uid]
        return


# -------------------- دستیار هوشمند (تحلیل متن) -------------------- #

def extract_info(text: str) -> Dict[str, Any]:
    info: Dict[str, Any] = {}

    m_color = re.search(r"رنگ\s*([آ-یA-Za-z0-9]+)", text)
    if m_color:
        info["color"] = m_color.group(1).strip()

    if "بدون تصادف" in text or "بی‌تصادف" in text:
        info["accident"] = "بدون تصادف"
    elif "تصادف" in text:
        info["accident"] = "تصادفی"
    else:
        info["accident"] = "نامشخص"

    if "سند تک‌برگ" in text or "سند تک برگ" in text:
        info["document"] = "تک برگ"
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

    lines = []
    lines.append("🔧 گزارش کارشناسی هوشمند موتور:\n")

    if accident == "بدون تصادف":
        lines.append("✅ موتور بدون سابقه تصادف اعلام شده است.")
    elif accident == "تصادفی":
        lines.append("⚠ موتور دارای سابقه تصادف است، نیاز به بررسی دقیق شاسی و فریم دارد.")
    else:
        lines.append("ℹ وضعیت تصادف موتور در متن مشخص نشده است.")

    if document == "تک برگ":
        lines.append("✅ سند تک برگ، وضعیت حقوقی موتور را شفاف‌تر می‌کند.")
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
    text = update.message.text

    if text == "دستیار هوشمند":
        await update.message.reply_text(
            "متن توضیحات موتور را بفرست (رنگ، بیمه، سند، قیمت، تصادف و ...):",
            reply_markup=admin_menu() if uid == OWNER_ID else user_menu(),
        )
        user_state[uid] = "assistant"
        return

    if uid in user_state and user_state[uid] == "assistant":
        info = extract_info(text)
        result = expert_analysis(info)

        if uid == OWNER_ID:
            await update.message.reply_text(result, reply_markup=admin_menu())
        else:
            await update.message.reply_text(result, reply_markup=user_menu())

        del user_state[uid]
        return


# -------------------- هندل پیام‌ها -------------------- #

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


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    msg = update.message
    text = msg.text.strip()

    # اگر در حالت جستجو یا دستیار هستیم
    if uid in user_state and user_state[uid] == "search":
        await search(update, context)
        return
    if uid in user_state and user_state[uid] == "assistant":
        await assistant(update, context)
        return

    # مراحل ثبت آگهی
    if uid in user_state:
        state = user_state[uid]

        if state == "province":
            temp_data[uid]["province"] = text
            user_state[uid] = "city"
            await msg.reply_text("شهر:")
            return

        if state == "city":
            temp_data[uid]["city"] = text
            user_state[uid] = "model"
            await msg.reply_text("مدل موتور:")
            return

        if state == "model":
            temp_data[uid]["model"] = text
            user_state[uid] = "price"
            await msg.reply_text("قیمت:")
            return

        if state == "price":
            temp_data[uid]["price"] = text
            user_state[uid] = "phone"
            await msg.reply_text("شماره تماس:")
            return

        if state == "phone":
            temp_data[uid]["phone"] = text
            user_state[uid] = "photos"
            await msg.reply_text(
                "حالا عکس‌های موتور را بفرست. اگر تمام شد، بنویس: تمام"
            )
            return

        if state == "photos":
            if text == "تمام":
                global next_ad_id
                ad_id = next_ad_id
                next_ad_id += 1

                pending_ads[ad_id] = {
                    "province": temp_data[uid]["province"],
                    "city": temp_data[uid]["city"],
                    "model": temp_data[uid]["model"],
                    "price": temp_data[uid]["price"],
                    "phone": temp_data[uid]["phone"],
                    "photos": temp_data[uid]["photos"],
                }

                await send_ad_to_admin(context, ad_id, pending_ads[ad_id])

                await msg.reply_text(
                    f"آگهی #{ad_id} ثبت شد و منتظر تأیید مدیر است.",
                    reply_markup=user_menu()
                    if uid != OWNER_ID
                    else admin_menu(),
                )
                del user_state[uid]
                del temp_data[uid]
                return
            else:
                await msg.reply_text("اگر عکس دیگری نداری، بنویس: تمام")
                return

    # دستورات منو
    if text == "ثبت آگهی موتور":
        await new_ad(update, context)
    elif text == "لیست آگهی‌ها":
        await list_ads(update, context)
    elif text == "آگهی‌های در انتظار تأیید":
        await list_pending(update, context)
    elif text == "تماس با پشتیبانی":
        await support(update, context)
    elif text == "جستجو":
        await search(update, context)
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