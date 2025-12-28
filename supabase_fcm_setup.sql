-- ===========================================
-- FCM Push Notifications Setup for CyVigil
-- Run this in Supabase SQL Editor
-- ===========================================

-- 1. Create FCM tokens table
CREATE TABLE IF NOT EXISTS fcm_tokens (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    token TEXT NOT NULL,
    platform TEXT DEFAULT 'android',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Enable RLS
ALTER TABLE fcm_tokens ENABLE ROW LEVEL SECURITY;

-- 3. Create policies
CREATE POLICY "Users can manage their own tokens"
    ON fcm_tokens
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 4. Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_fcm_tokens_user_id ON fcm_tokens(user_id);

-- 5. Create function to get FCM tokens for a device's owner
CREATE OR REPLACE FUNCTION get_fcm_tokens_for_device(device_uuid UUID)
RETURNS TABLE(token TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT ft.token
    FROM fcm_tokens ft
    JOIN devices d ON d.user_id = ft.user_id
    WHERE d.id = device_uuid;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ===========================================
-- DONE! Now set up the Edge Function
-- ===========================================
