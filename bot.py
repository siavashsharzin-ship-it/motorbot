import os
import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== تنظیمات اولیه ==========
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")
CARD_NUMBER = os.environ.get("CARD_NUMBER", "شماره کارت ثبت نشده")

if not TOKEN:
    print("❌ خطا: توکن ربات در متغیر محیطی BOT_TOKEN تنظیم نشده!")
    exit(1)

if not ADMIN_ID:
    print("⚠️ هشدار: ADMIN_ID تنظیم نشده، برخی امکانات غیرفعال خواهد شد.")

print("✅ ربات در حال راه‌اندازی...")

# ========== دیتابیس ==========
DB_NAME = "motor_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        phone TEXT,
        join_date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        brand TEXT,
        model TEXT,
        year TEXT,
        cc TEXT,
        gear_type TEXT,
        mileage TEXT,
        price TEXT,
        city TEXT,
        contact_number TEXT,
        description TEXT,
        status TEXT DEFAULT 'pending',
        is_vip INTEGER DEFAULT 0,
        view_count INTEGER DEFAULT 0,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()
    print("✅ دیتابیس آماده شد.")

init_db()

# ========== تابع کمکی ==========
def get_user_ads(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM ads WHERE user_id=? AND status IN ('active', 'pending') ORDER BY created_at DESC", (user_id,))
    result = c.fetchall()
    conn.close()
    return result

# ========== منوی اصلی ==========
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 جستجو", callback_data="search")],
        [InlineKeyboardButton("📝 ثبت آگهی", callback_data="new_ad")],
        [InlineKeyboardButton("📋 آگهی‌های من", callback_data="my_ads")],
        [InlineKeyboardButton("⭐ ویژه", callback_data="vip")],
        [InlineKeyboardButton("📊 قیمت‌روز", callback_data="prices")],
        [InlineKeyboardButton("💰 پرداخت", callback_data="payment")],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🏍️ به ربات خرید و فروش موتورسیکلت خوش آمدید!\n\nیک گزینه را انتخاب کنید:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

# ========== استارت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, join_date) VALUES (?, ?, ?)",
              (user.id, user.username or "", datetime.now().isoformat()))
    conn.commit()
    conn.close()
    await main_menu(update, context)

# ========== ثبت آگهی ==========
async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ad_step'] = 'brand'
    context.user_data['ad_data'] = {}
    await update.callback_query.edit_message_text(
        "📝 ثبت آگهی جدید\n\nلطفاً **برند و مدل** موتور را وارد کنید:\nمثال: هوندا CB400"
    )

