import React, { useState } from 'react';
import { Bell, BellOff } from 'lucide-react';
import { useNotifications } from '../../hooks/useNotifications';

export const NotificationCenter: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const {
    notifications,
    unreadCount,
    loading,
    error,
    markAsRead,
    markAllAsRead,
    clearError
  } = useNotifications();

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'text-red-600';
      case 'medium':
        return 'text-yellow-600';
      default:
        return 'text-blue-600';
    }
  };

  if (error) {
    return (
      <div className="text-red-500 p-2" onClick={clearError}>
        Error: {error}
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Кнопка уведомлений */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-full hover:bg-gray-100"
      >
        {unreadCount > 0 ? (
          <>
            <Bell className="h-6 w-6" />
            <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
              {unreadCount}
            </span>
          </>
        ) : (
          <BellOff className="h-6 w-6 text-gray-400" />
        )}
      </button>

      {/* Панель уведомлений */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 bg-white rounded-lg shadow-lg border border-gray-200 max-h-[80vh] overflow-y-auto">
          <div className="p-4 border-b border-gray-200 flex justify-between items-center">
            <h3 className="text-lg font-semibold">Notifications</h3>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Mark all as read
              </button>
            )}
          </div>

          <div className="divide-y divide-gray-200">
            {loading ? (
              <div className="p-4 text-center text-gray-500">
                Loading...
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-4 text-center text-gray-500">
                No notifications
              </div>
            ) : (
              notifications.map(notification => (
                <div
                  key={notification.id}
                  className={`p-4 ${
                    notification.status === 'unread'
                      ? 'bg-blue-50'
                      : 'bg-white'
                  }`}
                  onClick={() => notification.status === 'unread' && markAsRead(notification.id)}
                >
                  {notification.data.alerts.map((alert, index) => (
                    <div
                      key={index}
                      className={`mb-2 ${getSeverityColor(alert.severity)}`}
                    >
                      {alert.message}
                    </div>
                  ))}
                  
                  <div className="mt-2 text-sm text-gray-600">
                    Portfolio Value: ${notification.data.portfolio.total_value.toLocaleString()}
                    <br />
                    Daily P&L: {notification.data.portfolio.daily_pnl_percent > 0 ? '+' : ''}
                    {notification.data.portfolio.daily_pnl_percent.toFixed(2)}%
                    (${notification.data.portfolio.daily_pnl.toLocaleString()})
                  </div>
                  
                  <div className="mt-2 text-xs text-gray-400">
                    {new Date(notification.created_at).toLocaleString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}; 