-- Fix RLS to allow device registration from install script
-- The install script uses anon key

-- Drop existing insert policy
DROP POLICY IF EXISTS "devices_insert_policy" ON devices;

-- Create new policy that allows anon to insert
CREATE POLICY "devices_insert_policy" ON devices
    FOR INSERT TO anon, authenticated
    WITH CHECK (true);

-- Also ensure update policy exists for heartbeat
DROP POLICY IF EXISTS "devices_update_policy" ON devices;
CREATE POLICY "devices_update_policy" ON devices
    FOR UPDATE TO anon, authenticated
    USING (true)
    WITH CHECK (true);

-- Grant permissions
GRANT INSERT, UPDATE ON devices TO anon;
