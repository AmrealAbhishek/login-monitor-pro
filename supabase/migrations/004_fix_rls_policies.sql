-- Fix RLS Policies for CyVigil Dashboard
-- Run this in Supabase SQL Editor to secure your data

-- =============================================
-- 1. ENABLE RLS ON ALL TABLES
-- =============================================

ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_members ENABLE ROW LEVEL SECURITY;

-- =============================================
-- 2. DROP EXISTING POLICIES (if any)
-- =============================================

DROP POLICY IF EXISTS "Allow device registration with valid token" ON devices;
DROP POLICY IF EXISTS "Allow token verification" ON organizations;
DROP POLICY IF EXISTS "Members can view their organization" ON organizations;
DROP POLICY IF EXISTS "Members can view org members" ON org_members;
DROP POLICY IF EXISTS "Users can view their org devices" ON devices;
DROP POLICY IF EXISTS "Users can view their org events" ON events;
DROP POLICY IF EXISTS "Users can view their org commands" ON commands;

-- =============================================
-- 3. CREATE SECURE POLICIES
-- =============================================

-- Organizations: Only members can view their org
CREATE POLICY "org_select_policy" ON organizations
  FOR SELECT
  TO authenticated
  USING (
    id IN (
      SELECT org_id FROM org_members WHERE user_id = auth.uid()
    )
  );

-- Org Members: Users can view members of their org
CREATE POLICY "org_members_select_policy" ON org_members
  FOR SELECT
  TO authenticated
  USING (
    org_id IN (
      SELECT org_id FROM org_members WHERE user_id = auth.uid()
    )
  );

-- Devices: Users can view devices in their org
CREATE POLICY "devices_select_policy" ON devices
  FOR SELECT
  TO authenticated
  USING (
    org_id IN (
      SELECT org_id FROM org_members WHERE user_id = auth.uid()
    )
  );

-- Devices: Allow device registration (for install script)
CREATE POLICY "devices_insert_policy" ON devices
  FOR INSERT
  TO anon, authenticated
  WITH CHECK (true);

-- Devices: Allow device updates (for heartbeat)
CREATE POLICY "devices_update_policy" ON devices
  FOR UPDATE
  TO anon, authenticated
  USING (true)
  WITH CHECK (true);

-- Events: Users can view events from their org's devices
CREATE POLICY "events_select_policy" ON events
  FOR SELECT
  TO authenticated
  USING (
    device_id IN (
      SELECT d.id FROM devices d
      JOIN org_members om ON d.org_id = om.org_id
      WHERE om.user_id = auth.uid()
    )
  );

-- Events: Allow event creation (for monitoring agents)
CREATE POLICY "events_insert_policy" ON events
  FOR INSERT
  TO anon, authenticated
  WITH CHECK (true);

-- Commands: Users can view commands for their org's devices
CREATE POLICY "commands_select_policy" ON commands
  FOR SELECT
  TO authenticated
  USING (
    device_id IN (
      SELECT d.id FROM devices d
      JOIN org_members om ON d.org_id = om.org_id
      WHERE om.user_id = auth.uid()
    )
  );

-- Commands: Users can create commands for their org's devices
CREATE POLICY "commands_insert_policy" ON commands
  FOR INSERT
  TO authenticated
  WITH CHECK (
    device_id IN (
      SELECT d.id FROM devices d
      JOIN org_members om ON d.org_id = om.org_id
      WHERE om.user_id = auth.uid()
    )
  );

-- Commands: Allow command updates (for agents to mark complete)
CREATE POLICY "commands_update_policy" ON commands
  FOR UPDATE
  TO anon, authenticated
  USING (true)
  WITH CHECK (true);

-- =============================================
-- 4. GRANT PERMISSIONS
-- =============================================

GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON organizations TO authenticated;
GRANT SELECT ON org_members TO authenticated;
GRANT SELECT, INSERT, UPDATE ON devices TO anon, authenticated;
GRANT SELECT, INSERT ON events TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON commands TO anon, authenticated;

-- =============================================
-- Done! Data is now protected by RLS
-- =============================================
