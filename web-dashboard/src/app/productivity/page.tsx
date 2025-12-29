'use client';

import { useEffect, useState, useMemo } from 'react';
import { supabase } from '@/lib/supabase';
import {
  BarChart3,
  Clock,
  TrendingUp,
  Calendar,
  Monitor,
  Coffee,
  Zap,
  Chrome,
  Terminal,
  FileText,
  MessageCircle,
  Music,
  Video,
  Mail,
  Code,
  Folder,
  Phone,
  Globe,
  PlayCircle,
  Gamepad2,
  Image as ImageIcon,
  Settings,
  LucideIcon,
} from 'lucide-react';
import { format, subDays, startOfWeek } from 'date-fns';
import { HackerLoader } from '@/components/HackerLoader';

// App icon mappings based on bundle ID or app name
const APP_ICONS: Record<string, LucideIcon> = {
  // Browsers
  'com.google.Chrome': Chrome,
  'com.apple.Safari': Globe,
  'org.mozilla.firefox': Globe,
  'com.microsoft.edgemac': Globe,
  // Terminals
  'com.apple.Terminal': Terminal,
  'com.googlecode.iterm2': Terminal,
  'dev.warp.Warp-Stable': Terminal,
  // IDEs/Editors
  'com.microsoft.VSCode': Code,
  'com.visualstudio.code.oss': Code,
  'com.todesktop.230313mzl4w4u92': Code, // Cursor
  'com.apple.dt.Xcode': Code,
  'com.jetbrains.intellij': Code,
  'com.jetbrains.pycharm': Code,
  // Communication
  'net.whatsapp.WhatsApp': MessageCircle,
  'com.tinyspeck.slackmacgap': MessageCircle,
  'Mattermost.Desktop': MessageCircle,
  'com.microsoft.teams': MessageCircle,
  'com.hnc.Discord': MessageCircle,
  'com.apple.MobileSMS': MessageCircle,
  'com.apple.FaceTime': Phone,
  'com.apple.mobilephone': Phone,
  // Productivity
  'com.apple.Notes': FileText,
  'com.apple.Pages': FileText,
  'com.microsoft.Word': FileText,
  'com.apple.Numbers': FileText,
  'com.microsoft.Excel': FileText,
  'com.apple.Keynote': FileText,
  'com.microsoft.Powerpoint': FileText,
  // Media
  'com.spotify.client': Music,
  'com.apple.Music': Music,
  'org.videolan.vlc': Video,
  'com.apple.TV': PlayCircle,
  'com.netflix.Netflix': PlayCircle,
  'tv.twitch.TwitchClient': PlayCircle,
  // Mail
  'com.apple.mail': Mail,
  'com.microsoft.Outlook': Mail,
  // System
  'com.apple.finder': Folder,
  'com.apple.Preview': ImageIcon,
  'com.apple.systempreferences': Settings,
  // Games
  'com.valvesoftware.steam': Gamepad2,
};

function getAppIcon(bundleId: string, appName: string): LucideIcon {
  // Check by bundle ID first
  if (bundleId && APP_ICONS[bundleId]) {
    return APP_ICONS[bundleId];
  }
  // Fallback by app name patterns
  const nameLower = appName.toLowerCase();
  if (nameLower.includes('chrome')) return Chrome;
  if (nameLower.includes('safari')) return Globe;
  if (nameLower.includes('terminal') || nameLower.includes('warp')) return Terminal;
  if (nameLower.includes('code') || nameLower.includes('cursor') || nameLower.includes('xcode')) return Code;
  if (nameLower.includes('slack') || nameLower.includes('whatsapp') || nameLower.includes('mattermost') || nameLower.includes('discord')) return MessageCircle;
  if (nameLower.includes('notes') || nameLower.includes('word') || nameLower.includes('pages')) return FileText;
  if (nameLower.includes('spotify') || nameLower.includes('music')) return Music;
  if (nameLower.includes('vlc') || nameLower.includes('video')) return Video;
  if (nameLower.includes('mail') || nameLower.includes('outlook')) return Mail;
  if (nameLower.includes('finder')) return Folder;
  if (nameLower.includes('phone')) return Phone;
  return Monitor;
}

