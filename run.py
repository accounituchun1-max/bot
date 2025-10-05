import os
import asyncio
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, ChatPermissions, InputMediaPhoto, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# CONFIG
BOT_TOKEN = os.getenv("BOT_TOKEN", "your token")
ADMIN_ID = int(os.getenv("ADMIN_ID", "your id"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DATA_FILE = "channels.json"
LOG_FILE = "logs.txt"

# DATABASE
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return {int(k): v for k, v in json.load(f).items()}
        return {}
    except:
        return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

user_channels = load_data()

# STATES
class ChannelStates(StatesGroup):
    waiting_for_channel_id = State()
    waiting_for_new_title = State()
    waiting_for_new_description = State()
    waiting_for_message = State()
    waiting_for_photo = State()
    waiting_for_media_group = State()
    waiting_for_poll = State()
    waiting_for_ban_user = State()
    waiting_for_unban_user = State()
    waiting_for_restrict_user = State()
    waiting_for_promote_user = State()
    waiting_for_pin_message = State()
    waiting_for_chat_photo = State()

# LOG
def write_log(user_id, username, action, details=""):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {user_id} (@{username}) | {action} | {details}\n")
        asyncio.create_task(bot.send_message(ADMIN_ID, f"📋 {action}\n👤 {user_id}\n{details[:50]}"))
    except:
        pass

# KEYBOARDS
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton(text="📊 Kanallarim", callback_data="my_channels")],
        [InlineKeyboardButton(text="❓ Yordam", callback_data="help")]
    ])

def get_channel_list(user_id):
    kb = []
    if user_id in user_channels and user_channels[user_id]:
        for idx, ch in enumerate(user_channels[user_id]):
            emoji = "📢" if ch["type"] == "channel" else "👥"
            kb.append([InlineKeyboardButton(text=f"{emoji} {ch['name'][:25]}", callback_data=f"sel_{idx}")])
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_channel_menu(idx):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Ma'lumot", callback_data=f"info_{idx}"),
         InlineKeyboardButton(text="📤 Xabar", callback_data=f"send_{idx}")],
        [InlineKeyboardButton(text="✏️ Nom", callback_data=f"title_{idx}"),
         InlineKeyboardButton(text="📝 Tavsif", callback_data=f"desc_{idx}")],
        [InlineKeyboardButton(text="🖼 Rasm", callback_data=f"pic_{idx}"),
         InlineKeyboardButton(text="📌 Pin", callback_data=f"pin_{idx}")],
        [InlineKeyboardButton(text="👥 A'zolar", callback_data=f"mem_{idx}"),
         InlineKeyboardButton(text="🔗 Havola", callback_data=f"link_{idx}")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del_{idx}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="my_channels")]
    ])

def get_send_menu(idx):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Matn", callback_data=f"txt_{idx}"),
         InlineKeyboardButton(text="📸 Rasm", callback_data=f"pho_{idx}")],
        [InlineKeyboardButton(text="🖼 Media", callback_data=f"med_{idx}"),
         InlineKeyboardButton(text="📊 Poll", callback_data=f"pol_{idx}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"sel_{idx}")]
    ])

def get_member_menu(idx):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Ban", callback_data=f"ban_{idx}"),
         InlineKeyboardButton(text="✅ Unban", callback_data=f"unb_{idx}")],
        [InlineKeyboardButton(text="⚠️ Restrict", callback_data=f"res_{idx}"),
         InlineKeyboardButton(text="⭐️ Promote", callback_data=f"pro_{idx}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"sel_{idx}")]
    ])

def get_pin_menu(idx):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Pin", callback_data=f"dopin_{idx}"),
         InlineKeyboardButton(text="📍 Unpin", callback_data=f"unpin_{idx}")],
        [InlineKeyboardButton(text="🚫 Unpin All", callback_data=f"unpinall_{idx}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"sel_{idx}")]
    ])

def get_pic_menu(idx):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 O'rnatish", callback_data=f"setpic_{idx}"),
         InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delpic_{idx}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"sel_{idx}")]
    ])

