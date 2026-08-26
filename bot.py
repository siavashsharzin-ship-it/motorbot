import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== تنظیمات ==========
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
CARD_NUMBER = os.environ.get("CARD_NUMBER", "شماره کارت ثبت نشده")
PRICE = 500000  # هزینه ثبت آگهی به ریال (۵۰۰,۰۰۰ ریال = ۵۰,۰۰۰ تومان)

if not TOKEN:
    print("❌ خطا: TOKEN تنظیم نشده!")
    exit(1)

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
        images TEXT,
        status TEXT DEFAULT 'pending_payment',
        is_vip INTEGER DEFAULT 0,
        view_count INTEGER DEFAULT 0,
        created_at TEXT,
        sold_at TEXT
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

def get_user_ads(user_id, status=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if status:
        c.execute("SELECT * FROM ads WHERE user_id=? AND status=? ORDER BY created_at DESC", (user_id, status))
    else:
        c.execute("SELECT * FROM ads WHERE user_id=? AND status IN ('pending_payment','pending','active') ORDER BY created_at DESC", (user_id,))
    result = c.fetchall()
    conn.close()
    return result

def get_all_ads(status=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if status:
        c.execute("SELECT * FROM ads WHERE status=? ORDER BY created_at DESC", (status,))
    else:
        c.execute("SELECT * FROM ads ORDER BY created_at DESC")
    result = c.fetchall()
    conn.close()
    return result

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

def update_ad_images(ad_id, images):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE ads SET images=? WHERE id=?", (images, ad_id))
    conn.commit()
    conn.close()

def save_payment(ad_id, user_id, receipt):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO payments (ad_id, user_id, receipt, created_at) VALUES (?, ?, ?, ?)",
              (ad_id, user_id, receipt, datetime.now().isoformat()))
    conn.commit()
    conn.close()

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
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin_panel")])
    
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
    context.user_data['images'] = []
    await update.callback_query.edit_message_text(
        "📝 ثبت آگهی جدید\n\n"
        "لطفاً **برند و مدل** موتور را وارد کنید:\n"
        "مثال: هوندا CB400"
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
        context.user_data['ad_step'] = 'images'
        await update.message.reply_text(
            "📸 حالا عکس‌های موتور را ارسال کنید (حداقل ۱ عکس، حداکثر ۱۰ عکس).\n\n"
            "بعد از ارسال عکس‌ها، دکمه **پایان** را بزنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ پایان ارسال عکس", callback_data="done_images")]])
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('ad_step') != 'images':
        return
    
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = f"images/{file.file_id}.jpg"
    os.makedirs("images", exist_ok=True)
    await file.download_to_drive(file_path)
    
    context.user_data.setdefault('images', []).append(file_path)
    await update.message.reply_text(f"✅ عکس {len(context.user_data['images'])} ثبت شد. عکس بعدی یا دکمه پایان را بزنید.")

