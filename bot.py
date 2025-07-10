import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import sqlite3
import random
import string

API_TOKEN = '7686324441:AAEoHLF9dpgaSkgig-fxXcuY-mLrfWBZ3eE'  # Ton token intégré ici
ADMIN_IDS = [7858376486]

bot = Bot(API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(bot)

conn = sqlite3.connect('bot.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, is_active INTEGER DEFAULT 1)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS contents (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, message TEXT, slug TEXT UNIQUE)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS mandatory_channels (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS stats (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT, user_id INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

add_content_state = {}
edit_content_state = {}

@dp.message(Command('start'))
async def start(message: types.Message):
    user_id = message.from_user.id
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()

    args = message.text.split()
    if len(args) > 1:
        slug = args[1]
        cursor.execute('SELECT message FROM contents WHERE slug = ?', (slug,))
        result = cursor.fetchone()
        if result:
            cursor.execute('SELECT username FROM mandatory_channels')
            channels = cursor.fetchall()
            not_joined = []
            for ch in channels:
                try:
                    member = await bot.get_chat_member(ch[0], user_id)
                    if member.status == 'left':
                        not_joined.append(ch[0])
                except:
                    continue
            if not_joined:
                kb = InlineKeyboardMarkup()
                for ch in not_joined:
                    kb.add(InlineKeyboardButton(f"Rejoindre @{ch}", url=f"https://t.me/{ch}"))
                kb.add(InlineKeyboardButton("✅ J'ai rejoint", callback_data=f'check_join_{slug}'))
                await message.answer("🚩 Pour débloquer le contenu, rejoins les canaux obligatoires:", reply_markup=kb)
                return
            cursor.execute('INSERT INTO stats (slug, user_id) VALUES (?, ?)', (slug, user_id))
            conn.commit()
            await message.answer(result[0])
            return
    await message.answer("✅ Bienvenue sur le bot.")

@dp.callback_query(F.data.startswith('check_join_'))
async def check_join(callback: types.CallbackQuery):
    slug = callback.data.split('check_join_')[1]
    user_id = callback.from_user.id
    cursor.execute('SELECT username FROM mandatory_channels')
    channels = cursor.fetchall()
    not_joined = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch[0], user_id)
            if member.status == 'left':
                not_joined.append(ch[0])
        except:
            continue
    if not_joined:
        await callback.answer("❌ Tu dois rejoindre tous les canaux obligatoires.", show_alert=True)
    else:
        cursor.execute('SELECT message FROM contents WHERE slug = ?', (slug,))
        result = cursor.fetchone()
        if result:
            cursor.execute('INSERT INTO stats (slug, user_id) VALUES (?, ?)', (slug, user_id))
            conn.commit()
            await callback.message.answer(result[0])
        await callback.answer()

@dp.message(Command('settings'))
async def settings(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("➕ Ajouter un contenu", callback_data='add_content')],
        [InlineKeyboardButton("📜 Liste des contenus", callback_data='list_contents')],
        [InlineKeyboardButton("📊 Statistiques", callback_data='stats')],
        [InlineKeyboardButton("📢 Gérer canaux obligatoires", callback_data='manage_channels')]
    ])
    await message.answer("⚙️ PANNEAU DU BOT\nDepuis ce menu, vous pouvez gérer le bot.", reply_markup=kb)

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id

    if data == 'add_content':
        add_content_state[user_id] = {'step': 'name'}
        await callback.message.answer("✏️ Envoie le nom du contenu :")

    elif data == 'list_contents':
        cursor.execute('SELECT id, name FROM contents')
        rows = cursor.fetchall()
        kb = InlineKeyboardMarkup()
        for r in rows:
            kb.add(InlineKeyboardButton(r[1], callback_data=f'content_{r[0]}'))
        await callback.message.answer("📜 Liste des contenus :", reply_markup=kb)

    elif data.startswith('content_'):
        content_id = int(data.split('_')[1])
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("👁️ Voir le message", callback_data=f'view_{content_id}')],
            [InlineKeyboardButton("✏️ Modifier le message", callback_data=f'edit_{content_id}')],
            [InlineKeyboardButton("🔗 Copier le lien /start", callback_data=f'link_{content_id}')]
        ])
        await callback.message.answer("Que souhaites-tu faire avec ce contenu ?", reply_markup=kb)

    elif data.startswith('view_'):
        content_id = int(data.split('_')[1])
        cursor.execute('SELECT message FROM contents WHERE id = ?', (content_id,))
        row = cursor.fetchone()
        if row:
            await callback.message.answer(row[0])

    elif data.startswith('edit_'):
        content_id = int(data.split('_')[1])
        edit_content_state[user_id] = content_id
        await callback.message.answer("✏️ Envoie le nouveau message pour ce contenu :")

    elif data.startswith('link_'):
        content_id = int(data.split('_')[1])
        cursor.execute('SELECT slug FROM contents WHERE id = ?', (content_id,))
        row = cursor.fetchone()
        if row:
            await callback.message.answer(f"🔗 Lien de partage : https://t.me/{(await bot.get_me()).username}?start={row[0]}")

    elif data == 'stats':
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
        active = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 0')
        inactive = cursor.fetchone()[0]
        cursor.execute('SELECT slug, COUNT(*) FROM stats GROUP BY slug')
        stats = cursor.fetchall()
        text = f"📊 Statistiques :\nActifs : {active}\nInactifs : {inactive}\n\n"
        for s in stats:
            text += f"/start {s[0]} : {s[1]} vues\n"
        await callback.message.answer(text)

    elif data == 'manage_channels':
        await callback.message.answer("(Gestion des canaux à coder selon ta stratégie de gestion des admins)")

    await callback.answer()

@dp.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id in add_content_state:
        state = add_content_state[user_id]
        if state['step'] == 'name':
            state['name'] = text
            state['step'] = 'message'
            await message.answer("✏️ Envoie maintenant le message de ce contenu :")
        elif state['step'] == 'message':
            slug = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            cursor.execute('INSERT INTO contents (name, message, slug) VALUES (?, ?, ?)', (state['name'], text, slug))
            conn.commit()
            await message.answer(f"✅ Contenu ajouté avec succès. Lien de partage : https://t.me/{(await bot.get_me()).username}?start={slug}")
            del add_content_state[user_id]

    elif user_id in edit_content_state:
        content_id = edit_content_state[user_id]
        cursor.execute('UPDATE contents SET message = ? WHERE id = ?', (text, content_id))
        conn.commit()
        await message.answer("✅ Contenu mis à jour avec succès.")
        del edit_content_state[user_id]

async def main():
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())
