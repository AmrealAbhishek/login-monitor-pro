-- Add install_token to organizations table
-- Run this in Supabase SQL Editor

-- Add install_token column if not exists
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'organizations' AND column_name = 'install_token'
  ) THEN
    ALTER TABLE organizations ADD COLUMN install_token TEXT UNIQUE;

    -- Generate tokens for existing organizations
    UPDATE organizations
    SET install_token = upper(substring(md5(random()::text) from 1 for 12))
    WHERE install_token IS NULL;

    -- Make it not null going forward
    ALTER TABLE organizations ALTER COLUMN install_token SET NOT NULL;
  END IF;
END $$;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_organizations_install_token
ON organizations(install_token);

-- RLS policy to allow anonymous device registration using install token
-- (Devices can register themselves with a valid token)
CREATE POLICY IF NOT EXISTS "Allow device registration with valid token"
ON devices FOR INSERT
WITH CHECK (
  org_id IN (SELECT id FROM organizations WHERE install_token IS NOT NULL)
);

-- Allow anonymous reads to verify token
CREATE POLICY IF NOT EXISTS "Allow token verification"
ON organizations FOR SELECT
USING (true);
