import aiohttp
from bs4 import BeautifulSoup
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("read", "parse"))
async def parse_url(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: `/read https://example.com`", parse_mode="Markdown")
        return
    
    url = args[1]
    status = await message.answer("🌐 Загружаю и читаю страницу...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Извлекаем текст из заголовков и абзацев
                paragraphs = [p.get_text() for p in soup.find_all(['p', 'h1', 'h2'])]
                text_content = "\n".join(paragraphs)[:3500]
                
                if not text_content.strip():
                    text_content = "Не удалось извлечь чистый текст со страницы."
                    
                await status.edit_text(f"📄 **Выжимка со страницы:**\n\n{text_content}")
    except Exception as e:
        await status.edit_text(f"❌ Ошибка чтения URL: {e}")