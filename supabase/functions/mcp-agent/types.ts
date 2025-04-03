// Типы запросов
export type RequestType = 'portfolio' | 'analysis' | 'chat'

// Типы ответов
export interface BaseResponse {
  success: boolean
  error?: string
}

export interface PortfolioResponse extends BaseResponse {
  data?: {
    totalValue: number
    positions: Array<{
      ticker: string
      name: string
      quantity: number
      averagePrice: number
      currentPrice: number
      pnl: number
      pnlPercent: number
    }>
  }
}

export interface AnalysisResponse extends BaseResponse {
  data?: {
    riskLevel: 'low' | 'medium' | 'high'
    diversification: 'poor' | 'good' | 'excellent'
    recommendations: string[]
  }
}

export interface ChatResponse extends BaseResponse {
  data?: {
    message: string
  }
}

// Общий тип ответа
export type ResponseType = PortfolioResponse | AnalysisResponse | ChatResponse 