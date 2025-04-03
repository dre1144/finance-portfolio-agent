import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import { useAuth } from '../contexts/AuthContext';

export interface Alert {
  type: string;
  severity: string;
  message: string;
}

export interface PortfolioData {
  total_value: number;
  daily_pnl: number;
  daily_pnl_percent: number;
}

export interface Notification {
  id: string;
  type: string;
  status: string;
  data: {
    alerts: Alert[];
    portfolio: PortfolioData;
  };
  created_at: string;
}

export const useNotifications = () => {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      setNotifications([]);
      setUnreadCount(0);
      setLoading(false);
      return;
    }

    const loadNotifications = async () => {
      try {
        setLoading(true);
        const { data, error: fetchError } = await supabase
          .from('notifications')
          .select('*')
          .eq('user_id', user.id)
          .order('created_at', { ascending: false })
          .limit(50);

        if (fetchError) throw fetchError;

        setNotifications(data);
        setUnreadCount(data.filter(n => n.status === 'unread').length);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load notifications');
      } finally {
        setLoading(false);
      }
    };

    loadNotifications();

    // Подписываемся на новые уведомления
    const channel = supabase
      .channel(`user_notifications:${user.id}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'notifications',
          filter: `user_id=eq.${user.id}`,
        },
        (payload) => {
          setNotifications(prev => [payload.new as Notification, ...prev]);
          setUnreadCount(prev => prev + 1);
        }
      )
      .subscribe();

    return () => {
      channel.unsubscribe();
    };
  }, [user]);

  const markAsRead = async (notificationId: string) => {
    try {
      const { error: updateError } = await supabase
        .from('notifications')
        .update({ status: 'read' })
        .eq('id', notificationId);

      if (updateError) throw updateError;

      setNotifications(prev =>
        prev.map(n =>
          n.id === notificationId ? { ...n, status: 'read' } : n
        )
      );
      setUnreadCount(prev => prev - 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to mark notification as read');
    }
  };

  const markAllAsRead = async () => {
    try {
      const { error: updateError } = await supabase
        .from('notifications')
        .update({ status: 'read' })
        .eq('user_id', user?.id)
        .eq('status', 'unread');

      if (updateError) throw updateError;

      setNotifications(prev =>
        prev.map(n => ({ ...n, status: 'read' }))
      );
      setUnreadCount(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to mark all notifications as read');
    }
  };

  const clearError = () => setError(null);

  return {
    notifications,
    unreadCount,
    loading,
    error,
    markAsRead,
    markAllAsRead,
    clearError,
  };
}; 