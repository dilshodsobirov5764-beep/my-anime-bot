import os
from aiohttp import web

# Render portini ushlab turish uchun kichik server
async def handle(request):
    return web.Response(text="Bot ishlamoqda!")

async def start_background_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
import os
from supabase import create_client, Client

# Supabase ulanish ma'lumotlari
SUPABASE_URL = "https://onidxepfxwiujzsoglat.supabase.co"
SUPABASE_KEY = "sb_publishable_sgJ_UJj9iCxZIMTZWnCKGw_bDgZqSFu"

# Bazaga ulanish
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
)

TOKEN = "8986765239:AAFwBeAhl9Byxr8_cRiTL9T2vdWVVJEaHFk"
ADMIN_ID = 6625248174  # O'zingizning ID raqamingiz

# Baza yaratish
conn = sqlite3.connect("anime_database.db")
cursor = conn.cursor()

# Epizodlar jadvali
cursor.execute("""
    CREATE TABLE IF NOT EXISTS anime_episodes (
        anime_code TEXT,
        episode INTEGER,
        file_id TEXT,
        PRIMARY KEY (anime_code, episode)
    )
""")

# Anime ma'lumotlari jadvali (title — anime nomi qo'shildi)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS anime_info (
        anime_code TEXT PRIMARY KEY,
        title TEXT,
        photo_id TEXT,
        year TEXT,
        ep_count TEXT,
        lang TEXT
    )
