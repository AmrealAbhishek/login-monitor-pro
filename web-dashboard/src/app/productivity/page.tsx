'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import {
  BarChart3,
  Clock,
  TrendingUp,
  Calendar,
  Monitor,
  Coffee,
  Zap,
} from 'lucide-react';
import { format, subDays, startOfWeek, endOfWeek } from 'date-fns';

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

    // Fetch app usage
    const { data: usageData } = await supabase
      .from('app_usage')
      .select('*')
      .gte('recorded_at', startDate.toISOString())
      .order('duration_seconds', { ascending: false })
      .limit(50);

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
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBg = (score: number) => {
    if (score >= 80) return 'bg-green-100';
    if (score >= 60) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'productive':
        return 'bg-green-100 text-green-800';
      case 'unproductive':
        return 'bg-red-100 text-red-800';
      case 'communication':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Productivity Analytics</h1>
          <p className="text-gray-600">Track work patterns and app usage</p>
        </div>
        <div className="flex gap-2">
          {(['today', 'week', 'month'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setDateRange(range)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                dateRange === range
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {range.charAt(0).toUpperCase() + range.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Average Score</p>
              <p className={`text-3xl font-bold ${getScoreColor(avgScore)}`}>
                {avgScore.toFixed(0)}%
              </p>
            </div>
            <div className={`w-12 h-12 rounded-full ${getScoreBg(avgScore)} flex items-center justify-center`}>
              <TrendingUp className={`w-6 h-6 ${getScoreColor(avgScore)}`} />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Productive Time</p>
              <p className="text-3xl font-bold text-green-600">{formatDuration(totalProductive)}</p>
            </div>
            <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
              <Zap className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Idle Time</p>
              <p className="text-3xl font-bold text-yellow-600">{formatDuration(totalIdle)}</p>
            </div>
            <div className="w-12 h-12 rounded-full bg-yellow-100 flex items-center justify-center">
              <Coffee className="w-6 h-6 text-yellow-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Unproductive</p>
              <p className="text-3xl font-bold text-red-600">{formatDuration(totalUnproductive)}</p>
            </div>
            <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
              <Monitor className="w-6 h-6 text-red-600" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Scores */}
        <div className="bg-white rounded-xl shadow-sm border">
          <div className="p-4 border-b">
            <h2 className="font-semibold flex items-center gap-2">
              <Calendar className="w-5 h-5" />
              Daily Productivity
            </h2>
          </div>
          <div className="p-4">
            {scores.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <BarChart3 className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p>No productivity data yet</p>
                <p className="text-sm">Data will appear once app tracking starts</p>
              </div>
            ) : (
              <div className="space-y-3">
                {scores.slice(0, 7).map((score) => (
                  <div key={score.id} className="flex items-center gap-4">
                    <div className="w-24 text-sm text-gray-500">
                      {format(new Date(score.date), 'MMM d')}
                    </div>
                    <div className="flex-1">
                      <div className="h-6 bg-gray-100 rounded-full overflow-hidden flex">
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
            <div className="flex justify-center gap-6 mt-4 text-xs">
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
        <div className="bg-white rounded-xl shadow-sm border">
          <div className="p-4 border-b">
            <h2 className="font-semibold flex items-center gap-2">
              <Monitor className="w-5 h-5" />
              Top Applications
            </h2>
          </div>
          <div className="divide-y max-h-96 overflow-auto">
            {appUsage.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Monitor className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p>No app usage data yet</p>
              </div>
            ) : (
              appUsage.slice(0, 10).map((app) => (
                <div key={app.id} className="p-4 flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{app.app_name}</p>
                    <p className="text-sm text-gray-500 truncate">{app.window_title}</p>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(app.category)}`}>
                    {app.category}
                  </span>
                  <div className="text-right">
                    <p className="font-medium">{formatDuration(app.duration_seconds)}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Time Distribution */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5" />
          Time Distribution by Category
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(usageByCategory).map(([category, seconds]) => (
            <div key={category} className="text-center p-4 bg-gray-50 rounded-lg">
              <p className={`text-2xl font-bold ${
                category === 'productive' ? 'text-green-600' :
                category === 'unproductive' ? 'text-red-600' :
                category === 'communication' ? 'text-blue-600' : 'text-gray-600'
              }`}>
                {formatDuration(seconds)}
              </p>
              <p className="text-sm text-gray-500 capitalize">{category}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
