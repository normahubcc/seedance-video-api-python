#!/usr/bin/env python3
"""
Пример 3: Интеграция в асинхронный Telegram-бот (aiogram 3 / python-telegram-bot).
Демонстрирует нативный AsyncNormaVideoClient без блокировки event loop.
"""

import asyncio
from seedance import AsyncNormaVideoClient

# Инициализируем нативный асинхронный клиент NormaHub
video_client = AsyncNormaVideoClient()


async def mock_telegram_handler(chat_id: int, user_prompt: str) -> None:
    """Пример логики асинхронного хэндлера бота."""
    print(f"[*] Получен запрос от пользователя {chat_id}: \"{user_prompt}\"")
    print("[*] Отправляем сообщение в чат: '🎬 Генерация видео началась, это займет около 40 секунд...'")

    output_filename = f"video_{chat_id}.mp4"

    # Нативный асинхронный вызов — не блокирует другие корутины бота!
    saved_path = await video_client.generate_and_download(
        prompt=user_prompt,
        output_path=output_filename,
        model="seedance-2.5",
        duration=5,
    )

    print(f"[+] Видео успешно сгенерировано: {saved_path}")
    print(f"[*] Отправляем файл {saved_path} в Telegram через await bot.send_video(chat_id={chat_id})!")


async def main() -> None:
    print("[*] Демонстрация работы нативного AsyncNormaVideoClient в боте:")
    print("[*] Для реального вызова задайте переменную окружения NORMAHUB_API_KEY.")
    # Пример вызова:
    # await mock_telegram_handler(12345678, "Неоновый дракон в небе Токио, 4k photorealistic")


if __name__ == "__main__":
    asyncio.run(main())
