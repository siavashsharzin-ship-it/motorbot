import logging
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    ContextTypes, CallbackQueryHandler
)

# ------------------ تنظیمات اصلی ------------------

TOKEN = "8868906040:AAHFEcVX4u6Nh-K2AJG_9KDIix3PENqA4sc"   # توکن واقعی ربات persian_motor_bot
CHANNEL = "@persian_motor"                                  # کانال واقعی تو

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ------------------ ممبرگیر اجباری ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL, user_id=user_id)

        if member.status in ["member", "administrator", "creator"]:
            await update.message.reply_text("خوش آمدی سیوش ❤️ ربات برات فعال شد ✔️")
        else:
            await send_join_message(update, context)

    except:
        await send_join_message(update, context)


async def send_join_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL.replace('@','')}")],
        [InlineKeyboardButton("عضو شدم ✔️", callback_data="check_join")]
    ]

    await update.message.reply_text(
        "برای استفاده از ربات، لطفاً عضو کانال شوید 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    member = await context.bot.get_chat_member(chat_id=CHANNEL, user_id=user_id)

    if member.status in ["member", "administrator", "creator"]:
        await query.edit_message_text("عالیه سیوش! عضو شدی و ربات فعال شد ✔️")
    else:
        await query.edit_message_text(
            "هنوز عضو کانال نشدی ❌\nلطفاً عضو شو و دوباره امتحان کن."
        )

# ------------------ اجرای ربات ------------------

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
