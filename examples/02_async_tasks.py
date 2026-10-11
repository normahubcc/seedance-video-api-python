#!/usr/bin/env python3
"""
Пример 2: Неблокирующий запуск задачи и ручной поллинг.
Подходит для сервисов с очередями (Celery, RQ, RabbitMQ).
"""

import time
from seedance import NormaVideoClient

client = NormaVideoClient()

# 1. Быстро создаем задачу (возвращает task_id мгновенно)
task = client.create_task(
    prompt="Футуристический космический корабль выходит из гиперпространства",
    model="seedance-2.5",
    duration=5,
)
print(f"[*] Задача создана. ID: {task.id}, Начальный статус: {task.status}")

# 2. Имитируем внешний поллинг или проверку в фоновом воркере
for _ in range(30):
    current = client.get_status(task.id)
    print(f"[*] Проверка статуса: {current.status.value.upper()}")
    if current.is_finished:
        if current.is_successful:
            print(f"[+] Видео готово! Ссылка на скачивание: {current.video_url}")
        else:
            print(f"[!] Ошибка генерации: {current.error}")
        break
    time.sleep(5)
