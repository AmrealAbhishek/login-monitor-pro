'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { Session, User } from '@supabase/supabase-js';
import { supabase, Organization, OrgMember } from './supabase';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  organization: Organization | null;
  membership: OrgMember | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>;
  signUp: (email: string, password: string, orgName: string) => Promise<{ error: Error | null }>;
  signOut: () => Promise<void>;
  refreshOrg: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [membership, setMembership] = useState<OrgMember | null>(null);
  const [loading, setLoading] = useState(true);

  async function fetchOrganization(userId: string) {
    // Get user's organization membership
    const { data: memberData } = await supabase
      .from('org_members')
      .select('*, organizations(*)')
      .eq('user_id', userId)
      .single();

    if (memberData) {
      setMembership({
        id: memberData.id,
        org_id: memberData.org_id,
        user_id: memberData.user_id,
        role: memberData.role,
        joined_at: memberData.joined_at,
      });
      if (memberData.organizations) {
        setOrganization(memberData.organizations as unknown as Organization);
      }
    }
  }

  async function refreshOrg() {
    if (user) {
      await fetchOrganization(user.id);
    }
  }

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      if (session?.user) {
        fetchOrganization(session.user.id);
      }
      setLoading(false);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        setSession(session);
        setUser(session?.user ?? null);
        if (session?.user) {
          await fetchOrganization(session.user.id);
        } else {
          setOrganization(null);
          setMembership(null);
        }
      }
    );

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  async function signIn(email: string, password: string) {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    return { error: error as Error | null };
  }

  async function signUp(email: string, password: string, orgName: string) {
    // 1. Create user
    const { data: authData, error: authError } = await supabase.auth.signUp({
      email,
      password,
    });

    if (authError || !authData.user) {
      return { error: authError as Error | null };
    }

    // 2. Create organization with install token
    const slug = orgName.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-');
    const installToken = generateInstallToken();

    const { data: orgData, error: orgError } = await supabase
      .from('organizations')
      .insert({
        name: orgName,
        slug: slug,
        install_token: installToken,
        plan: 'pro',
      })
      .select()
      .single();

    if (orgError) {
      return { error: orgError as Error };
    }

    // 3. Add user as owner
    const { error: memberError } = await supabase
      .from('org_members')
      .insert({
        org_id: orgData.id,
        user_id: authData.user.id,
        role: 'owner',
        joined_at: new Date().toISOString(),
      });

    if (memberError) {
      return { error: memberError as Error };
    }

    return { error: null };
  }

  async function signOut() {
    await supabase.auth.signOut();
    setOrganization(null);
    setMembership(null);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        organization,
        membership,
        loading,
        signIn,
        signUp,
        signOut,
        refreshOrg,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

function generateInstallToken(): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let result = '';
  for (let i = 0; i < 12; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}
