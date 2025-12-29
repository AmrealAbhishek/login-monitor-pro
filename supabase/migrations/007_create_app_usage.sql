-- Create app_usage table for productivity tracking
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS app_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  app_name TEXT NOT NULL,
  bundle_id TEXT,
  window_title TEXT,
  launched_at TIMESTAMPTZ,
  terminated_at TIMESTAMPTZ,
  duration_seconds INTEGER DEFAULT 0,
  category TEXT DEFAULT 'neutral' CHECK (category IN ('productive', 'unproductive', 'communication', 'neutral')),
  recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_app_usage_device ON app_usage(device_id, recorded_at DESC);
CREATE INDEX idx_app_usage_category ON app_usage(category);

-- Enable RLS
ALTER TABLE app_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_usage FORCE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "app_usage_select" ON app_usage
    FOR SELECT TO authenticated
    USING (
        device_id IN (
            SELECT d.id FROM devices d
            JOIN org_members om ON d.org_id = om.org_id
            WHERE om.user_id = auth.uid()
        )
    );

CREATE POLICY "app_usage_insert" ON app_usage
    FOR INSERT TO anon, authenticated
    WITH CHECK (true);

-- Grant permissions
GRANT SELECT ON app_usage TO authenticated;
GRANT INSERT ON app_usage TO anon, authenticated;

-- Also fix productivity_scores RLS (add anon insert for agents)
DROP POLICY IF EXISTS "productivity_scores_insert" ON productivity_scores;
CREATE POLICY "productivity_scores_insert" ON productivity_scores
    FOR INSERT TO anon, authenticated
    WITH CHECK (true);

DROP POLICY IF EXISTS "productivity_scores_select" ON productivity_scores;
CREATE POLICY "productivity_scores_select" ON productivity_scores
    FOR SELECT TO authenticated
    USING (
        device_id IN (
            SELECT d.id FROM devices d
            JOIN org_members om ON d.org_id = om.org_id
            WHERE om.user_id = auth.uid()
        )
    );

GRANT SELECT ON productivity_scores TO authenticated;
GRANT INSERT, UPDATE ON productivity_scores TO anon, authenticated;
