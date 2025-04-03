import { supabase } from '../config/supabase'

export type RequestType = 'portfolio' | 'analysis' | 'chat'

export interface MCPResponse {
  success: boolean
  error?: string
  data?: any
}

export const mcpService = {
  async request(type: RequestType): Promise<MCPResponse> {
    try {
      const { data, error } = await supabase.functions.invoke('mcp-agent', {
        body: { type }
      })

      if (error) throw error

      return {
        success: true,
        data
      }
    } catch (error) {
      return {
        success: false,
        error: error.message
      }
    }
  },

  // Методы для конкретных типов запросов
  async getPortfolio() {
    return this.request('portfolio')
  },

  async getAnalysis() {
    return this.request('analysis')
  },

  async sendMessage(message: string) {
    return this.request('chat')
  }
} 