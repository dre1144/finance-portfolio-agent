export const config = {
  // Максимальное время выполнения функции (в секундах)
  maxExecutionTime: 30,
  
  // Размер максимального тела запроса (в байтах)
  maxRequestSize: 1024 * 1024, // 1MB
  
  // Настройки кэширования
  cache: {
    enabled: true,
    ttl: 60 * 5, // 5 минут
  },
  
  // Настройки логирования
  logging: {
    enabled: true,
    level: 'info',
  },
  
  // Настройки безопасности
  security: {
    // Список разрешенных доменов для CORS
    allowedOrigins: ['*'],
    // Максимальное количество запросов в минуту
    rateLimit: 60,
  }
} 