# Используем Python 3.9 как базовый образ
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем Poetry
RUN pip install poetry

# Копируем файлы конфигурации
COPY pyproject.toml poetry.lock ./
COPY .mcp.yaml ./

# Устанавливаем зависимости через Poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Копируем исходный код
COPY src/ ./src/
COPY mcp_finance_agent/ ./mcp_finance_agent/

# Устанавливаем переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Запускаем агента
CMD ["python", "-m", "src.agent.base"] 