def get_link_menu(idx):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Doimiy", callback_data=f"explink_{idx}"),
         InlineKeyboardButton(text="⏰ Cheklangan", callback_data=f"crtlink_{idx}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"sel_{idx}")]
    ])

# START
@dp.message(Command("start"))
async def start_cmd(msg: Message):
    write_log(msg.from_user.id, msg.from_user.username or "noname", "START", "")
    await msg.answer("🤖 <b>Telegram Kanal Bot</b>\n\nKanallaringizni boshqaring!", parse_mode="HTML", reply_markup=get_main_menu())

@dp.callback_query(F.data == "main")
async def main_cb(cb: CallbackQuery):
    await cb.message.edit_text("🤖 <b>Asosiy menyu</b>", parse_mode="HTML", reply_markup=get_main_menu())
    await cb.answer()

@dp.callback_query(F.data == "help")
async def help_cb(cb: CallbackQuery):
    await cb.message.edit_text("❓ <b>YORDAM</b>\n\n1. Kanal qo'shing\n2. Bot admin qiling\n3. Boshqaring!\n\n<b>Admin:</b> /stats /logs /backup", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="main")]]))
    await cb.answer()

# ADD CHANNEL
@dp.callback_query(F.data == "add_channel")
async def add_ch_cb(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("📝 <b>Kanal ID/username:</b>\n\n<code>-1001234567890</code>\n<code>@channel</code>", parse_mode="HTML")
    await state.set_state(ChannelStates.waiting_for_channel_id)
    await cb.answer()

@dp.message(ChannelStates.waiting_for_channel_id)
async def add_ch_proc(msg: Message, state: FSMContext):
    ch_id = msg.text.strip()
    try:
        chat = await bot.get_chat(chat_id=ch_id)
        bot_mem = await bot.get_chat_member(chat_id=chat.id, user_id=bot.id)
        if bot_mem.status not in ["administrator", "creator"]:
            await msg.answer("❌ Bot admin emas!", reply_markup=get_main_menu())
            await state.clear()
            return
        
        uid = msg.from_user.id
        if uid not in user_channels:
            user_channels[uid] = []
        
        if any(c["id"] == chat.id for c in user_channels[uid]):
            await msg.answer("⚠️ Allaqachon qo'shilgan!", reply_markup=get_main_menu())
            await state.clear()
            return
        
        user_channels[uid].append({"id": chat.id, "username": chat.username, "name": chat.title, "type": chat.type, "added": datetime.now().strftime("%Y-%m-%d %H:%M")})
        save_data(user_channels)
        write_log(uid, msg.from_user.username or "noname", "ADDED", chat.title)
        await msg.answer(f"✅ <b>Qo'shildi!</b>\n\n📢 {chat.title}\n🆔 <code>{chat.id}</code>", parse_mode="HTML", reply_markup=get_main_menu())
    except Exception as e:
        await msg.answer(f"❌ {str(e)[:100]}", reply_markup=get_main_menu())
    await state.clear()

# MY CHANNELS
@dp.callback_query(F.data == "my_channels")
async def my_ch_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    if uid not in user_channels or not user_channels[uid]:
        await cb.message.edit_text("📭 <b>Kanal yo'q!</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ Qo'shish", callback_data="add_channel")],[InlineKeyboardButton(text="🔙 Orqaga", callback_data="main")]]))
    else:
        await cb.message.edit_text(f"📊 <b>Kanallar ({len(user_channels[uid])} ta)</b>", parse_mode="HTML", reply_markup=get_channel_list(uid))
    await cb.answer()

@dp.callback_query(F.data.startswith("sel_"))
async def sel_ch_cb(cb: CallbackQuery):
    idx = int(cb.data.split("_")[1])
    uid = cb.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await cb.answer("❌ Topilmadi!", show_alert=True)
        return
    ch = user_channels[uid][idx]
    emoji = "📢" if ch["type"] == "channel" else "👥"
    await cb.message.edit_text(f"{emoji} <b>{ch['name']}</b>\n\n🆔 <code>{ch['id']}</code>\n📅 {ch['added']}", parse_mode="HTML", reply_markup=get_channel_menu(idx))
    await cb.answer()

