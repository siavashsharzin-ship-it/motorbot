import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== تنظیمات ==========
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
CARD_NUMBER = os.environ.get("CARD_NUMBER", "شماره کارت ثبت نشده")

if not TOKEN:
    print("❌ توکن نداریم!")
    exit(1)

print(f"✅ ادمین: {ADMIN_ID}")

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, join_date) VALUES (?, ?, ?)",
              (user_id, update.effective_user.username or "", datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
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

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['step'] = 'brand'
    context.user_data['data'] = {}
    context.user_data['images'] = []
    await update.callback_query.message.reply_text("📝 برند و مدل رو بنویس:")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get('step')
    data = context.user_data.get('data', {})
    
    if not step:
        return
    
    if step == 'brand':
        data['brand'] = update.message.text
        context.user_data['step'] = 'year'
        await update.message.reply_text("📅 سال تولید:")
    elif step == 'year':
        data['year'] = update.message.text
        context.user_data['step'] = 'cc'
        await update.message.reply_text("🔧 حجم موتور:")
    elif step == 'cc':
        data['cc'] = update.message.text
        context.user_data['step'] = 'price'
        await update.message.reply_text("💰 قیمت (تومان):")
    elif step == 'price':
        data['price'] = update.message.text
        context.user_data['step'] = 'city'
        await update.message.reply_text("📍 شهر:")
    elif step == 'city':
        data['city'] = update.message.text
        context.user_data['step'] = 'phone'
        await update.message.reply_text("📱 شماره تماس:")
    elif step == 'phone':
        data['phone'] = update.message.text
        context.user_data['step'] = 'desc'
        await update.message.reply_text("📝 توضیحات:")
    elif step == 'desc':
        data['desc'] = update.message.text
        context.user_data['step'] = 'images'
        await update.message.reply_text(
            "📸 عکس بفرست. بعدش دکمه پایان رو بزن.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ پایان", callback_data="done")]])
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('step') != 'images':
        return
    
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = f"images/{file.file_id}.jpg"
    os.makedirs("images", exist_ok=True)
    await file.download_to_drive(file_path)
    context.user_data['images'].append(file_path)
    await update.message.reply_text(f"✅ عکس {len(context.user_data['images'])} ثبت شد.")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data.get('data', {})
    images = context.user_data.get('images', [])
    
    if len(images) < 1:
        await update.callback_query.message.reply_text("❌ حداقل ۱ عکس بفرست!")
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
    
    if user_id == ADMIN_ID:
        update_ad_status(ad_id, 'active')
        await update.callback_query.message.reply_text("✅ آگهی به عنوان ادمین ثبت شد!")
        return
    
    keyboard = [
        [InlineKeyboardButton("✅ تایید", callback_data=f"approve_{ad_id}")],
        [InlineKeyboardButton("❌ رد", callback_data=f"reject_{ad_id}")]
    ]
    await context.bot.send_message(
        ADMIN_ID,
        f"📝 آگهی جدید!\nبرند: {data.get('brand')}\nقیمت: {data.get('price')}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    await update.callback_query.message.reply_text("✅ آگهی ثبت شد. منتظر تایید مدیر باش.")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ad_id = int(update.callback_query.data.split('_')[1])
    update_ad_status(ad_id, 'active')
    await update.callback_query.edit_message_text("✅ تایید شد!")
    ad = get_ad_by_id(ad_id)
    if ad:
        await context.bot.send_message(ad[1], "✅ آگهی شما تایید شد!")

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
        await context.bot.send_message(ad[1], "❌ آگهی شما رد شد.")

async def my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM ads WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    ads = c.fetchall()
    conn.close()
    
    if not ads:
        await update.callback_query.message.reply_text("📭 هیچ آگهی نداری.")
        return
    
    text = "📋 **آگهی‌های تو:**\n\n"
    for ad in ads[:5]:
        status_text = {
            'pending': '⏳ در انتظار تایید',
            'active': '✅ فعال',
            'sold': '🔴 فروخته شده'
        }.get(ad[10], ad[10])
        text += f"• {ad[2]} - {ad[5]} تومان ({status_text})\n"
    
    await update.callback_query.message.reply_text(text)

async def pending_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM ads WHERE status='pending'")
    ads = c.fetchall()
    conn.close()
    
    if not ads:
        await update.callback_query.message.reply_text("📭 هیچ آگهی در انتظار نیست.")
        return
    
    text = "📝 **در انتظار تایید:**\n\n"
    for ad in ads:
        text += f"🆔 {ad[0]} | {ad[2]} | {ad[5]} تومان\n"
    
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
    c.execute("SELECT * FROM ads WHERE status='active'")
    ads = c.fetchall()
    conn.close()
    
    if not ads:
        await update.callback_query.message.reply_text("📭 هیچ آگهی فعالی نیست.")
        return
    
    text = "✅ **آگهی‌های فعال:**\n\n"
    for ad in ads:
        text += f"🆔 {ad[0]} | {ad[2]} | {ad[5]} تومان\n"
    
    keyboard = []
    for ad in ads[:5]:
        keyboard.append([
            InlineKeyboardButton(f"🔴 فروخته شد {ad[0]}", callback_data=f"sold_{ad[0]}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="user_menu")])
    
    await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def sold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    ad_id = int(update.callback_query.data.split('_')[1])
    update_ad_status(ad_id, 'sold')
    await update.callback_query.edit_message_text(f"✅ فروخته شد!")
    
    ad = get_ad_by_id(ad_id)
    if ad:
        users = get_all_users()
        for user_id in users:
            try:
                await context.bot.send_message(
                    user_id,
                    f"🔔 **موتور فروخته شد!**\n🏍️ {ad[2]}\n💰 {ad[5]} تومان"
                )
            except:
                pass

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
        f"📊 **آمار:**\n\n👤 کاربران: {users}\n📝 کل: {total}\n✅ فعال: {active}\n⏳ در انتظار: {pending}\n🔴 فروخته: {sold_count}"
    )

async def user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 ثبت آگهی", callback_data="new_ad")],
        [InlineKeyboardButton("📋 آگهی‌های من", callback_data="my_ads")],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")],
    ]
    await update.callback_query.message.reply_text(
        "🏍️ **منوی کاربری**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== پشتیبانی با یوزرنیم شما ==========
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text(
        f"📞 **پشتیبانی**\n\n"
        f"برای ارتباط با پشتیبانی، روی لینک زیر کلیک کنید:\n"
        f"[ارسال پیام به پشتیبانی](https://t.me/mkhbs22)\n\n"
        f"یا با آیدی زیر تماس بگیرید:\n"
        f"`@mkhbs22`"
    )

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