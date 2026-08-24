`python
import logging
import re
from telegram import (
    Update, ReplyKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

---------------- تنظیمات ---------------- #
TOKEN = "8868906040:AAHFEcVX4u6Nh-K2AJG_9KDIix3PENqA4sc"
OWNER_ID = 8474856910
SUPPORT_PHONE = "+989910065071"
CARD_NUMBER = "6037998216767839"
CHANNELUSERNAME = "persianmotor"   # یوزرنیم کانال

logging.basicConfig(level=logging.INFO)

---------------- دیتابیس ---------------- #
ads = {}            # آگهی‌های تأیید شده
pending_ads = {}    # آگهی‌های در انتظار تأیید
user_state = {}
temp_data = {}
nextadid = 1

---------------- منوها ---------------- #
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

---------------- پیشنهاد عضویت کانال ---------------- #
async def suggestjoin(update: Update, context: ContextTypes.DEFAULTTYPE):
    try:
        member = await context.bot.getchatmember(f"@{CHANNELUSERNAME}", update.effectiveuser.id)
        if member.status not in ["member", "administrator", "creator"]:
            await update.message.reply_text(
                f"برای دیدن همه آگهی‌ها و عکس‌ها، بهتره عضو کانال بشی:\nhttps://t.me/{CHANNEL_USERNAME}"
            )
    except:
        pass

---------------- قوانین ---------------- #
def rules():
    return (
        "📜 قوانین ربات موتور:\n\n"
        "💰 هزینه ثبت هر آگهی: ۷,۰۰۰,۰۰۰ ریال\n"
        "📌 آگهی تا زمان فروش فعال می‌ماند\n"
        "❌ عکس شخصی، سلفی، شماره موبایل روی عکس ممنوع\n"
        "❌ آگهی غیرمرتبط حذف می‌شود\n"
        "✅ اعضا می‌توانند دوستانشان را به کانال و ربات اضافه کنند.\n"
    )

---------------- شروع ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await suggest_join(update, context)

    if uid == OWNER_ID:
        await update.message.replytext("سلام مدیر عزیز 👑", replymarkup=admin_menu())
    else:
        await update.message.replytext(rules(), replymarkup=user_menu())

---------------- تماس با پشتیبانی ---------------- #
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"📞 پشتیبانی:\n"
        f"شماره تماس: {SUPPORT_PHONE}\n"
        f"شماره کارت: {CARD_NUMBER}\n"
        f"برای هماهنگی، تماس یا واتساپ."
    )
    if update.effectiveuser.id == OWNERID:
        await update.message.replytext(text, replymarkup=admin_menu())
    else:
        await update.message.replytext(text, replymarkup=user_menu())

---------------- دستور /id ---------------- #
async def getid(update: Update, context: ContextTypes.DEFAULTTYPE):
    userid = update.effectiveuser.id
    await update.message.replytext(f"ایدی شما: {userid}")

---------------- ثبت آگهی ---------------- #
async def newad(update: Update, context: ContextTypes.DEFAULTTYPE):
    uid = update.effective_user.id
    user_state[uid] = "province"
    temp_data[uid] = {"photos": []}
    await update.message.reply_text("استان:")

---------------- دستیار هوشمند کارشناسی ---------------- #
async def assistant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = "assistant"
    await update.message.reply_text(
        "🤖 دستیار کارشناسی فعال شد.\n"
        "مشخصات موتور را یکجا بنویس:\n"
        "مدل، سال، کارکرد، رنگ، تصادفی/بی‌تصادف، سند، بیمه، قیمت پیشنهادی.\n"
        "مثال:\n"
        "آپاچی 180 مدل 1400، کارکرد 35000، رنگ مشکی، بدون تصادف، سند تک‌برگ، بیمه 6 ماه، قیمت 175000000"
    )

def extract_info(text: str):
    info = {
        "model": None,
        "year": None,
        "km": None,
        "color": None,
        "accident": None,
        "document": None,
        "insurance": None,
        "price": None
    }

    # مدل: اولین کلمه‌ها تا قبل از "مدل"
    m_model = re.search(r"(.+?)مدل", text)
    if m_model:
        info["model"] = m_model.group(1).strip()

    # سال
    m_year = re.search(r"مدل\s*(\d{4})", text)
    if m_year:
        info["year"] = int(m_year.group(1))

    # کارکرد
    m_km = re.search(r"کارکرد\s*([\d]+)", text)
    if m_km:
        info["km"] = int(m_km.group(1))

    # رنگ
    m_color = re.search(r"رنگ\s*([آ-ی\s]+?)(،|$)", text)
    if m_color:
        info["color"] = m_color.group(1).strip()

    # تصادف
    if "بدون تصادف" in text or "بی‌تصادف" in text:
        info["accident"] = "بدون تصادف"
    elif "تصادف" in text:
        info["accident"] = "تصادفی"

    # سند
    if "سند تک‌برگ" in text or "سند تک برگ" in text:
        info["document"] = "تک‌برگ"
    elif "سند" in text:
        info["document"] = "دارای سند"

    # بیمه
    m_ins = re.search(r"بیمه\s([\d]+)\sماه", text)
    if m_ins:
        info["insurance"] = int(m_ins.group(1))

    # قیمت
    m_price = re.search(r"قیمت\s*([\d]+)", text)
    if m_price:
        info["price"] = int(m_price.group(1))

    return info

def expert_analysis(info: dict) -> str:
    model = (info["model"] or "").lower()
    year = info["year"]
    km = info["km"]
    accident = info["accident"]
    document = info["document"]
    insurance = info["insurance"]
    price = info["price"]

    lines = []

    lines.append("📋 گزارش کارشناسی موتور:\n")

    if info["model"]:
        lines.append(f"• مدل: {info['model']}")
    if year:
        lines.append(f"• سال ساخت: {year}")
    if km is not None:
        lines.append(f"• کارکرد: {km} کیلومتر")
    if info["color"]:
        lines.append(f"• رنگ: {info['color']}")
    if accident:
        lines.append(f"• وضعیت تصادف: {accident}")
    if document:
        lines.append(f"• وضعیت سند: {document}")
    if insurance is not None:
        lines.append(f"• بیمه: {insurance} ماه")
    if price is not None:
        lines.append(f"• قیمت پیشنهادی: {price} تومان")

    lines.append("\n🔍 تحلیل کارشناسی:")

    # تحلیل قیمت بر اساس مدل و سال و کارکرد
    comment_price = "اطلاعات قیمت کافی نیست."
    if price is not None:
        if "هوندا" in model or "125" in model:
            basemin, basemax = 45000000, 150000000
        elif "آپاچی" in model or "apache" in model or "180" in model:
            basemin, basemax = 90000000, 230000000
        elif "پالس" in model or "bajaj" in model:
            basemin, basemax = 70000000, 200000000
        else:
            basemin, basemax = None, None

        if basemin and basemax:
            # تعدیل بر اساس سال و کارکرد
            if year and year >= 1400:
                base_min *= 1.1
                base_max *= 1.1
            if km and km > 50000:
                base_max *= 0.9

            if price < base_min:
                comment_price = "قیمت پیشنهادی پایین‌تر از محدودهٔ معمول بازار است."
            elif price > base_max:
                comment_price = "قیمت پیشنهادی بالاتر از محدودهٔ معمول بازار است."
            else:
                comment_price = "قیمت پیشنهادی در محدودهٔ منطقی بازار قرار دارد."
        else:
            comment_price = "مدل موتور ناشناس است؛ قیمت به‌صورت دقیق قابل ارزیابی نیست."

    lines.append(f"• {comment_price}")

    # تحلیل تصادف
    if accident == "بدون تصادف":
        lines.append("• عدم گزارش تصادف، امتیاز مثبت برای ارزش خرید است.")
    elif accident == "تصادفی":
        lines.append("• وجود سابقهٔ تصادف، نیازمند بررسی دقیق شاسی و فریم است.")

    # تحلیل سند
    if document == "تک‌برگ":
        lines.append("• سند تک‌برگ، وضعیت حقوقی موتور را شفاف‌تر می‌کند.")
    elif document == "دارای سند":
        lines.append("• وجود سند، نکتهٔ مثبت است؛ توصیه می‌شود تطبیق پلاک و شماره موتور انجام شود.")

    # تحلیل بیمه
    if insurance is not None:
        if insurance >= 6:
            lines.append("• بیمهٔ باقیمانده مناسب است و هزینهٔ اولیهٔ خریدار را کاهش می‌دهد.")
        else:
            lines.append("• بیمهٔ کم، هزینهٔ اضافی برای خریدار ایجاد می‌کند.")

    lines.append("\n✅ جمع‌بندی کارشناسی:")
    if price is not None and accident != "تصادفی":
        lines.append("در صورت تأیید سلامت فنی موتور (انجین، جلوبندی، سیستم ترمز) و عدم نشتی روغن، این قیمت می‌تواند قابل قبول باشد.")
    else:
        lines.append("توصیه می‌شود پیش از خرید، بازدید حضوری و تست فنی کامل انجام شود.")

    return "\n".join(lines)

async def handleassistant(update: Update, context: ContextTypes.DEFAULTTYPE):
    uid = update.effective_user.id
    text = update.message.text

    info = extract_info(text)
    result = expert_analysis(info)

    if uid == OWNER_ID:
        await update.message.replytext(result, replymarkup=admin_menu())
    else:
        await update.message.replytext(result, replymarkup=user_menu())

    del user_state[uid]

---------------- هندل پیام‌ها ---------------- #
async def handlemessage(update: Update, context: ContextTypes.DEFAULTTYPE):
    uid = update.effective_user.id
    msg = update.message

    if msg.photo:
        if uid in userstate and userstate[uid] == "photos":
            photoid = msg.photo[-1].fileid
            tempdata[uid]["photos"].append(photoid)
            await msg.reply_text("✅ عکس اضافه شد. اگر عکس دیگری داری، بفرست؛ اگر تمام شد، بنویس: تمام")
            return
        else:
            await msg.reply_text("❌ عکس فقط در مرحلهٔ ثبت آگهی موتور مجاز است.")
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
        await msg.reply_text("حالا عکس‌های موتور را بفرست.\nهرچقدر عکس داری بفرست.\nاگر تمام شد، بنویس: تمام")
        return

    if step == "photos":
        if text.strip() == "تمام":
            global nextadid
            pendingads[nextadid] = tempdata[uid]

            await msg.reply_text(
                f"آگهی #{nextadid} ثبت شد و منتظر تأیید مدیر است.",
                replymarkup=usermenu()
            )

            ad = temp_data[uid]
            admin_msg = (
                f"🔔 آگهی جدید:\n\n"
                f"#{nextadid}\n"
                f"{ad['province']} - {ad['city']}\n"
                f"{ad['model']} - {ad['price']}\n"
                f"تماس: {ad['phone']}\n"
                f"تعداد عکس: {len(ad['photos'])}"
            )
            await context.bot.sendmessage(OWNERID, admin_msg)

            nextadid += 1
            del user_state[uid]
            del temp_data[uid]
            return
        else:
            await msg.reply_text("اگر عکس دیگری نداری، بنویس: تمام")
            return

    if step == "approve":
        if uid != OWNER_ID:
            await msg.replytext("فقط مدیر.", replymarkup=user_menu())
            del user_state[uid]
            return

        try:
            ad_id = int(text)
            if adid in pendingads:
                ads[adid] = pendingads[ad_id]
                ad = ads[ad_id]

                caption = (
                    f"آگهی #{ad_id}\n"
                    f"{ad['province']} - {ad['city']}\n"
                    f"{ad['model']} - {ad['price']}\n"
                    f"تماس: {ad['phone']}"
                )

                if ad["photos"]:
                    media = [InputMediaPhoto(photo_id, caption=caption if i == 0 else "") 
                             for i, photo_id in enumerate(ad["photos"])]
                    await context.bot.sendmediagroup(chatid=f"@{CHANNELUSERNAME}", media=media)
                else:
                    await context.bot.sendmessage(chatid=f"@{CHANNEL_USERNAME}", text=caption)

                await msg.replytext(f"آگهی #{adid} تأیید و در کانال منتشر شد ✅", replymarkup=adminmenu())
                del pendingads[adid]
            else:
                await msg.replytext("آگهی در انتظار تأیید نیست.", replymarkup=admin_menu())
        except:
            await msg.replytext("شماره آگهی نامعتبر است.", replymarkup=admin_menu())

        del user_state[uid]
        return

    if step == "delete":
        if uid != OWNER_ID:
            await msg.replytext("فقط مدیر.", replymarkup=user_menu())
            del user_state[uid]
            return

        try:
            ad_id = int(text)
            if ad_id in ads:
                del ads[ad_id]
                await msg.replytext(f"آگهی #{adid} حذف شد.", replymarkup=adminmenu())
            else:
                await msg.replytext("آگهی پیدا نشد.", replymarkup=admin_menu())
        except:
            await msg.replytext("شماره آگهی نامعتبر است.", replymarkup=admin_menu())

        del user_state[uid]
        return

    if step == "search":
        await handle_search(update, context)
        return

---------------- لیست آگهی‌های تأیید شده ---------------- #
async def listads(update: Update, context: ContextTypes.DEFAULTTYPE):
    if not ads:
        await update.message.reply_text(
            "هیچ آگهی تأیید شده‌ای نیست.",
            replymarkup=adminmenu() if update.effectiveuser.id == OWNERID else user_menu()
        )
        return

    text = ""
    for ad_id, ad in ads.items():
        text += f"#{ad_id}\n{ad['province']} - {ad['city']}\n{ad['model']} - {ad['price']}\nتماس: {ad['phone']}\n\n"

    if update.effectiveuser.id == OWNERID:
        await update.message.replytext(text, replymarkup=admin_menu())
    else:
        await update.message.replytext(text, replymarkup=user_menu())

---------------- آگهی‌های در انتظار تأیید ---------------- #
async def pendinglist(update: Update, context: ContextTypes.DEFAULTTYPE):
    if update.effectiveuser.id != OWNERID:
        await update.message.replytext("فقط مدیر.", replymarkup=user_menu())
        return

    if not pending_ads:
        await update.message.replytext("هیچ آگهی در انتظار نیست.", replymarkup=admin_menu())
        return

    text = ""
    for adid, ad in pendingads.items():
        text += f"#{ad_id}\n{ad['province']} - {ad['city']}\n{ad['model']} - {ad['price']}\nتماس: {ad['phone']}\nتعداد عکس: {len(ad['photos'])}\n\n"

    await update.message.replytext(text, replymarkup=admin_menu())

---------------- تأیید آگهی ---------------- #
async def startapprove(update: Update, context: ContextTypes.DEFAULTTYPE):
    if update.effectiveuser.id != OWNERID:
        await update.message.replytext("فقط مدیر.", replymarkup=user_menu())
        return

    uid = update.effective_user.id
    user_state[uid] = "approve"
    await update.message.replytext("شماره آگهی برای تأیید:", replymarkup=admin_menu())

---------------- حذف آگهی ---------------- #
async def startdelete(update: Update, context: ContextTypes.DEFAULTTYPE):
    if update.effectiveuser.id != OWNERID:
        await update.message.replytext("فقط مدیر.", replymarkup=user_menu())
        return

    uid = update.effective_user.id
    user_state[uid] = "delete"
    await update.message.replytext("شماره آگهی برای حذف:", replymarkup=admin_menu())

---------------- جستجو ---------------- #
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = "search"
    await update.message.reply_text("عبارت مورد نظر (استان، شهر، مدل یا قیمت):")

async def handlesearch(update: Update, context: ContextTypes.DEFAULTTYPE):
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
            replymarkup=adminmenu() if uid == OWNERID else usermenu()
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
            replymarkup=adminmenu() if uid == OWNERID else usermenu()
        )

    del user_state[uid]

---------------- اجرای ربات ---------------- #
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.addhandler(CommandHandler("id", getid))

    app.addhandler(MessageHandler(filters.Regex("^ثبت آگهی موتور$"), newad))
    app.addhandler(MessageHandler(filters.Regex("^لیست آگهی‌ها$"), listads))
    app.addhandler(MessageHandler(filters.Regex("^آگهی‌های در انتظار تأیید$"), pendinglist))
    app.add_handler(MessageHandler(filters.Regex("^جستجو$"), search))
    app.add_handler(MessageHandler(filters.Regex("^تماس با پشتیبانی$"), support))
    app.add_handler(MessageHandler(filters.Regex("^دستیار هوشمند$"), assistant))
    app.addhandler(MessageHandler(filters.Regex("^تأیید آگهی$"), startapprove))
    app.addhandler(MessageHandler(filters.Regex("^حذف آگهی$"), startdelete))

    app.addhandler(MessageHandler(filters.TEXT | filters.PHOTO, handlemessage))

    app.run_polling()

if name == "main":
    main()
`