@dp.callback_query(F.data.startswith("del_"))
async def del_ch_cb(cb: CallbackQuery):
    idx = int(cb.data.split("_")[1])
    uid = cb.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await cb.answer("❌ Topilmadi!", show_alert=True)
        return
    ch = user_channels[uid].pop(idx)
    save_data(user_channels)
    write_log(uid, cb.from_user.username or "noname", "DELETED", ch['name'])
    await cb.message.edit_text(f"✅ <b>O'chirildi!</b>\n\n📢 {ch['name']}", parse_mode="HTML", reply_markup=get_main_menu())
    await cb.answer()

@dp.callback_query(F.data.startswith("info_"))
async def info_cb(cb: CallbackQuery):
    idx = int(cb.data.split("_")[1])
    uid = cb.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await cb.answer("❌ Topilmadi!", show_alert=True)
        return
    ch = user_channels[uid][idx]
    try:
        chat = await bot.get_chat(chat_id=ch["id"])
        count = await bot.get_chat_member_count(chat_id=ch["id"])
        await cb.message.edit_text(f"📊 <b>Ma'lumot</b>\n\n📝 {chat.title}\n🆔 <code>{chat.id}</code>\n📖 {chat.description or 'Yo`q'}\n👤 @{chat.username or 'Yo`q'}\n👥 {count:,}", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"sel_{idx}")]]))
    except Exception as e:
        await cb.answer(f"❌ {str(e)[:50]}", show_alert=True)
    await cb.answer()

# TITLE
@dp.callback_query(F.data.startswith("title_"))
async def title_cb(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split("_")[1])
    await state.update_data(idx=idx)
    await state.set_state(ChannelStates.waiting_for_new_title)
    await cb.message.edit_text("✏️ <b>Yangi nom:</b>", parse_mode="HTML")
    await cb.answer()

