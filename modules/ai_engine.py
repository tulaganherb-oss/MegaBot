import base64
import datetime
import aiohttp
from aiogram import Router, F
from aiogram.types import Message
from config import OPENROUTER_API_KEY, AI_MODEL

router = Router()
USER_HISTORIES = {}

async def ask_openrouter(messages: list) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json={"model": AI_MODEL, "messages": messages}) as resp:
            data = await resp.json()
            return data["choices"][0]["message"]["content"]

@router.message(F.text & ~F.text.startswith("/"))
async def handle_ai_chat(message: Message):
    chat_id = message.chat.id
    if chat_id not in USER_HISTORIES:
        USER_HISTORIES[chat_id] = []

    now = datetime.datetime.now()
    system_prompt = (
        "Ты — универсальный супер-интеллект, умеющий решать 1000+ прикладных задач: "
        "от написания кода и анализа данных до финансовых стратегий. "
        f"Текущее время: {now.strftime('%d.%m.%Y, %H:%M')}, 2026 год."
    )
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(USER_HISTORIES[chat_id])
    messages.append({"role": "user", "content": message.text})
    
    status_msg = await message.answer("🧠 Анализирую запрос...")
    try:
        answer = await ask_openrouter(messages)
        USER_HISTORIES[chat_id].append({"role": "user", "content": message.text})
        USER_HISTORIES[chat_id].append({"role": "assistant", "content": answer})
        
        # Ограничение памяти на 20 ходов
        if len(USER_HISTORIES[chat_id]) > 20:
            USER_HISTORIES[chat_id] = USER_HISTORIES[chat_id][-20:]
            
        await status_msg.edit_text(answer[:4000])
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка ИИ-модуля: {e}")