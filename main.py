import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from config import TELEGRAM_TOKEN

# Импорт роутеров
from modules.brain_engine import router as brain_router
from modules.crypto_tools import router as crypto_router
from modules.generator import router as generator_router
from modules.media_tools import router as media_router
from modules.multimedia import router as multimedia_router
from modules.planner_tools import router as planner_router
from modules.system_tools import router as system_router
from modules.super_search import router as live_search_router
from modules.web_tools import router as web_router

logging.basicConfig(level=logging.INFO)

async def main():
    # Настройка правильного прокси для PythonAnywhere
    session = AiohttpSession(proxy="http://proxy-server.pythonanywhere.com:3128")
    bot = Bot(token=TELEGRAM_TOKEN, session=session)
    dp = Dispatcher()

    # Подключение роутеров
    dp.include_router(system_router)
    dp.include_router(live_search_router)
    dp.include_router(brain_router)
    dp.include_router(crypto_router)
    dp.include_router(generator_router)
    dp.include_router(media_router)
    dp.include_router(multimedia_router)
    dp.include_router(planner_router)
    dp.include_router(web_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
