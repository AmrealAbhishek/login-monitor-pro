-- Fix RLS for commands table to allow Realtime to work
-- The command_listener uses anon key to subscribe to Realtime
-- It needs to be able to SELECT commands for its device_id

-- Drop any existing select policy
DROP POLICY IF EXISTS "commands_select_policy" ON commands;
DROP POLICY IF EXISTS "Allow anon select commands" ON commands;

-- Allow anon to SELECT commands (needed for Realtime subscription to work)
-- This is safe because commands are only useful if you have the device_id
CREATE POLICY "commands_select_policy" ON commands
    FOR SELECT TO anon, authenticated
    USING (true);

-- Also ensure INSERT and UPDATE policies exist
DROP POLICY IF EXISTS "commands_insert_policy" ON commands;
CREATE POLICY "commands_insert_policy" ON commands
    FOR INSERT TO anon, authenticated
    WITH CHECK (true);

DROP POLICY IF EXISTS "commands_update_policy" ON commands;
CREATE POLICY "commands_update_policy" ON commands
    FOR UPDATE TO anon, authenticated
    USING (true)
    WITH CHECK (true);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON commands TO anon;
GRANT SELECT, INSERT, UPDATE ON commands TO authenticated;
