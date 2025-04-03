import React, { useState, useRef, useEffect } from 'react'
import { mcpService } from '../../services/mcp'
import { Message } from './Message'
import { Input } from './Input'
import styles from './Chat.module.css'

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Array<{
    type: 'user' | 'assistant'
    content: string
  }>>([])
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return

    // Добавляем сообщение пользователя
    setMessages(prev => [...prev, { type: 'user', content: message }])
    setIsLoading(true)

    try {
      // Отправляем запрос в Edge Function
      const response = await mcpService.sendMessage(message)

      if (response.success) {
        // Добавляем ответ ассистента
        setMessages(prev => [...prev, { 
          type: 'assistant', 
          content: response.data.message 
        }])
      } else {
        // Обрабатываем ошибку
        setMessages(prev => [...prev, { 
          type: 'assistant', 
          content: 'Извините, произошла ошибка. Пожалуйста, попробуйте позже.' 
        }])
      }
    } catch (error) {
      setMessages(prev => [...prev, { 
        type: 'assistant', 
        content: 'Извините, произошла ошибка. Пожалуйста, попробуйте позже.' 
      }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={styles.chat}>
      <div className={styles.messages}>
        {messages.map((message, index) => (
          <Message
            key={index}
            type={message.type}
            content={message.content}
          />
        ))}
        {isLoading && (
          <Message
            type="assistant"
            content="..."
          />
        )}
        <div ref={messagesEndRef} />
      </div>
      <Input
        onSend={handleSendMessage}
        disabled={isLoading}
      />
    </div>
  )
} 