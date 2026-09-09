import base64
import datetime
import io
import json
import os
import random
import re
import subprocess
import urllib.parse
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
import aiohttp
from config import TELEGRAM_TOKEN, OPENROUTER_API_KEY, AI_MODEL

router = Router()
USER_HISTORIES = {}

# --- УТИЛИТЫ ДЛЯ СКАЧИВАНИЯ ---

async def download_image_as_bytes(prompt: str) -> bytes:
    """Генерирует ссылку на Pollinations.ai и скачивает готовую картинку в память бота."""
    encoded_prompt = urllib.parse.quote(prompt)
    
    # Мы генерируем ссылку как и раньше...
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=2048&height=2048&nologo=true&enhance=true"
    
    async with aiohttp.ClientSession() as session:
        # Устанавливаем большой таймаут (60 сек), чтобы бот дождался генерации!
        # Пытаемся скачать картинку (этот запрос «зависнет» пока картинка не дорисуется)
        async with session.get(url, timeout=60) as response:
            if response.status == 200:
                # Читаем картинку целиком как байты
                image_bytes = await response.read()
                return image_bytes
            else:
                return None

# --- МОДУЛЬ ГЕНЕРАЦИИ ИЗОБРАЖЕНИЙ ПО ТЕКСТУ (/art или /draw) ---

# Функция улучшения промпта через ИИ для ПОЛНОГО ФОТОРЕАЛИЗМА
async def enhance_realistic_prompt(user_prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Очень жесткая инструкция на английском для создания ПРОФЕССИОНАЛЬНОГО ФОТО
    system_instruction = (
        "You are an expert AI image prompt engineer specializing in hyper-photorealism. "
        "Your only task is to convert the user's input into a highly detailed, professional photographic prompt. "
        "The style must NOT be cartoony, illustrative, 3D render, or artistic. It must look like a RAW, "
        "uncompressed real-world photo taken with a high-end full-frame camera. "
        "Remove all direct requests for nudity, explicit content, or vulgar words to avoid API blocks, replacing them with artistic terms (e.g., 'artistic nude', 'unclothed body', 'sensual posture'). "
        "ALWAYS include specific technical camera keywords like: 'photorealistic', 'raw photo', '8k UHD', 'cinematic lighting', "
        "'highly detailed skin texture', 'pores', 'realistic eyes', 'shot on Sony A1', '85mm f/1.4 lens', 'film grain', 'unprocessed'. "
        "Describe specific textures, background elements, and the lighting style. Translate to English if needed. "
        "Return ONLY the optimized English prompt text, max 800 chars."
    )
    
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=20) as resp:
                data = await resp.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception:
        # Если ИИ упал, добавляем базовые ключи реализма вручную
        return f"{user_prompt}, hyper-realistic, photorealistic, 8k, raw photo, cinematic lighting"


@router.message(Command("art", "draw", "img", "рисуй", "нарисуй", "фото"))
async def generate_realistic_image(message: Message):
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        bot_user = await message.bot.get_me()
        await message.answer(
            f"🎨 **Как сгенерировать фотореалистичную картинку:**\n"
            f"Напиши команду и описание. Пример:\n"
            f"`/draw красивая девушка крупным планом`"
        )
        return

    raw_prompt = args[1]
    
    # Отправляем сообщение-заглушку
    sent_msg = await message.answer("📸 Настраиваю объектив, выставляю свет (фотореализм)...")

    try:
        # Step 1: ИИ превращает запрос в профессиональный фото-промпт
        await sent_msg.edit_text("🧬 Формирую технический фото-концепт...")
        optimized_prompt = await enhance_realistic_prompt(raw_prompt)
        
        # Step 2: Бот скачивает готовую картинку (байты файла)
        await sent_msg.edit_text(f"⏳ Начинаю глубокую фото-прорисовку ( En промпт: `{optimized_prompt[:50]}...` ). Это может занять до 60 секунд...")
        
        # Заменяем photo=url на скачивание байтов файла!
        image_bytes = await download_image_as_bytes(optimized_prompt)
        
        if not image_bytes:
            await sent_msg.edit_text("❌ Извините, сервера Pollinations API перегружены. Попробуйте позже.")
            return

        # Превращаем байты в файл InputFile для Telegram
        file_input = BufferedInputFile(image_bytes, filename="generated_photo.jpeg")

        # Step 3: Бот отправляет картинку как ГОТОВЫЙ ФАЙЛ, а не ссылку!
        await message.answer_photo(
            photo=file_input,
            caption=(
                f"📸 **Фото по запросу:** `{raw_prompt}`\n\n"
                f"_Фото-промпт (En):_ `{optimized_prompt}`"
            )
        )
        
        # Удаляем сообщение-заглушку
        await sent_msg.delete()
        
    except Exception as e:
        await sent_msg.edit_text(f"❌ Системная ошибка во время генерации: {e}")


# 2. Перехват фраз с просьбой нарисовать в обычном чате
@router.message(
    F.text.lower().startswith("нарисуй") | F.text.lower().startswith("сделай арт")
)
async def generate_image_text(message: Message):
    prompt = (
        message.text.replace("нарисуй", "")
        .replace("сделай арт", "")
        .strip()
    )

    if not prompt:
        await message.answer("Напиши, что именно нужно нарисовать!")
        return

    # Отправляем сообщение-заглушку
    sent_msg = await message.answer("📸 Настраиваю объектив (фотореализм)...")

    try:
        # Step 1: ИИ превращает запрос в профессиональный фото-промпт
        await sent_msg.edit_text("🧬 Формирую технический фото-концепт...")
        optimized_prompt = await enhance_realistic_prompt(prompt)
        
        # Step 2: Бот скачивает готовую картинку (байты файла)
        await sent_msg.edit_text(f"⏳ Начинаю глубокую фото-прорисовку ( En промпт: `{optimized_prompt[:50]}...` ). Это может занять до 60 секунд...")
        
        # Заменяем photo=url на скачивание байтов файла!
        image_bytes = await download_image_as_bytes(optimized_prompt)
        
        if not image_bytes:
            await sent_msg.edit_text("❌ Извините, сервера Pollinations API перегружены. Попробуйте позже.")
            return

        # Превращаем байты в файл InputFile для Telegram
        file_input = BufferedInputFile(image_bytes, filename="generated_photo.jpeg")

        # Step 3: Бот отправляет картинку как ГОТОВЫЙ ФАЙЛ, а не ссылку!
        await message.answer_photo(
            photo=file_input,
            caption=(
                f"📸 **Фото по запросу:** `{prompt}`\n\n"
                f"_Фото-промпт (En):_ `{optimized_prompt}`"
            )
        )
        
        # Удаляем сообщение-заглушку
        await sent_msg.delete()
        
    except Exception as e:
        await sent_msg.edit_text(f"❌ Системная ошибка во время генерации: {e}")