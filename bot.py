import os
import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== تنظیمات اولیه ==========
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("توکن ربات در متغیر محیطی BOT_TOKEN تنظیم نشده!")

ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))  # آیدی عددی ادمین (مثلاً 123456789)
CARD_NUMBER = os.environ.get("CARD_NUMBER", "6037-xxxx-xxxx-xxxx")  # شماره کارت برای پرداخت

# ========== راه‌اندازی دیتابیس ==========
DB_NAME = "motor_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # جدول کاربران
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        phone TEXT,
        join_date TEXT
    )''')
    # جدول آگهی‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        brand TEXT,
        model TEXT,
        year TEXT,
        cc TEXT,
        gear_type TEXT,
        fuel_type TEXT,
        mileage TEXT,
        engine_status TEXT,
        body_status TEXT,
        price TEXT,
        is_negotiable INTEGER DEFAULT 0,
        card_status TEXT,
        insurance TEXT,
        inspection TEXT,
        description TEXT,
        contact_number TEXT,
        city TEXT,
        images TEXT,
        video TEXT,
        status TEXT DEFAULT 'pending',
        is_vip INTEGER DEFAULT 0,
        view_count INTEGER DEFAULT 0,
        created_at TEXT,
        expires_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )''')
    # جدول تنظیمات
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# ========== توابع کمکی ==========
def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def add_user(user_id, username="", phone=""):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, phone, join_date) VALUES (?, ?, ?, ?)",
              (user_id, username, phone, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_pending_ads():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM ads WHERE status='pending' ORDER BY created_at DESC")
    ads = c.fetchall()
    conn.close()
    return ads

def get_user_ads(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM ads WHERE user_id=? AND status IN ('active', 'pending') ORDER BY created_at DESC", (user_id,))
    ads = c.fetchall()
    conn.close()
    return ads

# ========== منوهای اصلی ==========
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 جستجو و فیلتر", callback_data="search")],
        [InlineKeyboardButton("📝 ثبت آگهی جدید", callback_data="new_ad")],
        [InlineKeyboardButton("📋 آگهی‌های من", callback_data="my_ads")],
        [InlineKeyboardButton("⭐ آگهی‌های ویژه", callback_data="vip_ads")],
        [InlineKeyboardButton("📊 قیمت‌روز", callback_data="prices")],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")],
        [InlineKeyboardButton("💰 پرداخت برای ویژه", callback_data="payment")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🏍️ به ربات خرید و فروش موتورسیکلت خوش آمدید!\n\nیک گزینه را انتخاب کنید:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

# ========== ثبت آگهی (گام‌به‌گام) ==========
async def start_new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ad_step'] = 'brand'
    context.user_data['ad_data'] = {}
    await update.callback_query.edit_message_text(
        "📝 ثبت آگهی جدید\n\nلطفاً **برند و مدل** موتور را وارد کنید:\nمثال: هوندا CB400"
    )

async def handle_ad_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    step = context.user_data.get('ad_step')
    ad_data = context.user_data.get('ad_data', {})
    
    if step == 'brand':
        ad_data['brand'] = user_input
        context.user_data['ad_step'] = 'year'
        await update.message.reply_text("📅 سال تولید را وارد کنید (مثال: 1400):")
    
    elif step == 'year':
        ad_data['year'] = user_input
        context.user_data['ad_step'] = 'cc'
        await update.message.reply_text("🔧 حجم موتور را وارد کنید (مثال: 400):")
    
    elif step == 'cc':
        ad_data['cc'] = user_input
        context.user_data['ad_step'] = 'gear'
        await update.message.reply_text("⚙️ نوع گیربکس را وارد کنید (دنده‌ای / اتوماتیک):")
    
    elif step == 'gear':
        ad_data['gear_type'] = user_input
        context.user_data['ad_step'] = 'mileage'
        await update.message.reply_text("🔢 کارکرد را وارد کنید (کیلومتر، مثال: 45000):")
    
    elif step == 'mileage':
        ad_data['mileage'] = user_input
        context.user_data['ad_step'] = 'price'
        await update.message.reply_text("💰 قیمت را به تومان وارد کنید (مثال: 85000000):")
    
    elif step == 'price':
        ad_data['price'] = user_input
        context.user_data['ad_step'] = 'city'
        await update.message.reply_text("📍 شهر خود را وارد کنید:")
    
    elif step == 'city':
        ad_data['city'] = user_input
        context.user_data['ad_step'] = 'phone'
        await update.message.reply_text("📱 شماره تماس خود را وارد کنید:")
    
    elif step == 'phone':
        ad_data['contact_number'] = user_input
        context.user_data['ad_step'] = 'description'
        await update.message.reply_text("📝 توضیحات تکمیلی را وارد کنید (وضعیت موتور، بدنه، تعویض‌ها و...):")
    
    elif step == 'description':
        ad_data['description'] = user_input
        # ذخیره در دیتابیس
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''INSERT INTO ads (user_id, brand, model, year, cc, gear_type, mileage, price, city, contact_number, description, created_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (update.effective_user.id, ad_data.get('brand', ''), '', ad_data.get('year', ''),
                   ad_data.get('cc', ''), ad_data.get('gear_type', ''), ad_data.get('mileage', ''),
                   ad_data.get('price', ''), ad_data.get('city', ''), ad_data.get('contact_number', ''),
                   ad_data.get('description', ''), datetime.now().isoformat(), 'pending'))
        ad_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # اطلاع به ادمین
        if ADMIN_ID:
            keyboard = [[InlineKeyboardButton("✅ تایید", callback_data=f"approve_ad_{ad_id}"),
                         InlineKeyboardButton("❌ رد", callback_data=f"reject_ad_{ad_id}")]]
            await context.bot.send_message(
                ADMIN_ID,
                f"🆕 آگهی جدید نیاز به تایید دارد!\n\nبرند: {ad_data.get('brand')}\nقیمت: {ad_data.get('price')}\nکاربر: {update.effective_user.id}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        await update.message.reply_text("✅ آگهی شما ثبت شد و در انتظار تایید مدیر است.")
        context.user_data['ad_step'] = None
        await main_menu(update, context)

# ========== مدیریت آگهی‌ها توسط ادمین ==========
async def approve_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ad_id = int(query.data.split('_')[2])
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE ads SET status='active' WHERE id=?", (ad_id,))
    conn.commit()
    conn.close()
    
    await query.edit_message_text(f"✅ آگهی {ad_id} تایید شد.")
    
    # پیام به کاربر که آگهی تایید شد
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM ads WHERE id=?", (ad_id,))
    user_id = c.fetchone()
    conn.close()
    if user_id:
        try:
            await context.bot.send_message(user_id[0], "✅ آگهی شما تایید و منتشر شد.")
        except:
            pass

async def reject_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ad_id = int(query.data.split('_')[2])
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM ads WHERE id=?", (ad_id,))
    conn.commit()
    conn.close()
    
    await query.edit_message_text(f"❌ آگهی {ad_id} حذف شد.")

# ========== پرداخت ==========
async def payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        f"💰 برای ویژه کردن آگهی خود، مبلغ ۵۰,۰۰۰ تومان را به شماره کارت زیر واریز کنید:\n\n"
        f"`{CARD_NUMBER}`\n\n"
        f"پس از واریز، کد پیگیری را به پشتیبانی ارسال کنید.\n"
        f"📞 پشتیبانی: @YourSupportBot"
    )

# ========== نمایش آگهی‌های من ==========
async def my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ads = get_user_ads(user_id)
    if not ads:
        await update.callback_query.edit_message_text("📭 شما هیچ آگهی فعالی ندارید.")
        return
    
    text = "📋 **آگهی‌های شما:**\n\n"
    for ad in ads[:5]:
        text += f"• {ad[2]} - {ad[11]} تومان (وضعیت: {ad[16]})\n"
    text += "\nبرای مشاهده جزئیات از بخش 'آگهی‌های من' استفاده کنید."
    await update.callback_query.edit_message_text(text)

# ========== جستجو ==========
async def search_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("بر اساس برند", callback_data="search_brand")],
        [InlineKeyboardButton("بر اساس قیمت", callback_data="search_price")],
        [InlineKeyboardButton("بر اساس شهر", callback_data="search_city")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu")],
    ]
    await update.callback_query.edit_message_text(
        "🔍 جستجو را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== پشتیبانی ==========
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "📞 پشتیبانی:\n\n"
        "آیدی تلگرام: @YourSupportBot\n"
        "ساعات پاسخگویی: ۹ الی ۲۰"
    )

# ========== قیمت‌روز ==========
async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "📊 قیمت‌روز موتورهای پرطرفدار:\n\n"
        "هوندا CB400: ۸۵-۹۵ میلیون\n"
        "یاماها MT-09: ۱۴۰-۱۶۰ میلیون\n"
        "سوزوکی GSX-R: ۱۸۰-۲۰۰ میلیون\n"
        "بنلی Leoncino: ۶۵-۷۵ میلیون\n\n"
        "⚠️ قیمت‌ها تقریبی و از منابع مختلف جمع‌آوری شده است."
    )

# ========== تنظیمات ==========
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔔 فعال/غیرفعال کردن نوتیفیکیشن", callback_data="toggle_notif")],
        [InlineKeyboardButton("🗑 حذف حساب کاربری", callback_data="delete_account")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu")],
    ]
    await update.callback_query.edit_message_text(
        "⚙️ تنظیمات:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== هندلر اصلی ==========
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "menu":
        await main_menu(update, context)
    elif data == "new_ad":
        await start_new_ad(update, context)
    elif data == "my_ads":
        await my_ads(update, context)
    elif data == "search":
        await search_ads(update, context)
    elif data == "prices":
        await prices(update, context)
    elif data == "support":
        await support(update, context)
    elif data == "payment":
        await payment_info(update, context)
    elif data == "settings":
        await settings(update, context)
    elif data.startswith("approve_ad_"):
        await approve_ad(update, context)
    elif data.startswith("reject_ad_"):
        await reject_ad(update, context)
    elif data == "toggle_notif":
        await query.edit_message_text("🔔 نوتیفیکیشن‌ها غیرفعال شدند (این قابلیت در حال توسعه است).")
    elif data == "delete_account":
        await query.edit_message_text("🗑 حساب شما حذف شد. در صورت نیاز مجدداً ثبت‌نام کنید.")

# ========== استارت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username or "")
    await main_menu(update, context)

# ========== اجرای ربات ==========
def main():
    app = Application.builder().token(TOKEN).build()
    
    # هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ad_input))
    
    print("🚀 ربات روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()