interface ProductivityScore {
  id: string;
  device_id: string;
  date: string;
  productive_seconds: number;
  unproductive_seconds: number;
  idle_seconds: number;
  productivity_score: number;
  first_login: string;
  last_activity: string;
}

interface AppUsage {
  id: string;
  device_id: string;
  bundle_id: string;
  app_name: string;
  window_title: string;
  duration_seconds: number;
  category: string;
  recorded_at: string;
}

export default function ProductivityPage() {
  const [scores, setScores] = useState<ProductivityScore[]>([]);
  const [appUsage, setAppUsage] = useState<AppUsage[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState<'today' | 'week' | 'month'>('week');

  useEffect(() => {
    fetchProductivityData();

    // Realtime subscription for productivity scores
    const scoresChannel = supabase
      .channel('productivity-scores-realtime')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'productivity_scores' }, () => {
        fetchProductivityData();
      })
      .subscribe();

    // Realtime subscription for app usage
    const usageChannel = supabase
      .channel('app-usage-realtime')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'app_usage' }, () => {
        fetchProductivityData();
      })
      .subscribe();

    return () => {
      supabase.removeChannel(scoresChannel);
      supabase.removeChannel(usageChannel);
    };
  }, [dateRange]);

  async function fetchProductivityData() {
    setLoading(true);

    let startDate: Date;
    const endDate = new Date();

    switch (dateRange) {
      case 'today':
        startDate = new Date();
        startDate.setHours(0, 0, 0, 0);
        break;
      case 'week':
        startDate = startOfWeek(new Date());
        break;
      case 'month':
        startDate = subDays(new Date(), 30);
        break;
    }

    // Fetch productivity scores
    const { data: scoresData } = await supabase
      .from('productivity_scores')
      .select('*')
      .gte('date', format(startDate, 'yyyy-MM-dd'))
      .lte('date', format(endDate, 'yyyy-MM-dd'))
      .order('date', { ascending: false });

    if (scoresData) {
      setScores(scoresData);
    }

    // Fetch app usage - get more data for full analysis
    const { data: usageData } = await supabase
      .from('app_usage')
      .select('*')
      .gte('recorded_at', startDate.toISOString())
      .order('duration_seconds', { ascending: false })
      .limit(200);

    if (usageData) {
      setAppUsage(usageData);
    }

    setLoading(false);
  }

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-500';
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-500';
    return 'text-red-600 dark:text-red-500';
  };

  const getScoreBg = (score: number) => {
    if (score >= 80) return 'bg-green-100 dark:bg-green-900/30';
    if (score >= 60) return 'bg-yellow-100 dark:bg-yellow-900/30';
    return 'bg-red-100 dark:bg-red-900/30';
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'productive':
        return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400';
      case 'unproductive':
        return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400';
      case 'communication':
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400';
      default:
        return 'bg-gray-100 dark:bg-[#333] text-gray-800 dark:text-[#AAA]';
    }
  };

  // Calculate totals
  const totalProductive = scores.reduce((sum, s) => sum + (s.productive_seconds || 0), 0);
  const totalUnproductive = scores.reduce((sum, s) => sum + (s.unproductive_seconds || 0), 0);
  const totalIdle = scores.reduce((sum, s) => sum + (s.idle_seconds || 0), 0);
  const avgScore = scores.length > 0
    ? scores.reduce((sum, s) => sum + (s.productivity_score || 0), 0) / scores.length
    : 0;

  // Group app usage by category
  const usageByCategory = appUsage.reduce((acc, app) => {
    const cat = app.category || 'neutral';
    acc[cat] = (acc[cat] || 0) + app.duration_seconds;
    return acc;
  }, {} as Record<string, number>);

  // Aggregate app usage by app_name (sum durations for same app)
  const aggregatedApps = useMemo(() => {
    const appMap = new Map<string, { app_name: string; bundle_id: string; category: string; total_duration: number }>();

    for (const app of appUsage) {
      const key = app.bundle_id || app.app_name;
      const existing = appMap.get(key);

      if (existing) {
        existing.total_duration += app.duration_seconds;
      } else {
        appMap.set(key, {
          app_name: app.app_name,
          bundle_id: app.bundle_id,
          category: app.category || 'neutral',
          total_duration: app.duration_seconds,
        });
      }
    }

    // Sort by total duration descending
    return Array.from(appMap.values()).sort((a, b) => b.total_duration - a.total_duration);
  }, [appUsage]);

  if (loading) {
    return <HackerLoader message="Calculating productivity metrics..." />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Productivity Analytics</h1>
          <p className="text-gray-600 dark:text-[#888]">Track work patterns and app usage</p>
        </div>
        <div className="flex gap-2">
          {(['today', 'week', 'month'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setDateRange(range)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                dateRange === range
                  ? 'bg-red-600 text-white shadow-lg shadow-red-500/20'
                  : 'bg-gray-100 dark:bg-[#1A1A1A] text-gray-700 dark:text-[#AAA] hover:bg-gray-200 dark:hover:bg-[#222] border border-gray-200 dark:border-[#333]'
              }`}
            >
              {range.charAt(0).toUpperCase() + range.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl p-6 shadow-sm border border-gray-200 dark:border-[#333]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-[#888]">Average Score</p>
              <p className={`text-3xl font-bold ${getScoreColor(avgScore)}`}>
                {avgScore.toFixed(0)}%
              </p>
            </div>
            <div className={`w-12 h-12 rounded-full ${getScoreBg(avgScore)} flex items-center justify-center`}>
              <TrendingUp className={`w-6 h-6 ${getScoreColor(avgScore)}`} />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl p-6 shadow-sm border border-gray-200 dark:border-[#333]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-[#888]">Productive Time</p>
              <p className="text-3xl font-bold text-green-600 dark:text-green-500">{formatDuration(totalProductive)}</p>
            </div>
            <div className="w-12 h-12 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
              <Zap className="w-6 h-6 text-green-600 dark:text-green-500" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl p-6 shadow-sm border border-gray-200 dark:border-[#333]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-[#888]">Idle Time</p>
              <p className="text-3xl font-bold text-yellow-600 dark:text-yellow-500">{formatDuration(totalIdle)}</p>
            </div>
            <div className="w-12 h-12 rounded-full bg-yellow-100 dark:bg-yellow-900/30 flex items-center justify-center">
              <Coffee className="w-6 h-6 text-yellow-600 dark:text-yellow-500" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl p-6 shadow-sm border border-gray-200 dark:border-[#333]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-[#888]">Unproductive</p>
              <p className="text-3xl font-bold text-red-600 dark:text-red-500">{formatDuration(totalUnproductive)}</p>
            </div>
            <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
              <Monitor className="w-6 h-6 text-red-600 dark:text-red-500" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Scores */}
        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl shadow-sm border border-gray-200 dark:border-[#333]">
          <div className="p-4 border-b border-gray-200 dark:border-[#333]">
            <h2 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Calendar className="w-5 h-5" />
              Daily Productivity
            </h2>
          </div>
          <div className="p-4">
            {scores.length === 0 ? (
              <div className="text-center py-8 text-gray-500 dark:text-[#888]">
                <BarChart3 className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-[#444]" />
                <p>No productivity data yet</p>
                <p className="text-sm text-gray-400 dark:text-[#666]">Data will appear once app tracking starts</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-80 overflow-auto">
                {scores.map((score) => (
                  <div key={score.id} className="flex items-center gap-4">
                    <div className="w-24 text-sm text-gray-500 dark:text-[#888]">
                      {format(new Date(score.date), 'MMM d')}
                    </div>
                    <div className="flex-1">
                      <div className="h-6 bg-gray-100 dark:bg-[#333] rounded-full overflow-hidden flex">
                        <div
                          className="bg-green-500 h-full"
                          style={{
                            width: `${(score.productive_seconds / (score.productive_seconds + score.unproductive_seconds + score.idle_seconds)) * 100}%`,
                          }}
                        />
                        <div
                          className="bg-yellow-500 h-full"
                          style={{
                            width: `${(score.idle_seconds / (score.productive_seconds + score.unproductive_seconds + score.idle_seconds)) * 100}%`,
                          }}
                        />
                        <div
                          className="bg-red-500 h-full"
                          style={{
                            width: `${(score.unproductive_seconds / (score.productive_seconds + score.unproductive_seconds + score.idle_seconds)) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                    <div className={`w-16 text-right font-medium ${getScoreColor(score.productivity_score)}`}>
                      {score.productivity_score?.toFixed(0)}%
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div className="flex justify-center gap-6 mt-4 text-xs text-gray-600 dark:text-[#AAA]">
              <span className="flex items-center gap-1">
                <div className="w-3 h-3 bg-green-500 rounded" /> Productive
              </span>
              <span className="flex items-center gap-1">
                <div className="w-3 h-3 bg-yellow-500 rounded" /> Idle
              </span>
              <span className="flex items-center gap-1">
                <div className="w-3 h-3 bg-red-500 rounded" /> Unproductive
              </span>
            </div>
          </div>
        </div>

        {/* Top Apps */}
        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl shadow-sm border border-gray-200 dark:border-[#333]">
          <div className="p-4 border-b border-gray-200 dark:border-[#333]">
            <h2 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Monitor className="w-5 h-5" />
              Top Applications
            </h2>
          </div>
          <div className="divide-y divide-gray-100 dark:divide-[#333] max-h-80 overflow-auto">
            {aggregatedApps.length === 0 ? (
              <div className="text-center py-8 text-gray-500 dark:text-[#888]">
                <Monitor className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-[#444]" />
                <p>No app usage data yet</p>
              </div>
            ) : (
              aggregatedApps.slice(0, 20).map((app, index) => {
                const AppIcon = getAppIcon(app.bundle_id, app.app_name);
                const categoryBgColor = app.category === 'productive' ? 'bg-green-100 dark:bg-green-900/30' :
                                        app.category === 'unproductive' ? 'bg-red-100 dark:bg-red-900/30' :
                                        app.category === 'communication' ? 'bg-blue-100 dark:bg-blue-900/30' :
                                        'bg-gray-100 dark:bg-[#333]';
                const categoryIconColor = app.category === 'productive' ? 'text-green-600 dark:text-green-400' :
                                          app.category === 'unproductive' ? 'text-red-600 dark:text-red-400' :
                                          app.category === 'communication' ? 'text-blue-600 dark:text-blue-400' :
                                          'text-gray-600 dark:text-[#888]';

                return (
                  <div key={`${app.bundle_id}-${index}`} className="p-4 flex items-center gap-4 hover:bg-gray-50 dark:hover:bg-[#222] transition-colors">
                    <div className={`w-10 h-10 rounded-xl ${categoryBgColor} flex items-center justify-center flex-shrink-0`}>
                      <AppIcon className={`w-5 h-5 ${categoryIconColor}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 dark:text-white truncate">{app.app_name}</p>
                      <p className="text-xs text-gray-500 dark:text-[#666] truncate">{app.bundle_id}</p>
                    </div>
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${getCategoryColor(app.category)}`}>
                      {app.category}
                    </span>
                    <div className="text-right min-w-[60px]">
                      <p className="font-bold text-gray-900 dark:text-white">{formatDuration(app.total_duration)}</p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Time Distribution */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl shadow-sm border border-gray-200 dark:border-[#333] p-6">
        <h2 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5" />
          Time Distribution by Category
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(usageByCategory).map(([category, seconds]) => (
            <div key={category} className="text-center p-4 bg-gray-50 dark:bg-[#222] rounded-lg border border-gray-100 dark:border-[#333]">
              <p className={`text-2xl font-bold ${
                category === 'productive' ? 'text-green-600 dark:text-green-500' :
                category === 'unproductive' ? 'text-red-600 dark:text-red-500' :
                category === 'communication' ? 'text-blue-600 dark:text-blue-500' : 'text-gray-600 dark:text-[#AAA]'
              }`}>
                {formatDuration(seconds)}
              </p>
              <p className="text-sm text-gray-500 dark:text-[#888] capitalize">{category}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
