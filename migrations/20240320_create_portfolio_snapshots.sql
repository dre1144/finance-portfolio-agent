-- Create portfolio snapshots table
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    total_value DECIMAL(20, 2) NOT NULL,
    positions JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    
    -- Индексы для быстрого поиска
    CONSTRAINT portfolio_snapshots_user_account_idx UNIQUE (user_id, account_id, timestamp)
);

-- Добавляем RLS политики
ALTER TABLE portfolio_snapshots ENABLE ROW LEVEL SECURITY;

-- Пользователи могут видеть только свои снимки
CREATE POLICY "Users can view their own snapshots"
    ON portfolio_snapshots
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- Пользователи могут создавать снимки только для себя
CREATE POLICY "Users can create their own snapshots"
    ON portfolio_snapshots
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- Пользователи могут удалять только свои снимки
CREATE POLICY "Users can delete their own snapshots"
    ON portfolio_snapshots
    FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- Создаем индекс для быстрого поиска по времени
CREATE INDEX portfolio_snapshots_timestamp_idx ON portfolio_snapshots (timestamp DESC);

-- Создаем индекс для быстрого поиска по пользователю и времени
CREATE INDEX portfolio_snapshots_user_timestamp_idx ON portfolio_snapshots (user_id, timestamp DESC);

-- Комментарии к таблице и колонкам
COMMENT ON TABLE portfolio_snapshots IS 'Snapshots of user portfolio states for monitoring changes';
COMMENT ON COLUMN portfolio_snapshots.user_id IS 'Reference to auth.users table';
COMMENT ON COLUMN portfolio_snapshots.account_id IS 'Broker account ID';
COMMENT ON COLUMN portfolio_snapshots.timestamp IS 'When the snapshot was taken';
COMMENT ON COLUMN portfolio_snapshots.total_value IS 'Total portfolio value at the time of snapshot';
COMMENT ON COLUMN portfolio_snapshots.positions IS 'JSON array of portfolio positions'; 