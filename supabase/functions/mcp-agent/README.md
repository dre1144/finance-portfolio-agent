# MCP Agent Edge Function

Edge Function для интеграции MCP агента с Lovable через Supabase.

## Структура

```
mcp-agent/
├── index.ts          # Основной файл Edge Function
├── config.ts         # Конфигурация
├── types.ts          # Типы данных
├── test.ts           # Тесты
└── README.md         # Документация
```

## API

### Запросы

Edge Function принимает POST запросы с JSON телом следующего формата:

```typescript
{
  type: 'portfolio' | 'analysis' | 'chat'
}
```

### Ответы

#### Portfolio Response
```typescript
{
  success: true,
  data: {
    totalValue: number,
    positions: Array<{
      ticker: string,
      name: string,
      quantity: number,
      averagePrice: number,
      currentPrice: number,
      pnl: number,
      pnlPercent: number
    }>
  }
}
```

#### Analysis Response
```typescript
{
  success: true,
  data: {
    riskLevel: 'low' | 'medium' | 'high',
    diversification: 'poor' | 'good' | 'excellent',
    recommendations: string[]
  }
}
```

#### Chat Response
```typescript
{
  success: true,
  data: {
    message: string
  }
}
```

## Разработка

### Локальная разработка

1. Установите Deno
2. Запустите Edge Function локально:
```bash
deno run --allow-net index.ts
```

### Тестирование

Запустите тесты:
```bash
deno test --allow-net test.ts
```

## Развертывание

Для развертывания Edge Function используйте Supabase CLI:

```bash
supabase functions deploy mcp-agent
``` 