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
          // Fetch org name separately
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
    <aside className="w-64 bg-gray-900 text-white min-h-screen flex flex-col">
      <div className="p-6">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <Shield className="w-6 h-6 text-red-500" />
          CyVigil
        </h1>
        <p className="text-gray-400 text-sm mt-1">Enterprise Security</p>
      </div>

      {/* User Profile Section */}
      {userInfo && (
        <div className="px-4 mb-4">
          <button
            onClick={() => setShowProfile(!showProfile)}
            className="w-full p-3 bg-gray-800 rounded-lg hover:bg-gray-750 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-red-600 rounded-full flex items-center justify-center">
                <User className="w-4 h-4 text-white" />
              </div>
              <div className="flex-1 text-left min-w-0">
                <p className="text-sm font-medium text-white truncate">{userInfo.email}</p>
                <p className="text-xs text-gray-400 flex items-center gap-1">
                  <Building2 className="w-3 h-3" />
                  {userInfo.org_name}
                </p>
              </div>
              <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${showProfile ? 'rotate-180' : ''}`} />
            </div>
          </button>
          {showProfile && (
            <div className="mt-2 p-3 bg-gray-800 rounded-lg space-y-2">
              <div className="text-xs text-gray-400">
                <p>Role: <span className="text-white capitalize">{userInfo.role}</span></p>
              </div>
              <Link
                href="/settings"
                className="block text-sm text-gray-300 hover:text-white py-1"
              >
                Account Settings
              </Link>
            </div>
          )}
        </div>
      )}

      <nav className="flex-1 px-4 overflow-y-auto">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-red-600 text-white'
                      : 'text-gray-300 hover:bg-gray-800'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Admin Section */}
        <div className="mt-6">
          <button
            onClick={() => setAdminExpanded(!adminExpanded)}
            className="flex items-center justify-between w-full px-4 py-3 text-gray-400 hover:text-white transition-colors"
          >
            <div className="flex items-center gap-3">
              <Sliders className="w-5 h-5" />
              <span className="text-sm font-medium uppercase tracking-wider">Admin</span>
            </div>
            {adminExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>

          {adminExpanded && (
            <ul className="space-y-1 mt-1">
              {adminItems.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;

                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={`flex items-center gap-3 px-4 py-2.5 pl-12 rounded-lg transition-colors text-sm ${
                        isActive
                          ? 'bg-red-600 text-white'
                          : 'text-gray-400 hover:bg-gray-800 hover:text-white'
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

        {/* Settings at bottom of nav */}
        <div className="mt-6">
          <Link
            href="/settings"
            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
              pathname === '/settings'
                ? 'bg-red-600 text-white'
                : 'text-gray-300 hover:bg-gray-800'
            }`}
          >
            <Settings className="w-5 h-5" />
            Settings
          </Link>
        </div>
      </nav>

      <div className="p-4 border-t border-gray-800">
        <button
          onClick={handleSignOut}
          className="flex items-center gap-3 px-4 py-3 w-full text-gray-300 hover:bg-gray-800 rounded-lg transition-colors"
        >
          <LogOut className="w-5 h-5" />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
