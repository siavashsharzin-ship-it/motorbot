# -*- coding: utf-8 -*-
import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ================== تنظیمات ==================
TOKEN = os.getenv("BOT_TOKEN")  # توکن از محیط (برای Railway)

if not TOKEN:
    print("❌ خطا: متغیر محیطی BOT_TOKEN تنظیم نشده!")
    print("📌 برای تست روی گوشی: TOKEN رو مستقیم وارد کن")
    # برای تست روی گوشی، این خط رو فعال کن:
    # TOKEN = "توکن_واقعی_اینجا"
    exit()

# ================== دیتابیس ساده (موقت) ==================
properties_db = []
property_counter = 1

def save_property(address, area, price):
    global property_counter
    prop = {
        'id': property_counter,
        'address': address,
        'area': area,
        'price': price,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'is_sold': False
    }
    properties_db.append(prop)
    property_counter += 1
    return prop

def get_all_properties():
    return [p for p in properties_db if not p['is_sold']]

def search_properties(max_price):
    return [p for p in properties_db if not p['is_sold'] and p['price'] <= max_price]

# ================== دستورات ربات ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ ثبت ملک جدید", callback_data='add')],
        [InlineKeyboardButton("📋 لیست املاک", callback_data='list')],
        [InlineKeyboardButton("🔍 جستجو", callback_data='search')],
        [InlineKeyboardButton("📊 آمار", callback_data='stats')],
    ]
    await update.message.reply_text(
        "🏠 **به ربات خرید و فروش بنگاه خوش آمدی!**\n\n"
        "از دکمه‌های زیر استفاده کن:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'add':
        await query.edit_message_text(
            "📝 **ثبت ملک جدید**\n\n"
            "فرمت: `/add آدرس متراژ قیمت`\n"
            "مثال: `/add خیابان آزادی 80 500000000`"
        )
    elif query.data == 'list':
        props = get_all_properties()
        if not props:
            await query.edit_message_text("📭 هنوز ملکی ثبت نشده!")
            return
        msg = "📋 **لیست املاک:**\n\n"
        for p in props[:5]:
            msg += f"🏠 {p['address']}\n"
            msg += f"📐 {p['area']} متر | 💰 {p['price']:,} تومان\n"
            msg += f"🆔 کد: {p['id']}\n➖➖➖➖➖\n"
        if len(props) > 5:
            msg += f"\nو {len(props)-5} ملک دیگر..."
        await query.edit_message_text(msg, parse_mode='Markdown')
    elif query.data == 'search':
        await query.edit_message_text(
            "🔍 **جستجو**\n\n"
            "از دستور زیر استفاده کن:\n"
            "`/search حداکثر_قیمت`\n"
            "مثال: `/search 300000000`"
        )
    elif query.data == 'stats':
        total = len(properties_db)
        sold = sum(1 for p in properties_db if p['is_sold'])
        await query.edit_message_text(
            f"📊 **آمار بنگاه**\n\n"
            f"🏠 کل املاک: {total}\n"
            f"✅ موجود: {total - sold}\n"
            f"❌ فروش رفته: {sold}"
        )

async def add_property(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "❌ فرمت: `/add آدرس متراژ قیمت`\n"
            "مثال: `/add خیابان آزادی 80 500000000`"
        )
        return
    
    address = " ".join(args[:-2])
    try:
        area = int(args[-2])
        price = int(args[-1])
    except ValueError:
        await update.message.reply_text("❌ متراژ و قیمت باید عدد باشن!")
        return
    
    prop = save_property(address, area, price)
    await update.message.reply_text(
        f"✅ **ملک ثبت شد!**\n\n"
        f"📍 آدرس: {address}\n"
        f"📐 متراژ: {area} متر\n"
        f"💰 قیمت: {price:,} تومان\n"
        f"🆔 کد: {prop['id']}"
    )

async def search_property(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً قیمت حداکثر رو وارد کن: `/search 500000000`")
        return
    
    try:
        max_price = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ قیمت باید عدد باشه!")
        return
    
    results = search_properties(max_price)
    if not results:
        await update.message.reply_text(f"🔍 هیچ ملکی تا {max_price:,} تومان پیدا نشد!")
        return
    
    msg = f"🔍 **نتایج جستجو (تا {max_price:,} تومان):**\n\n"
    for p in results[:5]:
        msg += f"🏠 {p['address']}\n"
        msg += f"💰 {p['price']:,} تومان | 📐 {p['area']} متر\n"
        msg += f"🆔 کد: {p['id']}\n➖➖➖\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

# ================== اجرا ==================
def main():
    print("🤖 در حال روشن کردن ربات...")
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_property))
    app.add_handler(CommandHandler("search", search_property))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ ربات روشن شد! منتظر پیام‌ها هستم...")
    app.run_polling()

if __name__ == "__main__":
    main()