import os
import math
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from database import init_db, add_user, save_attendance, get_user_info, update_user_role_dept, set_user_block_status
from config import TELEGRAM_TOKEN, ADMIN_ID, OFFICE_LAT, OFFICE_LON, ALLOWED_DISTANCE

# Asosiy bo'limlar menyusi (Ikonkalar bilan)
DEPARTMENT_BUTTONS = [
    [KeyboardButton("🏛 Rahbariyat"), KeyboardButton("📋 Bo'lim boshlig'i")],
    [KeyboardButton("🎓 Fakultet dekanlari"), KeyboardButton("👨‍🏫 Professor-o'qituvchilar")],
    [KeyboardButton("📌 Kafedra mudiri"), KeyboardButton("🛠 Xo'jalik bo'limi")],
    [KeyboardButton("🔙 Orqaga")]
]

# 1. Rahbariyat ichidagi lavozimlar
RAHBARIYAT_BUTTONS = [
    [KeyboardButton("👤 Rektor"), KeyboardButton("👨‍💼 Ma'naviy va ma'rifiyi ishlar prorektori")],
    [KeyboardButton("🏗 Xo'jalik ishlar prorektori"), KeyboardButton("📚 O'quv ishlar prorektori")],
    [KeyboardButton("🔬 Ilmiy ishlar va innovatsiyalar prorektori"), KeyboardButton("🌐 Xalqaro aloqalar prorektori")],
    [KeyboardButton("💡 Yoshlar bilan ishlash bo'yicha rektor maslahatchisi"), KeyboardButton("📁 Devonxona mudiri")],
    [KeyboardButton("🔍 Ichki nazorat va monitoring mudiri"), KeyboardButton("💰 Bosh hisobchi")],
    [KeyboardButton("助手 Rektor yordamchisi"), KeyboardButton("🔙 Orqaga")]
]

# 2. Bo'lim boshlig'i ichidagi lavozimlar
BOLIM_BOSHLIGI_BUTTONS = [
    [KeyboardButton("🔬 Ilmiy bo'lim boshlig'i"), KeyboardButton("📚 O'quv bo'lim boshlig'i")],
    [KeyboardButton("📜 Magistratura bo'lim boshlig'i"), KeyboardButton("🌟 Ma'naviyat bo'lim boshlig'i")],
    [KeyboardButton("🗣 Fuqarolar murojatlari bilan ishlash bo'lim boshlig'i"), KeyboardButton("👥 Xodimlar bo'lim boshlig'i")],
    [KeyboardButton("🛡 Korrupsiya qarshi bo'lim boshlig'i"), KeyboardButton("🌍 Xalqaro aloqalar bo'lim boshlig'i")],
    [KeyboardButton("🛠 Xo'jalik ishlari bo'lim boshlig'i"), KeyboardButton("📊 Ta’lim jarayonini tashkil etish bo‘limi boshlig'i")],
    [KeyboardButton("🗂 Registrator ofisi bo'lim boshlig'i"), KeyboardButton("🔙 Orqaga")]
]

# 3. Fakultet dekanlari ichidagi lavozimlar
FAKULTET_BUTTONS = [
    [KeyboardButton("🎨 San'at va sport fakulteti dekani"), KeyboardButton("📐 Aniq fanlar va muhandislik fakulteti dekani")],
    [KeyboardButton("📖 Boshlang‘ich va texnologik ta’lim fakulteti dekani"), KeyboardButton("🌿 Tabiiy fanlar va iqtisodiyot fakulteti dekani")],
    [KeyboardButton("🗣 Gumanitar fanlar va tillar fakultetida dekani"), KeyboardButton("🧠 Pedagogika va psixologiya fakulteti dekani")],
    [KeyboardButton("🔙 Orqaga")]
]

