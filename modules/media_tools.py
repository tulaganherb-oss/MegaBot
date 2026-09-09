import io
import urllib.parse
import qrcode
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile

router = Router()

@router.message(Command("art", "draw"))
async def generate_art(message: Message):
    prompt = message.text.split(maxsplit=1)
    if len(prompt) < 2:
        await message.answer("Использование: `/draw неоновый город`", parse_mode="Markdown")
        return
    
    status = await message.answer("🎨 Генерирую медиа-контент...")
    encoded = urllib.parse.quote(prompt[1])
    img_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
    
    try:
        await message.answer_photo(photo=img_url, caption=f"✨ **Запрос:** {prompt[1]}")
        await status.delete()
    except Exception as e:
        await status.edit_text(f"❌ Ошибка генерации: {e}")

@router.message(Command("qr"))
async def generate_qr(message: Message):
    text = message.text.replace("/qr", "").strip()
    if not text:
        await message.answer("Использование: `/qr https://example.com`", parse_mode="Markdown")
        return
    
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    file = BufferedInputFile(buf.getvalue(), filename="qr.png")
    await message.answer_photo(photo=file, caption=f"📱 **QR для:** `{text}`", parse_mode="Markdown")