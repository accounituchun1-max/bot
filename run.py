import os
import asyncio
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from typing import Optional
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, ChatPermissions, InputMediaPhoto, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== KONFIGURATSIYA ====================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1029657375"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

DATA_FILE = "user_channels.json"
LOG_FILE = "bot_logs.txt"

# ==================== MA'LUMOTLAR BAZASI ====================

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        return {}
    except:
        return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Saqlashda xatolik: {e}")

user_channels = load_data()

# ==================== STATE'LAR ====================

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
    waiting_for_unpin_message = State()

# ==================== LOG TIZIMI ====================

def write_log(user_id, username, action, details=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] User: {user_id} (@{username}) | Action: {action} | Details: {details}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except:
        pass
    # Send logs only to admin, never to end users
    asyncio.create_task(send_log_to_admin(user_id, username, action, details))

async def send_log_to_admin(user_id, username, action, details):
    try:
        log_msg = f"📋 <b>LOG</b>\n\n👤 {user_id} (@{username})\n⚡ {action}\n📝 {details}"
        await bot.send_message(ADMIN_ID, log_msg, parse_mode="HTML")
    except:
        pass

# ==================== UTILITIES ====================

DEFAULT_ERROR_TEXT = "❌ Xatolik yuz berdi. Keyinroq urinib ko'ring."

async def edit_or_send_message(chat_id: int, fallback_message: types.Message, text: str, *,
                               message_id: Optional[int] = None,
                               reply_markup: Optional[InlineKeyboardMarkup] = None,
                               parse_mode: Optional[str] = "HTML"):
    """
    Try to edit an existing bot message. If not possible, send a new message.
    """
    try:
        if message_id is not None:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text,
                                        reply_markup=reply_markup, parse_mode=parse_mode)
            return
    except Exception:
        # Fallback to sending a new message below
        pass
    await fallback_message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

# ==================== KEYBOARD FUNKSIYALARI ====================

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton(text="📊 Mening kanallarim", callback_data="my_channels")],
        [InlineKeyboardButton(text="📋 Ma'lumot", callback_data="menu_info"),
         InlineKeyboardButton(text="⚙️ Boshqarish", callback_data="menu_manage")],
        [InlineKeyboardButton(text="📤 Xabar yuborish", callback_data="menu_send"),
         InlineKeyboardButton(text="👥 A'zolar", callback_data="menu_members")],
        [InlineKeyboardButton(text="🔗 Havolalar", callback_data="menu_links")]
    ])

def get_channel_list_keyboard(user_id):
    keyboard = []
    if user_id in user_channels and user_channels[user_id]:
        for idx, channel in enumerate(user_channels[user_id]):
            emoji = "📢" if channel["type"] == "channel" else "👥"
            keyboard.append([InlineKeyboardButton(text=f"{emoji} {channel['name'][:30]}", callback_data=f"select_{idx}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_channel_actions_keyboard(idx):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Ma'lumot", callback_data=f"info_{idx}")],
        [InlineKeyboardButton(text="✏️ Nom", callback_data=f"title_{idx}"),
         InlineKeyboardButton(text="📝 Tavsif", callback_data=f"desc_{idx}")],
        [InlineKeyboardButton(text="📤 Xabar", callback_data=f"msg_{idx}"),
         InlineKeyboardButton(text="🖼 Rasm", callback_data=f"photo_{idx}")],
        [InlineKeyboardButton(text="📌 Pin", callback_data=f"pin_{idx}"),
         InlineKeyboardButton(text="👥 A'zolar", callback_data=f"members_{idx}")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delete_{idx}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="my_channels")]
    ])

def get_info_menu(idx):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Kanal ma'lumoti", callback_data=f"getchat_{idx}")],
        [InlineKeyboardButton(text="👤 Adminlar", callback_data=f"getadmins_{idx}")],
        [InlineKeyboardButton(text="📊 A'zolar soni", callback_data=f"getcount_{idx}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"select_{idx}")]
    ])

def get_manage_menu(idx):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 Rasm o'rnatish", callback_data=f"setphoto_{idx}")],
        [InlineKeyboardButton(text="🗑 Rasmni o'chirish", callback_data=f"delphoto_{idx}")],
        [InlineKeyboardButton(text="📌 Pin", callback_data=f"dopin_{idx}"),
         InlineKeyboardButton(text="📍 Unpin", callback_data=f"unpin_{idx}")],
        [InlineKeyboardButton(text="🚫 Unpin all", callback_data=f"unpinall_{idx}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"select_{idx}")]
    ])

def get_send_menu(idx):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Matn", callback_data=f"sendtext_{idx}")],
        [InlineKeyboardButton(text="📸 Rasm", callback_data=f"sendphoto_{idx}")],
        [InlineKeyboardButton(text="🖼 Media", callback_data=f"sendmedia_{idx}")],
        [InlineKeyboardButton(text="📊 Poll", callback_data=f"sendpoll_{idx}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"select_{idx}")]
    ])

