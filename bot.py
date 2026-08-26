import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== تنظیمات ==========
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
CARD_NUMBER = os.environ.get("CARD_NUMBER", "شماره کارت ثبت نشده")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@IranMotoHub")

if not TOKEN:
    print("❌ توکن نداریم!")
    exit(1)

print(f"✅ ادمین: {ADMIN_ID}")
print(f"✅ کانال: {CHANNEL_ID}")

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
    conn.commit()
    conn.close()

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

def get_active_ads():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM ads WHERE status='active' ORDER BY created_at DESC")
    ads = c.fetchall()
    conn.close()
    return ads

def update_ad_status(ad_id, status):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE ads SET status=? WHERE id=?", (status, ad_id))
    conn.commit()
    conn.close()

# ========== بررسی عضویت (فقط برای کاربران عادی) ==========
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # ادمین معاف از شرط عضویت
    if user_id == ADMIN_ID:
        return True
    
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
        return False
    except:
        return False

# ========== منوی دائمی پایین صفحه ==========
def get_main_keyboard(user_id):
    if user_id == ADMIN_ID:
        keyboard = [
            ["🏍️ لیست موتورها", "📝 ثبت آگهی"],
            ["📝 در انتظار تایید", "✅ آگهی‌های فعال"],
            ["📊 آمار"],
        ]
    else:
        keyboard = [
            ["🏍️ لیست موتورها", "📝 ثبت آگهی"],
            ["📋 آگهی‌های من", "📞 پشتیبانی"],
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ========== استارت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, join_date) VALUES (?, ?, ?)",
              (user_id, update.effective_user.username or "", datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    # فقط کاربران عادی چک عضویت میشن
    if user_id != ADMIN_ID:
        is_member = await check_membership(update, context)
        if not is_member:
            keyboard = [
                [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")],
                [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_membership")]
            ]
            await update.message.reply_text(
                f"🔒 **برای استفاده از ربات، ابتدا عضو کانال زیر شوید:**\n\n"
                f"📢 {CHANNEL_ID}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
    
    reply_markup = get_main_keyboard(user_id)
    if user_id == ADMIN_ID:
        text = "⚙️ **پنل مدیریت - سلام ادمین!**\n\nلطفاً یک گزینه را انتخاب کنید:"
    else:
        text = "🏍️ **به ربات خرید و فروش موتورسیکلت خوش آمدید!**\n\nلطفاً یک گزینه را انتخاب کنید:"
    
    await update.message.reply_text(text, reply_markup=reply_markup)

# ========== بررسی مجدد عضویت ==========
async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    is_member = await check_membership(update, context)
    
    if is_member:
        await query.edit_message_text("✅ عضویت شما تایید شد! لطفاً مجدداً /start را بزنید.")
    else:
        await query.edit_message_text(
            f"❌ شما هنوز عضو کانال نشده‌اید.\n\n📢 {CHANNEL_ID}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")],
                [InlineKeyboardButton("✅ بررسی مجدد", callback_data="check_membership")]
            ])
        )

