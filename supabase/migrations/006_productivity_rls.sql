-- RLS policies for productivity_scores and app_usage tables

-- Enable RLS
ALTER TABLE productivity_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_usage ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any
DROP POLICY IF EXISTS "Users can view productivity scores for their org devices" ON productivity_scores;
DROP POLICY IF EXISTS "Users can view app usage for their org devices" ON app_usage;

-- Create policy for productivity_scores
CREATE POLICY "Users can view productivity scores for their org devices"
ON productivity_scores FOR SELECT
USING (
  device_id IN (
    SELECT d.id FROM devices d
    JOIN org_members om ON d.org_id = om.org_id
    WHERE om.user_id = auth.uid()
  )
);

-- Create policy for app_usage
CREATE POLICY "Users can view app usage for their org devices"
ON app_usage FOR SELECT
USING (
  device_id IN (
    SELECT d.id FROM devices d
    JOIN org_members om ON d.org_id = om.org_id
    WHERE om.user_id = auth.uid()
  )
);

-- Also allow service role to insert
CREATE POLICY "Service role can insert productivity scores"
ON productivity_scores FOR INSERT
WITH CHECK (true);

CREATE POLICY "Service role can update productivity scores"
ON productivity_scores FOR UPDATE
USING (true);

CREATE POLICY "Service role can insert app usage"
ON app_usage FOR INSERT
WITH CHECK (true);