# 4. Professor-o'qituvchilar ichidagi lavozimlar
PROFESSOR_OTUVCHILAR_BUTTONS = [
    [KeyboardButton("🎓 Professor"), KeyboardButton("🏅 Dotsent")],
    [KeyboardButton("🎖 Professor v.b."), KeyboardButton("🏅 Dotsent v.b.")],
    [KeyboardButton("📖 Katta o'qituvchi"), KeyboardButton("✍️ Assistent o'qituvchi")],
    [KeyboardButton("📌 Stajyor o'qituvchi"), KeyboardButton("🔙 Orqaga")]
]

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
        if 'selected_dept' in context.user_data:
            context.user_data.pop('selected_dept', None)
            reply_markup = ReplyKeyboardMarkup(DEPARTMENT_BUTTONS, resize_keyboard=True)
            await update.message.reply_text("Bosh menyuga qaytdingiz. Bo'limingizni tanlang:", reply_markup=reply_markup)
        else:
            add_user(user_id, user.full_name, None, None)
            reply_markup = ReplyKeyboardMarkup(DEPARTMENT_BUTTONS, resize_keyboard=True)
            await update.message.reply_text("Bosh menyuga qaytdingiz. Bo'limingizni qaytadan tanlang:", reply_markup=reply_markup)
        return

    # Asosiy bo'limlar
    if text == "🏛 Rahbariyat":
        context.user_data['selected_dept'] = text
        reply_markup = ReplyKeyboardMarkup(RAHBARIYAT_BUTTONS, resize_keyboard=True)
        await update.message.reply_text("Rahbariyat lavozimini tanlang:", reply_markup=reply_markup)
        return

    if text == "📋 Bo'lim boshlig'i":
        context.user_data['selected_dept'] = text
        reply_markup = ReplyKeyboardMarkup(BOLIM_BOSHLIGI_BUTTONS, resize_keyboard=True)
        await update.message.reply_text("Bo'lim boshlig'i yo'nalishini tanlang:", reply_markup=reply_markup)
        return

    if text == "🎓 Fakultet dekanlari":
        context.user_data['selected_dept'] = text
        reply_markup = ReplyKeyboardMarkup(FAKULTET_BUTTONS, resize_keyboard=True)
        await update.message.reply_text("Fakultetni tanlang:", reply_markup=reply_markup)
        return

    if text == "👨‍🏫 Professor-o'qituvchilar":
        context.user_data['selected_dept'] = text
        reply_markup = ReplyKeyboardMarkup(PROFESSOR_OTUVCHILAR_BUTTONS, resize_keyboard=True)
        await update.message.reply_text("Professor-o'qituvchilar lavozimini tanlang:", reply_markup=reply_markup)
        return

    if text == "📌 Kafedra mudiri":
        selected_dept = "Kafedralar"
        update_user_role_dept(user_id, selected_dept, text)
        reply_markup = ReplyKeyboardMarkup(ATTENDANCE_BUTTONS, resize_keyboard=True)
        await update.message.reply_text(
            f"✅ Ma'lumotlaringiz saqlandi!\nBo'lim: *{selected_dept}*\nLavozim: *{text}*.\n\nEndi davomat uchun quyidagi tugmalardan birini bosing:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    if text == "🛠 Xo'jalik bo'limi":
        selected_dept = text
        update_user_role_dept(user_id, selected_dept, "Xodim")
        reply_markup = ReplyKeyboardMarkup(ATTENDANCE_BUTTONS, resize_keyboard=True)
        await update.message.reply_text(
            f"✅ Ma'lumotlaringiz saqlandi!\nBo'lim: *{selected_dept}*.\n\nEndi davomat uchun quyidagi tugmalardan birini bosing:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    # Barcha ichki lavozimlar ro'yxati
    all_roles = [
        "👤 Rektor", "👨‍💼 Ma'naviy va ma'rifiyi ishlar prorektori", "🏗 Xo'jalik ishlar prorektori", "📚 O'quv ishlar prorektori",
        "🔬 Ilmiy ishlar va innovatsiyalar prorektori", "🌐 Xalqaro aloqalar prorektori", "💡 Yoshlar bilan ishlash bo'yicha rektor maslahatchisi",
        "📁 Devonxona mudiri", "🔍 Ichki nazorat va monitoring mudiri", "💰 Bosh hisobchi", "助手 Rektor yordamchisi",
        "🔬 Ilmiy bo'lim boshlig'i", "📚 O'quv bo'lim boshlig'i", "📜 Magistratura bo'lim boshlig'i", "🌟 Ma'naviyat bo'lim boshlig'i",
        "🗣 Fuqarolar murojatlari bilan ishlash bo'lim boshlig'i", "👥 Xodimlar bo'lim boshlig'i", "🛡 Korrupsiya qarshi bo'lim boshlig'i",
        "🌍 Xalqaro aloqalar bo'lim boshlig'i", "🛠 Xo'jalik ishlari bo'lim boshlig'i", "📊 Ta’lim jarayonini tashkil etish bo‘limi boshlig'i",
        "🗂 Registrator ofisi bo'lim boshlig'i",
        "🎨 San'at va sport fakulteti dekani", "📐 Aniq fanlar va muhandislik fakulteti dekani", "📖 Boshlang‘ich va texnologik ta’lim fakulteti dekani",
        "🌿 Tabiiy fanlar va iqtisodiyot fakulteti dekani", "🗣 Gumanitar fanlar va tillar fakultetida dekani", "🧠 Pedagogika va psixologiya fakulteti dekani",
        "🎓 Professor", "🏅 Dotsent", "🎖 Professor v.b.", "🏅 Dotsent v.b.", "📖 Katta o'qituvchi", "✍️ Assistent o'qituvchi", "📌 Stajyor o'qituvchi"
    ]

    if text in all_roles:
        selected_dept = context.user_data.get('selected_dept', "Rahbariyat")
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

    if distance > ALLOWED_DISTANCE:
        await update.message.reply_text(
            f"❌ Siz belgilangan chegaradan tashqaridasiz!\n"
            f"Siz turgan masofa: {dist_str}\n"
            f"Ruxsat etilgan maksimal masofa: 1000 metr. Lokatsiyangiz qabul qilmadi!"
        )
        return

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
    
    print("Bot ishga tushdi...")
    app.run_polling()