async def done_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    images = context.user_data.get('images', [])
    if not images:
        await update.callback_query.edit_message_text("❌ حداقل ۱ عکس باید ارسال کنید!")
        return
    
    ad_data = context.user_data.get('ad_data', {})
    user_id = update.effective_user.id
    
    # ذخیره آگهی
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT INTO ads (user_id, brand, model, year, cc, gear_type, mileage, price, city, contact_number, description, images, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (user_id, ad_data.get('brand', ''), '', ad_data.get('year', ''),
               ad_data.get('cc', ''), ad_data.get('gear_type', ''), ad_data.get('mileage', ''),
               ad_data.get('price', ''), ad_data.get('city', ''), ad_data.get('contact_number', ''),
               ad_data.get('description', ''), ','.join(images), datetime.now().isoformat(), 'pending_payment'))
    ad_id = c.lastrowid
    conn.commit()
    conn.close()
    
    context.user_data['ad_step'] = None
    context.user_data['ad_data'] = {}
    context.user_data['images'] = []
    
    # اگر ادمین باشه، مستقیم تایید میشه
    if user_id == ADMIN_ID:
        update_ad_status(ad_id, 'active')
        await update.callback_query.edit_message_text("✅ آگهی شما به عنوان ادمین ثبت و منتشر شد!")
        return
    
    # درخواست پرداخت
    keyboard = [[InlineKeyboardButton("💳 پرداخت ۵۰,۰۰۰ تومان", callback_data=f"pay_{ad_id}")]]
    await update.callback_query.edit_message_text(
        f"✅ آگهی شما ثبت شد!\n\n"
        f"💰 مبلغ **۵۰,۰۰۰ تومان** (۵۰۰,۰۰۰ ریال) برای انتشار آگهی باید پرداخت شود.\n\n"
        f"💳 شماره کارت: `{CARD_NUMBER}`\n\n"
        f"پس از واریز، دکمه زیر را بزنید و رسید را ارسال کنید.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== پرداخت ==========
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ad_id = int(query.data.split('_')[1])
    context.user_data['paying_ad'] = ad_id
    await query.edit_message_text(
        f"💳 لطفاً رسید پرداخت را به صورت **عکس** ارسال کنید.\n\n"
        f"مبلغ: ۵۰,۰۰۰ تومان\nشماره کارت: `{CARD_NUMBER}`"
    )

async def handle_payment_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ad_id = context.user_data.get('paying_ad')
    if not ad_id:
        await update.message.reply_text("❌ ابتدا دکمه پرداخت را بزنید.")
        return
    
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = f"receipts/{file.file_id}.jpg"
    os.makedirs("receipts", exist_ok=True)
    await file.download_to_drive(file_path)
    
    save_payment(ad_id, update.effective_user.id, file_path)
    context.user_data['paying_ad'] = None
    
    # ارسال به ادمین
    ad = get_ad_by_id(ad_id)
    keyboard = [
        [InlineKeyboardButton("✅ تایید پرداخت", callback_data=f"confirm_payment_{ad_id}")],
        [InlineKeyboardButton("❌ رد پرداخت", callback_data=f"reject_payment_{ad_id}")]
    ]
    await context.bot.send_photo(
        ADMIN_ID,
        photo=open(file_path, 'rb'),
        caption=f"🧾 رسید پرداخت\n\nآگهی: {ad[2]} - {ad[8]} تومان\nکاربر: {update.effective_user.id}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    await update.message.reply_text("✅ رسید شما ارسال شد. پس از تایید مدیر، آگهی منتشر می‌شود.")

# ========== تایید/رد پرداخت توسط ادمین ==========
async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ad_id = int(query.data.split('_')[2])
    update_ad_status(ad_id, 'active')
    await query.edit_message_caption(caption="✅ پرداخت تایید شد. آگهی منتشر گردید.")
    
    ad = get_ad_by_id(ad_id)
    await context.bot.send_message(ad[1], "✅ پرداخت شما تایید شد و آگهی شما منتشر گردید!")

async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ad_id = int(query.data.split('_')[2])
    update_ad_status(ad_id, 'rejected')
    await query.edit_message_caption(caption="❌ پرداخت رد شد.")
    
    ad = get_ad_by_id(ad_id)
    await context.bot.send_message(ad[1], "❌ پرداخت شما رد شد. لطفاً با پشتیبانی تماس بگیرید.")

# ========== آگهی‌های من ==========
async def my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ads = get_user_ads(user_id)
    if not ads:
        await update.callback_query.edit_message_text("📭 شما هیچ آگهی فعالی ندارید.")
        return
    
    text = "📋 **آگهی‌های شما:**\n\n"
    for ad in ads[:10]:
        status_text = {
            'pending_payment': '⏳ در انتظار پرداخت',
            'pending': '⏳ در انتظار تایید',
            'active': '✅ فعال',
            'rejected': '❌ رد شده',
            'sold': '🔴 فروخته شده'
        }.get(ad[13], ad[13])
        text += f"• {ad[2]} - {ad[8]:,} تومان ({status_text})\n"
    
    if len(ads) > 10:
        text += f"\nو {len(ads)-10} آگهی دیگر..."
    
    await update.callback_query.edit_message_text(text)

# ========== فروخته شد ==========
async def mark_sold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ad_id = int(query.data.split('_')[2])
    ad = get_ad_by_id(ad_id)
    
    if not ad or ad[1] != update.effective_user.id:
        await query.answer("شما اجازه این کار را ندارید!")
        return
    
    update_ad_status(ad_id, 'sold')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE ads SET sold_at=? WHERE id=?", (datetime.now().isoformat(), ad_id))
    conn.commit()
    conn.close()
    
    await query.edit_message_text(f"✅ آگهی {ad[2]} به عنوان فروخته شده ثبت شد.")
    
    # اطلاع به همه کاربران
    users = get_all_users()
    for user_id in users:
        try:
            await context.bot.send_message(
                user_id,
                f"🔔 **موتور فروخته شد!**\n\n"
                f"🏍️ {ad[2]}\n💰 {ad[8]:,} تومان\n📍 {ad[9]}\n\n"
                f"این آگهی به فروش رسید."
            )
        except:
            pass

# ========== پنل ادمین ==========
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.callback_query.answer("شما دسترسی ندارید!")
        return
    
    pending_ads = get_all_ads('pending_payment')
    active_ads = get_all_ads('active')
    
    keyboard = [
        [InlineKeyboardButton(f"📝 آگهی‌های در انتظار ({len(pending_ads)})", callback_data="admin_pending")],
        [InlineKeyboardButton(f"✅ آگهی‌های فعال ({len(active_ads)})", callback_data="admin_active")],
        [InlineKeyboardButton("📊 آمار کلی", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu")],
    ]
    await update.callback_query.edit_message_text(
        "⚙️ **پنل مدیریت**\n\nیک گزینه را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_pending_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    ads = get_all_ads('pending_payment')
    if not ads:
        await update.callback_query.edit_message_text("📭 هیچ آگهی در انتظار پرداخت نیست.")
        return
    
    text = "📝 **آگهی‌های در انتظار پرداخت:**\n\n"
    for ad in ads[:10]:
        text += f"🆔 {ad[0]} | {ad[2]} | {ad[8]:,} تومان | {ad[9]}\n"
    text += "\nبرای مشاهده جزئیات، از دکمه‌های زیر استفاده کنید."
    
    keyboard = []
    for ad in ads[:5]:
        keyboard.append([InlineKeyboardButton(f"🆔 {ad[0]} - {ad[2]}", callback_data=f"view_ad_{ad[0]}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")])
    
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_active_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    ads = get_all_ads('active')
    if not ads:
        await update.callback_query.edit_message_text("📭 هیچ آگهی فعالی نیست.")
        return
    
    text = "✅ **آگهی‌های فعال:**\n\n"
    for ad in ads[:10]:
        text += f"🆔 {ad[0]} | {ad[2]} | {ad[8]:,} تومان | {ad[9]}\n"
    
    keyboard = []
    for ad in ads[:5]:
        keyboard.append([
            InlineKeyboardButton(f"🔴 فروخته شد {ad[0]}", callback_data=f"sold_{ad[0]}"),
            InlineKeyboardButton(f"👁 {ad[0]}", callback_data=f"view_ad_{ad[0]}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")])
    
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ads")
    total_ads = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ads WHERE status='active'")
    active_ads = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ads WHERE status='sold'")
    sold_ads = c.fetchone()[0]
    conn.close()
    
    await update.callback_query.edit_message_text(
        f"📊 **آمار کلی:**\n\n"
        f"👤 کاربران: {users_count}\n"
        f"📝 کل آگهی‌ها: {total_ads}\n"
        f"✅ آگهی‌های فعال: {active_ads}\n"
        f"🔴 فروخته شده: {sold_ads}"
    )

async def view_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ad_id = int(update.callback_query.data.split('_')[2])
    ad = get_ad_by_id(ad_id)
    if not ad:
        await update.callback_query.edit_message_text("❌ آگهی پیدا نشد.")
        return
    
    text = f"🏍️ **{ad[2]}**\n"
    text += f"📅 سال: {ad[4]}\n"
    text += f"🔧 حجم: {ad[5]} سی‌سی\n"
    text += f"⚙️ گیربکس: {ad[6]}\n"
    text += f"🔢 کارکرد: {ad[7]:,} کیلومتر\n"
    text += f"💰 قیمت: {ad[8]:,} تومان\n"
    text += f"📍 شهر: {ad[9]}\n"
    text += f"📱 تماس: {ad[10]}\n"
    text += f"📝 توضیحات: {ad[11]}\n"
    text += f"📌 وضعیت: {ad[13]}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ========== جستجو ==========
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "🔍 **جستجوی پیشرفته:**\n\n"
        "عبارت مورد نظر را ارسال کنید:\n\n"
        "• `برند:هوندا`\n"
        "• `قیمت:۵۰ تا ۱۰۰`\n"
        "• `شهر:تهران`\n\n"
        "مثال: `برند:یاماها قیمت:۷۰ تا ۱۲۰`"
    )

# ========== قیمت‌روز ==========
async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "📊 **قیمت‌روز موتورهای پرطرفدار:**\n\n"
        "هوندا CB400: ۸۵-۹۵ میلیون\n"
        "یاماها MT-09: ۱۴۰-۱۶۰ میلیون\n"
        "سوزوکی GSX-R: ۱۸۰-۲۰۰ میلیون\n"
        "بنلی Leoncino: ۶۵-۷۵ میلیون\n\n"
        "⚠️ قیمت‌ها تقریبی است."
    )

# ========== پشتیبانی ==========
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "📞 **پشتیبانی:**\n\n"
        "آیدی: @YourSupportBot\n"
        "ساعت پاسخگویی: ۹ تا ۲۰"
    )

# ========== ویژه ==========
async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "⭐ **آگهی‌های ویژه:**\n\n"
        "• نمایش در بالای لیست\n"
        "• تگ طلایی 🔥\n"
        "• نوتیفیکیشن به همه\n\n"
        f"💰 هزینه: ۵۰,۰۰۰ تومان\n"
        f"💳 شماره کارت: `{CARD_NUMBER}`"
    )

# ========== پرداخت عمومی ==========
async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        f"💰 شماره کارت برای واریز:\n\n`{CARD_NUMBER}`"
    )

