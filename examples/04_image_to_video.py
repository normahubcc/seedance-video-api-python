#!/usr/bin/env python3
"""
Пример 4: Оживление статичных изображений (Image-to-Video) с SeeDance 2.5 / Grok Video.
Демонстрирует автоматическую кодировку локальных файлов в Base64 Data URI и передачу image_url.
"""

from pathlib import Path
from seedance import AsyncNormaVideoClient, NormaVideoClient

# 1. Синхронный вариант (простой скрипт):
def sync_image_to_video_demo():
    print("[*] --- Синхронный Image-to-Video ---")
    client = NormaVideoClient()

    # Путь к вашей картинке (PNG, JPG, WEBP)
    sample_image = Path("character.png")

    if not sample_image.exists():
        print(f"[-] Файл {sample_image} не найден. Для теста используем image_url.")
        image_arg = {"image_url": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675"}
    else:
        # Локальный файл автоматически конвертируется в Base64 Data URL:
        image_arg = {"image_path": sample_image}

    video_path = client.generate_and_download(
        prompt="Персонаж плавно моргает, улыбается и поворачивает голову, кинематографичный свет",
        model="seedance-2.5",
        output_path="animated_character.mp4",
        duration=5,
        **image_arg,
    )
    print(f"[+] Видео сохранено в: {video_path}")


# 2. Асинхронный вариант (FastAPI / Telegram Bot):
async def async_image_to_video_demo():
    print("\n[*] --- Асинхронный Image-to-Video (AsyncNormaVideoClient) ---")
    async_client = AsyncNormaVideoClient()

    # Мгновенная отправка задачи в очередь
    task = await async_client.create_task(
        prompt="Камера облетает картину, оживляя водопад на заднем плане",
        model="seedance-2.5",
        image_url="https://images.unsplash.com/photo-1579783902614-a3fb3927b675",
        duration=5,
    )
    print(f"[+] Задача Image-to-Video создана! Task ID: {task.id}")

    # Неблокирующее ожидание рендера
    finished = await async_client.wait_for_completion(task.id)
    print(f"[+] Рендер завершен! URL: {finished.video_url}")

    # Скачивание готового MP4
    downloaded_file = await async_client.download_video(finished.video_url, "waterfall_animated.mp4")
    print(f"[+] Файл скачан: {downloaded_file}")


if __name__ == "__main__":
    print("[*] Демонстрация Image-to-Video (I2V) через NormaHub:")
    print("[*] Для запуска укажите NORMAHUB_API_KEY в окружении.")
    # sync_image_to_video_demo()
    # asyncio.run(async_image_to_video_demo())
