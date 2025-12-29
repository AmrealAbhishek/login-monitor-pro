-- Fix org_members RLS infinite recursion

DROP POLICY IF EXISTS "org_members_select_policy" ON org_members;
DROP POLICY IF EXISTS "Members can view org members" ON org_members;
DROP POLICY IF EXISTS "org_select_policy" ON organizations;
DROP POLICY IF EXISTS "Members can view their organization" ON organizations;

ALTER TABLE org_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_members FORCE ROW LEVEL SECURITY;
ALTER TABLE organizations FORCE ROW LEVEL SECURITY;

CREATE POLICY "users_own_memberships" ON org_members
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "users_own_orgs" ON organizations
    FOR SELECT TO authenticated
    USING (
        id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );
