-- Fix RLS Policies for UAM/Admin Tables
-- Run this in Supabase SQL Editor

-- =============================================
-- 1. DROP EXISTING POLICIES
-- =============================================

-- url_rules
DROP POLICY IF EXISTS "Service role full access to url_rules" ON url_rules;
DROP POLICY IF EXISTS "url_rules_select" ON url_rules;
DROP POLICY IF EXISTS "url_rules_insert" ON url_rules;
DROP POLICY IF EXISTS "url_rules_update" ON url_rules;
DROP POLICY IF EXISTS "url_rules_delete" ON url_rules;

-- sensitive_file_rules
DROP POLICY IF EXISTS "Service role full access to sensitive_file_rules" ON sensitive_file_rules;
DROP POLICY IF EXISTS "sensitive_file_rules_select" ON sensitive_file_rules;
DROP POLICY IF EXISTS "sensitive_file_rules_insert" ON sensitive_file_rules;
DROP POLICY IF EXISTS "sensitive_file_rules_update" ON sensitive_file_rules;
DROP POLICY IF EXISTS "sensitive_file_rules_delete" ON sensitive_file_rules;

-- suspicious_activity_rules
DROP POLICY IF EXISTS "Service role full access to suspicious_activity_rules" ON suspicious_activity_rules;
DROP POLICY IF EXISTS "suspicious_activity_rules_select" ON suspicious_activity_rules;
DROP POLICY IF EXISTS "suspicious_activity_rules_insert" ON suspicious_activity_rules;
DROP POLICY IF EXISTS "suspicious_activity_rules_update" ON suspicious_activity_rules;
DROP POLICY IF EXISTS "suspicious_activity_rules_delete" ON suspicious_activity_rules;

-- device_groups
DROP POLICY IF EXISTS "device_groups_select" ON device_groups;
DROP POLICY IF EXISTS "device_groups_insert" ON device_groups;
DROP POLICY IF EXISTS "device_groups_update" ON device_groups;
DROP POLICY IF EXISTS "device_groups_delete" ON device_groups;

-- =============================================
-- 2. FORCE RLS ON ALL TABLES
-- =============================================

ALTER TABLE url_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE url_rules FORCE ROW LEVEL SECURITY;

ALTER TABLE sensitive_file_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE sensitive_file_rules FORCE ROW LEVEL SECURITY;

ALTER TABLE suspicious_activity_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE suspicious_activity_rules FORCE ROW LEVEL SECURITY;

ALTER TABLE device_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_groups FORCE ROW LEVEL SECURITY;

-- =============================================
-- 3. URL RULES POLICIES
-- =============================================

-- SELECT: Authenticated users can see global rules (org_id is null) + their org's rules
CREATE POLICY "url_rules_select" ON url_rules
    FOR SELECT TO authenticated
    USING (
        org_id IS NULL  -- Global/default rules
        OR org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );

-- INSERT: Authenticated users can create rules for their org
CREATE POLICY "url_rules_insert" ON url_rules
    FOR INSERT TO authenticated
    WITH CHECK (
        org_id IS NULL  -- Allow creating global rules
        OR org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );

-- UPDATE: Authenticated users can update rules in their org (not global)
CREATE POLICY "url_rules_update" ON url_rules
    FOR UPDATE TO authenticated
    USING (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
        OR org_id IS NULL
    )
    WITH CHECK (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
        OR org_id IS NULL
    );

-- DELETE: Authenticated users can delete rules in their org
CREATE POLICY "url_rules_delete" ON url_rules
    FOR DELETE TO authenticated
    USING (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
        OR org_id IS NULL
    );

-- =============================================
-- 4. SENSITIVE FILE RULES POLICIES
-- =============================================

CREATE POLICY "sensitive_file_rules_select" ON sensitive_file_rules
    FOR SELECT TO authenticated
    USING (
        org_id IS NULL
        OR org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );

CREATE POLICY "sensitive_file_rules_insert" ON sensitive_file_rules
    FOR INSERT TO authenticated
    WITH CHECK (
        org_id IS NULL
        OR org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );

CREATE POLICY "sensitive_file_rules_update" ON sensitive_file_rules
    FOR UPDATE TO authenticated
    USING (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
        OR org_id IS NULL
    )
    WITH CHECK (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
        OR org_id IS NULL
    );

CREATE POLICY "sensitive_file_rules_delete" ON sensitive_file_rules
    FOR DELETE TO authenticated
    USING (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
        OR org_id IS NULL
    );

-- =============================================
-- 5. SUSPICIOUS ACTIVITY RULES POLICIES
-- =============================================

CREATE POLICY "suspicious_activity_rules_select" ON suspicious_activity_rules
    FOR SELECT TO authenticated
    USING (
        org_id IS NULL
        OR org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );

CREATE POLICY "suspicious_activity_rules_insert" ON suspicious_activity_rules
    FOR INSERT TO authenticated
    WITH CHECK (
        org_id IS NULL
        OR org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );

CREATE POLICY "suspicious_activity_rules_update" ON suspicious_activity_rules
    FOR UPDATE TO authenticated
    USING (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
        OR org_id IS NULL
    )
    WITH CHECK (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
        OR org_id IS NULL
    );

CREATE POLICY "suspicious_activity_rules_delete" ON suspicious_activity_rules
    FOR DELETE TO authenticated
    USING (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
        OR org_id IS NULL
    );

-- =============================================
-- 6. DEVICE GROUPS POLICIES
-- =============================================

CREATE POLICY "device_groups_select" ON device_groups
    FOR SELECT TO authenticated
    USING (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );

CREATE POLICY "device_groups_insert" ON device_groups
    FOR INSERT TO authenticated
    WITH CHECK (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );

CREATE POLICY "device_groups_update" ON device_groups
    FOR UPDATE TO authenticated
    USING (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    )
    WITH CHECK (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );

CREATE POLICY "device_groups_delete" ON device_groups
    FOR DELETE TO authenticated
    USING (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );

-- =============================================
-- 7. SECURITY ALERTS POLICIES
-- =============================================

ALTER TABLE security_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_alerts FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "security_alerts_select" ON security_alerts;
DROP POLICY IF EXISTS "security_alerts_update" ON security_alerts;

CREATE POLICY "security_alerts_select" ON security_alerts
    FOR SELECT TO authenticated
    USING (
        device_id IN (
            SELECT d.id FROM devices d
            JOIN org_members om ON d.org_id = om.org_id
            WHERE om.user_id = auth.uid()
        )
    );

CREATE POLICY "security_alerts_update" ON security_alerts
    FOR UPDATE TO authenticated
    USING (
        device_id IN (
            SELECT d.id FROM devices d
            JOIN org_members om ON d.org_id = om.org_id
            WHERE om.user_id = auth.uid()
        )
    );

-- =============================================
-- 8. GRANT PERMISSIONS
-- =============================================

GRANT SELECT, INSERT, UPDATE, DELETE ON url_rules TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON sensitive_file_rules TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON suspicious_activity_rules TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON device_groups TO authenticated;
GRANT SELECT, UPDATE ON security_alerts TO authenticated;

-- =============================================
-- DONE - Admin tables now accessible to authenticated users
-- =============================================