# ========== هندلر دکمه‌ها ==========
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "menu":
        await main_menu(update, context)
    elif data == "new_ad":
        await new_ad(update, context)
    elif data == "my_ads":
        await my_ads(update, context)
    elif data == "search":
        await search(update, context)
    elif data == "prices":
        await prices(update, context)
    elif data == "support":
        await support(update, context)
    elif data == "payment":
        await payment(update, context)
    elif data == "vip":
        await vip(update, context)
    elif data == "admin_panel":
        await admin_panel(update, context)
    elif data == "admin_pending":
        await admin_pending_ads(update, context)
    elif data == "admin_active":
        await admin_active_ads(update, context)
    elif data == "admin_stats":
        await admin_stats(update, context)
    elif data == "done_images":
        await done_images(update, context)
    elif data.startswith("pay_"):
        await pay(update, context)
    elif data.startswith("confirm_payment_"):
        await confirm_payment(update, context)
    elif data.startswith("reject_payment_"):
        await reject_payment(update, context)
    elif data.startswith("sold_"):
        await mark_sold(update, context)
    elif data.startswith("view_ad_"):
        await view_ad(update, context)

# ========== اجرا ==========
def main():
    print("🚀 ربات در حال اجرا...")
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ad_input))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("✅ ربات آماده است!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()