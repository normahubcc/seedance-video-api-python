#!/usr/bin/env python3
"""
Пример асинхронного вызова в обработчике Telegram-бота (aiogram / python-telegram-bot).
AsyncNormaVideoClient работает с нативным asyncio без блокировки event loop.
"""

import asyncio
from seedance import AsyncNormaVideoClient

video_client = AsyncNormaVideoClient()


async def mock_telegram_handler(chat_id: int, user_prompt: str) -> None:
    """Пример корутины для бота."""
    print(f"Запрос от {chat_id}: \"{user_prompt}\"")
    output_filename = f"video_{chat_id}.mp4"

    saved_path = await video_client.generate_and_download(
        prompt=user_prompt,
        output_path=output_filename,
        model="seedance-2.5",
        duration=5,
    )

    print(f"Готово: {saved_path}")


async def main() -> None:
    print("[*] Демонстрация работы нативного AsyncNormaVideoClient в боте:")
    print("[*] Для реального вызова задайте переменную окружения NORMAHUB_API_KEY.")
    # Пример вызова:
    # await mock_telegram_handler(12345678, "Неоновый дракон в небе Токио, 4k photorealistic")


if __name__ == "__main__":
    asyncio.run(main())
