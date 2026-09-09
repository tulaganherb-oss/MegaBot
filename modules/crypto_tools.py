import aiohttp
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("crypto", "coin"))
async def get_crypto_info(message: Message):
    args = message.text.split(maxsplit=1)
    coin = args[1].lower() if len(args) > 1 else "bitcoin"
    
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd,uah&include_24hr_change=true"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                data = await resp.json()
                if coin not in data:
                    await message.answer(f"❌ Монета `{coin}` не найдена.", parse_mode="Markdown")
                    return
                
                usd = data[coin]["usd"]
                uah = data[coin]["uah"]
                change = data[coin].get("usd_24h_change", 0)
                
                emoji = "📈" if change >= 0 else "📉"
                
                report = (
                    f"📊 **Аналитика монеты ({coin.upper()}):**\n"
                    f"• Цена USD: `${usd:,.2f}`\n"
                    f"• Цена UAH: `{uah:,.2f} ₴`\n"
                    f"• Изменение за 24ч: {emoji} `{change:.2f}%`"
                )
                await message.answer(report, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка получения крипто-данных: {e}")