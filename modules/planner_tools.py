from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()
USER_NOTES = {}

@router.message(Command("note", "save"))
async def save_note(message: Message):
    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        await message.answer("Использование: `/note Купить сервер в пятницу`", parse_mode="Markdown")
        return
    
    user_id = message.from_user.id
    if user_id not in USER_NOTES:
        USER_NOTES[user_id] = []
        
    USER_NOTES[user_id].append(text[1])
    await message.answer(f"✅ Заметка сохранена! Всего заметок: {len(USER_NOTES[user_id])}")

@router.message(Command("notes", "list"))
async def show_notes(message: Message):
    user_id = message.from_user.id
    notes = USER_NOTES.get(user_id, [])
    
    if not notes:
        await message.answer("📝 У вас пока нет сохраненных заметок.")
        return
        
    formatted = "\n".join([f"{i+1}. {note}" for i, note in enumerate(notes)])
    await message.answer(f"📝 **Ваши заметки:**\n\n{formatted}", parse_mode="Markdown")