@dp.message(ChannelStates.waiting_for_new_title)
async def title_proc(msg: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("idx")
    uid = msg.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await msg.answer("❌ Topilmadi!", reply_markup=get_main_menu())
        await state.clear()
        return
    ch = user_channels[uid][idx]
    try:
        await bot.set_chat_title(chat_id=ch["id"], title=msg.text.strip())
        user_channels[uid][idx]["name"] = msg.text.strip()
        save_data(user_channels)
        write_log(uid, msg.from_user.username or "noname", "TITLE", msg.text.strip())
        await msg.answer("✅ <b>Nom o'zgartirildi!</b>", parse_mode="HTML", reply_markup=get_main_menu())
    except Exception as e:
        await msg.answer(f"❌ {str(e)[:100]}", reply_markup=get_main_menu())
    await state.clear()

# DESCRIPTION
@dp.callback_query(F.data.startswith("desc_"))
async def desc_cb(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split("_")[1])
    await state.update_data(idx=idx)
    await state.set_state(ChannelStates.waiting_for_new_description)
    await cb.message.edit_text("📝 <b>Yangi tavsif:</b>", parse_mode="HTML")
    await cb.answer()

@dp.message(ChannelStates.waiting_for_new_description)
async def desc_proc(msg: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("idx")
    uid = msg.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await msg.answer("❌ Topilmadi!", reply_markup=get_main_menu())
        await state.clear()
        return
    ch = user_channels[uid][idx]
    try:
        await bot.set_chat_description(chat_id=ch["id"], description=msg.text.strip())
        write_log(uid, msg.from_user.username or "noname", "DESC", ch['name'])
        await msg.answer("✅ <b>Tavsif o'zgartirildi!</b>", parse_mode="HTML", reply_markup=get_main_menu())
    except Exception as e:
        await msg.answer(f"❌ {str(e)[:100]}", reply_markup=get_main_menu())
    await state.clear()

# SEND MENU
@dp.callback_query(F.data.startswith("send_"))
async def send_cb(cb: CallbackQuery):
    idx = int(cb.data.split("_")[1])
    await cb.message.edit_text("📤 <b>Xabar yuborish</b>", parse_mode="HTML", reply_markup=get_send_menu(idx))
    await cb.answer()

@dp.callback_query(F.data.startswith("txt_"))
async def txt_cb(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split("_")[1])
    await state.update_data(idx=idx)
    await state.set_state(ChannelStates.waiting_for_message)
    await cb.message.edit_text("💬 <b>Matn yuboring:</b>", parse_mode="HTML")
    await cb.answer()

@dp.message(ChannelStates.waiting_for_message)
async def txt_proc(msg: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("idx")
    uid = msg.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await msg.answer("❌ Topilmadi!", reply_markup=get_main_menu())
        await state.clear()
        return
    ch = user_channels[uid][idx]
    try:
        await bot.send_message(chat_id=ch["id"], text=msg.text, parse_mode="HTML")
        write_log(uid, msg.from_user.username or "noname", "MSG_SENT", ch['name'])
        await msg.answer("✅ <b>Yuborildi!</b>", parse_mode="HTML", reply_markup=get_main_menu())
    except Exception as e:
        await msg.answer(f"❌ {str(e)[:100]}", reply_markup=get_main_menu())
    await state.clear()

@dp.callback_query(F.data.startswith("pho_"))
async def pho_cb(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split("_")[1])
    await state.update_data(idx=idx)
    await state.set_state(ChannelStates.waiting_for_photo)
    await cb.message.edit_text("📸 <b>Rasm yuboring:</b>", parse_mode="HTML")
    await cb.answer()

@dp.message(ChannelStates.waiting_for_photo, F.photo)
async def pho_proc(msg: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("idx")
    uid = msg.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await msg.answer("❌ Topilmadi!", reply_markup=get_main_menu())
        await state.clear()
        return
    ch = user_channels[uid][idx]
    try:
        await bot.send_photo(chat_id=ch["id"], photo=msg.photo[-1].file_id, caption=msg.caption, parse_mode="HTML")
        write_log(uid, msg.from_user.username or "noname", "PHOTO_SENT", ch['name'])
        await msg.answer("✅ <b>Yuborildi!</b>", parse_mode="HTML", reply_markup=get_main_menu())
    except Exception as e:
        await msg.answer(f"❌ {str(e)[:100]}", reply_markup=get_main_menu())
    await state.clear()

@dp.callback_query(F.data.startswith("med_"))
async def med_cb(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split("_")[1])
    await state.update_data(idx=idx, media=[])
    await state.set_state(ChannelStates.waiting_for_media_group)
    await cb.message.edit_text("🖼 <b>Rasmlar yuboring</b>\n\n/done - tugadi", parse_mode="HTML")
    await cb.answer()

@dp.message(ChannelStates.waiting_for_media_group, F.photo)
async def med_collect(msg: Message, state: FSMContext):
    data = await state.get_data()
    media = data.get("media", [])
    media.append({"file_id": msg.photo[-1].file_id, "caption": msg.caption})
    await state.update_data(media=media)
    await msg.answer(f"✅ {len(media)} ta\n\n/done")

@dp.message(ChannelStates.waiting_for_media_group, Command("done"))
async def med_done(msg: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("idx")
    media = data.get("media", [])
    uid = msg.from_user.id
    if not media or len(media) < 2:
        await msg.answer("❌ Kamida 2 ta!", reply_markup=get_main_menu())
        return
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await msg.answer("❌ Topilmadi!", reply_markup=get_main_menu())
        await state.clear()
        return
    ch = user_channels[uid][idx]
    try:
        group = []
        for i, m in enumerate(media):
            if i == 0:
                group.append(InputMediaPhoto(media=m["file_id"], caption=m["caption"]))
            else:
                group.append(InputMediaPhoto(media=m["file_id"]))
        await bot.send_media_group(chat_id=ch["id"], media=group)
        write_log(uid, msg.from_user.username or "noname", "MEDIA_SENT", f"{len(media)} photos")
        await msg.answer(f"✅ <b>Yuborildi!</b>\n\n🖼 {len(media)} ta", parse_mode="HTML", reply_markup=get_main_menu())
    except Exception as e:
        await msg.answer(f"❌ {str(e)[:100]}", reply_markup=get_main_menu())
    await state.clear()

@dp.callback_query(F.data.startswith("pol_"))
async def pol_cb(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split("_")[1])
    await state.update_data(idx=idx)
    await state.set_state(ChannelStates.waiting_for_poll)
    await cb.message.edit_text("📊 <b>Format:</b>\n\nSavol\nVariant1\nVariant2", parse_mode="HTML")
    await cb.answer()

@dp.message(ChannelStates.waiting_for_poll)
async def pol_proc(msg: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("idx")
    uid = msg.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await msg.answer("❌ Topilmadi!", reply_markup=get_main_menu())
        await state.clear()
        return
    lines = msg.text.strip().split("\n")
    if len(lines) < 3:
        await msg.answer("❌ Kamida savol va 2 variant!", reply_markup=get_main_menu())
        return
    ch = user_channels[uid][idx]
    try:
        await bot.send_poll(chat_id=ch["id"], question=lines[0], options=[l.strip() for l in lines[1:] if l.strip()], is_anonymous=True)
        write_log(uid, msg.from_user.username or "noname", "POLL_SENT", ch['name'])
        await msg.answer("✅ <b>Yuborildi!</b>", parse_mode="HTML", reply_markup=get_main_menu())
    except Exception as e:
        await msg.answer(f"❌ {str(e)[:100]}", reply_markup=get_main_menu())
    await state.clear()

# PICTURE
@dp.callback_query(F.data.startswith("pic_"))
async def pic_cb(cb: CallbackQuery):
    idx = int(cb.data.split("_")[1])
    await cb.message.edit_text("🖼 <b>Kanal rasmi</b>", parse_mode="HTML", reply_markup=get_pic_menu(idx))
    await cb.answer()

@dp.callback_query(F.data.startswith("setpic_"))
async def setpic_cb(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split("_")[1])
    await state.update_data(idx=idx)
    await state.set_state(ChannelStates.waiting_for_chat_photo)
    await cb.message.edit_text("🖼 <b>Rasm yuboring:</b>", parse_mode="HTML")
    await cb.answer()

@dp.message(ChannelStates.waiting_for_chat_photo, F.photo)
async def setpic_proc(msg: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("idx")
    uid = msg.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await msg.answer("❌ Topilmadi!", reply_markup=get_main_menu())
        await state.clear()
        return
    ch = user_channels[uid][idx]
    path = f"temp_{uid}.jpg"
    try:
        file = await bot.get_file(msg.photo[-1].file_id)
        await bot.download_file(file.file_path, path)
        with open(path, 'rb') as photo:
            await bot.set_chat_photo(chat_id=ch["id"], photo=photo)
        if os.path.exists(path):
            os.remove(path)
        write_log(uid, msg.from_user.username or "noname", "PIC_SET", ch['name'])
        await msg.answer("✅ <b>O'rnatildi!</b>", parse_mode="HTML", reply_markup=get_main_menu())
    except Exception as e:
        await msg.answer(f"❌ {str(e)[:100]}", reply_markup=get_main_menu())
        if os.path.exists(path):
            os.remove(path)
    await state.clear()

@dp.callback_query(F.data.startswith("delpic_"))
async def delpic_cb(cb: CallbackQuery):
    idx = int(cb.data.split("_")[1])
    uid = cb.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await cb.answer("❌ Topilmadi!", show_alert=True)
        return
    ch = user_channels[uid][idx]
    try:
        await bot.delete_chat_photo(chat_id=ch["id"])
        write_log(uid, cb.from_user.username or "noname", "PIC_DEL", ch['name'])
        await cb.message.edit_text("✅ <b>O'chirildi!</b>", parse_mode="HTML", reply_markup=get_main_menu())
    except Exception as e:
        await cb.answer(f"❌ {str(e)[:50]}", show_alert=True)
    await cb.answer()

# PIN
@dp.callback_query(F.data.startswith("pin_"))
async def pin_cb(cb: CallbackQuery):
    idx = int(cb.data.split("_")[1])
    await cb.message.edit_text("📌 <b>Pin</b>", parse_mode="HTML", reply_markup=get_pin_menu(idx))
    await cb.answer()

@dp.callback_query(F.data.startswith("dopin_"))
async def dopin_cb(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split("_")[1])
    await state.update_data(idx=idx)
    await state.set_state(ChannelStates.waiting_for_pin_message)
    await cb.message.edit_text("📌 <b>Xabar ID:</b>", parse_mode="HTML")
    await cb.answer()

@dp.message(ChannelStates.waiting_for_pin_message)
async def dopin_proc(msg: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("idx")
    uid = msg.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await msg.answer("❌ Topilmadi!", reply_markup=get_main_menu())
        await state.clear()
        return
    ch = user_channels[uid][idx]
    try:
        msg_id = int(msg.text.strip())
        await bot.pin_chat_message(chat_id=ch["id"], message_id=msg_id)
        write_log(uid, msg.from_user.username or "noname", "PINNED", f"ID: {msg_id}")
        await msg.answer("✅ <b>Pin qilindi!</b>", parse_mode="HTML", reply_markup=get_main_menu())
    except ValueError:
        await msg.answer("❌ Faqat raqam!", reply_markup=get_main_menu())
    except Exception as e:
        await msg.answer(f"❌ {str(e)[:100]}", reply_markup=get_main_menu())
    await state.clear()

@dp.callback_query(F.data.startswith("unpin_"))
async def unpin_cb(cb: CallbackQuery):
    idx = int(cb.data.split("_")[1])
    uid = cb.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await cb.answer("❌ Topilmadi!", show_alert=True)
        return
    ch = user_channels[uid][idx]
    try:
        await bot.unpin_chat_message(chat_id=ch["id"])
        write_log(uid, cb.from_user.username or "noname", "UNPINNED", ch['name'])
        await cb.message.edit_text("✅ <b>Unpin!</b>", parse_mode="HTML", reply_markup=get_main_menu())
    except Exception as e:
        await cb.answer(f"❌ {str(e)[:50]}", show_alert=True)
    await cb.answer()

@dp.callback_query(F.data.startswith("unpinall_"))
async def unpinall_cb(cb: CallbackQuery):
    idx = int(cb.data.split("_")[1])
    uid = cb.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await cb.answer("❌ Topilmadi!", show_alert=True)
        return
    ch = user_channels[uid][idx]
    try:
        await bot.unpin_all_chat_messages(chat_id=ch["id"])
        write_log(uid, cb.from_user.username or "noname", "UNPINNED_ALL", ch['name'])
        await cb.message.edit_text("✅ <b>Hammasi unpin!</b>", parse_mode="HTML", reply_markup=get_main_menu())
    except Exception as e:
        await cb.answer(f"❌ {str(e)[:50]}", show_alert=True)
    await cb.answer()

# MEMBERS
@dp.callback_query(F.data.startswith("mem_"))
async def mem_cb(cb: CallbackQuery):
    idx = int(cb.data.split("_")[1])
    await cb.message.edit_text("👥 <b>A'zolar</b>", parse_mode="HTML", reply_markup=get_member_menu(idx))
    await cb.answer()

@dp.callback_query(F.data.startswith("ban_"))
async def ban_cb(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split("_")[1])
    await state.update_data(idx=idx)
    await state.set_state(ChannelStates.waiting_for_ban_user)
    await cb.message.edit_text("🚫 <b>User ID:</b>", parse_mode="HTML")
    await cb.answer()

@dp.message(ChannelStates.waiting_for_ban_user)
async def ban_proc(msg: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("idx")
    uid = msg.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await msg.answer("❌ Topilmadi!", reply_markup=get_main_menu())
        await state.clear()
        return
    ch = user_channels[uid][idx]
    try:
        ban_uid = int(msg.text.strip())
        await bot.ban_chat_member(chat_id=ch["id"], user_id=ban_uid)
        write_log(uid, msg.from_user.username or "noname", "BANNED", f"User: {ban_uid}")
        await msg.answer(f"✅ <b>Ban!</b>\n\n👤 {ban_uid}", parse_mode="HTML", reply_markup=get_main_menu())
    except ValueError:
        await msg.answer("❌ Faqat raqam!", reply_markup=get_main_menu())
    except Exception as e:
        await msg.answer(f"❌ {str(e)[:100]}", reply_markup=get_main_menu())
    await state.clear()

@dp.callback_query(F.data.startswith("unb_"))
async def unb_cb(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split("_")[1])
    await state.update_data(idx=idx)
    await state.set_state(ChannelStates.waiting_for_unban_user)
    await cb.message.edit_text("✅ <b>User ID:</b>", parse_mode="HTML")
    await cb.answer()

@dp.message(ChannelStates.waiting_for_unban_user)
async def unb_proc(msg: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("idx")
    uid = msg.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await msg.answer("❌ Topilmadi!", reply_markup=get_main_menu())
        await state.clear()
        return
    ch = user_channels[uid][idx]
    try:
        unban_uid = int(msg.text.strip())
        await bot.unban_chat_member(chat_id=ch["id"], user_id=unban_uid)
        write_log(uid, msg.from_user.username or "noname", "UNBANNED", f"User: {unban_uid}")
        await msg.answer(f"✅ <b>Unban!</b>\n\n👤 {unban_uid}", parse_mode="HTML", reply_markup=get_main_menu())
    except ValueError:
        await msg.answer("❌ Faqat raqam!", reply_markup=get_main_menu())
    except Exception as e:
        await msg.answer(f"❌ {str(e)[:100]}", reply_markup=get_main_menu())
    await state.clear()

@dp.callback_query(F.data.startswith("res_"))
async def res_cb(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split("_")[1])
    await state.update_data(idx=idx)
    await state.set_state(ChannelStates.waiting_for_restrict_user)
    await cb.message.edit_text("⚠️ <b>User ID:</b>", parse_mode="HTML")
    await cb.answer()

@dp.message(ChannelStates.waiting_for_restrict_user)
async def res_proc(msg: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("idx")
    uid = msg.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await msg.answer("❌ Topilmadi!", reply_markup=get_main_menu())
        await state.clear()
        return
    ch = user_channels[uid][idx]
    try:
        res_uid = int(msg.text.strip())
        perms = ChatPermissions(can_send_messages=False, can_send_media_messages=False, can_send_polls=False)
        await bot.restrict_chat_member(chat_id=ch["id"], user_id=res_uid, permissions=perms, until_date=datetime.now() + timedelta(days=365))
        write_log(uid, msg.from_user.username or "noname", "RESTRICTED", f"User: {res_uid}")
        await msg.answer(f"✅ <b>Restrict!</b>\n\n👤 {res_uid}", parse_mode="HTML", reply_markup=get_main_menu())
    except ValueError:
        await msg.answer("❌ Faqat raqam!", reply_markup=get_main_menu())
    except Exception as e:
        await msg.answer(f"❌ {str(e)[:100]}", reply_markup=get_main_menu())
    await state.clear()

@dp.callback_query(F.data.startswith("pro_"))
async def pro_cb(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split("_")[1])
    await state.update_data(idx=idx)
    await state.set_state(ChannelStates.waiting_for_promote_user)
    await cb.message.edit_text("⭐️ <b>User ID:</b>", parse_mode="HTML")
    await cb.answer()

@dp.message(ChannelStates.waiting_for_promote_user)
async def pro_proc(msg: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("idx")
    uid = msg.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await msg.answer("❌ Topilmadi!", reply_markup=get_main_menu())
        await state.clear()
        return
    ch = user_channels[uid][idx]
    try:
        pro_uid = int(msg.text.strip())
        await bot.promote_chat_member(chat_id=ch["id"], user_id=pro_uid, can_manage_chat=True, can_post_messages=True, can_edit_messages=True, can_delete_messages=True, can_restrict_members=True, can_promote_members=False, can_change_info=True, can_invite_users=True, can_pin_messages=True)
        write_log(uid, msg.from_user.username or "noname", "PROMOTED", f"User: {pro_uid}")
        await msg.answer(f"✅ <b>Admin!</b>\n\n👤 {pro_uid}", parse_mode="HTML", reply_markup=get_main_menu())
    except ValueError:
        await msg.answer("❌ Faqat raqam!", reply_markup=get_main_menu())
    except Exception as e:
        await msg.answer(f"❌ {str(e)[:100]}", reply_markup=get_main_menu())
    await state.clear()

# LINKS
@dp.callback_query(F.data.startswith("link_"))
async def link_cb(cb: CallbackQuery):
    idx = int(cb.data.split("_")[1])
    await cb.message.edit_text("🔗 <b>Havolalar</b>", parse_mode="HTML", reply_markup=get_link_menu(idx))
    await cb.answer()

@dp.callback_query(F.data.startswith("explink_"))
async def explink_cb(cb: CallbackQuery):
    idx = int(cb.data.split("_")[1])
    uid = cb.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await cb.answer("❌ Topilmadi!", show_alert=True)
        return
    ch = user_channels[uid][idx]
    try:
        link = await bot.export_chat_invite_link(chat_id=ch["id"])
        write_log(uid, cb.from_user.username or "noname", "LINK_EXPORTED", ch['name'])
        await cb.message.edit_text(f"🔗 <b>Doimiy havola:</b>\n\n{link}", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="main")]]))
    except Exception as e:
        await cb.answer(f"❌ {str(e)[:50]}", show_alert=True)
    await cb.answer()

@dp.callback_query(F.data.startswith("crtlink_"))
async def crtlink_cb(cb: CallbackQuery):
    idx = int(cb.data.split("_")[1])
    uid = cb.from_user.id
    if uid not in user_channels or idx >= len(user_channels[uid]):
        await cb.answer("❌ Topilmadi!", show_alert=True)
        return
    ch = user_channels[uid][idx]
    try:
        link = await bot.create_chat_invite_link(chat_id=ch["id"], expire_date=datetime.now() + timedelta(days=1), member_limit=100)
        write_log(uid, cb.from_user.username or "noname", "LINK_CREATED", ch['name'])
        await cb.message.edit_text(f"⏰ <b>Cheklangan:</b>\n\n{link.invite_link}\n\n⏰ 24h | 👥 100", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="main")]]))
    except Exception as e:
        await cb.answer(f"❌ {str(e)[:50]}", show_alert=True)
    await cb.answer()

# ADMIN
@dp.message(Command("stats"))
async def stats_cmd(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    total_users = len(user_channels)
    total_channels = sum(len(ch) for ch in user_channels.values())
    await msg.answer(f"📊 <b>STATISTIKA</b>\n\n👥 Users: {total_users}\n📢 Channels: {total_channels}", parse_mode="HTML")

@dp.message(Command("logs"))
async def logs_cmd(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        if os.path.exists(LOG_FILE):
            await msg.answer_document(FSInputFile(LOG_FILE), caption="📋 <b>Logs</b>", parse_mode="HTML")
        else:
            await msg.answer("❌ Yo'q")
    except Exception as e:
        await msg.answer(f"❌ {e}")

@dp.message(Command("backup"))
async def backup_cmd(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        if os.path.exists(DATA_FILE):
            await msg.answer_document(FSInputFile(DATA_FILE), caption="💾 <b>Backup</b>", parse_mode="HTML")
        else:
            await msg.answer("❌ Yo'q")
    except Exception as e:
        await msg.answer(f"❌ {e}")

@dp.message()
async def unknown_msg(msg: Message):
    await msg.answer("❓ /start", reply_markup=get_main_menu())

# MAIN
async def on_startup():
    print("="*40)
    print("🚀 BOT ISHGA TUSHDI!")
    print(f"📊 Users: {len(user_channels)}")
    print("="*40)
    try:
        await bot.send_message(ADMIN_ID, f"✅ <b>Bot ishga tushdi!</b>\n\n📊 {len(user_channels)} users", parse_mode="HTML")
    except:
        pass

async def on_shutdown():
    print("\n🛑 To'xtatildi!")
    save_data(user_channels)
    try:
        await bot.send_message(ADMIN_ID, "🛑 <b>Bot to'xtatildi!</b>", parse_mode="HTML")
    except:
        pass

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Ctrl+C")
    except Exception as e:
        print(f"\n❌ {e}")
