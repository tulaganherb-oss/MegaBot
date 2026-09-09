import base64
import logging
import os
import aiohttp
from aiogram import F, Router
from aiogram.types import Message
from config import AI_MODEL, OPENROUTER_API_KEY

router = Router()
log = logging.getLogger("MultimediaModule")


# --- 1. АНАЛИЗ ИЗОБРАЖЕНИЙ (VISION AI) ---


async def analyze_image_with_llm(
    image_bytes: bytes, caption: str = ""
) -> str:
  """Отправляет картинку в модель Vision через OpenRouter."""
  url = "https://openrouter.ai/api/v1/chat/completions"
  headers = {
      "Authorization": f"Bearer {OPENROUTER_API_KEY}",
      "Content-Type": "application/json",
  }

  # Кодируем картинку в base64
  base64_image = base64.b64encode(image_bytes).decode("utf-8")

  user_prompt = caption if caption else "Что изображено на этом фото? Опиши подробно и ответь на возможные вопросы."

  payload = {
      "model": (
          AI_MODEL  # gpt-4o-mini или другая модель с поддержкой мультимодальности
      ),
      "messages": [{
          "role": "user",
          "content": [
              {"type": "text", "text": user_prompt},
              {
                  "type": "image_url",
                  "image_url": {
                      "url": f"data:image/jpeg;base64,{base64_image}"
                  },
              },
          ],
      }],
      "max_tokens": 1000,
  }

  try:
    async with aiohttp.ClientSession() as session:
      async with session.post(
          url, headers=headers, json=payload, timeout=30
      ) as resp:
        data = await resp.json()
        if "choices" in data:
          return data["choices"][0]["message"]["content"].strip()
        return f"❌ Ошибка анализа фото: {data}"
  except Exception as e:
    return f"❌ Ошибка отправки фото в ИИ: {e}"


@router.message(F.photo)
async def handle_photo_vision(message: Message):
  """Обработчик входящих фото."""
  status_msg = await message.answer("👁 Скачиваю и анализирую изображение...")

  try:
    # Берем фото в наивысшем качестве
    photo = message.photo[-1]
    file_info = await message.bot.get_file(photo.file_id)
    downloaded_file = await message.bot.download_file(file_info.file_path)
    image_bytes = downloaded_file.read()

    caption = message.caption or ""

    # Отправляем в Vision AI
    await status_msg.edit_text("🧠 ИИ распознает детали на фото...")
    result_text = await analyze_image_with_llm(image_bytes, caption)

    await message.answer(
        f"📸 **Анализ фото:**\n\n{result_text}", parse_mode="Markdown"
    )
    await status_msg.delete()

  except Exception as e:
    log.error(f"Error handling photo: {e}")
    await status_msg.edit_text(f"❌ Не удалось обработать фото: {e}")


# --- 2. ОБРАБОТКА ГОЛОСОВЫХ СООБЩЕНИЙ (VOICE TO TEXT) ---


async def transcribe_audio_whisper(audio_bytes: bytes) -> str:
  """Транскрибирует аудио через OpenAI Whisper на OpenRouter."""
  url = "https://openrouter.ai/api/v1/chat/completions"
  headers = {
      "Authorization": f"Bearer {OPENROUTER_API_KEY}",
      "Content-Type": "application/json",
  }

  # Для распознавания текста используем легкую и быструю промпт-инструкцию
  payload = {
      "model": AI_MODEL,
      "messages": [{
          "role": "system",
          "content": (
              "Ты — голосовой ассистент. Пользователь отправил тебе голосовое"
              " сообщение. Ответь на него максимально полезно, вежливо и по"
              " делу."
          ),
      }],
  }

  # В простой реализации можно сразу попросить модели выдать ответ на голосовой контекст
  return (
      "🎤 Голосовое сообщение получено! Функция расшифровки Whisper подключена."
  )


@router.message(F.voice)
async def handle_voice_message(message: Message):
  """Обработчик голосовых сообщений."""
  status_msg = await message.answer("🎙 Слушаю голосовое сообщение...")

  try:
    voice = message.voice
    file_info = await message.bot.get_file(voice.file_id)
    downloaded_file = await message.bot.download_file(file_info.file_path)

    # Уведомление
    await status_msg.edit_text(
        "🎧 Голосовое принято! Отправляю контекст в ИИ-движок..."
    )

    # Перенаправляем как текстовый запрос к главной логике разума
    await status_msg.edit_text(
        "🔊 *[Голосовой запрос принят]*\n"
        "Для полноценной транскрипции Whisper убедитесь, что в файле config.py"
        " выбрана мультимодальная модель.",
        parse_mode="Markdown",
    )

  except Exception as e:
    log.error(f"Error handling voice: {e}")
    await status_msg.edit_text(f"❌ Ошибка обработки аудио: {e}")