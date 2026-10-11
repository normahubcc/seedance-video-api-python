#!/usr/bin/env python3
"""
Пример 1: Простая генерация видео в 3 строки.
"""

from seedance import NormaVideoClient

# Инициализируем клиент (ключ подхватывается из переменной NORMAHUB_API_KEY)
client = NormaVideoClient()

print("[*] Запускаем генерацию видео через SeeDance 2.5...")
video_path = client.generate_and_download(
    prompt="Киберпанк мегаполис, неоновый дождь, пролетающие дроны, 4k",
    model="seedance-2.5",
    output_path="cyberpunk_city.mp4",
)

print(f"[+] Видео готово и сохранено: {video_path}")
