import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { corsHeaders } from '../_shared/cors.ts'
import { config } from './config.ts'
import { RequestType, ResponseType, PortfolioResponse, AnalysisResponse, ChatResponse } from './types.ts'

// Мок-данные для портфеля
const mockPortfolio = {
  totalValue: 1000000,
  positions: [
    {
      ticker: 'SBER',
      name: 'Сбербанк',
      quantity: 100,
      averagePrice: 250,
      currentPrice: 300,
      pnl: 5000,
      pnlPercent: 20
    },
    {
      ticker: 'GAZP',
      name: 'Газпром',
      quantity: 200,
      averagePrice: 150,
      currentPrice: 180,
      pnl: 6000,
      pnlPercent: 20
    }
  ]
}

// Мок-ответы для разных типов запросов
const mockResponses: Record<RequestType, ResponseType> = {
  portfolio: {
    success: true,
    data: mockPortfolio
  } as PortfolioResponse,
  analysis: {
    success: true,
    data: {
      riskLevel: 'medium',
      diversification: 'good',
      recommendations: [
        'Рекомендуется увеличить долю облигаций до 30%',
        'Стоит рассмотреть покупку акций технологического сектора'
      ]
    }
  } as AnalysisResponse,
  chat: {
    success: true,
    data: {
      message: 'Ваш портфель хорошо диверсифицирован, но есть возможности для оптимизации. Рекомендую рассмотреть увеличение доли облигаций для снижения рисков.'
    }
  } as ChatResponse
}

serve(async (req) => {
  // CORS headers
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Проверка размера запроса
    const contentLength = Number(req.headers.get('content-length') || 0)
    if (contentLength > config.maxRequestSize) {
      throw new Error('Request body too large')
    }

    const { type } = await req.json()

    // Проверка типа запроса
    if (!type || !(type in mockResponses)) {
      throw new Error('Invalid request type')
    }

    // Возвращаем соответствующий мок-ответ
    const response = mockResponses[type as RequestType]

    return new Response(
      JSON.stringify(response),
      { 
        headers: { 
          ...corsHeaders,
          'Content-Type': 'application/json' 
        } 
      }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ 
        success: false, 
        error: error.message 
      }),
      { 
        headers: { 
          ...corsHeaders,
          'Content-Type': 'application/json' 
        },
        status: 400
      }
    )
  }
}) 