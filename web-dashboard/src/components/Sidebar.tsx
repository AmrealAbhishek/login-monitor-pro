'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import {
  LayoutDashboard,
  Monitor,
  Activity,
  AlertTriangle,
  BarChart3,
  Shield,
  Settings,
  LogOut,
  FileText,
  Globe,
  Zap,
  Users,
  ChevronDown,
  ChevronRight,
  Sliders,
  Download,
  User,
  Building2,
} from 'lucide-react';

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/devices', label: 'Devices', icon: Monitor },
  { href: '/events', label: 'Activity', icon: Activity },
  { href: '/alerts', label: 'Alerts', icon: AlertTriangle },
  { href: '/productivity', label: 'Productivity', icon: BarChart3 },
  { href: '/security', label: 'Security Rules', icon: Shield },
  { href: '/install', label: 'Install Agent', icon: Download },
];

const adminItems = [
  { href: '/admin/file-rules', label: 'File Rules', icon: FileText },
  { href: '/admin/url-rules', label: 'URL Rules', icon: Globe },
  { href: '/admin/activity-rules', label: 'Activity Rules', icon: Zap },
  { href: '/admin/groups', label: 'Device Groups', icon: Users },
];

interface UserInfo {
  email: string;
  org_name: string;
  role: string;
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [adminExpanded, setAdminExpanded] = useState(pathname.startsWith('/admin'));
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [showProfile, setShowProfile] = useState(false);

  useEffect(() => {
    async function fetchUser() {
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        const { data: memberData } = await supabase
          .from('org_members')
          .select('role, org_id')
          .eq('user_id', user.id)
          .single();

        if (memberData) {
          const { data: orgData } = await supabase
            .from('organizations')
            .select('name')
            .eq('id', memberData.org_id)
            .single();

          setUserInfo({
            email: user.email || '',
            org_name: orgData?.name || 'Unknown',
            role: memberData.role,
          });
        }
      }
    }
    fetchUser();
  }, []);

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push('/login');
  }

  return (
    <aside className="fixed left-0 top-0 w-64 h-screen bg-[#0A0A0A] border-r border-[#1A1A1A] flex flex-col z-50">
      {/* Logo Section */}
      <div className="p-6 border-b border-[#1A1A1A]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-red-600 to-red-800 rounded-xl flex items-center justify-center shadow-lg shadow-red-500/20">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">CyVigil</h1>
            <p className="text-[#666] text-xs font-medium uppercase tracking-wider">Enterprise Security</p>
          </div>
        </div>
      </div>

      {/* User Profile Section */}
      {userInfo && (
        <div className="px-4 py-4 border-b border-[#1A1A1A]">
          <button
            onClick={() => setShowProfile(!showProfile)}
            className="w-full p-3 bg-[#111] rounded-xl hover:bg-[#1A1A1A] transition-all duration-200 border border-[#222] hover:border-[#333]"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-gradient-to-br from-red-600 to-red-800 rounded-lg flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1 text-left min-w-0">
                <p className="text-sm font-medium text-white truncate">{userInfo.email}</p>
                <p className="text-xs text-[#666] flex items-center gap-1">
                  <Building2 className="w-3 h-3" />
                  {userInfo.org_name}
                </p>
              </div>
              <ChevronDown className={`w-4 h-4 text-[#666] transition-transform duration-200 ${showProfile ? 'rotate-180' : ''}`} />
            </div>
          </button>
          {showProfile && (
            <div className="mt-2 p-3 bg-[#111] rounded-xl border border-[#222] space-y-2">
              <div className="text-xs text-[#666]">
                <p>Role: <span className="text-white capitalize font-medium">{userInfo.role}</span></p>
              </div>
              <Link
                href="/settings"
                className="block text-sm text-[#AAA] hover:text-red-500 py-1 transition-colors"
              >
                Account Settings
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${
                    isActive
                      ? 'bg-red-600 text-white shadow-lg shadow-red-500/20'
                      : 'text-[#AAA] hover:bg-[#111] hover:text-white'
                  }`}
                >
                  <Icon className={`w-5 h-5 transition-colors ${isActive ? 'text-white' : 'text-[#666] group-hover:text-red-500'}`} />
                  <span className="font-medium">{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Admin Section */}
        <div className="mt-6">
          <button
            onClick={() => setAdminExpanded(!adminExpanded)}
            className="flex items-center justify-between w-full px-4 py-3 text-[#666] hover:text-white transition-colors rounded-xl hover:bg-[#111]"
          >
            <div className="flex items-center gap-3">
              <Sliders className="w-5 h-5" />
              <span className="text-xs font-semibold uppercase tracking-widest">Admin</span>
            </div>
            {adminExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>

          {adminExpanded && (
            <ul className="space-y-1 mt-1 ml-2 border-l border-[#222] pl-2">
              {adminItems.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;

                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 text-sm ${
                        isActive
                          ? 'bg-red-600 text-white'
                          : 'text-[#888] hover:bg-[#111] hover:text-white'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Settings */}
        <div className="mt-4">
          <Link
            href="/settings"
            className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${
              pathname === '/settings'
                ? 'bg-red-600 text-white shadow-lg shadow-red-500/20'
                : 'text-[#AAA] hover:bg-[#111] hover:text-white'
            }`}
          >
            <Settings className={`w-5 h-5 ${pathname === '/settings' ? 'text-white' : 'text-[#666] group-hover:text-red-500'}`} />
            <span className="font-medium">Settings</span>
          </Link>
        </div>
      </nav>

      {/* Sign Out - Fixed at bottom */}
      <div className="p-4 border-t border-[#1A1A1A] bg-[#0A0A0A]">
        <button
          onClick={handleSignOut}
          className="flex items-center gap-3 px-4 py-3 w-full text-[#AAA] hover:text-red-500 hover:bg-[#111] rounded-xl transition-all duration-200 group"
        >
          <LogOut className="w-5 h-5 text-[#666] group-hover:text-red-500" />
          <span className="font-medium">Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
