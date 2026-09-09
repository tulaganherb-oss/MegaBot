import asyncio
import datetime
import logging
import re
import urllib.parse

import aiohttp
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from bs4 import BeautifulSoup
import wikipediaapi

from config import OPENROUTER_API_KEY, AI_MODEL

router = Router()
log = logging.getLogger("SuperSearch")

wiki = wikipediaapi.Wikipedia(
    user_agent="MegaBot/1.0 (https://github.com/MegaBot)", language="ru"
)

# Ускоренные таймауты
FAST_TIMEOUT = aiohttp.ClientTimeout(total=8)
LLM_TIMEOUT = aiohttp.ClientTimeout(total=20)


async def fetch_url_content(session: aiohttp.ClientSession, url: str) -> str:
    """Быстрый скачиватель страниц со строгим лимитом времени."""
    try:
        async with session.get(url, timeout=FAST_TIMEOUT) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                for script in soup(["script", "style", "nav", "footer"]):
                    script.extract()
                text = soup.get_text(separator=" ")
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                return "\n".join(chunk for chunk in chunks if chunk)[:2000]
            return ""
    except Exception:
        return ""


async def google_search_free(session: aiohttp.ClientSession, query: str) -> list:
    """Ускоренный поиск в Google."""
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
            " like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
    }
    try:
        async with session.get(url, headers=headers, timeout=FAST_TIMEOUT) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                results = []
                for g in soup.find_all("div", class_="g")[:4]:
                    anchors = g.find_all("a")
                    if anchors:
                        link = anchors[0].get("href", "")
                        title_el = g.find("h3")
                        title = title_el.text if title_el else "Без заголовка"
                        snippet_el = g.find("div", class_="VwiC3b")
                        snippet_text = snippet_el.text if snippet_el else ""
                        if link.startswith("http"):
                            results.append({"title": title, "link": link, "snippet": snippet_text})
                return results
            return []
    except Exception:
        return []


async def search_wikipedia(query: str) -> str:
    """Быстрый поиск в Википедии через отдельный поток."""
    try:
        loop = asyncio.get_event_loop()
        page = await loop.run_in_executor(None, wiki.page, query)
        if page.exists():
            return f"Wikipedia ({page.title}): {page.summary[:1000]}"
        return ""
    except Exception:
        return ""


async def ask_llm_with_search(session: aiohttp.ClientSession, user_query: str, search_results_text: str) -> str:
    """Запрос к нейросети со сниженным таймаутом."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    now = datetime.datetime.now()
    system_instruction = (
        "Ты — Супер-агент Живого Поиска. Отвечай лаконично, точно и быстро, "
        "используя выдержки из поиска. Указывай ссылки на источники [1], [2]. "
        f"Дата: {now.strftime('%d.%m.%Y')}, Kyiv."
    )

    user_message = (
        f"Запрос: '{user_query}'\n\n"
        f"ДАННЫЕ ИЗ СЕТИ:\n{search_results_text}\n\n"
        "Сформируй краткий и емкий ответ."
    )

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "max_tokens": 1000,
    }

    try:
        async with session.post(url, headers=headers, json=payload, timeout=LLM_TIMEOUT) as resp:
            data = await resp.json()
            if "choices" in data:
                return data["choices"][0]["message"]["content"].strip()
            return "Не удалось сформировать ответ ИИ."
    except Exception as e:
        return f"Ошибка получения ответа от ИИ: {e}"


@router.message(Command("live", "search", "гугл", "поиск"))
async def super_search_command(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Пример: `/live новости футбола`", parse_mode="Markdown")
        return

    query = args[1]
    status_msg = await message.answer("⚡ *Быстрый поиск...*", parse_mode="Markdown")

    try:
        async with aiohttp.ClientSession() as session:
            # Запускаем Google и Wikipedia одновременно
            google_task = google_search_free(session, query)
            wiki_task = search_wikipedia(query)

            google_results, wiki_summary = await asyncio.gather(google_task, wiki_task)

            if not google_results and not wiki_summary:
                await status_msg.edit_text("🤔 Ничего не найдено по вашему запросу.")
                return

            search_context = ""
            if wiki_summary:
                search_context += f"{wiki_summary}\n\n"

            references = []
            for i, res in enumerate(google_results):
                ref_num = i + 1
                search_context += f"[{ref_num}] {res['title']}: {res['snippet']}\n"
                references.append(f"[{ref_num}] <a href='{res['link']}'>{res['title']}</a>")

            await status_msg.edit_text("🧠 *Генерирую ответ...*", parse_mode="Markdown")

            final_answer = await ask_llm_with_search(session, query, search_context)
            formatted_refs = "\n".join(references) if references else "Источники недоступны."

            await message.answer(
                f"🧐 **Результат по запросу:** `{query}`\n\n"
                f"{final_answer}\n\n"
                f"🔗 **Источники:**\n{formatted_refs}",
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )

            await status_msg.delete()

    except Exception as e:
        log.error(f"Error in SuperSearch: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {e}")