def get_members_menu(idx):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Ban", callback_data=f"ban_{idx}")],
        [InlineKeyboardButton(text="✅ Unban", callback_data=f"unban_{idx}")],
        [InlineKeyboardButton(text="⚠️ Restrict", callback_data=f"restrict_{idx}")],
        [InlineKeyboardButton(text="⭐️ Promote", callback_data=f"promote_{idx}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"select_{idx}")]
    ])

def get_links_menu(idx):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Doimiy havola", callback_data=f"exportlink_{idx}")],
        [InlineKeyboardButton(text="⏰ Cheklangan", callback_data=f"createlink_{idx}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"select_{idx}")]
    ])

# ==================== START ====================

@dp.message(Command("start"))
async def start_handler(message: Message):
    write_log(message.from_user.id, message.from_user.username, "START", "Bot started")
    await message.answer(
        "🤖 <b>Telegram Kanal Boshqaruv Boti</b>\n\n"
        "Kanallaringizni to'liq boshqaring!\n\n"
        "Boshlash uchun kanal qo'shing 👇",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

# ==================== KANAL QO'SHISH ====================

@dp.callback_query(F.data == "add_channel")
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    await state.update_data(prompt_message_id=callback.message.message_id)
    await callback.message.edit_text(
        "📝 <b>Kanal ID'sini yuboring:</b>\n\n"
        "• <code>-1001234567890</code>\n"
        "• <code>@username</code>\n\n"
        "⚠️ Bot admin bo'lishi kerak!",
        parse_mode="HTML"
    )
    await state.set_state(ChannelStates.waiting_for_channel_id)
    await callback.answer()

@dp.message(ChannelStates.waiting_for_channel_id)
async def process_channel_id(message: Message, state: FSMContext):
    channel_id = message.text.strip()
    try:
        chat = await bot.get_chat(chat_id=channel_id)
        bot_member = await bot.get_chat_member(chat_id=chat.id, user_id=bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            data = await state.get_data()
            await edit_or_send_message(
                message.chat.id,
                message,
                "❌ Bot kanal/guruhda admin emas!",
                message_id=data.get("prompt_message_id"),
                reply_markup=get_main_menu()
            )
            await state.clear()
            return
        
        user_id = message.from_user.id
        if user_id not in user_channels:
            user_channels[user_id] = []
        
        if any(ch["id"] == chat.id for ch in user_channels[user_id]):
            data = await state.get_data()
            await edit_or_send_message(
                message.chat.id,
                message,
                "⚠️ Bu kanal/guruh allaqachon qo'shilgan!",
                message_id=data.get("prompt_message_id"),
                reply_markup=get_main_menu()
            )
            await state.clear()
            return
        
        channel_data = {
            "id": chat.id,
            "username": chat.username,
            "name": chat.title,
            "type": chat.type,
            "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        user_channels[user_id].append(channel_data)
        save_data(user_channels)
        write_log(user_id, message.from_user.username, "CHANNEL_ADDED", f"{chat.title}")
        
        data = await state.get_data()
        await edit_or_send_message(
            message.chat.id,
            message,
            f"✅ <b>Qo'shildi!</b>\n\n📢 {chat.title}\n🆔 <code>{chat.id}</code>",
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    except Exception:
        data = await state.get_data()
        await edit_or_send_message(
            message.chat.id,
            message,
            DEFAULT_ERROR_TEXT,
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    await state.clear()

@dp.callback_query(F.data == "my_channels")
async def show_my_channels(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_channels or not user_channels[user_id]:
        await callback.message.edit_text(
            "📭 <b>Kanal yo'q!</b>\n\nAvval kanal qo'shing.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Qo'shish", callback_data="add_channel")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")]
            ])
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"📊 <b>Kanallaringiz ({len(user_channels[user_id])} ta):</b>\n\nTanlang 👇",
        parse_mode="HTML",
        reply_markup=get_channel_list_keyboard(user_id)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("select_"))
async def select_channel(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await callback.answer("❌ Kanal topilmadi!", show_alert=True)
        return
    
    channel = user_channels[user_id][idx]
    emoji = "📢" if channel["type"] == "channel" else "👥"
    
    await callback.message.edit_text(
        f"{emoji} <b>{channel['name']}</b>\n\n"
        f"🆔 <code>{channel['id']}</code>\n"
        f"📊 {channel['type']}\n"
        f"📅 {channel['added_date']}\n\n"
        "Amalni tanlang 👇",
        parse_mode="HTML",
        reply_markup=get_channel_actions_keyboard(idx)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("delete_"))
async def delete_channel(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await callback.answer("❌ Topilmadi!", show_alert=True)
        return
    
    channel = user_channels[user_id][idx]
    write_log(user_id, callback.from_user.username, "DELETED", channel['name'])
    user_channels[user_id].pop(idx)
    save_data(user_channels)
    
    await callback.message.edit_text(
        f"✅ <b>O'chirildi!</b>\n\n📢 {channel['name']}",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )
    await callback.answer()

# ==================== NOM/TAVSIF O'ZGARTIRISH ====================

@dp.callback_query(F.data.startswith("title_"))
async def change_title_start(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    await state.update_data(channel_idx=idx, prompt_message_id=callback.message.message_id)
    await state.set_state(ChannelStates.waiting_for_new_title)
    await callback.message.edit_text("✏️ <b>Yangi nomni yuboring:</b>", parse_mode="HTML")
    await callback.answer()

@dp.message(ChannelStates.waiting_for_new_title)
async def process_new_title(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("channel_idx")
    user_id = message.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await message.answer("❌ Topilmadi!")
        await state.clear()
        return
    
    channel = user_channels[user_id][idx]
    new_title = message.text.strip()
    try:
        await bot.set_chat_title(chat_id=channel["id"], title=new_title)
        old_title = channel["name"]
        user_channels[user_id][idx]["name"] = new_title
        save_data(user_channels)
        write_log(user_id, message.from_user.username, "TITLE_CHANGED", f"{old_title} -> {new_title}")
        await edit_or_send_message(
            message.chat.id,
            message,
            f"✅ <b>Nom o'zgartirildi!</b>\n\n📢 Yangi: {new_title}",
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    except Exception:
        await edit_or_send_message(
            message.chat.id,
            message,
            DEFAULT_ERROR_TEXT,
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    await state.clear()

# ==================== RASM BOSHQARISH ====================

@dp.callback_query(F.data.startswith("photo_"))
async def show_photo_menu(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    await callback.message.edit_text("🖼 <b>Rasm boshqarish</b>", parse_mode="HTML", reply_markup=get_manage_menu(idx))
    await callback.answer()

@dp.callback_query(F.data.startswith("setphoto_"))
async def set_photo_start(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    await state.update_data(channel_idx=idx, prompt_message_id=callback.message.message_id)
    await state.set_state(ChannelStates.waiting_for_chat_photo)
    await callback.message.edit_text("🖼 <b>Yangi rasm yuboring:</b>", parse_mode="HTML")
    await callback.answer()

@dp.message(ChannelStates.waiting_for_chat_photo, F.photo)
async def process_set_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("channel_idx")
    user_id = message.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await message.answer("❌ Topilmadi!")
        await state.clear()
        return
    
    channel = user_channels[user_id][idx]
    try:
        file = await bot.get_file(message.photo[-1].file_id)
        photo_path = f"temp_{user_id}.jpg"
        # Download to local path
        try:
            await bot.download_file(file.file_path, photo_path)
        except Exception:
            # aiogram v3 alternative
            await bot.download(file, destination=photo_path)

        await bot.set_chat_photo(chat_id=channel["id"], photo=FSInputFile(photo_path))

        if os.path.exists(photo_path):
            os.remove(photo_path)
        write_log(user_id, message.from_user.username, "PHOTO_SET", channel['name'])
        data = await state.get_data()
        await edit_or_send_message(
            message.chat.id,
            message,
            f"✅ <b>Rasm o'rnatildi!</b>\n\n📢 {channel['name']}",
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    except Exception:
        if os.path.exists(f"temp_{user_id}.jpg"):
            os.remove(f"temp_{user_id}.jpg")
        data = await state.get_data()
        await edit_or_send_message(
            message.chat.id,
            message,
            DEFAULT_ERROR_TEXT,
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    await state.clear()

@dp.callback_query(F.data.startswith("delphoto_"))
async def delete_photo(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await callback.answer("❌ Topilmadi!", show_alert=True)
        return
    
    channel = user_channels[user_id][idx]
    try:
        await bot.delete_chat_photo(chat_id=channel["id"])
        write_log(user_id, callback.from_user.username, "PHOTO_DELETED", channel['name'])
        await callback.message.edit_text(f"✅ <b>Rasm o'chirildi!</b>\n\n📢 {channel['name']}", parse_mode="HTML", reply_markup=get_main_menu())
        await callback.answer("✅")
    except Exception:
        await callback.answer("❌ Xatolik", show_alert=True)

# ==================== PIN/UNPIN ====================

@dp.callback_query(F.data.startswith("pin_"))
async def show_pin_menu(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    await callback.message.edit_text("📌 <b>Pin</b>", parse_mode="HTML", reply_markup=get_manage_menu(idx))
    await callback.answer()

@dp.callback_query(F.data.startswith("dopin_"))
async def pin_message_start(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    await state.update_data(channel_idx=idx, prompt_message_id=callback.message.message_id)
    await state.set_state(ChannelStates.waiting_for_pin_message)
    await callback.message.edit_text("📌 <b>Pin qilinadigan xabar ID'sini yuboring:</b>", parse_mode="HTML")
    await callback.answer()

@dp.message(ChannelStates.waiting_for_pin_message)
async def process_pin_message(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("channel_idx")
    user_id = message.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await message.answer("❌ Topilmadi!")
        await state.clear()
        return
    
    channel = user_channels[user_id][idx]
    try:
        message_id = int(message.text.strip())
        await bot.pin_chat_message(chat_id=channel["id"], message_id=message_id)
        write_log(user_id, message.from_user.username, "PINNED", f"ID: {message_id}")
        await edit_or_send_message(
            message.chat.id,
            message,
            f"✅ <b>Pin qilindi!</b>\n\n📢 {channel['name']}",
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    except ValueError:
        await edit_or_send_message(
            message.chat.id,
            message,
            "❌ Faqat raqam yuboring!",
            message_id=data.get("prompt_message_id")
        )
    except Exception:
        await edit_or_send_message(
            message.chat.id,
            message,
            DEFAULT_ERROR_TEXT,
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    await state.clear()

@dp.callback_query(F.data.startswith("unpin_"))
async def unpin_message_start(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await callback.answer("❌ Topilmadi!", show_alert=True)
        return
    
    # Ask for message ID to unpin
    await state.update_data(channel_idx=idx, prompt_message_id=callback.message.message_id)
    await state.set_state(ChannelStates.waiting_for_unpin_message)
    await callback.message.edit_text("📍 <b>Unpin qilinadigan xabar ID'sini yuboring:</b>", parse_mode="HTML")
    await callback.answer()

@dp.message(ChannelStates.waiting_for_unpin_message)
async def process_unpin_message(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("channel_idx")
    user_id = message.from_user.id
    
    if user_id not in user_channels or idx is None or idx >= len(user_channels[user_id]):
        await message.answer("❌ Topilmadi!")
        await state.clear()
        return
    
    channel = user_channels[user_id][idx]
    try:
        message_id = int(message.text.strip())
        await bot.unpin_chat_message(chat_id=channel["id"], message_id=message_id)
        write_log(user_id, message.from_user.username, "UNPINNED", f"ID: {message_id}")
        await edit_or_send_message(
            message.chat.id,
            message,
            f"✅ <b>Unpin bajarildi!</b>\n\n📢 {channel['name']}",
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    except ValueError:
        await edit_or_send_message(
            message.chat.id,
            message,
            "❌ Faqat raqam yuboring!",
            message_id=data.get("prompt_message_id")
        )
    except Exception:
        await edit_or_send_message(
            message.chat.id,
            message,
            DEFAULT_ERROR_TEXT,
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    await state.clear()

@dp.callback_query(F.data.startswith("unpinall_"))
async def unpin_all_messages(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await callback.answer("❌ Topilmadi!", show_alert=True)
        return
    
    channel = user_channels[user_id][idx]
    try:
        await bot.unpin_all_chat_messages(chat_id=channel["id"])
        write_log(user_id, callback.from_user.username, "UNPINNED_ALL", channel['name'])
        await callback.message.edit_text(f"✅ <b>Barcha pinlar olib tashlandi!</b>\n\n📢 {channel['name']}", parse_mode="HTML", reply_markup=get_main_menu())
        await callback.answer("✅")
    except Exception:
        await callback.answer("❌ Xatolik", show_alert=True)

@dp.callback_query(F.data.startswith("desc_"))
async def change_desc_start(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    await state.update_data(channel_idx=idx, prompt_message_id=callback.message.message_id)
    await state.set_state(ChannelStates.waiting_for_new_description)
    await callback.message.edit_text("📝 <b>Yangi tavsifni yuboring:</b>", parse_mode="HTML")
    await callback.answer()

@dp.message(ChannelStates.waiting_for_new_description)
async def process_new_description(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("channel_idx")
    user_id = message.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await message.answer("❌ Topilmadi!")
        await state.clear()
        return
    
    channel = user_channels[user_id][idx]
    try:
        await bot.set_chat_description(chat_id=channel["id"], description=message.text.strip())
        write_log(user_id, message.from_user.username, "DESC_CHANGED", channel['name'])
        await edit_or_send_message(
            message.chat.id,
            message,
            f"✅ <b>Tavsif o'zgartirildi!</b>\n\n📢 {channel['name']}",
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    except Exception:
        await edit_or_send_message(
            message.chat.id,
            message,
            DEFAULT_ERROR_TEXT,
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    await state.clear()

# ==================== MA'LUMOT ====================

@dp.callback_query(F.data.startswith("info_"))
async def show_info_menu_handler(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    await callback.message.edit_text("📊 <b>Ma'lumot</b>", parse_mode="HTML", reply_markup=get_info_menu(idx))
    await callback.answer()

@dp.callback_query(F.data.startswith("getchat_"))
async def get_chat_info(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await callback.answer("❌ Topilmadi!", show_alert=True)
        return
    
    channel = user_channels[user_id][idx]
    try:
        chat = await bot.get_chat(chat_id=channel["id"])
        info = (
            "📊 <b>Ma'lumot:</b>\n\n"
            f"🆔 <code>{chat.id}</code>\n"
            f"📝 {chat.title}\n"
            f"📖 {chat.description or 'Yo\`q'}\n"
            f"👤 @{chat.username or 'Yo\`q'}"
        )
        await callback.message.edit_text(info, parse_mode="HTML", reply_markup=get_info_menu(idx))
        await callback.answer("✅")
    except Exception:
        await callback.answer("❌ Xatolik", show_alert=True)

@dp.callback_query(F.data.startswith("getadmins_"))
async def get_admins(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await callback.answer("❌ Topilmadi!", show_alert=True)
        return
    
    channel = user_channels[user_id][idx]
    try:
        admins = await bot.get_chat_administrators(chat_id=channel["id"])
        admin_list = "👥 <b>Adminlar:</b>\n\n"
        for admin in admins:
            status = "👑" if getattr(admin, 'status', '') == "creator" else "🛡"
            username = f"@{admin.user.username}" if admin.user.username else "Yo'q"
            admin_list += f"{status} {admin.user.full_name} ({username})\n"
        await callback.message.edit_text(admin_list, parse_mode="HTML", reply_markup=get_info_menu(idx))
        await callback.answer("✅")
    except Exception:
        await callback.answer("❌ Xatolik", show_alert=True)

@dp.callback_query(F.data.startswith("getcount_"))
async def get_member_count(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await callback.answer("❌ Topilmadi!", show_alert=True)
        return
    
    channel = user_channels[user_id][idx]
    try:
        count = await bot.get_chat_member_count(chat_id=channel["id"])
        await callback.message.edit_text(f"👥 <b>A'zolar:</b> {count:,}", parse_mode="HTML", reply_markup=get_info_menu(idx))
        await callback.answer("✅")
    except Exception:
        await callback.answer("❌ Xatolik", show_alert=True)

# ==================== XABAR YUBORISH ====================

@dp.callback_query(F.data.startswith("msg_"))
async def show_send_menu_handler(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    await callback.message.edit_text("📤 <b>Xabar yuborish</b>", parse_mode="HTML", reply_markup=get_send_menu(idx))
    await callback.answer()

@dp.callback_query(F.data.startswith("sendtext_"))
async def send_text_start(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    await state.update_data(channel_idx=idx, prompt_message_id=callback.message.message_id)
    await state.set_state(ChannelStates.waiting_for_message)
    await callback.message.edit_text("💬 <b>Yuboriladigan matnni yuboring:</b>", parse_mode="HTML")
    await callback.answer()

@dp.message(ChannelStates.waiting_for_message)
async def process_send_message(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("channel_idx")
    user_id = message.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await message.answer("❌ Topilmadi!")
        await state.clear()
        return
    
    channel = user_channels[user_id][idx]
    try:
        await bot.send_message(chat_id=channel["id"], text=message.text, parse_mode="HTML")
        write_log(user_id, message.from_user.username, "MESSAGE_SENT", channel['name'])
        await edit_or_send_message(
            message.chat.id,
            message,
            f"✅ <b>Yuborildi!</b>\n\n📢 {channel['name']}",
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    except Exception:
        await edit_or_send_message(
            message.chat.id,
            message,
            DEFAULT_ERROR_TEXT,
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    await state.clear()

@dp.callback_query(F.data.startswith("sendphoto_"))
async def send_photo_start(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    await state.update_data(channel_idx=idx, prompt_message_id=callback.message.message_id)
    await state.set_state(ChannelStates.waiting_for_photo)
    await callback.message.edit_text("📸 <b>Rasm yuboring (caption ixtiyoriy):</b>", parse_mode="HTML")
    await callback.answer()

@dp.message(ChannelStates.waiting_for_photo, F.photo)
async def process_send_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("channel_idx")
    user_id = message.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await message.answer("❌ Topilmadi!")
        await state.clear()
        return
    
    channel = user_channels[user_id][idx]
    try:
        await bot.send_photo(chat_id=channel["id"], photo=message.photo[-1].file_id, caption=message.caption, parse_mode="HTML")
        write_log(user_id, message.from_user.username, "PHOTO_SENT", channel['name'])
        await edit_or_send_message(
            message.chat.id,
            message,
            f"✅ <b>Rasm yuborildi!</b>\n\n📢 {channel['name']}",
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    except Exception:
        await edit_or_send_message(
            message.chat.id,
            message,
            DEFAULT_ERROR_TEXT,
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    await state.clear()

@dp.callback_query(F.data.startswith("sendmedia_"))
async def send_media_group_start(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    await state.update_data(channel_idx=idx, media_list=[], prompt_message_id=callback.message.message_id)
    await state.set_state(ChannelStates.waiting_for_media_group)
    await callback.message.edit_text("🖼 <b>Rasmlarni yuboring (2-10 ta)</b>\n\n/done - Yuborish", parse_mode="HTML")
    await callback.answer()

@dp.message(ChannelStates.waiting_for_media_group, F.photo)
async def collect_media(message: Message, state: FSMContext):
    data = await state.get_data()
    media_list = data.get("media_list", [])
    media_list.append({"file_id": message.photo[-1].file_id, "caption": message.caption})
    await state.update_data(media_list=media_list)

@dp.message(ChannelStates.waiting_for_media_group, Command("done"))
async def send_media_group(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("channel_idx")
    media_list = data.get("media_list", [])
    user_id = message.from_user.id
    
    if not media_list or len(media_list) < 2:
        await message.answer("❌ Kamida 2 ta rasm kerak!")
        return
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await message.answer("❌ Topilmadi!")
        await state.clear()
        return
    
    channel = user_channels[user_id][idx]
    try:
        media_group = []
        for i, media in enumerate(media_list):
            if i == 0:
                media_group.append(InputMediaPhoto(media=media["file_id"], caption=media["caption"]))
            else:
                media_group.append(InputMediaPhoto(media=media["file_id"]))

        await bot.send_media_group(chat_id=channel["id"], media=media_group)
        write_log(user_id, message.from_user.username, "MEDIA_SENT", f"{len(media_list)} photos")
        await edit_or_send_message(
            message.chat.id,
            message,
            f"✅ <b>Yuborildi!</b>\n\n📢 {channel['name']}\n🖼 {len(media_list)} ta",
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    except Exception:
        await edit_or_send_message(
            message.chat.id,
            message,
            DEFAULT_ERROR_TEXT,
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    await state.clear()

@dp.callback_query(F.data.startswith("sendpoll_"))
async def send_poll_start(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    await state.update_data(channel_idx=idx, prompt_message_id=callback.message.message_id)
    await state.set_state(ChannelStates.waiting_for_poll)
    await callback.message.edit_text("📊 <b>So'rovnoma yuboring</b>:\n\nSavol\nVariant 1\nVariant 2", parse_mode="HTML")
    await callback.answer()

@dp.message(ChannelStates.waiting_for_poll)
async def process_send_poll(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("channel_idx")
    user_id = message.from_user.id
    if user_id not in user_channels or idx is None or idx >= len(user_channels[user_id]):
        await state.clear()
        await message.answer("❌ Topilmadi!")
        return
    channel = user_channels[user_id][idx]
    lines = message.text.strip().split("\n")
    if len(lines) < 3:
        await edit_or_send_message(
            message.chat.id,
            message,
            "❌ Kamida savol va 2 ta variant yuboring!",
            message_id=data.get("prompt_message_id")
        )
        return
    question = lines[0]
    options = [line.strip() for line in lines[1:] if line.strip()]
    if len(options) < 2:
        await edit_or_send_message(
            message.chat.id,
            message,
            "❌ Kamida 2 ta variant kerak!",
            message_id=data.get("prompt_message_id")
        )
        return
    try:
        await bot.send_poll(chat_id=channel["id"], question=question, options=options, is_anonymous=True)
        write_log(user_id, message.from_user.username, "POLL_SENT", channel['name'])
        await edit_or_send_message(
            message.chat.id,
            message,
            f"✅ <b>So'rovnoma yuborildi!</b>\n\n📢 {channel['name']}",
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    except Exception:
        await edit_or_send_message(
            message.chat.id,
            message,
            DEFAULT_ERROR_TEXT,
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    await state.clear()

# ==================== A'ZOLAR BOSHQARUVI ====================

@dp.callback_query(F.data.startswith("members_"))
async def show_members_menu_handler(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    await callback.message.edit_text("👥 <b>A'zolar</b>", parse_mode="HTML", reply_markup=get_members_menu(idx))
    await callback.answer()

@dp.callback_query(F.data.startswith("ban_"))
async def ban_user_start(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    await state.update_data(channel_idx=idx, prompt_message_id=callback.message.message_id)
    await state.set_state(ChannelStates.waiting_for_ban_user)
    await callback.message.edit_text("🚫 <b>Ban uchun User ID yuboring:</b>", parse_mode="HTML")
    await callback.answer()

@dp.message(ChannelStates.waiting_for_ban_user)
async def process_ban_user(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("channel_idx")
    user_id = message.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await message.answer("❌ Topilmadi!")
        await state.clear()
        return
    
    channel = user_channels[user_id][idx]
    try:
        ban_user_id = int(message.text.strip())
        await bot.ban_chat_member(chat_id=channel["id"], user_id=ban_user_id)
        write_log(user_id, message.from_user.username, "BANNED", f"User: {ban_user_id}")
        await edit_or_send_message(
            message.chat.id,
            message,
            f"✅ <b>Ban qilindi!</b>\n\n📢 {channel['name']}\n👤 {ban_user_id}",
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    except ValueError:
        await edit_or_send_message(
            message.chat.id,
            message,
            "❌ Faqat raqam yuboring!",
            message_id=data.get("prompt_message_id")
        )
    except Exception:
        await edit_or_send_message(
            message.chat.id,
            message,
            DEFAULT_ERROR_TEXT,
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    await state.clear()

@dp.callback_query(F.data.startswith("unban_"))
async def unban_user_start(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    await state.update_data(channel_idx=idx, prompt_message_id=callback.message.message_id)
    await state.set_state(ChannelStates.waiting_for_unban_user)
    await callback.message.edit_text("✅ <b>Unban uchun User ID yuboring:</b>", parse_mode="HTML")
    await callback.answer()

@dp.message(ChannelStates.waiting_for_unban_user)
async def process_unban_user(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("channel_idx")
    user_id = message.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await message.answer("❌ Topilmadi!")
        await state.clear()
        return
    
    channel = user_channels[user_id][idx]
    try:
        unban_user_id = int(message.text.strip())
        await bot.unban_chat_member(chat_id=channel["id"], user_id=unban_user_id)
        write_log(user_id, message.from_user.username, "UNBANNED", f"User: {unban_user_id}")
        await edit_or_send_message(
            message.chat.id,
            message,
            f"✅ <b>Unban qilindi!</b>\n\n📢 {channel['name']}\n👤 {unban_user_id}",
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    except ValueError:
        await edit_or_send_message(
            message.chat.id,
            message,
            "❌ Faqat raqam yuboring!",
            message_id=data.get("prompt_message_id")
        )
    except Exception:
        await edit_or_send_message(
            message.chat.id,
            message,
            DEFAULT_ERROR_TEXT,
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    await state.clear()

@dp.callback_query(F.data.startswith("restrict_"))
async def restrict_user_start(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    await state.update_data(channel_idx=idx, prompt_message_id=callback.message.message_id)
    await state.set_state(ChannelStates.waiting_for_restrict_user)
    await callback.message.edit_text("⚠️ <b>Restrict uchun User ID yuboring:</b>", parse_mode="HTML")
    await callback.answer()

@dp.message(ChannelStates.waiting_for_restrict_user)
async def process_restrict_user(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("channel_idx")
    user_id = message.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await message.answer("❌ Topilmadi!")
        await state.clear()
        return
    
    channel = user_channels[user_id][idx]
    try:
        restrict_user_id = int(message.text.strip())
        permissions = ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False
        )
        until_ts = int((datetime.now() + timedelta(days=365)).timestamp())
        await bot.restrict_chat_member(chat_id=channel["id"], user_id=restrict_user_id, permissions=permissions, until_date=until_ts)
        write_log(user_id, message.from_user.username, "RESTRICTED", f"User: {restrict_user_id}")
        await edit_or_send_message(
            message.chat.id,
            message,
            f"✅ <b>Restrict qilindi!</b>\n\n📢 {channel['name']}\n👤 {restrict_user_id}",
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    except ValueError:
        await edit_or_send_message(
            message.chat.id,
            message,
            "❌ Faqat raqam yuboring!",
            message_id=data.get("prompt_message_id")
        )
    except Exception:
        await edit_or_send_message(
            message.chat.id,
            message,
            DEFAULT_ERROR_TEXT,
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    await state.clear()

@dp.callback_query(F.data.startswith("promote_"))
async def promote_user_start(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    await state.update_data(channel_idx=idx, prompt_message_id=callback.message.message_id)
    await state.set_state(ChannelStates.waiting_for_promote_user)
    await callback.message.edit_text("⭐️ <b>Admin qilish uchun User ID yuboring:</b>", parse_mode="HTML")
    await callback.answer()

@dp.message(ChannelStates.waiting_for_promote_user)
async def process_promote_user(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("channel_idx")
    user_id = message.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await message.answer("❌ Topilmadi!")
        await state.clear()
        return
    
    channel = user_channels[user_id][idx]
    try:
        promote_user_id = int(message.text.strip())
        await bot.promote_chat_member(
            chat_id=channel["id"], user_id=promote_user_id,
            can_manage_chat=True, can_post_messages=True, can_edit_messages=True,
            can_delete_messages=True, can_manage_video_chats=True,
            can_restrict_members=True, can_promote_members=False,
            can_change_info=True, can_invite_users=True, can_pin_messages=True
        )
        write_log(user_id, message.from_user.username, "PROMOTED", f"User: {promote_user_id}")
        await edit_or_send_message(
            message.chat.id,
            message,
            f"✅ <b>Admin qilib qo'yildi!</b>\n\n📢 {channel['name']}\n👤 {promote_user_id}",
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    except ValueError:
        await edit_or_send_message(
            message.chat.id,
            message,
            "❌ Faqat raqam yuboring!",
            message_id=data.get("prompt_message_id")
        )
    except Exception:
        await edit_or_send_message(
            message.chat.id,
            message,
            DEFAULT_ERROR_TEXT,
            message_id=data.get("prompt_message_id"),
            reply_markup=get_main_menu()
        )
    await state.clear()

# ==================== HAVOLALAR ====================

@dp.callback_query(F.data.startswith("exportlink_"))
async def export_invite_link(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await callback.answer("❌ Topilmadi!", show_alert=True)
        return
    
    channel = user_channels[user_id][idx]
    try:
        link = await bot.export_chat_invite_link(chat_id=channel["id"])
        write_log(user_id, callback.from_user.username, "LINK_EXPORTED", channel['name'])
        await callback.message.edit_text(f"🔗 <b>Doimiy havola:</b>\n\n📢 {channel['name']}\n🔗 {link}", parse_mode="HTML", reply_markup=get_links_menu(idx))
        await callback.answer("✅")
    except Exception:
        await callback.answer("❌ Xatolik", show_alert=True)

@dp.callback_query(F.data.startswith("createlink_"))
async def create_invite_link(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    if user_id not in user_channels or idx >= len(user_channels[user_id]):
        await callback.answer("❌ Topilmadi!", show_alert=True)
        return
    
    channel = user_channels[user_id][idx]
    try:
        expire_ts = int((datetime.now() + timedelta(days=1)).timestamp())
        link = await bot.create_chat_invite_link(chat_id=channel["id"], expire_date=expire_ts, member_limit=100)
        write_log(user_id, callback.from_user.username, "LINK_CREATED", channel['name'])
        await callback.message.edit_text(
            f"⏰ <b>Cheklangan havola:</b>\n\n📢 {channel['name']}\n🔗 {link.invite_link}\n\n⏰ 24 soat | 👥 100",
            parse_mode="HTML",
            reply_markup=get_links_menu(idx)
        )
        await callback.answer("✅")
    except Exception:
        await callback.answer("❌ Xatolik", show_alert=True)

# ==================== NAVIGATSIYA ====================

@dp.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text("🤖 <b>Asosiy Menyu</b>", parse_mode="HTML", reply_markup=get_main_menu())
    await callback.answer()

@dp.callback_query(F.data == "menu_info")
async def menu_info(callback: CallbackQuery):
    await callback.message.edit_text("📊 <b>Ma'lumot</b>\n\nKanal tanlang:", parse_mode="HTML", reply_markup=get_channel_list_keyboard(callback.from_user.id))
    await callback.answer()

@dp.callback_query(F.data == "menu_manage")
async def menu_manage(callback: CallbackQuery):
    await callback.message.edit_text("⚙️ <b>Boshqarish</b>\n\nKanal tanlang:", parse_mode="HTML", reply_markup=get_channel_list_keyboard(callback.from_user.id))
    await callback.answer()

@dp.callback_query(F.data == "menu_send")
async def menu_send(callback: CallbackQuery):
    await callback.message.edit_text("📤 <b>Xabar</b>\n\nKanal tanlang:", parse_mode="HTML", reply_markup=get_channel_list_keyboard(callback.from_user.id))
    await callback.answer()

@dp.callback_query(F.data == "menu_members")
async def menu_members(callback: CallbackQuery):
    await callback.message.edit_text("👥 <b>A'zolar</b>\n\nKanal tanlang:", parse_mode="HTML", reply_markup=get_channel_list_keyboard(callback.from_user.id))
    await callback.answer()

@dp.callback_query(F.data == "menu_links")
async def menu_links(callback: CallbackQuery):
    await callback.message.edit_text("🔗 <b>Havolalar</b>\n\nKanal tanlang:", parse_mode="HTML", reply_markup=get_channel_list_keyboard(callback.from_user.id))
    await callback.answer()

# ==================== ADMIN BUYRUQLARI ====================

@dp.message(Command("stats"))
async def show_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    total_users = len(user_channels)
    total_channels = sum(len(ch) for ch in user_channels.values())
    await message.answer(f"📊 <b>STATISTIKA</b>\n\n👥 Users: {total_users}\n📢 Channels: {total_channels}", parse_mode="HTML")

@dp.message(Command("logs"))
async def send_logs(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        if os.path.exists(LOG_FILE):
            await message.answer_document(FSInputFile(LOG_FILE), caption="📋 <b>Logs</b>", parse_mode="HTML")
        else:
            await message.answer("❌ Yo'q")
    except Exception:
        await message.answer(DEFAULT_ERROR_TEXT)

@dp.message(Command("backup"))
async def send_backup(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        if os.path.exists(DATA_FILE):
            await message.answer_document(FSInputFile(DATA_FILE), caption="💾 <b>Backup</b>", parse_mode="HTML")
        else:
            await message.answer("❌ Yo'q")
    except Exception:
        await message.answer(DEFAULT_ERROR_TEXT)

@dp.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "🤖 <b>BUYRUQLAR</b>\n\n"
        "/start - Boshlash\n"
        "/help - Yordam\n\n"
        "<b>Admin:</b>\n"
        "/stats - Statistika\n"
        "/logs - Loglar\n"
        "/backup - Backup",
        parse_mode="HTML"
    )

@dp.message()
async def handle_unknown(message: Message):
    await message.answer("❓ /start", reply_markup=get_main_menu())

# ==================== MAIN ====================

async def on_startup():
    print("=" * 40)
    print("🚀 BOT ISHGA TUSHDI!")
    print(f"📊 Users: {len(user_channels)}")
    print("=" * 40)
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
    except Exception:
        print("\n❌ Xatolik")
