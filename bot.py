import os
import math
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from database import init_db, add_user, save_attendance, get_user_role, update_user_role, set_user_block_status
from config import TELEGRAM_TOKEN, ADMIN_ID, OFFICE_LAT, OFFICE_LON, ALLOWED_DISTANCE

ROLE_BUTTONS = [
    [KeyboardButton("🏛 Rahbariyat"), KeyboardButton("📋 Bo'lim xodimi")],
    [KeyboardButton("🎓 Fakultet dekani"), KeyboardButton("📚 Kafedra mudiri")],
    [KeyboardButton("👨‍🏫 Kafedra o'qituvchisi"), KeyboardButton("🛠 Ishchi xodim")],
    [KeyboardButton("🔙 Orqaga")]
]

ATTENDANCE_BUTTONS = [
    [KeyboardButton("📍 Ishga keldim (Lokatsiya yuborish)", request_location=True)],
    [KeyboardButton("🚪 Ishdan ketdim")],
    [KeyboardButton("🔙 Orqaga")]
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Bloklanganligini tekshirish
    role_status = get_user_role(user_id)
    if role_status == "BLOCKED":
        await update.message.reply_text("⛔ Siz admin tomonidan botdan bloklangansiz!")
        return

    add_user(user_id, user.full_name, None)
    user_role = get_user_role(user_id)
    
    welcome_text = (
        "Assalomu alaykum hurmatli xodim, "
        "men sizning bugundan boshlab ishga kelish va ketish vaqtingizni aniqlab turuvchi yordamchingizman. "
        "Kuningiz hayrli, ishingiz barokotli o'tsin. "
        "Marhamat qilib kerakli bo'limni tanlang va davom eting"
    )
    
    if not user_role:
        reply_markup = ReplyKeyboardMarkup(ROLE_BUTTONS, resize_keyboard=True)
        await update.message.reply_text(
            f"{welcome_text}\n\nIltimos, o'z lavozimingizni tanlang:",
            reply_markup=reply_markup
        )
    else:
        reply_markup = ReplyKeyboardMarkup(ATTENDANCE_BUTTONS, resize_keyboard=True)
        await update.message.reply_text(
            f"{welcome_text}\n\nSizning lavozimingiz: *{user_role}*.\nKerakli amalni tanlang:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

# Admin uchun foydalanuvchini bloklash buyrug'i: /block F_ID
async def block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Bu buyruq faqat admin uchun!")
        return
    
    if not context.args:
        await update.message.reply_text("Foydalanish: /block <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        set_user_block_status(target_id, 1)
        await update.message.reply_text(f"✅ ID: {target_id} bo'lgan foydalanuvchi bloklandi.")
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")

# Admin uchun foydalanuvchini blokdan chiqarish buyrug'i: /unblock F_ID
async def unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Bu buyruq faqat admin uchun!")
        return
    
    if not context.args:
        await update.message.reply_text("Foydalanish: /unblock <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        set_user_block_status(target_id, 0)
        await update.message.reply_text(f"✅ ID: {target_id} bo'lgan foydalanuvchi blokdan chiqarildi.")
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    if get_user_role(user_id) == "BLOCKED":
        await update.message.reply_text("⛔ Siz admin tomonidan botdan bloklangansiz!")
        return

    text = update.message.text
    if text == "🔙 Orqaga":
        update_user_role(user_id, None)
        reply_markup = ReplyKeyboardMarkup(ROLE_BUTTONS, resize_keyboard=True)
        await update.message.reply_text("Bosh menyuga qaytdingiz. Iltimos, lavozimingizni qayta tanlang:", reply_markup=reply_markup)
        return

    role_mapping = {
        "🏛 Rahbariyat": "Rahbariyat",
        "📋 Bo'lim xodimi": "Bo'lim xodimi",
        "🎓 Fakultet dekani": "Fakultet dekani",
        "📚 Kafedra mudiri": "Kafedra mudiri",
        "👨‍🏫 Kafedra o'qituvchisi": "Kafedra o'qituvchisi",
        "🛠 Ishchi xodim": "Ishchi xodim"
    }
    
    if text in role_mapping:
        clean_role = role_mapping[text]
        add_user(user_id, user.full_name, clean_role)
        update_user_role(user_id, clean_role)
        reply_markup = ReplyKeyboardMarkup(ATTENDANCE_BUTTONS, resize_keyboard=True)
        await update.message.reply_text(
            f"Lavozimingiz muvaffaqiyatli saqlandi: *{clean_role}*.\nEndi davomat qilish uchun quyidagi tugmani bosing:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    if text == "🚪 Ishdan ketdim":
        user_role = get_user_role(user_id) or "Noma'lum"
        now = datetime.now()
        current_time_str = now.strftime("%H:%M:%S")
        
        save_attendance(user_id, user.full_name, user_role, "Ishdan ketdi", current_time_str, "Ketdi", "N/A")
        await update.message.reply_text(f"🚪 Ishdan ketgan vaqtingiz qayd etildi: {current_time_str}. Xayr!")
        
        admin_text = (
            f"🚪 **Xodim ishdan ketdi:**\n"
            f"👤 Ism: {user.full_name}\n"
            f"🆔 ID: `{user_id}`\n"
            f"💼 Lavozim: {user_role}\n"
            f"⏰ Vaqt: {current_time_str}"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="Markdown")
        except Exception as e:
            print(f"Adminga yuborishda xatolik: {e}")
        return

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    if get_user_role(user_id) == "BLOCKED":
        await update.message.reply_text("⛔ Siz admin tomonidan botdan bloklangansiz!")
        return

    full_name = user.full_name if user.full_name else ""
    name_parts = full_name.split()
    if len(name_parts) < 2:
        await update.message.reply_text(
            "⚠️ Diqqat! Telegram profilingizda ism va familiyangiz to'liq ko'rsatilmagan.\n"
            "Iltimos, avval Telegram profilingiz nomini *Ism va Familiya* ko'rinishiga o'zgartiring, "
            "so'ngra qaytadan lokatsiya yuboring!",
            parse_mode="Markdown"
        )
        return

    user_role = get_user_role(user_id)
    if not user_role or user_role == "BLOCKED":
        user_role = "Bo'lim xodimi"
        add_user(user_id, full_name, user_role)

    user_location = update.message.location
    if not user_location:
        await update.message.reply_text("Iltimos, haqiqiy geolokatsiya yuboring.")
        return

    lat2 = user_location.latitude
    lon2 = user_location.longitude

    R = 6371000
    phi1 = math.radians(OFFICE_LAT)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - OFFICE_LAT)
    delta_lambda = math.radians(lon2 - OFFICE_LON)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    now = datetime.now()
    current_time_str = now.strftime("%H:%M:%S")
    dist_str = f"{distance:.2f} metr" if distance < 1000 else f"{distance / 1000:.2f} km"

    if distance > ALLOWED_DISTANCE:
        await update.message.reply_text(
            f"❌ Siz ish joyidan uzoqdasiz!\n"
            f"Masofa: {dist_str}\n"
            f"Ruxsat etilgan hududdan tashqaridasiz."
        )
    else:
        limit_time = now.replace(hour=8, minute=30, second=0, microsecond=0)
        status = "O'z vaqtida" if now <= limit_time else "Kechikdi"

        save_attendance(user_id, full_name, user_role, "Ishga keldi", current_time_str, status, dist_str)
        
        if status == "Kechikdi":
            await update.message.reply_text(f"⚠️ Siz belgilangan vaqtdan (08:30) kechikib keldingiz!\nKelgan vaqtingiz: {current_time_str}")
        else:
            await update.message.reply_text(f"✅ O'z vaqtida keldingiz!\nKelgan vaqtingiz: {current_time_str}")

        admin_text = (
            f"📌 **Xodim ishga keldi:**\n"
            f"👤 Ism: {full_name}\n"
            f"🆔 ID: `{user_id}`\n"
            f"💼 Lavozim: {user_role}\n"
            f"⏰ Vaqt: {current_time_str}\n"
            f"📊 Holati: {status}\n"
            f"📍 Masofa: {dist_str}"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="Markdown")
        except Exception as e:
            print(f"Adminga yuborishda xatolik: {e}")

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("block", block_user))
    app.add_handler(CommandHandler("unblock", unblock_user))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Bot ishga tushdi...")
    app.run_polling()
