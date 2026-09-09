import asyncio
import datetime
import logging
import sqlite3
import aiohttp
from aiogram import Router, F
from aiogram.types import Message
from config import OPENROUTER_API_KEY, AI_MODEL

router = Router()
log = logging.getLogger("BrainEngine")

DB_PATH = "bot_memory.db"

# --- БАЗА ДАННЫХ ПАМЯТИ ---

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            username TEXT,
            timestamp DATETIME,
            role TEXT,
            content TEXT,
            semanic_tag TEXT
        )
    ''')
    conn.commit()
    conn.close()

async def save_to_memory(chat_id, user_id, username, role, content):
    now = datetime.datetime.now()
    tags = " ".join(content.split()[:3]).lower()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO memory (chat_id, user_id, username, timestamp, role, content, semanic_tag) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (chat_id, user_id, username, now, role, content, tags)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.error(f"Ошибка БД: {e}")

async def recall_relevant_memories(query: str, limit=5) -> str:
    words = query.lower().split()
    search_terms = [f"%{word}%" for word in words if len(word) > 2]
    if not search_terms:
        return ""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        query_parts = ["semanic_tag LIKE ?" for _ in search_terms]
        sql = f"SELECT role, content, timestamp FROM memory WHERE {' OR '.join(query_parts)} ORDER BY timestamp DESC LIMIT ?"
        cursor.execute(sql, (*search_terms, limit))
        results = cursor.fetchall()
        conn.close()
        if not results:
            return ""
        memories = []
        for role, content, timestamp in results:
            prefix = "Стетхем" if role == 'assistant' else "Собеседник"
            memories.append(f"[{timestamp}] {prefix}: \"{content}\"")
        return "\n".join(memories)
    except Exception:
        return ""

# --- ВЫЗОВ ИИ (СЕРЬЕЗНЫЙ ДЖЕЙСОН СТЕТХЕМ БЕЗ ЦИТАТ) ---

async def ask_llm_with_memory(user_query: str, recalled_context: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Серьезный характер Стетхема без цитат
    system_instruction = (
        "Ты — Джейсон Стетхем (Jason Statham). "
        "Твой характер: суровый, абсолютно серьезный, хладнокровный, молчаливый и сдержанный. "
        "Никакого клоунства, эмодзи, смайликов и пафосных пацанских цитат. "
        "Разговаривай строго, сдержанно, по-мужски жестко и уверенно. "
        "Отвечай максимально коротко, четко и прямо по делу, без лишней воды и размышлений."
    )
    
    messages = [{"role": "system", "content": system_instruction}]
    if recalled_context:
        messages.append({"role": "system", "content": f"Память Стетхема о прошлых темах:\n{recalled_context}"})
    messages.append({"role": "user", "content": user_query})
    
    payload = {
        "model": AI_MODEL if AI_MODEL else "openai/gpt-4o-mini",
        "messages": messages,
        "temperature": 0.5
    }
    
    timeout = aiohttp.ClientTimeout(total=25)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    err_body = await resp.text()
                    log.error(f"OpenRouter Error {resp.status}: {err_body}")
                    return "Сбой связи с сервером. Повтори запрос."
                
                data = await resp.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"].strip()
                return "Повтори вопрос."
    except asyncio.TimeoutError:
        return "Таймаут соединения. Повтори запрос."
    except Exception as e:
        return f"Ошибка: {e}"

# --- ОБРАБОТЧИК ---

@router.message(F.text & ~F.text.startswith("/"))
async def handle_brain_chat(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    user_text = message.text

    asyncio.create_task(save_to_memory(chat_id, user_id, username, 'user', user_text))
    
    status_msg = await message.answer("🗿 Стетхем обдумывает вопрос...")

    recalled_context = await recall_relevant_memories(user_text)
    
    try:
        await status_msg.edit_text("💬 Стетхем готовит ответ...")
        ai_answer = await ask_llm_with_memory(user_text, recalled_context)
        
        asyncio.create_task(save_to_memory(chat_id, message.bot.id, "Стетхем", 'assistant', ai_answer))
        
        await status_msg.edit_text(ai_answer, parse_mode="Markdown")
    except Exception as e:
        await status_msg.edit_text(f"Сбой: {e}")

init_db()