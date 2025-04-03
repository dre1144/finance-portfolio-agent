-- Включаем расширение для шифрования
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Функция для шифрования токена
CREATE OR REPLACE FUNCTION encrypt_token(
    p_token TEXT,
    p_user_id UUID
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_key TEXT;
BEGIN
    -- Получаем ключ шифрования из переменных окружения
    v_key := current_setting('app.encryption_key');
    
    -- Шифруем токен с использованием ключа
    RETURN pgp_sym_encrypt(
        p_token,
        v_key
    )::TEXT;
END;
$$;

-- Функция для расшифровки токена
CREATE OR REPLACE FUNCTION decrypt_token(
    p_encrypted_token TEXT,
    p_user_id UUID
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_key TEXT;
    v_token TEXT;
BEGIN
    -- Проверяем, что пользователь имеет доступ к токену
    IF NOT EXISTS (
        SELECT 1
        FROM user_connections
        WHERE user_id = p_user_id
        AND encrypted_token = p_encrypted_token
    ) THEN
        RAISE EXCEPTION 'Access denied';
    END IF;

    -- Получаем ключ шифрования из переменных окружения
    v_key := current_setting('app.encryption_key');
    
    -- Расшифровываем токен
    SELECT pgp_sym_decrypt(
        p_encrypted_token::bytea,
        v_key
    )::TEXT INTO v_token;
    
    RETURN v_token;
END;
$$;

-- Функция для создания подключения с шифрованием токена
CREATE OR REPLACE FUNCTION create_user_connection(
    p_user_id UUID,
    p_broker_type TEXT,
    p_token TEXT
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_connection_id UUID;
BEGIN
    -- Проверяем, что пользователь существует
    IF NOT EXISTS (
        SELECT 1 FROM auth.users WHERE id = p_user_id
    ) THEN
        RAISE EXCEPTION 'User not found';
    END IF;

    -- Создаем новое подключение
    INSERT INTO user_connections (
        user_id,
        broker_type,
        encrypted_token,
        is_active,
        metadata
    ) VALUES (
        p_user_id,
        p_broker_type,
        encrypt_token(p_token, p_user_id),
        true,
        jsonb_build_object(
            'created_by', current_user,
            'created_at', now()
        )
    )
    RETURNING id INTO v_connection_id;

    RETURN v_connection_id;
END;
$$;

-- Функция для обновления токена
CREATE OR REPLACE FUNCTION update_user_connection_token(
    p_connection_id UUID,
    p_new_token TEXT
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_user_id UUID;
BEGIN
    -- Получаем user_id для проверки доступа
    SELECT user_id INTO v_user_id
    FROM user_connections
    WHERE id = p_connection_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Connection not found';
    END IF;

    -- Обновляем токен
    UPDATE user_connections
    SET encrypted_token = encrypt_token(p_new_token, v_user_id),
        metadata = jsonb_set(
            metadata,
            '{updated_at}',
            to_jsonb(now())
        )
    WHERE id = p_connection_id;
END;
$$;

-- Добавляем RLS политики для функций
REVOKE ALL ON FUNCTION encrypt_token(TEXT, UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION decrypt_token(TEXT, UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION create_user_connection(UUID, TEXT, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION update_user_connection_token(UUID, TEXT) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION create_user_connection(UUID, TEXT, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION update_user_connection_token(UUID, TEXT) TO authenticated; 