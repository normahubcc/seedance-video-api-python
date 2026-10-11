<p align="center">
  <a href="https://normahub.cc">
    <img src="./docs/images/logo.png" alt="NormaHub" width="120" />
  </a>
</p>

# SeeDance & Grok Video Python SDK

[![Release](https://img.shields.io/badge/release-v0.2.0-blue?style=flat-square)](https://github.com/normahubcc/seedance-video-api-python/releases)
[![Python](https://img.shields.io/badge/python-3.9+-blue?style=flat-square)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/normahubcc/seedance-video-api-python/blob/main/examples/seedance_video_quickstart.ipynb)

Python SDK и CLI для генерации видео нейросетями **SeeDance 2.5 / 2.0** и **xAI Grok Imagine Video** через API [NormaHub](https://normahub.cc).

Прямой доступ из РФ, оплата в рублях (карты РФ, СБП), OpenAI-совместимый протокол.

---

## Возможности

- **Без сторонних зависимостей:** работает на стандартной библиотеке Python 3.9+ (`urllib` + `asyncio`), без конфликтов версий `requests` или `aiohttp`.
- **Синхронный и асинхронный клиенты:** `NormaVideoClient` для скриптов и `AsyncNormaVideoClient` для FastAPI, Celery, aiogram.
- **Image-to-Video (I2V):** автоматическая конвертация локальных изображений (`.png`, `.jpg`, `.webp`) в Base64 Data URI или передача `image_url`.
- **Автоматический retry:** повтор запросов при временных сетевых сбоях и ошибках 502/503/524 с экспоненциальным backoff.
- **CLI-утилита:** консольный запуск с отслеживанием статуса задачи и сохранением MP4.

---

## Установка

```bash
pip install seedance-video-api
```

Или установите локально:

```bash
git clone https://github.com/normahubcc/seedance-video-api-python.git
cd seedance-video-api-python
pip install .
```

---

## Настройка

Получите ключ в личном кабинете [normahub.cc](https://normahub.cc) и экспортируйте переменную окружения:

```bash
export NORMAHUB_API_KEY="nr_hub_..."
```

---

## Примеры использования

> 🚀 **Интерактивный запуск в 1 клик:** Откройте готовый Jupyter-блокнот в Google Colab: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/normahubcc/seedance-video-api-python/blob/main/examples/seedance_video_quickstart.ipynb)

### 1. Синхронная генерация (Text-to-Video)

```python
from seedance import NormaVideoClient

client = NormaVideoClient()

# Создает задачу, ожидает рендера и скачивает MP4
path = client.generate_and_download(
    prompt="Киберпанк мегаполис, неоновый дождь, 4k",
    model="seedance-2.5",
    output_path="cyberpunk.mp4"
)
print(f"Видео сохранено: {path}")
```

### 2. Асинхронный вызов (`AsyncNormaVideoClient`)

Для сервисов на базе FastAPI, aiohttp или aiogram:

```python
import asyncio
from seedance import AsyncNormaVideoClient

async def main():
    client = AsyncNormaVideoClient()
    path = await client.generate_and_download(
        prompt="Космический корабль выходит на орбиту Сатурна",
        model="seedance-2.5",
        duration=5,
        output_path="saturn.mp4"
    )
    print(f"Готово: {path}")

asyncio.run(main())
```

### 3. Оживление изображений (Image-to-Video)

```python
from seedance import NormaVideoClient

client = NormaVideoClient()

path = client.generate_and_download(
    prompt="Персонаж плавно поворачивает голову и улыбается",
    model="seedance-2.5",
    image_path="portrait.png",  # Локальный файл автоматически конвертируется в Data URI
    output_path="animated.mp4"
)
```

### 4. Создание задачи и ручной опрос статуса

Подходит для очередей задач (Celery, Redis Queue):

```python
from seedance import NormaVideoClient

client = NormaVideoClient()

# Возвращает объект задачи с ID
task = client.create_task(
    prompt="Закат над океаном",
    model="seedance-2.5",
    duration=5
)
print(f"Task ID: {task.id}")

# Проверка статуса
status = client.get_status(task.id)
if status.is_successful:
    print(f"URL: {status.video_url}")
```

---

## CLI

```bash
# Генерация из текста
seedance "Космонавт идет по песчаным дюнам Марса" -o mars.mp4

# Image-to-Video
seedance "Плавное движение воды в водопаде" -i waterfall.jpg -o waterfall.mp4

# Выбор модели и параметров
seedance "Ночной город" --model seedance-2.5 --duration 5 --aspect-ratio 16:9 -o city.mp4
```

### Флаги CLI

| Параметр | Описание | По умолчанию |
|---|---|---|
| `prompt` | Описание сцены | *Обязательный* |
| `-i, --image` | Путь к изображению или URL | `None` |
| `-o, --output` | Выходной файл MP4 | `output.mp4` |
| `-m, --model` | Модель (`seedance-2.5`, `seedance-2.0`, `grok-imagine-video-1.5`) | `seedance-2.5` |
| `-d, --duration` | Длительность (сек) | `5` |
| `--aspect-ratio` | Соотношение сторон (`16:9`, `9:16`, `1:1`) | `16:9` |
| `-t, --timeout` | Таймаут ожидания (сек) | `300` |
| `--api-key` | API-ключ (по умолчанию берется из `$NORMAHUB_API_KEY`) | `None` |

---

## Модели

| Model ID | Вендор | Назначение |
|---|---|---|
| `seedance-2.5` | ByteDance / SeeDance | 1080p кинематографичное видео, T2V и I2V |
| `seedance-2.0` | ByteDance / SeeDance | Базовое HD видео |
| `seedance-2.0-fast` | ByteDance / SeeDance | Быстрый рендер для превью |
| `grok-imagine-video-1.5` | xAI | Стилизованная видеогенерация Grok |

Полный каталог моделей доступен на [normahub.cc/models](https://normahub.cc/models).

---

## Лицензия

MIT License. См. [LICENSE](LICENSE).
