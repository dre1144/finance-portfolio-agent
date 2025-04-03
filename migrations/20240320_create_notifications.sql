-- Create notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    priority TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    read BOOLEAN DEFAULT false,
    dismissed BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL,
    
    -- Индексы для быстрого поиска
    CONSTRAINT notifications_user_created_idx UNIQUE (user_id, created_at)
);

-- Добавляем RLS политики
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Пользователи могут видеть только свои уведомления
CREATE POLICY "Users can view their own notifications"
    ON notifications
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- Пользователи могут обновлять только свои уведомления
CREATE POLICY "Users can update their own notifications"
    ON notifications
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id);

-- Создаем индексы для быстрого поиска
CREATE INDEX notifications_user_read_idx ON notifications (user_id, read);
CREATE INDEX notifications_user_dismissed_idx ON notifications (user_id, dismissed);
CREATE INDEX notifications_created_at_idx ON notifications (created_at DESC);

-- Функция для подсчета непрочитанных уведомлений
CREATE OR REPLACE FUNCTION count_unread_notifications(p_user_id UUID)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM notifications
        WHERE user_id = p_user_id
        AND read = false
        AND dismissed = false
    );
END;
$$;

-- Функция для удаления старых уведомлений
CREATE OR REPLACE FUNCTION delete_old_notifications(p_days INTEGER)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    DELETE FROM notifications
    WHERE created_at < NOW() - (p_days || ' days')::INTERVAL;
END;
$$;

-- Функция для отправки realtime уведомлений
CREATE OR REPLACE FUNCTION broadcast_notification(p_user_id UUID, p_notification JSONB)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Отправляем уведомление через Supabase Realtime
    PERFORM pg_notify(
        'notifications',
        json_build_object(
            'user_id', p_user_id,
            'notification', p_notification
        )::text
    );
END;
$$;

-- Комментарии к таблице и колонкам
COMMENT ON TABLE notifications IS 'User notifications for portfolio changes and alerts';
COMMENT ON COLUMN notifications.user_id IS 'Reference to auth.users table';
COMMENT ON COLUMN notifications.type IS 'Type of notification (portfolio_change, price_target, risk_alert, etc)';
COMMENT ON COLUMN notifications.title IS 'Notification title';
COMMENT ON COLUMN notifications.message IS 'Notification message';
COMMENT ON COLUMN notifications.priority IS 'Notification priority (low, normal, high, urgent)';
COMMENT ON COLUMN notifications.metadata IS 'Additional notification data in JSON format';
COMMENT ON COLUMN notifications.read IS 'Whether the notification has been read';
COMMENT ON COLUMN notifications.dismissed IS 'Whether the notification has been dismissed';
COMMENT ON COLUMN notifications.created_at IS 'When the notification was created'; 