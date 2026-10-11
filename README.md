# SeeDance & Grok Video API Python SDK (S-Tier)

[![PyPI Version](https://img.shields.io/badge/pypi-v0.2.0-blue.svg)](https://pypi.org)
[![Python Support](https://img.shields.io/badge/python-3.9+-3776AB.svg?logo=python&logoColor=white)](https://pypi.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![NormaHub Gateway](https://img.shields.io/badge/API-NormaHub%20Direct-7B48E8.svg)](https://normahub.cc/?utm_source=github&utm_medium=oss&utm_campaign=seedance-video-api-python&utm_content=badge)
[![No VPN](https://img.shields.io/badge/VPN-Not%20Required%20(РФ)-success.svg)](https://normahub.cc)
[![Billing](https://img.shields.io/badge/Оплата-Карты%20РФ%20%2F%20СБП-orange.svg)](https://normahub.cc)
[![Async Native](https://img.shields.io/badge/Async-Native%20asyncio-brightgreen.svg)](#2-нативная-асинхронность-asyncnormavideoclient)
[![Image-to-Video](https://img.shields.io/badge/I2V-Image--to--Video%20Ready-blueviolet.svg)](#3-оживление-картинок-image-to-video)

Официальная Python-библиотека и интерактивная CLI-утилита корпоративного уровня (S-Tier) для генерации видео нейросетями **SeeDance 2.5 / 2.0** и **xAI Grok Imagine Video** через единый OpenAI-совместимый шлюз [NormaHub](https://normahub.cc/?utm_source=github&utm_medium=oss&utm_campaign=seedance-video-api-python&utm_content=hero_link).

Прямой доступ из России, оплата рублями (карты РФ, СБП), без зарубежных карт и без VPN.

---

## ⚡ Особенности библиотеки (S-Tier)

- **Zero External Dependencies:** Работает исключительно на стандартной библиотеке Python 3.9+ (`urllib` + `asyncio`). Никаких конфликтов версий `requests`, `urllib3` или `aiohttp`.
- **Нативная асинхронность (`AsyncNormaVideoClient`):** Полноценная поддержка `async`/`await` для Telegram-ботов (aiogram 3), FastAPI, Discord-ботов и микросервисов.
- **Image-to-Video (I2V):** Автоматическая конвертация локальных картинок (`.png`, `.jpg`, `.webp`) в Base64 Data URI и поддержка прямых web-ссылок (`image_url`).
- **Сетевая отказоустойчивость (Transparent Retries):** Автоматические повторы (3 попытки с exponential backoff и случайным jitter) при временных сбоях сети и кодах 502 Bad Gateway, 503 Service Unavailable, 524 Timeout.
- **Премиальный CLI:** Живой спиннер, цветные бейджи статусов (`PENDING`, `PROCESSING`, `COMPLETED`), форматированные панели и таймстампы на базе `rich` с элегантным ANSI-fallback.

---

## 🚀 Быстрый старт

### 1. Установка
```bash
pip install seedance-video-api
```
*(Или скопируйте модуль `seedance/` в корень вашего проекта).*

### 2. Получение API-ключа
Зарегистрируйтесь на [normahub.cc](https://normahub.cc/?utm_source=github&utm_medium=oss&utm_campaign=seedance-video-api-python&utm_content=get_key) и выпустите API-ключ в личном кабинете.

Установите переменную окружения:
```bash
export NORMAHUB_API_KEY="nr_hub_ваш_ключ"
```

---

## 💻 Примеры использования (Python)

### 1. Синхронная генерация (Text-to-Video) в 3 строки:
```python
from seedance import NormaVideoClient

client = NormaVideoClient()

# Генерирует видео и автоматически скачивает готовый MP4
video_path = client.generate_and_download(
    prompt="Киберпанк мегаполис, неоновый дождь, летающие автомобили, 4k photorealistic",
    model="seedance-2.5",
    output_path="cyberpunk_city.mp4"
)

print(f"Видео сохранено в: {video_path}")
```

### 2. Нативная асинхронность (`AsyncNormaVideoClient`):
Идеально для **FastAPI**, **aiogram 3** и очередей задач без блокировки event loop:

```python
import asyncio
from seedance import AsyncNormaVideoClient

async def main():
    client = AsyncNormaVideoClient()

    video_path = await client.generate_and_download(
        prompt="Космический корабль гиперпрыжком выходит на орбиту Сатурна",
        model="seedance-2.5",
        duration=5,
        output_path="saturn.mp4"
    )
    print(f"Готово: {video_path}")

asyncio.run(main())
```

### 3. Оживление картинок (Image-to-Video):
Передайте путь к локальному файлу через `image_path` (он автоматически преобразуется в Data URI) или ссылку через `image_url`:

```python
from seedance import NormaVideoClient

client = NormaVideoClient()

# Оживление портрета или арта
video_path = client.generate_and_download(
    prompt="Персонаж плавно улыбается, поворачивает голову и смотрит в камеру, кинематографичное освещение",
    model="seedance-2.5",
    image_path="portrait.png",  # Автоматический Base64 Data URI!
    output_path="animated_portrait.mp4"
)
```

### 4. Неблокирующий запуск с контролем очередей:
```python
from seedance import NormaVideoClient

client = NormaVideoClient()

# Мгновенно отправляет задачу в очередь NormaHub
task = client.create_task(
    prompt="Закат над океаном на футуристической планете",
    model="seedance-2.5",
    duration=5
)
print(f"Задача создана! ID: {task.id}")

# Проверка статуса (pending / processing / completed)
status = client.get_status(task.id)
if status.is_successful:
    print(f"Ссылка на скачивание: {status.video_url}")
```

---

## 🖥️ Использование из командной строки (CLI)

Библиотека включает встроенную консольную команду `seedance`:

```bash
# Текстовая генерация:
seedance "Космонавт идет по песчаным дюнам Марса" -o mars.mp4

# Оживление изображения (Image-to-Video):
seedance "Оживи воду в водопаде, плавное движение камеры вперед" \
  -i waterfall.jpg \
  -o waterfall.mp4

# Выбор модели, длительности и соотношения сторон:
seedance "Неоновый замок в ночных горах" \
  --model seedance-2.5 \
  --duration 5 \
  --aspect-ratio 16:9 \
  --output castle.mp4
```

### Параметры CLI:

| Флаг | Описание | По умолчанию |
|---|---|---|
| `prompt` | Текстовое описание сцены или движения | *Обязательный* |
| `-i, --image` | Путь к локальной картинке или URL для Image-to-Video | `None` |
| `-o, --output` | Имя сохраняемого файла `.mp4` | `output.mp4` |
| `-m, --model` | Модель (`seedance-2.5`, `seedance-2.0`, `grok-imagine-video-1.5`) | `seedance-2.5` |
| `-d, --duration` | Длительность ролика в секундах | `5` |
| `--aspect-ratio` | Соотношение сторон (`16:9`, `9:16`, `1:1`) | `16:9` |
| `-t, --timeout` | Максимальное время ожидания рендера в секундах | `300` |
| `--api-key` | API-ключ NormaHub (по умолчанию из `$NORMAHUB_API_KEY`) | `None` |

---

## 📊 Доступные видео-модели NormaHub

| Модель (Model ID) | Вендор | Назначение / Разрешение | Тарификация |
|---|---|---|---|
| `seedance-2.5` | SeeDance | Флагман: кинематографичное качество 1080p, реалистичная физика, T2V и I2V | Фикс. за видео |
| `seedance-2.0` | SeeDance | Базовая генерация высокой четкости | Фикс. за видео |
| `seedance-2.0-fast`| SeeDance | Ускоренный рендер для превью | Фикс. за видео |
| `grok-imagine-video-1.5` | xAI | Стилизованная динамика xAI Grok | Фикс. за видео |

Полный каталог текстовых и графических моделей доступен на [normahub.cc/models](https://normahub.cc/models).

---

## 💡 Преимущества перед прямым доступом

| Параметр | Официальный доступ | Через NormaHub API |
|---|---|---|
| **Способ оплаты** | Иностранные карты / криптобиржи | **Карты РФ, СБП, рубли** |
| **Доступность** | Блокировки по IP, обязательный VPN | **Прямой маршрут из РФ без VPN** |
| **Интеграция** | Отдельный API для каждого вендора | **Единый OpenAI-совместимый API** |
| **Лимиты** | Непредсказуемые списания | Жесткий настраиваемый лимит на каждый ключ |

---

## 🎁 Промокод на приветственный баланс

Используйте промокод **`GH-SEEDANCE`** при регистрации на [normahub.cc](https://normahub.cc/?utm_source=github&utm_medium=oss&utm_campaign=seedance-video-api-python&utm_content=promo) — он начислит **200 ₽** на ваш баланс для бесплатной тестовой генерации видеороликов.

---

## 📚 Полезные ссылки
- Сравнение AI API провайдеров в РФ: [normahub.cc/company/articles/ai-api-provaydery-rossii-sravnenie](https://normahub.cc/company/articles/ai-api-provaydery-rossii-sravnenie)
- Официальный Telegram-канал: [@nhubcc](https://t.me/nhubcc)
- Поддержка: [@NhubManager](https://t.me/NhubManager)

---

## Лицензия
Распространяется под свободной лицензией [MIT](LICENSE).
