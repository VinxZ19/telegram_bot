import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
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
cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('welcome_message', '✅ Bienvenue, tu as maintenant accès aux contenus.'))
conn.commit()

admin_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton('➕ Ajouter un contenu')],
    [KeyboardButton('📜 Liste des contenus')],
    [KeyboardButton('📊 Statistiques')],
    [KeyboardButton('📢 Envoyer à tous')],
    [KeyboardButton('✏️ Modifier le message')]
], resize_keyboard=True)

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
        await message.answer('⚙️ PANNEAU DU BOT\nDepuis ce menu, vous pouvez gérer le bot.', reply_markup=admin_kb)

@dp.message()
async def handle_buttons(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text
    if text == '➕ Ajouter un contenu':
        await message.answer('✏️ Envoie le texte du contenu à ajouter :')
        @dp.message()
        async def add_content(msg: types.Message):
            cursor.execute('INSERT INTO contents (text) VALUES (?)', (msg.text,))
            conn.commit()
            await msg.answer('✅ Contenu ajouté avec succès.')
    elif text == '📜 Liste des contenus':
        cursor.execute('SELECT id, text FROM contents')
        rows = cursor.fetchall()
        if rows:
            listing = '\n'.join([f"{r[0]}: {r[1][:50]}..." for r in rows])
            await message.answer(listing)
        else:
            await message.answer('Aucun contenu enregistré.')
    elif text == '📊 Statistiques':
        cursor.execute('SELECT COUNT(*) FROM users')
        users = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM contents')
        contents = cursor.fetchone()[0]
        await message.answer(f'📊 Statistiques :\n👥 Utilisateurs : {users}\n🗂️ Contenus : {contents}')
    elif text == '📢 Envoyer à tous':
        await message.answer('📢 Envoie le message à diffuser à tous les utilisateurs :')
        @dp.message()
        async def broadcast(msg: types.Message):
            cursor.execute('SELECT user_id FROM users')
            users = cursor.fetchall()
            for user in users:
                try:
                    await bot.send_message(user[0], msg.text)
                except:
                    continue
            await msg.answer('✅ Message envoyé à tous.')
    elif text == '✏️ Modifier le message':
        await message.answer('✏️ Envoie le nouveau message d\'accueil souhaité :')
        @dp.message()
        async def update_welcome(msg: types.Message):
            cursor.execute('UPDATE settings SET value = ? WHERE key = ?', (msg.text, 'welcome_message'))
            conn.commit()
            await msg.answer('✅ Message d\'accueil mis à jour.')

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

