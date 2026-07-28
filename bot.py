import os
import math
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from database import init_db, add_user, save_attendance, get_user_role, update_user_role
from config import TELEGRAM_TOKEN, OFFICE_LAT, OFFICE_LON, ALLOWED_DISTANCE

# Rol tugmalari
ROLE_BUTTONS = [
    [KeyboardButton("Rahbariyat"), KeyboardButton("Bo'lim xodimi")],
    [KeyboardButton("Fakultet dekani"), KeyboardButton("Kafedra mudiri")],
    [KeyboardButton("Kafedra o'qituvchisi"), KeyboardButton("Ishchi xodim")],
    [KeyboardButton("🔙 Orqaga")]
]

# Asosiy davomat tugmalari
ATTENDANCE_BUTTONS = [
    [KeyboardButton("📍 Ishga keldim (Lokatsiya yuborish)", request_location=True)],
    [KeyboardButton("🚪 Ishdan ketdim")],
    [KeyboardButton("🔙 Orqaga")]
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_role = get_user_role(user_id)
    
    if not user_role:
        reply_markup = ReplyKeyboardMarkup(ROLE_BUTTONS, resize_keyboard=True)
        await update.message.reply_text(
            "Assalomu alaykum! Davomat botiga xush kelibsiz.\nIltimos, o'z lavozimingizni tanlang:",
            reply_markup=reply_markup
        )
    else:
        reply_markup = ReplyKeyboardMarkup(ATTENDANCE_BUTTONS, resize_keyboard=True)
        await update.message.reply_text(
            f"Sizning lavozimingiz: *{user_role}*.\nKerakli amalni tanlang:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "🔙 Orqaga":
        # Orqaga bosilganda bosh menyuga yoki rol tanlashga qaytarish
        update_user_role(user_id, None)
        reply_markup = ReplyKeyboardMarkup(ROLE_BUTTONS, resize_keyboard=True)
        await update.message.reply_text("Bosh menyuga qaytdingiz. Iltimos, lavozimingizni qayta tanlang:", reply_markup=reply_markup)
        return

    # Rol tanlash jarayoni
    roles = ["Rahbariyat", "Bo'lim xodimi", "Fakultet dekani", "Kafedra mudiri", "Kafedra o'qituvchisi", "Ishchi xodim"]
    if text in roles:
        update_user_role(user_id, text)
        reply_markup = ReplyKeyboardMarkup(ATTENDANCE_BUTTONS, resize_keyboard=True)
        await update.message.reply_text(
            f"Lavozimingiz muvaffaqiyatli saqlandi: *{text}*.\nEndi davomat qilish uchun quyidagi tugmani bosing:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    if text == "🚪 Ishdan ketdim":
        await update.message.reply_text("Ishdan ketgan vaqtingiz qayd etildi. Xayr!")
        return

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    user_role = get_user_role(user_id)
    
    if not user_role:
        reply_markup = ReplyKeyboardMarkup(ROLE_BUTTONS, resize_keyboard=True)
        await update.message.reply_text("Avval o'z lavozimingizni tanlang!", reply_markup=reply_markup)
        return

    user_location = update.message.location
    lat2 = user_location.latitude
    lon2 = user_location.longitude

    # Masofani hisoblash (Haversine formulasi)
    R = 6371000  # Metrda Yer radiusi
    phi1 = math.radians(OFFICE_LAT)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - OFFICE_LAT)
    delta_lambda = math.radians(lon2 - OFFICE_LON)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c  # Metrda

    now = datetime.now()
    current_time_str = now.strftime("%H:%M:%S")
    
    # Masofani km yoki metrda ko'rsatish
    dist_str = f"{distance:.2f} metr" if distance < 1000 else f"{distance / 1000:.2f} km"

    if distance > ALLOWED_DISTANCE:
        await update.message.reply_text(
            f"❌ Siz ish joyidan uzoqdasiz!\n"
            f"Masofa: {dist_str}\n"
            f"Ruxsat etilgan hududdan tashqaridasiz."
        )
    else:
        # Vaqtni tekshirish (masalan, 08:30 dan kech qolganini aniqlash)
        limit_time = now.replace(hour=8, minute=30, second=0, microsecond=0)
        status = "O'z vaqtida" if now <= limit_time else "Kechikdi"

        save_attendance(user_id, user.full_name, user_role, current_time_str, status, dist_str)
        
        if status == "Kechikdi":
            await update.message.reply_text(f"⚠️ Siz belgilangan vaqtdan (08:30) kechikib keldingiz!\nKelgan vaqtingiz: {current_time_str}")
        else:
            await update.message.reply_text(f"✅ O'z vaqtida keldingiz!\nKelgan vaqtingiz: {current_time_str}")

        await update.message.reply_text(
            f"📌 Xodim ishga keldi:\n"
            f"👤 Ism: {user.full_name}\n"
            f"💼 Lavozim: {user_role}\n"
            f"⏰ Vaqt: {current_time_str}\n"
            f"📊 Holati: {status}\n"
            f"📍 Masofa: {dist_str}"
        )

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Bot ishga tushdi...")
    app.run_polling()
