import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import sqlite3

API_TOKEN = '7686324441:AAEoHLF9dpgaSkgig-fxXcuY-mLrfWBZ3eE'
ADMIN_IDS = [7858376486]
MANDATORY_CHANNELS = []

bot = Bot(API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(bot)

conn = sqlite3.connect('bot.db')
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
cursor.execute('CREATE TABLE IF NOT EXISTS contents (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, photo BLOB)')
cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('welcome_message', '✅ Bienvenue, tu as maintenant accès aux contenus.'))
conn.commit()

async def is_user_subscribed(user_id):
    for channel in MANDATORY_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status == 'left':
                return False
        except:
            continue
    return True

@dp.message(Command('start'))
async def start(message: types.Message):
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (message.from_user.id,))
    conn.commit()
    if await is_user_subscribed(message.from_user.id):
        cursor.execute('SELECT value FROM settings WHERE key = ?', ('welcome_message',))
        welcome_text = cursor.fetchone()[0]
        await message.answer(welcome_text)
    else:
        kb = InlineKeyboardMarkup()
        for channel in MANDATORY_CHANNELS:
            kb.add(InlineKeyboardButton(text='Rejoindre le canal', url=f'https://t.me/{channel.lstrip("@")}'))
        kb.add(InlineKeyboardButton(text='✅ Vérifier', callback_data='verify_sub'))
        await message.answer("🚩 Avant d'accéder au contenu, merci de rejoindre les canaux obligatoires.", reply_markup=kb)

@dp.callback_query()
async def verify_sub(callback: types.CallbackQuery):
    data = callback.data
    if not data:
        await callback.answer()
        return
    if data == 'verify_sub':
        if await is_user_subscribed(callback.from_user.id):
            cursor.execute('SELECT value FROM settings WHERE key = ?', ('welcome_message',))
            welcome_text = cursor.fetchone()[0]
            await callback.message.edit_text(welcome_text)
        else:
            await callback.answer('❌ Tu dois rejoindre tous les canaux obligatoires avant de continuer.', show_alert=True)
    elif data == 'add_content':
        await callback.message.answer('✏️ Envoie le texte du contenu à ajouter :')
    elif data == 'list_contents':
        cursor.execute('SELECT id, text FROM contents')
        rows = cursor.fetchall()
        if rows:
            listing = '\n'.join([f"{r[0]}: {r[1][:50]}..." for r in rows])
            await callback.message.answer(listing)
        else:
            await callback.message.answer('Aucun contenu enregistré.')
    elif data == 'stats':
        cursor.execute('SELECT COUNT(*) FROM users')
        users = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM contents')
        contents = cursor.fetchone()[0]
        await callback.message.answer(f'📊 Statistiques :\n👥 Utilisateurs : {users}\n🗂️ Contenus : {contents}')
    elif data == 'broadcast':
        await callback.message.answer('📢 Envoie le message à diffuser à tous les utilisateurs :')
    elif data == 'edit_message':
        await callback.message.answer('✏️ Envoie le nouveau message d\'accueil souhaité :')

@dp.message(Command('settings'))
async def settings(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton(text='➕ Ajouter un contenu', callback_data='add_content'),
        InlineKeyboardButton(text='📜 Liste des contenus', callback_data='list_contents'),
        InlineKeyboardButton(text='📊 Statistiques', callback_data='stats'),
        InlineKeyboardButton(text='📢 Envoyer à tous', callback_data='broadcast'),
        InlineKeyboardButton(text='✏️ Modifier le message', callback_data='edit_message')
    )
    await message.answer('⚙️ Panneau admin : choisis une action.', reply_markup=kb)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
