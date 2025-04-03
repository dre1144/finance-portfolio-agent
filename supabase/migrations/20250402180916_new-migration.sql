-- Create schema for our app
CREATE SCHEMA IF NOT EXISTS ai_banking;

-- Create table for chat history
CREATE TABLE IF NOT EXISTS ai_banking.chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    context JSONB
);

-- Create table for user settings
CREATE TABLE IF NOT EXISTS ai_banking.user_settings (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    tinkoff_token TEXT,
    preferred_currency TEXT DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create RLS policies
ALTER TABLE ai_banking.chat_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_banking.user_settings ENABLE ROW LEVEL SECURITY;

-- Chat history policies
CREATE POLICY "Users can view their own chat history"
    ON ai_banking.chat_history
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can insert their own chat messages"
    ON ai_banking.chat_history
    FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

-- User settings policies
CREATE POLICY "Users can view their own settings"
    ON ai_banking.user_settings
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can update their own settings"
    ON ai_banking.user_settings
    FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can insert their own settings"
    ON ai_banking.user_settings
    FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

-- Create function to handle user creation
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO ai_banking.user_settings (user_id)
    VALUES (NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger for new user creation
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
