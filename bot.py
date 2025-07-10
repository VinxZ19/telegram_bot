import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3

API_TOKEN = '7686324441:AAEoHLF9dpgaSkgig-fxXcuY-mLrfWBZ3eE'
ADMIN_IDS = [7858376486]

bot = Bot(API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

conn = sqlite3.connect('bot.db')
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
cursor.execute('CREATE TABLE IF NOT EXISTS contents (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT)')
cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('welcome_message', '✅ Bienvenue, tu as maintenant accès aux contenus.'))
conn.commit()

@dp.message(Command('start'))
async def start(message: types.Message):
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (message.from_user.id,))
    conn.commit()
    cursor.execute('SELECT value FROM settings WHERE key = ?', ('welcome_message',))
    welcome_text = cursor.fetchone()[0]
    await message.answer(welcome_text)

@dp.message(Command('settings'))
async def settings(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton(text='+ Ajouter un contenu', callback_data='add_content'),
            InlineKeyboardButton(text='📜 Liste des contenus', callback_data='list_contents'),
            InlineKeyboardButton(text='📊 Statistiques', callback_data='stats'),
            InlineKeyboardButton(text='📢 Envoyer à tous', callback_data='broadcast'),
            InlineKeyboardButton(text='✏️ Modifier le message', callback_data='edit_welcome'),
            InlineKeyboardButton(text='📣 Gérer les canaux obligatoires', callback_data='manage_channels'),
            InlineKeyboardButton(text='✅ Ajouter des canaux', callback_data='add_channel'),
            InlineKeyboardButton(text='💬 Voir le message', callback_data='view_message')
        )
        await message.answer('⚙️ PANNEAU DU BOT\nDepuis ce menu, vous pouvez gérer le bot.', reply_markup=keyboard)

@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    data = callback.data
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer('🚫 Non autorisé')
        return
    if data == 'add_content':
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
        cursor.execute('SELECT COUNT(*) FROM channels')
        channels = cursor.fetchone()[0]
        await callback.message.answer(f'📊 Statistiques :\n👥 Utilisateurs : {users}\n🗂️ Contenus : {contents}\n📣 Canaux obligatoires : {channels}')
    elif data == 'broadcast':
        await callback.message.answer('📢 Envoie le message à diffuser à tous les utilisateurs :')
    elif data == 'edit_welcome':
        await callback.message.answer('✏️ Envoie le nouveau message d\'accueil souhaité :')
    elif data == 'manage_channels':
        cursor.execute('SELECT id, username FROM channels')
        rows = cursor.fetchall()
        if rows:
            listing = '\n'.join([f"{r[0]}: {r[1]}" for r in rows])
            await callback.message.answer(f'📣 Canaux obligatoires :\n{listing}')
        else:
            await callback.message.answer('Aucun canal obligatoire enregistré.')
    elif data == 'add_channel':
        await callback.message.answer('✏️ Envoie le @username du canal à ajouter comme obligatoire :')
    elif data == 'view_message':
        cursor.execute('SELECT value FROM settings WHERE key = ?', ('welcome_message',))
        welcome_text = cursor.fetchone()[0]
        await callback.message.answer(f'💬 Message d\'accueil actuel :\n{welcome_text}')
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
