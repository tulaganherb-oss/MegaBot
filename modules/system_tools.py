import asyncio
import psutil
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from config import TELEGRAM_TOKEN

router = Router()

@router.message(Command("status"))
async def system_status(message: Message):
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    
    report = (
        f"🖥 **Системный монитор:**\n"
        f"• Нагрузка ЦП: `{cpu}%`\n"
        f"• ОЗУ: `{ram}%`\n"
        f"• Диск: `{disk}%`"
    )
    await message.answer(report, parse_mode="Markdown")

@router.message(Command("cmd"))
async def run_cmd(message: Message):
    cmd = message.text.replace("/cmd", "").strip()
    if not cmd:
        await message.answer("Укажите команду: `/cmd dir`", parse_mode="Markdown")
        return
    
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode() or stderr.decode()
        await message.answer(f"```\n{output[:3900]}\n```", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка консоли: {e}")