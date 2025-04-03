-- Создаем таблицу для хранения подключений пользователей
CREATE TABLE user_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    broker_type TEXT NOT NULL,
    encrypted_token TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_check_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(user_id, broker_type)
);

-- Добавляем RLS политики
ALTER TABLE user_connections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own connections"
    ON user_connections FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own connections"
    ON user_connections FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own connections"
    ON user_connections FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own connections"
    ON user_connections FOR DELETE
    USING (auth.uid() = user_id);

-- Создаем таблицу для уведомлений
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unread',
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Добавляем RLS политики для уведомлений
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own notifications"
    ON notifications FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own notifications"
    ON notifications FOR UPDATE
    USING (auth.uid() = user_id);

-- Функция для получения активных подключений
CREATE OR REPLACE FUNCTION get_active_connections()
RETURNS SETOF user_connections
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT *
    FROM user_connections
    WHERE is_active = true
    AND (
        last_check_at IS NULL
        OR last_check_at < NOW() - INTERVAL '5 minutes'
    );
$$;

-- Функция для получения расшифрованного токена
CREATE OR REPLACE FUNCTION get_broker_token(p_connection_id UUID)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_token TEXT;
    v_key TEXT;
BEGIN
    -- Получаем ключ шифрования из переменных окружения
    v_key := current_setting('app.encryption_key');
    
    -- Получаем и расшифровываем токен
    SELECT pgp_sym_decrypt(
        encrypted_token::bytea,
        v_key
    )::TEXT INTO v_token
    FROM user_connections
    WHERE id = p_connection_id;
    
    RETURN v_token;
END;
$$;

-- Функция для отправки уведомления через Realtime
CREATE OR REPLACE FUNCTION broadcast_notification(
    p_user_id UUID,
    p_notification_id UUID
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Отправляем событие в канал пользователя
    PERFORM pg_notify(
        'user_notifications',
        json_build_object(
            'user_id', p_user_id,
            'notification_id', p_notification_id
        )::text
    );
END;
$$; 