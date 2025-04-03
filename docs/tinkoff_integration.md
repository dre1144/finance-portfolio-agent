# Интеграция с Tinkoff Invest API

## Особенности API

### Аутентификация
- Использование токена доступа через заголовок `Authorization: Bearer <token>`
- Токен должен иметь права на чтение портфеля и операций
- Рекомендуется использовать readonly-токен для безопасности

### Зависимости
```python
# Основные зависимости
tinkoff-investments==0.2.0b51  # Официальный SDK
aiohttp==3.9.3                 # Для асинхронных HTTP запросов
pytz==2024.1                   # Для работы с таймзонами
pandas==2.2.1                  # Для обработки данных

# Опциональные зависимости
numpy==1.26.4                  # Для вычислений
plotly==5.19.0                # Для визуализации
```

### Особенности работы с API

#### Ограничения и квоты
- Лимит на количество запросов: 120 запросов в минуту
- Рекомендуется использовать кэширование для часто запрашиваемых данных
- Некоторые эндпоинты имеют собственные лимиты

#### Обработка ошибок
1. **Сетевые ошибки**
```python
try:
    async with client.get(url) as response:
        if response.status == 429:  # Too Many Requests
            await asyncio.sleep(1)  # Пауза перед повторной попыткой
            return await retry_request()
        response.raise_for_status()
        return await response.json()
except aiohttp.ClientError as e:
    logger.error(f"Network error: {e}")
    raise TinkoffAPIError("Network error") from e
```

2. **Ошибки API**
```python
if response.status == 400:
    error_data = await response.json()
    if "message" in error_data:
        raise TinkoffAPIError(error_data["message"])
```

3. **Обработка таймаутов**
```python
async with timeout(30):  # 30 секунд таймаут
    try:
        return await make_request()
    except asyncio.TimeoutError:
        logger.warning("Request timeout")
        raise TinkoffAPIError("Request timeout")
```

#### Форматы данных

1. **Даты и время**
- API ожидает и возвращает даты в формате ISO 8601
- Необходимо конвертировать в UTC при отправке
- Ответы приходят в UTC, нужно конвертировать в локальное время
```python
from datetime import datetime
import pytz

def to_api_date(dt: datetime) -> str:
    return dt.astimezone(pytz.UTC).isoformat()

def from_api_date(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str).astimezone(pytz.UTC)
```

2. **Денежные значения**
- Суммы приходят в минимальных единицах (копейках)
- Необходимо конвертировать в рубли для отображения
```python
def convert_money(amount: int, currency: str) -> float:
    return amount / 100.0  # копейки в рубли
```

### Полезные эндпоинты

1. **Портфель**
- `/portfolio` - текущий портфель
- `/portfolio/currencies` - валютные позиции
- `/portfolio/positions` - все позиции

2. **Операции**
- `/operations` - история операций
- Важные параметры:
  - `from` - начало периода
  - `to` - конец периода
  - `state` - статус операций (EXECUTED, CANCELED, etc.)

3. **Инструменты**
- `/market/instruments` - информация об инструментах
- `/market/candles` - исторические данные

### Рекомендации по реализации

1. **Кэширование**
```python
class Cache:
    def __init__(self, ttl: int = 300):  # 5 минут по умолчанию
        self.data = {}
        self.ttl = ttl
        self.timestamps = {}

    async def get_or_fetch(self, key: str, fetch_func: Callable):
        if key in self.data:
            if time.time() - self.timestamps[key] < self.ttl:
                return self.data[key]
        
        value = await fetch_func()
        self.data[key] = value
        self.timestamps[key] = time.time()
        return value
```

2. **Переподключение**
```python
async def with_retry(func: Callable, max_attempts: int = 3):
    attempt = 0
    while attempt < max_attempts:
        try:
            return await func()
        except TinkoffAPIError as e:
            attempt += 1
            if attempt == max_attempts:
                raise
            await asyncio.sleep(1 * attempt)  # Увеличивающаяся пауза
```

3. **Логирование**
```python
import logging

logger = logging.getLogger("tinkoff_api")
logger.setLevel(logging.INFO)

# Добавляем информативное логирование
logger.info("Fetching portfolio", extra={"account_id": account_id})
logger.error("API error", extra={"error": str(e), "endpoint": "/portfolio"})
```

### Известные проблемы

1. **Несоответствие форматов дат**
- Проблема: API может возвращать даты в разных форматах
- Решение: Использовать гибкий парсер дат
```python
def parse_date(date_str: str) -> datetime:
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unknown date format: {date_str}")
```

2. **Задержки в обновлении данных**
- Проблема: Данные по операциям могут появляться с задержкой
- Решение: Добавить буфер времени при запросе данных
```python
from_date = target_date - timedelta(minutes=5)
to_date = target_date + timedelta(minutes=5)
```

3. **Различия в валютах**
- Проблема: Разные эндпоинты могут возвращать суммы в разных валютах
- Решение: Явное указание валюты в ответах и конвертация
```python
def normalize_currency(amount: float, from_currency: str, to_currency: str) -> float:
    if from_currency == to_currency:
        return amount
    # Получаем курс конвертации
    rate = get_exchange_rate(from_currency, to_currency)
    return amount * rate
```

## Следующие шаги

1. Создание изолированного API клиента
2. Реализация системы кэширования
3. Добавление мониторинга и метрик
4. Реализация автоматических тестов 