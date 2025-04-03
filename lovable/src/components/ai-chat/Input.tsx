import React, { useState } from 'react'
import styles from './Input.module.css'

interface InputProps {
  onSend: (message: string) => void
  disabled?: boolean
}

export const Input: React.FC<InputProps> = ({ onSend, disabled = false }) => {
  const [message, setMessage] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim() && !disabled) {
      onSend(message)
      setMessage('')
    }
  }

  return (
    <form onSubmit={handleSubmit} className={styles.form}>
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Введите сообщение..."
        disabled={disabled}
        className={styles.input}
      />
      <button
        type="submit"
        disabled={disabled || !message.trim()}
        className={styles.button}
      >
        Отправить
      </button>
    </form>
  )
} 