import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== تنظیمات ==========
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = 8474856910  # آیدی شما
CARD_NUMBER = os.environ.get("CARD_NUMBER", "6037-9981-2167-6789")

if not TOKEN:
    print("❌ توکن نداریم!")
    exit(1)

print(f"✅ ادمین: {ADMIN_ID}")
print(f"✅ کارت: {CARD_NUMBER}")

# ========== دیتابیس ==========
DB_NAME = "motor_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        join_date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        brand TEXT,
        year TEXT,
        cc TEXT,
        price TEXT,
        city TEXT,
        phone TEXT,
        desc TEXT,
        images TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad_id INTEGER,
        user_id INTEGER,
        receipt TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT
    )''')
    conn.commit()
    conn.close()
    print("✅ دیتابیس آماده شد.")

init_db()

# ========== توابع کمکی ==========
def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    return [u[0] for u in users]

def get_ad_by_id(ad_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM ads WHERE id=?", (ad_id,))
    result = c.fetchone()
    conn.close()
    return result

def update_ad_status(ad_id, status):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE ads SET status=? WHERE id=?", (status, ad_id))
    conn.commit()
    conn.close()

# ========== استارت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # ذخیره کاربر
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, join_date) VALUES (?, ?, ?)",
              (user_id, update.effective_user.username or "", datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    # تشخیص ادمین
    if user_id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("📝 در انتظار تایید", callback_data="pending")],
            [InlineKeyboardButton("✅ آگهی‌های فعال", callback_data="active_ads")],
            [InlineKeyboardButton("📊 آمار", callback_data="stats")],
            [InlineKeyboardButton("👤 منوی کاربری", callback_data="user_menu")],
        ]
        text = "⚙️ **پنل مدیریت - سلام ادمین!**"
    else:
        keyboard = [
            [InlineKeyboardButton("📝 ثبت آگهی", callback_data="new_ad")],
            [InlineKeyboardButton("📋 آگهی‌های من", callback_data="my_ads")],
            [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")],
        ]
        text = "🏍️ **به ربات خرید و فروش موتورسیکلت خوش آمدید!**"
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ========== ثبت آگهی ==========
async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['step'] = 'brand'
    context.user_data['data'] = {}
    context.user_data['images'] = []
    await update.callback_query.message.reply_text("📝 برند و مدل رو بنویس (مثال: هوندا CB400):")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get('step')
    data = context.user_data.get('data', {})
    
    if not step:
        return
    
    if step == 'brand':
        data['brand'] = update.message.text
        context.user_data['step'] = 'year'
        await update.message.reply_text("📅 سال تولید (مثال: 1400):")
    elif step == 'year':
        data['year'] = update.message.text
        context.user_data['step'] = 'cc'
        await update.message.reply_text("🔧 حجم موتور (سی‌سی، مثال: 400):")
    elif step == 'cc':
        data['cc'] = update.message.text
        context.user_data['step'] = 'price'
        await update.message.reply_text("💰 قیمت (تومان، مثال: 85000000):")
    elif step == 'price':
        data['price'] = update.message.text
        context.user_data['step'] = 'city'
        await update.message.reply_text("📍 شهر (مثال: تهران):")
    elif step == 'city':
        data['city'] = update.message.text
        context.user_data['step'] = 'phone'
        await update.message.reply_text("📱 شماره تماس (مثال: 09121234567):")
    elif step == 'phone':
        data['phone'] = update.message.text
        context.user_data['step'] = 'desc'
        await update.message.reply_text("📝 توضیحات تکمیلی (وضعیت موتور، بدنه، تعویض‌ها):")
    elif step == 'desc':
        data['desc'] = update.message.text
        context.user_data['step'] = 'images'
        await update.message.reply_text(
            "📸 **ارسال عکس‌ها**\n\n"
            "حداقل ۱ عکس و حداکثر ۵ عکس ارسال کنید.\n"
            "عکس‌ها رو یکی‌یکی بفرستید.\n"
            "بعد از ارسال همه عکس‌ها، دکمه **پایان** رو بزنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ پایان ارسال عکس", callback_data="done")]])
        )

# ========== دریافت عکس ==========
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('step') != 'images':
        await update.message.reply_text("❌ لطفاً ابتدا ثبت آگهی را شروع کنید.")
        return
    
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = f"images/{file.file_id}.jpg"
    os.makedirs("images", exist_ok=True)
    await file.download_to_drive(file_path)
    context.user_data['images'].append(file_path)
    await update.message.reply_text(
        f"✅ عکس {len(context.user_data['images'])} ثبت شد.\n"
        "عکس بعدی رو بفرستید یا دکمه **پایان** رو بزنید.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ پایان ارسال عکس", callback_data="done")]])
    )

# ========== پایان عکس‌ها ==========
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data.get('data', {})
    images = context.user_data.get('images', [])
    
    if len(images) < 1:
        await update.callback_query.message.reply_text("❌ حداقل ۱ عکس باید ارسال کنید!")
        return
    
    user_id = update.effective_user.id
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT INTO ads (user_id, brand, year, cc, price, city, phone, desc, images, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (user_id, data.get('brand'), data.get('year'), data.get('cc'),
               data.get('price'), data.get('city'), data.get('phone'),
               data.get('desc'), ','.join(images), datetime.now().isoformat(), 'pending'))
    ad_id = c.lastrowid
    conn.commit()
    conn.close()
    
    context.user_data.clear()
    
    # اگر ادمین باشه، مستقیم تایید بشه
    if user_id == ADMIN_ID:
        update_ad_status(ad_id, 'active')
        await update.callback_query.message.reply_text("✅ آگهی شما به عنوان ادمین ثبت و منتشر شد!")
        return
    
    # ارسال به ادمین برای تایید
    keyboard = [
        [InlineKeyboardButton("✅ تایید", callback_data=f"approve_{ad_id}")],
        [InlineKeyboardButton("❌ رد", callback_data=f"reject_{ad_id}")]
    ]
    await context.bot.send_message(
        ADMIN_ID,
        f"📝 **آگهی جدید نیاز به تایید دارد!**\n\n"
        f"🏍️ برند: {data.get('brand')}\n"
        f"💰 قیمت: {data.get('price')} تومان\n"
        f"📍 شهر: {data.get('city')}\n"
        f"🆔 کاربر: {user_id}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    await update.callback_query.message.reply_text("✅ آگهی شما ثبت شد و در انتظار تایید مدیر است.")

# ========== تایید/رد توسط ادمین ==========
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ad_id = int(update.callback_query.data.split('_')[1])
    update_ad_status(ad_id, 'active')
    await update.callback_query.edit_message_text("✅ تایید شد!")
    
    ad = get_ad_by_id(ad_id)
    if ad:
        await context.bot.send_message(ad[1], "✅ آگهی شما تایید و منتشر شد!")

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ad_id = int(update.callback_query.data.split('_')[1])
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM ads WHERE id=?", (ad_id,))
    conn.commit()
    conn.close()
    await update.callback_query.edit_message_text("❌ رد شد!")
    
    ad = get_ad_by_id(ad_id)
    if ad:
        await context.bot.send_message(ad[1], "❌ آگهی شما رد شد. لطفاً با پشتیبانی تماس بگیرید.")

# ========== آگهی‌های من ==========
async def my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM ads WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    ads = c.fetchall()
    conn.close()
    
    if not ads:
        await update.callback_query.message.reply_text("📭 شما هیچ آگهی فعالی ندارید.")
        return
    
    text = "📋 **آگهی‌های شما:**\n\n"
    for ad in ads[:5]:
        status_text = {
            'pending': '⏳ در انتظار تایید',
            'active': '✅ فعال',
            'rejected': '❌ رد شده',
            'sold': '🔴 فروخته شده'
        }.get(ad[10], ad[10])
        text += f"• {ad[2]} - {ad[5]} تومان ({status_text})\n"
    
    if len(ads) > 5:
        text += f"\nو {len(ads)-5} آگهی دیگر..."
    
    await update.callback_query.message.reply_text(text)

# ========== پنل ادمین ==========
async def pending_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.callback_query.message.reply_text("❌ دسترسی ندارید!")
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM ads WHERE status='pending' ORDER BY created_at DESC")
    ads = c.fetchall()
    conn.close()
    
    if not ads:
        await update.callback_query.message.reply_text("📭 هیچ آگهی در انتظار تایید نیست.")
        return
    
    text = "📝 **آگهی‌های در انتظار تایید:**\n\n"
    for ad in ads:
        text += f"🆔 {ad[0]} | {ad[2]} | {ad[5]} تومان | {ad[6]}\n"
    
    # دکمه برای تایید سریع
    keyboard = []
    for ad in ads[:5]:
        keyboard.append([
            InlineKeyboardButton(f"✅ تایید {ad[0]}", callback_data=f"approve_{ad[0]}"),
            InlineKeyboardButton(f"❌ رد {ad[0]}", callback_data=f"reject_{ad[0]}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="user_menu")])
    
    await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def active_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM ads WHERE status='active' ORDER BY created_at DESC")
    ads = c.fetchall()
    conn.close()
    
    if not ads:
        await update.callback_query.message.reply_text("📭 هیچ آگهی فعالی نیست.")
        return
    
    text = "✅ **آگهی‌های فعال:**\n\n"
    for ad in ads:
        text += f"🆔 {ad[0]} | {ad[2]} | {ad[5]} تومان | {ad[6]}\n"
    
    # دکمه فروخته شد
    keyboard = []
    for ad in ads[:5]:
        keyboard.append([
            InlineKeyboardButton(f"🔴 فروخته شد {ad[0]}", callback_data=f"sold_{ad[0]}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="user_menu")])
    
    await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ========== فروخته شد ==========
async def sold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    ad_id = int(update.callback_query.data.split('_')[1])
    update_ad_status(ad_id, 'sold')
    await update.callback_query.edit_message_text(f"✅ آگهی {ad_id} به عنوان فروخته شده ثبت شد.")
    
    # اطلاع به همه کاربران
    ad = get_ad_by_id(ad_id)
    if ad:
        users = get_all_users()
        for user_id in users:
            try:
                await context.bot.send_message(
                    user_id,
                    f"🔔 **موتور فروخته شد!**\n\n"
                    f"🏍️ {ad[2]}\n💰 {ad[5]} تومان\n📍 {ad[6]}\n\n"
                    f"این آگهی به فروش رسید."
                )
            except:
                pass

# ========== آمار ==========
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ads")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ads WHERE status='active'")
    active = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ads WHERE status='pending'")
    pending = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ads WHERE status='sold'")
    sold_count = c.fetchone()[0]
    conn.close()
    
    await update.callback_query.message.reply_text(
        f"📊 **آمار کلی:**\n\n"
        f"👤 کاربران: {users}\n"
        f"📝 کل آگهی‌ها: {total}\n"
        f"✅ فعال: {active}\n"
        f"⏳ در انتظار تایید: {pending}\n"
        f"🔴 فروخته شده: {sold_count}"
    )

# ========== منوی کاربری ==========
async def user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 ثبت آگهی", callback_data="new_ad")],
        [InlineKeyboardButton("📋 آگهی‌های من", callback_data="my_ads")],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")],
    ]
    await update.callback_query.message.reply_text(
        "🏍️ **منوی کاربری**\n\nیک گزینه را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== پشتیبانی ==========
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text(
        "📞 **پشتیبانی**\n\n"
        "برای ارتباط با پشتیبانی، روی لینک زیر کلیک کنید:\n"
        "[ارسال پیام به ادمین](tg://user?id=8474856910)"
    )

# ========== هندلر دکمه‌ها ==========
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "new_ad":
        await new_ad(update, context)
    elif data == "my_ads":
        await my_ads(update, context)
    elif data == "support":
        await support(update, context)
    elif data == "pending":
        await pending_ads(update, context)
    elif data == "active_ads":
        await active_ads(update, context)
    elif data == "stats":
        await stats(update, context)
    elif data == "user_menu":
        await user_menu(update, context)
    elif data == "done":
        await done(update, context)
    elif data.startswith("approve_"):
        await approve(update, context)
    elif data.startswith("reject_"):
        await reject(update, context)
    elif data.startswith("sold_"):
        await sold(update, context)

# ========== اجرا ==========
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("🚀 ربات روشن شد!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()