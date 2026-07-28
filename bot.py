import os
import math
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from database import init_db, add_user, save_attendance, get_user_info, update_user_role_dept, set_user_block_status
from config import TELEGRAM_TOKEN, ADMIN_ID, OFFICE_LAT, OFFICE_LON, ALLOWED_DISTANCE

DEPARTMENT_BUTTONS = [
    [KeyboardButton("🏛 Rektorat va Rahbariyat"), KeyboardButton("📚 O'quv bo'limi")],
    [KeyboardButton("🎓 Fakultet dekanatlari"), KeyboardButton("🔬 Kafedralar")],
    [KeyboardButton("🛠 Xo'jalik bo'limi"), KeyboardButton("🔙 Orqaga")]
]

ROLE_BUTTONS = [
    [KeyboardButton("🏛 Rahbar / Dean"), KeyboardButton("📋 Bo'lim xodimi")],
    [KeyboardButton("👨‍🏫 O'qituvchi"), KeyboardButton("🛠 Ishchi xodim")],
    [KeyboardButton("🔙 Orqaga")]
]

# Ishga kelish va ishdan ketish uchun alohida lokatsiya talab qiluvchi tugmalar
ATTENDANCE_BUTTONS = [
    [KeyboardButton("📍 Ishga keldim (Lokatsiya yuborish)", request_location=True)],
    [KeyboardButton("🚪 Ishdan ketdim (Lokatsiya yuborish)", request_location=True)],
    [KeyboardButton("🔙 Orqaga")]
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    role, dept = get_user_info(user_id)
    if role == "BLOCKED":
        await update.message.reply_text("⛔ Siz admin tomonidan botdan bloklangansiz!")
        return

    add_user(user_id, user.full_name, None, None)
    
    welcome_text = (
        "Assalomu alaykum hurmatli xodim, "
        "men sizning bugundan boshlab ishga kelish va ketish vaqtingizni aniqlab turuvchi yordamchingizman. "
        "Kuningiz hayrli, ishingiz barokotli o'tsin. "
        "Marhamat qilib kerakli bo'limni tanlang va davom eting"
    )
    
    if not role or not dept:
        reply_markup = ReplyKeyboardMarkup(DEPARTMENT_BUTTONS, resize_keyboard=True)
        await update.message.reply_text(
            f"{welcome_text}\n\nIltimos, o'zingizning **bo'limingizni** tanlang:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        reply_markup = ReplyKeyboardMarkup(ATTENDANCE_BUTTONS, resize_keyboard=True)
        await update.message.reply_text(
            f"{welcome_text}\n\nBo'lim: *{dept}*\nLavozim: *{role}*.\nKerakli amalni tanlang:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

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
        await update.message.reply_text(f"✅ ID: {target_id} foydalanuvchi bloklandi.")
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")

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
        await update.message.reply_text(f"✅ ID: {target_id} foydalanuvchi blokdan chiqarildi.")
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    user_id = user.id
    
    role, dept = get_user_info(user_id)
    if role == "BLOCKED":
        await update.message.reply_text("⛔ Siz admin tomonidan botdan bloklangansiz!")
        return

    if text == "🔙 Orqaga":
        add_user(user_id, user.full_name, None, None)
        reply_markup = ReplyKeyboardMarkup(DEPARTMENT_BUTTONS, resize_keyboard=True)
        await update.message.reply_text("Bosh menyuga qaytdingiz. Bo'limingizni qaytadan tanlang:", reply_markup=reply_markup)
        return

    departments = ["🏛 Rektorat va Rahbariyat", "📚 O'quv bo'limi", "🎓 Fakultet dekanatlari", "🔬 Kafedralar", "🛠 Xo'jalik bo'limi"]
    if text in departments:
        context.user_data['selected_dept'] = text
        reply_markup = ReplyKeyboardMarkup(ROLE_BUTTONS, resize_keyboard=True)
        await update.message.reply_text("Endi o'z **lavozimingizni** tanlang:", reply_markup=reply_markup, parse_mode="Markdown")
        return

    roles = ["🏛 Rahbar / Dean", "📋 Bo'lim xodimi", "👨‍🏫 O'qituvchi", "🛠 Ishchi xodim"]
    if text in roles:
        selected_dept = context.user_data.get('selected_dept', "Umumiy bo'lim")
        update_user_role_dept(user_id, selected_dept, text)
        reply_markup = ReplyKeyboardMarkup(ATTENDANCE_BUTTONS, resize_keyboard=True)
        await update.message.reply_text(
            f"✅ Ma'lumotlaringiz saqlandi!\nBo'lim: *{selected_dept}*\nLavozim: *{text}*.\n\nEndi davomat uchun quyidagi tugmalardan birini bosing:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    role, dept = get_user_info(user_id)
    if role == "BLOCKED":
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

    if not role or not dept:
        role = "Xodim"
        dept = "Umumiy"

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

    # Agar masofa 1000 metrdan oshsa, qat'iy rad etiladi
    if distance > ALLOWED_DISTANCE:
        await update.message.reply_text(
            f"❌ Siz belgilangan chegaradan tashqaridasiz!\n"
            f"Siz turgan masofa: {dist_str}\n"
            f"Ruxsat etilgan maksimal masofa: 1000 metr. Lokatsiyangiz qabul qilmadi!"
        )
        return

    # Foydalanuvchi oxirgi marta qaysi tugmani bosganini yoki xabar kontekstini aniqlaymiz
    # Telegramda lokatsiya yuborilganda foydalanuvchi "Ishga keldim" yoki "Ishdan ketdim" tugmasini bosgan bo'ladi.
    # Buni aniqlash uchun foydalanuvchi yuborgan oxirgi xabardagi tugma matnini tekshiramiz:
    # (Agar foydalanuvchi tugma orqali lokatsiya yuborgan bo'lsa, Telegram odatda matn bermaydi, 
    # shuning uchun har ikkala amalni aniqlash uchun vaqt yoki ketma-ketlik qo'llaniladi).
    
    # Oddiy va aniq mantiq: Agar soat 14:00 gacha bo'lsa "Ishga keldi", undan keyin "Ishdan ketdi" deb taxmin qilish mumkin 
    # yoki foydalanuvchiga har safar tanlov berish mumkin. Keling, buni yanada mukammal qilamiz:
    # Xodim lokatsiya yuborganda bot undan "Bu qaysi amal?" deb so'rashi yoki avtomat ravishda vaqtga qarab ajratishi mumkin.
    
    # Keling, vaqt oralig'iga qarab aniqlaymiz: soat 13:00 gacha "Ishga keldi", 13:00 dan keyin "Ishdan ketdi" deb belgilaymiz.
    if now.hour < 13:
        action = "Ishga keldi"
        limit_time = now.replace(hour=8, minute=30, second=0, microsecond=0)
        status = "O'z vaqtida" if now <= limit_time else "Kechikdi"
    else:
        action = "Ishdan ketdi"
        status = "Ketdi"

    save_attendance(user_id, full_name, dept, role, action, current_time_str, status, dist_str)
    
    if action == "Ishga keldi":
        if status == "Kechikdi":
            await update.message.reply_text(f"⚠️ Siz belgilangan vaqtdan (08:30) kechikib keldingiz!\nKelgan vaqtingiz: {current_time_str}")
        else:
            await update.message.reply_text(f"✅ O'z vaqtida keldingiz!\nKelgan vaqtingiz: {current_time_str}")
    else:
        await update.message.reply_text(f"🚪 Ishdan ketgan vaqtingiz muvaffaqiyatli qayd etildi!\nVaqt: {current_time_str}")

    # Adminga xabar yuborish
    admin_text = (
        f"📌 **Xodim davomati ({action}):**\n"
        f"👤 Ism: {full_name}\n"
        f"🆔 ID: `{user_id}`\n"
        f"🏛 Bo'lim: {dept}\n"
        f"💼 Lavozim: {role}\n"
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
    
    print("Davomat boti to'liq ishga tushdi...")
    app.run_polling()
