import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
import sqlite3

API_TOKEN = '7686324441:AAEoHLF9dpgaSkgig-fxXcuY-mLrfWBZ3eE'
ADMIN_IDS = [7858376486]
MANDATORY_CHANNELS = []

bot = Bot(API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

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
        kb = InlineKeyboardBuilder()
        for channel in MANDATORY_CHANNELS:
            kb.add(InlineKeyboardButton(text='Rejoindre le canal', url=f'https://t.me/{channel.lstrip("@")}'))
        kb.add(InlineKeyboardButton(text='✅ Vérifier', callback_data='verify_sub'))
        await message.answer("🚩 Avant d'accéder au contenu, merci de rejoindre les canaux obligatoires.", reply_markup=kb.as_markup())

@dp.callback_query(F.data == 'verify_sub')
async def verify_sub(callback: types.CallbackQuery):
    if await is_user_subscribed(callback.from_user.id):
        cursor.execute('SELECT value FROM settings WHERE key = ?', ('welcome_message',))
        welcome_text = cursor.fetchone()[0]
        await callback.message.edit_text(welcome_text)
    else:
        await callback.answer('❌ Tu dois rejoindre tous les canaux obligatoires avant de continuer.', show_alert=True)

@dp.message(Command('settings'))
async def settings(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    kb = InlineKeyboardBuilder()
    kb.add(
        InlineKeyboardButton(text='➕ Ajouter un contenu', callback_data='add_content'),
        InlineKeyboardButton(text='📜 Liste des contenus', callback_data='list_contents'),
        InlineKeyboardButton(text='📊 Statistiques', callback_data='stats'),
        InlineKeyboardButton(text='📢 Envoyer à tous', callback_data='broadcast'),
        InlineKeyboardButton(text='✏️ Modifier le message', callback_data='edit_message')
    )
    await message.answer('⚙️ Panneau admin : choisis une action.', reply_markup=kb.as_markup())

@dp.callback_query(F.data == 'add_content')
async def add_content(callback: types.CallbackQuery):
    await callback.message.answer('✏️ Envoie le texte ou la photo avec légende du contenu à ajouter :')

    @dp.message()
    async def save_content(message: types.Message):
        if message.photo:
            photo = await bot.download(message.photo[-1])
            photo_bytes = photo.read()
            cursor.execute('INSERT INTO contents (text, photo) VALUES (?, ?)', (message.caption or '', photo_bytes))
        else:
            cursor.execute('INSERT INTO contents (text) VALUES (?)', (message.text,))
        conn.commit()
        await message.answer('✅ Contenu ajouté avec succès.')
        dp.message.middleware.unregister(save_content)

@dp.callback_query(F.data == 'list_contents')
async def list_contents(callback: types.CallbackQuery):
    cursor.execute('SELECT id, text FROM contents')
    rows = cursor.fetchall()
    if rows:
        text = '\n'.join([f"{r[0]}: {r[1][:50]}..." for r in rows])
        await callback.message.answer(text)
    else:
        await callback.message.answer('Aucun contenu enregistré.')

@dp.callback_query(F.data == 'stats')
async def stats(callback: types.CallbackQuery):
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM contents')
    content_count = cursor.fetchone()[0]
    await callback.message.answer(f'📊 Statistiques :\n👥 Utilisateurs : {user_count}\n🗂️ Contenus : {content_count}')

@dp.callback_query(F.data == 'broadcast')
async def broadcast(callback: types.CallbackQuery):
    await callback.message.answer('📢 Envoie le message que tu souhaites envoyer à tous les utilisateurs :')

    @dp.message()
    async def send_broadcast(message: types.Message):
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
        for user in users:
            try:
                await bot.send_message(user[0], message.text)
            except:
                continue
        await message.answer('✅ Message envoyé à tous les utilisateurs.')
        dp.message.middleware.unregister(send_broadcast)

@dp.callback_query(F.data == 'edit_message')
async def edit_message(callback: types.CallbackQuery):
    await callback.message.answer('✏️ Envoie le nouveau texte d\'accueil souhaité :')

    @dp.message()
    async def update_welcome(message: types.Message):
        cursor.execute('UPDATE settings SET value = ? WHERE key = ?', (message.text, 'welcome_message'))
        conn.commit()
        await message.answer('✅ Message d\'accueil mis à jour.')
        dp.message.middleware.unregister(update_welcome)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