# ========== نمایش لیست موتورها ==========
async def list_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # کاربر عادی باید عضو باشه
    if user_id != ADMIN_ID:
        is_member = await check_membership(update, context)
        if not is_member:
            await update.message.reply_text(
                f"❌ شما عضو کانال نیستید!\n\n📢 {CHANNEL_ID}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")]
                ])
            )
            return
    
    ads = get_active_ads()
    
    if not ads:
        await update.message.reply_text(
            "📭 **هیچ موتوری برای فروش وجود ندارد.**\n\nاولین نفری باشید که آگهی ثبت می‌کند!",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    for ad in ads[:10]:
        text = (
            f"🏍️ **{ad[2]}**\n"
            f"📅 سال: {ad[3]}\n"
            f"🔧 حجم: {ad[4]} سی‌سی\n"
            f"💰 قیمت: {ad[5]:,} تومان\n"
            f"📍 شهر: {ad[6]}\n"
            f"📱 تماس: {ad[7]}\n"
            f"📝 {ad[8]}\n"
        )
        await update.message.reply_text(text, reply_markup=get_main_keyboard(user_id))
    
    await update.message.reply_text("✅ **پایان لیست موتورها**", reply_markup=get_main_keyboard(user_id))

# ========== ثبت آگهی ==========
async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # فقط کاربران عادی چک عضویت میشن (ادمین معاف)
    if user_id != ADMIN_ID:
        is_member = await check_membership(update, context)
        if not is_member:
            await update.message.reply_text(
                f"❌ شما عضو کانال نیستید!\n\n📢 {CHANNEL_ID}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")]
                ])
            )
            return
    
    context.user_data['step'] = 'brand'
    context.user_data['data'] = {}
    context.user_data['images'] = []
    
    await update.message.reply_text(
        "📝 **ثبت آگهی جدید**\n\nبرند و مدل رو بنویس (مثال: هوندا CB400):",
        reply_markup=get_main_keyboard(user_id)
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = context.user_data.get('step')
    data = context.user_data.get('data', {})
    
    if not step:
        return
    
    if step == 'brand':
        data['brand'] = update.message.text
        context.user_data['step'] = 'year'
        await update.message.reply_text("📅 سال تولید (مثال: 1400):", reply_markup=get_main_keyboard(user_id))
    elif step == 'year':
        data['year'] = update.message.text
        context.user_data['step'] = 'cc'
        await update.message.reply_text("🔧 حجم موتور (سی‌سی، مثال: 400):", reply_markup=get_main_keyboard(user_id))
    elif step == 'cc':
        data['cc'] = update.message.text
        context.user_data['step'] = 'price'
        await update.message.reply_text("💰 قیمت (تومان، مثال: 85000000):", reply_markup=get_main_keyboard(user_id))
    elif step == 'price':
        data['price'] = update.message.text
        context.user_data['step'] = 'city'
        await update.message.reply_text("📍 شهر (مثال: تهران):", reply_markup=get_main_keyboard(user_id))
    elif step == 'city':
        data['city'] = update.message.text
        context.user_data['step'] = 'phone'
        await update.message.reply_text("📱 شماره تماس (مثال: 09121234567):", reply_markup=get_main_keyboard(user_id))
    elif step == 'phone':
        data['phone'] = update.message.text
        context.user_data['step'] = 'desc'
        await update.message.reply_text("📝 توضیحات تکمیلی:", reply_markup=get_main_keyboard(user_id))
    elif step == 'desc':
        data['desc'] = update.message.text
        context.user_data['step'] = 'images'
        await update.message.reply_text(
            "📸 **ارسال عکس‌ها**\n\nحداقل ۱ عکس ارسال کنید.\nبعد از ارسال، دکمه **پایان** رو بزنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ پایان", callback_data="done")]])
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
        f"✅ عکس {len(context.user_data['images'])} ثبت شد.\nعکس بعدی یا دکمه پایان:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ پایان", callback_data="done")]])
    )

# ========== پایان عکس‌ها ==========
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = context.user_data.get('data', {})
    images = context.user_data.get('images', [])
    
    if len(images) < 1:
        await query.message.reply_text("❌ حداقل ۱ عکس باید ارسال کنید!", reply_markup=get_main_keyboard(user_id))
        return
    
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
    
    # ====== اگر ادمین باشه، مستقیم تایید بشه ======
    if user_id == ADMIN_ID:
        update_ad_status(ad_id, 'active')
        await query.message.reply_text("✅ آگهی شما به عنوان ادمین ثبت و منتشر شد!", reply_markup=get_main_keyboard(user_id))
        return
    
    # ====== کاربر عادی: ارسال به ادمین برای تایید ======
    keyboard = [
        [InlineKeyboardButton("✅ تایید", callback_data=f"approve_{ad_id}")],
        [InlineKeyboardButton("❌ رد", callback_data=f"reject_{ad_id}")]
    ]
    await context.bot.send_message(
        ADMIN_ID,
        f"📝 **آگهی جدید!**\n\n🏍️ {data.get('brand')}\n💰 {data.get('price')} تومان\n📍 {data.get('city')}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    await query.message.reply_text(
        "✅ آگهی شما ثبت شد و در انتظار تایید مدیر است.",
        reply_markup=get_main_keyboard(user_id)
    )

# ========== تایید آگهی ==========
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ad_id = int(update.callback_query.data.split('_')[1])
    update_ad_status(ad_id, 'active')
    await update.callback_query.edit_message_text("✅ تایید شد!")
    
    ad = get_ad_by_id(ad_id)
    if ad:
        await context.bot.send_message(ad[1], "✅ آگهی شما تایید و منتشر شد!")
        
        users = get_all_users()
        text = (
            f"🆕 **آگهی جدید منتشر شد!**\n\n"
            f"🏍️ **{ad[2]}**\n"
            f"💰 قیمت: {ad[5]:,} تومان\n"
            f"📍 شهر: {ad[6]}\n"
            f"📱 تماس: {ad[7]}"
        )
        
        for user_id in users:
            try:
                await context.bot.send_message(user_id, text)
            except:
                pass

# ========== رد آگهی ==========
async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ad_id = int(update.callback_query.data.split('_')[1])
    ad = get_ad_by_id(ad_id)
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM ads WHERE id=?", (ad_id,))
    conn.commit()
    conn.close()
    
    await update.callback_query.edit_message_text("❌ رد شد!")
    
    if ad:
        await context.bot.send_message(ad[1], "❌ آگهی شما رد شد. لطفاً با پشتیبانی تماس بگیرید.")