async def handle_ad_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    step = context.user_data.get('ad_step')
    ad_data = context.user_data.get('ad_data', {})
    
    if not step:
        return
    
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
        await update.message.reply_text("⚙️ نوع گیربکس (دنده‌ای / اتوماتیک):")
    
    elif step == 'gear':
        ad_data['gear_type'] = user_input
        context.user_data['ad_step'] = 'mileage'
        await update.message.reply_text("🔢 کارکرد (کیلومتر، مثال: 45000):")
    
    elif step == 'mileage':
        ad_data['mileage'] = user_input
        context.user_data['ad_step'] = 'price'
        await update.message.reply_text("💰 قیمت به تومان (مثال: 85000000):")
    
    elif step == 'price':
        ad_data['price'] = user_input
        context.user_data['ad_step'] = 'city'
        await update.message.reply_text("📍 شهر:")
    
    elif step == 'city':
        ad_data['city'] = user_input
        context.user_data['ad_step'] = 'phone'
        await update.message.reply_text("📱 شماره تماس:")
    
    elif step == 'phone':
        ad_data['contact_number'] = user_input
        context.user_data['ad_step'] = 'description'
        await update.message.reply_text("📝 توضیحات تکمیلی (وضعیت موتور، بدنه، تعویض‌ها):")
    
    elif step == 'description':
        ad_data['description'] = user_input
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''INSERT INTO ads (user_id, brand, model, year, cc, gear_type, mileage, price, city, contact_number, description, created_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (update.effective_user.id, ad_data.get('brand', ''), '', ad_data.get('year', ''),
                   ad_data.get('cc', ''), ad_data.get('gear_type', ''), ad_data.get('mileage', ''),
                   ad_data.get('price', ''), ad_data.get('city', ''), ad_data.get('contact_number', ''),
                   ad_data.get('description', ''), datetime.now().isoformat(), 'pending'))
        conn.commit()
        conn.close()
        
        await update.message.reply_text("✅ آگهی شما ثبت شد و در انتظار تایید مدیر است.")
        context.user_data['ad_step'] = None
        
        # اطلاع به ادمین
        if ADMIN_ID:
            try:
                keyboard = [[
                    InlineKeyboardButton("✅ تایید", callback_data=f"approve_{ad_data.get('brand', '')}"),
                    InlineKeyboardButton("❌ رد", callback_data="reject")
                ]]
                await context.bot.send_message(
                    int(ADMIN_ID),
                    f"🆕 آگهی جدید نیاز به تایید دارد!\n\nبرند: {ad_data.get('brand', '')}\nقیمت: {ad_data.get('price', '')}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                pass

# ========== آگهی‌های من ==========
async def my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ads = get_user_ads(user_id)
    if not ads:
        await update.callback_query.edit_message_text("📭 شما هیچ آگهی فعالی ندارید.")
        return
    
    text = "📋 **آگهی‌های شما:**\n\n"
    for ad in ads[:5]:
        text += f"• {ad[2]} - {ad[8]} تومان (وضعیت: {ad[13]})\n"
    text += "\nبرای جزئیات بیشتر به پشتیبانی پیام دهید."
    await update.callback_query.edit_message_text(text)

# ========== پرداخت ==========
async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        f"💰 برای ویژه کردن آگهی، مبلغ ۵۰,۰۰۰ تومان را به شماره کارت زیر واریز کنید:\n\n"
        f"`{CARD_NUMBER}`\n\n"
        f"پس از واریز، کد پیگیری را به پشتیبانی ارسال کنید."
    )

# ========== قیمت‌روز ==========
async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "📊 قیمت‌روز موتورهای پرطرفدار:\n\n"
        "هوندا CB400: ۸۵-۹۵ میلیون\n"
        "یاماها MT-09: ۱۴۰-۱۶۰ میلیون\n"
        "سوزوکی GSX-R: ۱۸۰-۲۰۰ میلیون\n"
        "بنلی Leoncino: ۶۵-۷۵ میلیون\n\n"
        "⚠️ قیمت‌ها تقریبی است."
    )

# ========== پشتیبانی ==========
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "📞 پشتیبانی:\n\n"
        "آیدی تلگرام: @YourSupportBot\n"
        "ساعات پاسخگویی: ۹ الی ۲۰"
    )

# ========== ویژه ==========
async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "⭐ **آگهی‌های ویژه:**\n\n"
        "• نمایش در بالای لیست\n"
        "• تگ طلایی 🔥\n"
        "• ارسال نوتیفیکیشن به کاربران\n\n"
        f"💰 هزینه: ۵۰,۰۰۰ تومان\n"
        f"💳 شماره کارت: `{CARD_NUMBER}`"
    )

# ========== جستجو ==========
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "🔍 **جستجوی پیشرفته:**\n\n"
        "برای جستجو، عبارت مورد نظر را به یکی از فرمت‌های زیر ارسال کنید:\n\n"
        "• `برند:هوندا`\n"
        "• `قیمت:۵۰ تا ۱۰۰`\n"
        "• `شهر:تهران`\n\n"
        "مثال: `برند:یاماها قیمت:۷۰ تا ۱۲۰`"
    )

# ========== هندلر دکمه‌ها ==========
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "search":
        await search(update, context)
    elif data == "new_ad":
        await new_ad(update, context)
    elif data == "my_ads":
        await my_ads(update, context)
    elif data == "vip":
        await vip(update, context)
    elif data == "prices":
        await prices(update, context)
    elif data == "payment":
        await payment(update, context)
    elif data == "support":
        await support(update, context)
    elif data == "menu":
        await main_menu(update, context)
    else:
        await main_menu(update, context)

# ========== اجرای اصلی ==========
def main():
    print("🚀 ربات در حال اجرا...")
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ad_input))
    
    print("✅ ربات آماده است!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()