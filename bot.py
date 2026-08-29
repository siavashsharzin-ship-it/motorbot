from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
import sqlite3

# ==================== تنظیمات ====================
BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"   # <--- اینجا توکن خودت رو بنویس

updater = Updater(BOT_TOKEN, use_context=True)
dp = updater.dispatcher

# دیتابیس برای آگهی‌های ملک
conn = sqlite3.connect("real_estate.db")
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS ads 
             (id INTEGER PRIMARY KEY, type TEXT, location TEXT, price REAL, size REAL, year TEXT, description TEXT)''')
conn.commit()

# دیتابیس برای آگهی‌های موتورسیکلت (حفظ شده)
conn2 = sqlite3.connect("motor_ads.db")
c2 = conn2.cursor()
c2.execute('''CREATE TABLE IF NOT EXISTS ads2 
             (id INTEGER PRIMARY KEY, type TEXT, brand TEXT, price REAL, year INTEGER, description TEXT)''')
conn2.commit()

# ==================== توابع ربات ملک ====================
def start_realty(update, context):
    keyboard = [
        [InlineKeyboardButton("🏠 آگهی جدید ملک", callback_data="new_realty")],
        [InlineKeyboardButton("🔍 جستجو", callback_data="search")],
        [InlineKeyboardButton("📋 لیست آگهی‌های ملک", callback_data="list_realty")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("سلام! ربات آگهی‌های ملک آماده‌ست.\nکدام کار را می‌خواهید انجام دهید؟", reply_markup=reply_markup)

def list_realty(update, context):
    c.execute("SELECT * FROM ads")
    ads = c.fetchall()
    if not ads:
        update.message.reply_text("هیچ آگهی‌ای ثبت نشده!")
        return
    text = "لیست آگهی‌های ملک:\n\n"
    for ad in ads:
        text += f"آگهی #{ad[0]} | {ad[1]} | {ad[2]} | {ad[3]} میلیون | {ad[4]} متر\n"
    update.message.reply_text(text)

def button_realty(update, context):
    query = update.callback_query
    query.answer()

    if query.data == "new_realty":
        query.edit_message_text("لطفا نوع ملک را بفرستید (آپارتمان / ویلایی / زمین)")
        context.user_data['waiting'] = 'type'
    elif query.data == "search":
        query.edit_message_text("لطفا آدرس یا شهر را بفرستید:")
        context.user_data['waiting'] = 'search'

def handle_realty(update, context):
    if 'waiting' in context.user_data:
        if context.user_data['waiting'] == 'type':
            context.user_data['type'] = update.message.text
            update.message.reply_text("لطفا موقعیت را بفرستید")
            context.user_data['waiting'] = 'location'
        elif context.user_data['waiting'] == 'location':
            context.user_data['location'] = update.message.text
            update.message.reply_text("قیمت ملک را بفرستید")
            context.user_data['waiting'] = 'price'
        elif context.user_data['waiting'] == 'price':
            context.user_data['price'] = float(update.message.text)
            update.message.reply_text("اندازه را بفرستید")
            context.user_data['waiting'] = 'size'
        elif context.user_data['waiting'] == 'size':
            context.user_data['size'] = float(update.message.text)
            update.message.reply_text("سال ساخت را بفرستید")
            context.user_data['waiting'] = 'year'
        elif context.user_data['waiting'] == 'year':
            context.user_data['year'] = update.message.text
            update.message.reply_text("توضیحات را بفرستید")
            context.user_data['waiting'] = 'description'

    # ذخیره آگهی ملک
    if 'type' in context.user_data and 'location' in context.user_data and 'price' in context.user_data and 'size' in context.user_data and 'year' in context.user_data and 'description' in context.user_data:
        c.execute("INSERT INTO ads (type, location, price, size, year, description) VALUES (?, ?, ?, ?, ?, ?)",
                  (context.user_data['type'], context.user_data['location'], context.user_data['price'], context.user_data['size'], context.user_data['year'], context.user_data['description']))
        conn.commit()
        del context.user_data['type']
        del context.user_data['location']
        del context.user_data['price']
        del context.user_data['size']
        del context.user_data['year']
        del context.user_data['description']
        update.message.reply_text("✅ آگهی ملک با موفقیت ثبت شد!")

# ==================== توابع ربات موتورسیکلت (حفظ شده) ====================
def start_motor(update, context):
    keyboard = [
        [InlineKeyboardButton("🚗 آگهی جدید موتورسیکلت", callback_data="new_motor")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("سلام! ربات آگهی موتورسیکلت آماده‌ست.", reply_markup=reply_markup)

def button_motor(update, context):
    query = update.callback_query
    query.answer()
    if query.data == "new_motor":
        query.edit_message_text("لطفا مدل موتورسیکلت را بفرستید")
        context.user_data['waiting'] = 'brand'

def handle_motor(update, context):
    if 'waiting' in context.user_data:
        if context.user_data['waiting'] == 'brand':
            context.user_data['brand'] = update.message.text
            update.message.reply_text("قیمت را بفرستید")
            context.user_data['waiting'] = 'price'
        elif context.user_data['waiting'] == 'price':
            context.user_data['price'] = float(update.message.text)
            update.message.reply_text("سال را بفرستید")
            context.user_data['waiting'] = 'year'
        elif context.user_data['waiting'] == 'year':
            context.user_data['year'] = int(update.message.text)
            update.message.reply_text("توضیحات را بفرستید")
            context.user_data['waiting'] = 'description'

    # ذخیره آگهی موتور
    if 'brand' in context.user_data and 'price' in context.user_data and 'year' in context.user_data and 'description' in context.user_data:
        c2.execute("INSERT INTO ads2 (type, brand, price, year, description) VALUES (?, ?, ?, ?, ?)",
                   ("موتورسیکلت", context.user_data['brand'], context.user_data['price'], context.user_data['year'], context.user_data['description']))
        conn2.commit()
        del context.user_data['brand']
        del context.user_data['price']
        del context.user_data['year']
        del context.user_data['description']
        update.message.reply_text("✅ آگهی موتورسیکلت ثبت شد!")

# هندلرها
dp.add_handler(CommandHandler("start", start_realty))
dp.add_handler(CallbackQueryHandler(button_realty))
dp.add_handler(MessageHandler(Filters.text, handle_realty))

# ربات موتورسیکلت (با prefix @motor_bot در نام ربات)
dp.add_handler(CommandHandler("start", start_motor))
dp.add_handler(CallbackQueryHandler(button_motor))
dp.add_handler(MessageHandler(Filters.text, handle_motor))

print("🤖 ربات آگهی‌های ملک و موتورسیکلت (دو ربات با یک توکن) شروع شد!")
updater.start_polling()
updater.idle()
