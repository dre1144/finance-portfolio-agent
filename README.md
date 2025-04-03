# MCP Finance Agent

Model Context Protocol агент для анализа финансового портфеля и генерации рекомендаций.

## Возможности

- Интеграция с Tinkoff Invest API
- Анализ портфеля и рисков
- Генерация рекомендаций по оптимизации портфеля
- Мониторинг рыночных данных
- Расчет метрик эффективности

## Установка

1. Убедитесь, что у вас установлен Python 3.11+
2. Установите Poetry:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd mcp-finance-agent
```

4. Установите зависимости:
```bash
poetry install
```

5. Создайте файл .env на основе .env.example:
```bash
cp .env.example .env
```

6. Настройте переменные окружения в .env

## Разработка

1. Активируйте виртуальное окружение:
```bash
poetry shell
```

2. Установите pre-commit хуки:
```bash
pre-commit install
```

3. Запустите тесты:
```bash
pytest
```

## Использование

1. Запустите агента:
```bash
poetry run python -m src.main
```

2. API будет доступно по адресу: http://localhost:8000

## Тестирование

```bash
# Запуск всех тестов с отчетом о покрытии
pytest

# Запуск конкретного теста
pytest tests/test_specific.py

# Запуск тестов с метками
pytest -m "not integration"
```

## Структура проекта

```
mcp_finance_agent/
├── src/
│   ├── agent/            # Ядро MCP агента
│   ├── services/         # Внешние сервисы
│   └── models/          # Модели данных
├── tests/               # Тесты
└── docs/               # Документация
```

## Лицензия

MIT 