""")
conn.commit()

dp = Dispatcher()

# Bosh menyu
def get_main_menu():
    kb = [
        [KeyboardButton(text="🔍 Anime qidirish"), KeyboardButton(text="🔢 Kodi orqali qidirish")],
        [KeyboardButton(text="🤝 Reklama va hamkorlik")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(CommandStart())
async def command_start_handler(message: Message):
    await message.answer(
        f"Salom, <b>{html.quote(message.from_user.full_name)}</b>!\n\n"
        f"Botimizga xush kelibsiz! Anime <b>nomini</b> yoki <b>kodini</b> yuboring:",
        reply_markup=get_main_menu()
    )

@dp.message(F.text.contains("Reklama va hamkorlik"))
async def ad_info(message: Message):
    await message.answer(
        "🤝 <b>Reklama va Hamkorlik bo'yicha:</b>\n\n"
        "Kanalingiz yoki mahsulotingizni botimizda reklama qilmoqchi bo'lsangiz adminga bog'laning:\n\n"
        "📩 Admin: @admin_profil"
    )

@dp.message(F.text.contains("Anime qidirish"))
@dp.message(F.text.contains("Kodi orqali qidirish"))
async def ask_for_code(message: Message):
    await message.answer("Sizga kerakli **Anime nomini** yoki **kodini** yozib yuboring (Masalan: <code>Nana</code> yoki <code>1</code>):")

# ADMIN: Anime posteri, nomi va ma'lumotlarini qo'shish
# Format: 1 rasm 2024 12 Uzbek | Qobiliyatsiz Nana
@dp.message(F.photo)
async def add_anime_info(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    if not message.caption or "|" not in message.caption:
        await message.answer("⚠️ Izohga shaklni yozing:\n<code>kod rasm yil qismlar tili | Anime Nomi</code>\n\n<b>Masalan:</b> <code>1 rasm 2024 12 Uzbek | Qobiliyatsiz Nana</code>")
        return

    main_part, title = message.caption.strip().split("|")
    title = title.strip()
    
    parts = main_part.strip().split()
    if len(parts) < 5 or parts[1] != "rasm":
        await message.answer("⚠️ Izoh formati xato! Masalan: <code>1 rasm 2024 12 Uzbek | Qobiliyatsiz Nana</code>")
        return

    anime_code, _, year, ep_count, lang = parts[0], parts[1], parts[2], parts[3], " ".join(parts[4:])
    photo_id = message.photo[-1].file_id

    cursor.execute("INSERT OR REPLACE INTO anime_info VALUES (?, ?, ?, ?, ?, ?)",
                   (anime_code, title, photo_id, year, ep_count, lang))
    conn.commit()

    await message.answer(f"✅ <b>Anime ma'lumotlari saqlandi!</b>\n🎬 <b>Nomi:</b> {title}\nKodi: <code>{anime_code}</code>\nYili: {year}\nQismlar: {ep_count}")

# ADMIN: Video va qism qo'shish (Format: 1 1)
@dp.message(F.video | F.document)
async def add_episode(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    if not message.caption:
        await message.answer("⚠️ Izohga <code>anime_kodi qism_raqami</code> yozing (Masalan: <code>1 1</code>)!")
        return

    parts = message.caption.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("⚠️ Izohni to'g'ri yozing: <code>1 1</code>")
        return

    anime_code = parts[0]
    episode = int(parts[1])
    file_id = message.video.file_id if message.video else message.document.file_id

    cursor.execute("INSERT OR REPLACE INTO anime_episodes VALUES (?, ?, ?)",
                   (anime_code, episode, file_id))
    conn.commit()

    await message.answer(f"✅ <b>{episode}-qism saqlandi!</b> (Anime kodi: <code>{anime_code}</code>)")

# FOYDALANUVCHILAR: Kod yoki Nom bo'yicha qidiruv
@dp.message(F.text)
async def search_anime(message: Message):
    query = message.text.strip()

    # Avval kodi bo'yicha yoki nomi bo'yicha qidiramiz
    cursor.execute("""
        SELECT anime_code, title, photo_id, year, ep_count, lang 
        FROM anime_info 
        WHERE anime_code = ? OR title LIKE ?
    """, (query, f"%{query}%"))
    
    info = cursor.fetchone()

    if info:
        code, title, photo_id, year, ep_count, lang = info
        
        # Qismlarni olish
        cursor.execute("SELECT episode FROM anime_episodes WHERE anime_code = ? ORDER BY episode ASC", (code,))
        episodes = cursor.fetchall()

        if episodes:
            keyboard = []
            row = []
            for ep in episodes:
                ep_num = ep[0]
                row.append(InlineKeyboardButton(text=f"{ep_num}-qism", callback_data=f"play_{code}_{ep_num}"))
                if len(row) == 3:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)

            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            caption_text = (
                f"🎬 <b>Anime: {title}</b>\n"
                f"🔢 <b>Kodi:</b> <code>{code}</code>\n"
                f"📅 <b>Yili:</b> {year}\n"
                f"🎞 <b>Qismlar:</b> {ep_count}\n"
                f"🇺🇿 <b>Tili:</b> {lang}\n\n"
                f"👇 Ko'rmoqchi bo'lgan qismingizni tanlang:"
            )
            await message.answer_photo(photo=photo_id, caption=caption_text, reply_markup=markup)
        else:
            await message.answer(f"⚠️ <b>{title}</b> animesining ma'lumotlari bor, lekin hali qismlar yuklanmagan.")
    else:
        await message.answer("❌ Kechirasiz, bunday nomli yoki kodli anime topilmadi.")

# Qism bosilganda videoni navigatsiya bilan yuborish
@dp.callback_query(F.data.startswith("play_"))
async def send_episode_video(call: CallbackQuery):
    _, code, ep_num = call.data.split("_")
    ep_num = int(ep_num)
    
    cursor.execute("SELECT file_id FROM anime_episodes WHERE anime_code = ? AND episode = ?", (code, ep_num))
    result = cursor.fetchone()

    if result:
        file_id = result[0]
        await call.answer()

        nav_buttons = []
        
        # Oldingi qism
        cursor.execute("SELECT episode FROM anime_episodes WHERE anime_code = ? AND episode = ?", (code, ep_num - 1))
        if cursor.fetchone():
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"play_{code}_{ep_num - 1}"))

        # Qismlar ro'yxatiga qaytish
        nav_buttons.append(InlineKeyboardButton(text="📋 Qismlar", callback_data=f"list_{code}"))

        # Keyingi qism
        cursor.execute("SELECT episode FROM anime_episodes WHERE anime_code = ? AND episode = ?", (code, ep_num + 1))
        if cursor.fetchone():
            nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"play_{code}_{ep_num + 1}"))

        markup = InlineKeyboardMarkup(inline_keyboard=[nav_buttons])
        caption = f"🎬 <b>Anime kodi:</b> {code}\n🍿 <b>{ep_num}-qism</b>"

        try:
            await call.message.answer_video(video=file_id, caption=caption, reply_markup=markup)
        except Exception:
            await call.message.answer_document(document=file_id, caption=caption, reply_markup=markup)
    else:
        await call.answer("⚠️ Video topilmadi!", show_alert=True)

# "📋 Qismlar" tugmasi
@dp.callback_query(F.data.startswith("list_"))
async def back_to_list(call: CallbackQuery):
    code = call.data.split("_")[1]
    
    cursor.execute("SELECT episode FROM anime_episodes WHERE anime_code = ? ORDER BY episode ASC", (code,))
    episodes = cursor.fetchall()

    if episodes:
        keyboard = []
        row = []
        for ep in episodes:
            ep_num = ep[0]
            row.append(InlineKeyboardButton(text=f"{ep_num}-qism", callback_data=f"play_{code}_{ep_num}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await call.message.answer(f"🎬 <b>Anime kodi: {code}</b>\n\nQismni tanlang:", reply_markup=markup)
        await call.answer()

async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(start_background_web_server())
    print("Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
