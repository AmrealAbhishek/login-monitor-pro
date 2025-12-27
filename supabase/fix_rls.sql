-- Login Monitor PRO - Fix RLS Policies
-- Run this in Supabase Dashboard → SQL Editor
-- =============================================

-- Drop existing restrictive policies
DROP POLICY IF EXISTS "Users can view own devices" ON devices;
DROP POLICY IF EXISTS "Users can update own devices" ON devices;
DROP POLICY IF EXISTS "Anyone can insert devices (for pairing)" ON devices;
DROP POLICY IF EXISTS "Users can delete own devices" ON devices;
DROP POLICY IF EXISTS "Users can view own device events" ON events;
DROP POLICY IF EXISTS "Devices can insert events" ON events;
DROP POLICY IF EXISTS "Users can update own device events" ON events;
DROP POLICY IF EXISTS "Users can view own device commands" ON commands;
DROP POLICY IF EXISTS "Users can insert commands for own devices" ON commands;
DROP POLICY IF EXISTS "Devices can update command status" ON commands;

-- Create permissive policies for devices
CREATE POLICY "Allow all device operations" ON devices FOR ALL USING (true) WITH CHECK (true);

-- Create permissive policies for events
CREATE POLICY "Allow all event operations" ON events FOR ALL USING (true) WITH CHECK (true);

-- Create permissive policies for commands
CREATE POLICY "Allow all command operations" ON commands FOR ALL USING (true) WITH CHECK (true);

-- Verify RLS is enabled but with permissive policies
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE commands ENABLE ROW LEVEL SECURITY;
