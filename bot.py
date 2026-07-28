import logging
from datetime import datetime
from geopy.distance import geodesic
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN, ADMIN_ID, OFFICE_LAT, OFFICE_LON, MAX_DISTANCE_KM
from database import init_db, save_arrival, save_departure

logging.basicConfig(level=logging.INFO)

def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📍 Ishga keldim (Lokatsiya yuborish)", request_location=True)],
        [KeyboardButton("🚪 Ishdan ketdim")]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    await update.message.reply_text(
        "Assalomu alaykum! Ish vaqtini nazorat qilish botiga xush kelibsiz.\n"
        "Ishga kelganingizni tasdiqlash uchun pastdagi tugmani bosing va geolokatsiyangizni yuboring:",
        reply_markup=main_keyboard()
    )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    loc = update.message.location
    
    user_coords = (loc.latitude, loc.longitude)
    office_coords = (OFFICE_LAT, OFFICE_LON)
    
    distance = geodesic(user_coords, office_coords).km
    
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    
    if distance > MAX_DISTANCE_KM:
        await update.message.reply_text(
            f"❌ Siz ishxona hududidan tashqarisidasiz!\n"
            f"Masofa: {distance:.2f} km (Ruxsat etilgan radius: {MAX_DISTANCE_KM} km)."
        )
        return
    
    limit_time = datetime.strptime("08:30:00", "%H:%M:%S").time()
    user_time = now.time()
    
    if user_time > limit_time:
        status = "Kechikdi"
        time_status = "⚠️ Siz belgilangan vaqtdan (08:30) kechikib keldingiz!"
    else:
        status = "O'z vaqtida"
        time_status = "✅ O'z vaqtida keldingiz. Rahmat!"
        
    save_arrival(user.id, user.full_name, current_date, current_time, status)
    
    await update.message.reply_text(f"{time_status}\nKelgan vaqtingiz: {current_time}")
    
    if ADMIN_ID:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📌 <b>Xodim ishga keldi:</b>\n"
                 f"👤 {user.full_name}\n"
                 f"⏰ Vaqt: {current_time}\n"
                 f"📊 Holati: {status}\n"
                 f"📍 Masofa: {distance:.2f} km",
            parse_mode="HTML"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user
    
    if text == "🚪 Ishdan ketdim":
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")
        
        save_departure(user.id, current_date, current_time)
        await update.message.reply_text(f"👋 Xayr! Ishdan ketgan vaqtingiz qayd etildi: {current_time}")
        
        if ADMIN_ID:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🚪 <b>Xodim ishdan ketdi:</b>\n👤 {user.full_name}\n⏰ Vaqt: {current_time}",
                parse_mode="HTML"
            )

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Davomat boti ishga tushdi...")
    app.run_polling()