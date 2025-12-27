-- Login Monitor PRO - Fix RLS Policies
-- Run this in Supabase Dashboard → SQL Editor
-- =============================================

-- Drop existing restrictive policies on tables
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
DROP POLICY IF EXISTS "Allow all device operations" ON devices;
DROP POLICY IF EXISTS "Allow all event operations" ON events;
DROP POLICY IF EXISTS "Allow all command operations" ON commands;

-- Create permissive policies for tables
CREATE POLICY "Allow all device operations" ON devices FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all event operations" ON events FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all command operations" ON commands FOR ALL USING (true) WITH CHECK (true);

-- Enable RLS on tables
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE commands ENABLE ROW LEVEL SECURITY;

-- Fix storage policies
DROP POLICY IF EXISTS "Authenticated users can upload" ON storage.objects;
DROP POLICY IF EXISTS "Users can view own files" ON storage.objects;
DROP POLICY IF EXISTS "Devices can upload files" ON storage.objects;
DROP POLICY IF EXISTS "Allow all storage operations" ON storage.objects;

-- Allow all storage operations
CREATE POLICY "Allow all storage operations" ON storage.objects
  FOR ALL USING (true) WITH CHECK (true);