# ========== آگهی‌های من ==========
async def my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # کاربر عادی باید عضو باشه
    if user_id != ADMIN_ID:
        is_member = await check_membership(update, context)
        if not is_member:
            await update.message.reply_text(
                f"❌ شما عضو کانال نیستید!\n\n📢 {CHANNEL_ID}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")]
                ])
            )
            return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM ads WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    ads = c.fetchall()
    conn.close()
    
    if not ads:
        await update.message.reply_text("📭 شما هیچ آگهی فعالی ندارید.", reply_markup=get_main_keyboard(user_id))
        return
    
    text = "📋 **آگهی‌های شما:**\n\n"
    for ad in ads[:5]:
        status_text = {
            'pending': '⏳ در انتظار تایید',
            'active': '✅ فعال',
            'sold': '🔴 فروخته شده'
        }.get(ad[10], ad[10])
        text += f"• {ad[2]} - {ad[5]:,} تومان ({status_text})\n"
    
    await update.message.reply_text(text, reply_markup=get_main_keyboard(user_id))

# ========== پنل ادمین ==========
async def pending_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM ads WHERE status='pending' ORDER BY created_at DESC")
    ads = c.fetchall()
    conn.close()
    
    if not ads:
        await update.message.reply_text("📭 هیچ آگهی در انتظار تایید نیست.", reply_markup=get_main_keyboard(user_id))
        return
    
    text = "📝 **در انتظار تایید:**\n\n"
    for ad in ads:
        text += f"🆔 {ad[0]} | {ad[2]} | {ad[5]:,} تومان\n"
    
    keyboard = []
    for ad in ads[:5]:
        keyboard.append([
            InlineKeyboardButton(f"✅ تایید {ad[0]}", callback_data=f"approve_{ad[0]}"),
            InlineKeyboardButton(f"❌ رد {ad[0]}", callback_data=f"reject_{ad[0]}")
        ])
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def active_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    ads = get_active_ads()
    
    if not ads:
        await update.message.reply_text("📭 هیچ آگهی فعالی نیست.", reply_markup=get_main_keyboard(user_id))
        return
    
    text = "✅ **آگهی‌های فعال:**\n\n"
    for ad in ads:
        text += f"🆔 {ad[0]} | {ad[2]} | {ad[5]:,} تومان\n"
    
    keyboard = []
    for ad in ads[:5]:
        keyboard.append([
            InlineKeyboardButton(f"🔴 فروخته شد {ad[0]}", callback_data=f"sold_{ad[0]}")
        ])
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def sold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    ad_id = int(update.callback_query.data.split('_')[1])
    update_ad_status(ad_id, 'sold')
    await update.callback_query.edit_message_text("✅ فروخته شد!")
    
    ad = get_ad_by_id(ad_id)
    if ad:
        users = get_all_users()
        for user_id in users:
            try:
                await context.bot.send_message(
                    user_id,
                    f"🔔 **موتور فروخته شد!**\n\n🏍️ {ad[2]}\n💰 {ad[5]:,} تومان"
                )
            except:
                pass

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
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
    
    await update.message.reply_text(
        f"📊 **آمار کلی:**\n\n"
        f"👤 کاربران: {users}\n"
        f"📝 کل: {total}\n"
        f"✅ فعال: {active}\n"
        f"⏳ در انتظار: {pending}\n"
        f"🔴 فروخته: {sold_count}",
        reply_markup=get_main_keyboard(user_id)
    )

# ========== پشتیبانی ==========
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # کاربر عادی باید عضو باشه
    if user_id != ADMIN_ID:
        is_member = await check_membership(update, context)
        if not is_member:
            await update.message.reply_text(
                f"❌ شما عضو کانال نیستید!\n\n📢 {CHANNEL_ID}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")]
                ])
            )
            return
    
    await update.message.reply_text(
        f"📞 **پشتیبانی**\n\nارسال پیام:\n[https://t.me/mkhbs22](https://t.me/mkhbs22)",
        reply_markup=get_main_keyboard(user_id)
    )

# ========== هندلر ==========
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == "🏍️ لیست موتورها":
        await list_ads(update, context)
    elif text == "📝 ثبت آگهی":
        await new_ad(update, context)
    elif text == "📋 آگهی‌های من":
        await my_ads(update, context)
    elif text == "📞 پشتیبانی":
        await support(update, context)
    elif text == "📝 در انتظار تایید" and user_id == ADMIN_ID:
        await pending_ads(update, context)
    elif text == "✅ آگهی‌های فعال" and user_id == ADMIN_ID:
        await active_ads(update, context)
    elif text == "📊 آمار" and user_id == ADMIN_ID:
        await stats(update, context)
    else:
        await handle_text(update, context)

# ========== هندلر دکمه‌های اینلاین ==========
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "check_membership":
        await check_membership_callback(update, context)
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(callback))
    
    print("🚀 ربات روشن شد!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()