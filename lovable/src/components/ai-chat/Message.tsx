import React from 'react'
import styles from './Message.module.css'

interface MessageProps {
  type: 'user' | 'assistant'
  content: string
}

export const Message: React.FC<MessageProps> = ({ type, content }) => {
  return (
    <div className={`${styles.message} ${styles[type]}`}>
      <div className={styles.content}>
        {content}
      </div>
    </div>
  )
} 