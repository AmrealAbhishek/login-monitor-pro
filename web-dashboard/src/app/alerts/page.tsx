'use client';

import { useEffect, useState } from 'react';
import { supabase, SecurityAlert } from '@/lib/supabase';
import { AlertTriangle, Check, Clock, Shield, X, User } from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'active' | 'acknowledged'>('all');

  useEffect(() => {
    fetchAlerts();

    // Realtime subscription
    const channel = supabase
      .channel('alerts-realtime')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'security_alerts' }, (payload) => {
        if (payload.eventType === 'INSERT') {
          setAlerts(prev => [payload.new as SecurityAlert, ...prev]);
        } else if (payload.eventType === 'UPDATE') {
          setAlerts(prev =>
            prev.map(alert => alert.id === payload.new.id ? payload.new as SecurityAlert : alert)
          );
        }
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  async function fetchAlerts() {
    let query = supabase
      .from('security_alerts')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(100);

    if (filter === 'active') {
      query = query.eq('acknowledged', false);
    } else if (filter === 'acknowledged') {
      query = query.eq('acknowledged', true);
    }

    const { data } = await query;
    if (data) {
      setAlerts(data);
    }
    setLoading(false);
  }

  useEffect(() => {
    fetchAlerts();
  }, [filter]);

  async function acknowledgeAlert(alertId: string) {
    await supabase
      .from('security_alerts')
      .update({
        acknowledged: true,
        acknowledged_at: new Date().toISOString(),
      })
      .eq('id', alertId);
  }

  async function dismissAlert(alertId: string) {
    await supabase.from('security_alerts').delete().eq('id', alertId);
    setAlerts(prev => prev.filter(a => a.id !== alertId));
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500';
      case 'high':
        return 'bg-orange-500';
      case 'medium':
        return 'bg-yellow-500';
      default:
        return 'bg-blue-500';
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400 border-red-200 dark:border-red-800';
      case 'high':
        return 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-400 border-orange-200 dark:border-orange-800';
      case 'medium':
        return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800';
      default:
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400 border-blue-200 dark:border-blue-800';
    }
  };

  const activeAlerts = alerts.filter(a => !a.acknowledged);
  const acknowledgedAlerts = alerts.filter(a => a.acknowledged);

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
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Security Alerts</h1>
          <p className="text-gray-600 dark:text-[#888]">Monitor and respond to security threats</p>
        </div>
        <div className="flex gap-2">
          {['all', 'active', 'acknowledged'].map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type as typeof filter)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === type
                  ? 'bg-red-600 text-white shadow-lg shadow-red-500/20'
                  : 'bg-gray-100 dark:bg-[#1A1A1A] text-gray-700 dark:text-[#AAA] hover:bg-gray-200 dark:hover:bg-[#222] border border-gray-200 dark:border-[#333]'
              }`}
            >
              {type.charAt(0).toUpperCase() + type.slice(1)}
              {type === 'active' && activeAlerts.length > 0 && (
                <span className="ml-2 px-2 py-0.5 bg-red-500 text-white rounded-full text-xs">
                  {activeAlerts.length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl p-4 shadow-sm border border-gray-200 dark:border-[#333]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-[#888]">Total Alerts</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{alerts.length}</p>
            </div>
            <AlertTriangle className="w-8 h-8 text-gray-300 dark:text-[#444]" />
          </div>
        </div>
        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl p-4 shadow-sm border border-gray-200 dark:border-[#333]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-[#888]">Active</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-500">{activeAlerts.length}</p>
            </div>
            <div className="w-8 h-8 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
              <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-500" />
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl p-4 shadow-sm border border-gray-200 dark:border-[#333]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-[#888]">Critical</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-500">
                {alerts.filter(a => a.severity === 'critical' && !a.acknowledged).length}
              </p>
            </div>
            <div className="w-8 h-8 bg-red-500 rounded-full flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl p-4 shadow-sm border border-gray-200 dark:border-[#333]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-[#888]">Acknowledged</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-500">{acknowledgedAlerts.length}</p>
            </div>
            <div className="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
              <Check className="w-4 h-4 text-green-600 dark:text-green-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Alerts List */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl shadow-sm border border-gray-200 dark:border-[#333]">
        <div className="p-4 border-b border-gray-200 dark:border-[#333]">
          <h2 className="font-semibold text-gray-900 dark:text-white">
            {filter === 'all' ? 'All Alerts' : filter === 'active' ? 'Active Alerts' : 'Acknowledged Alerts'}
          </h2>
        </div>
        <div className="divide-y divide-gray-100 dark:divide-[#333]">
          {alerts.length === 0 ? (
            <div className="p-12 text-center">
              <Shield className="w-12 h-12 text-green-300 dark:text-green-800 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-[#888]">No alerts found</p>
            </div>
          ) : (
            alerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-4 hover:bg-gray-50 dark:hover:bg-[#222] transition-colors ${
                  alert.acknowledged ? 'opacity-60' : ''
                }`}
              >
                <div className="flex items-start gap-4">
                  <div className={`w-1 self-stretch rounded-full ${getSeverityColor(alert.severity)}`} />
                  <AlertTriangle
                    className={`w-5 h-5 mt-0.5 flex-shrink-0 ${
                      alert.severity === 'critical'
                        ? 'text-red-500'
                        : alert.severity === 'high'
                        ? 'text-orange-500'
                        : alert.severity === 'medium'
                        ? 'text-yellow-500'
                        : 'text-blue-500'
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-medium text-gray-900 dark:text-white">{alert.title}</h3>
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getSeverityBadge(
                          alert.severity
                        )}`}
                      >
                        {alert.severity}
                      </span>
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-[#333] text-gray-600 dark:text-[#AAA]">
                        {alert.alert_type}
                      </span>
                      {alert.acknowledged && (
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400">
                          Acknowledged
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 dark:text-[#AAA] mt-1">{alert.description}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-500 dark:text-[#666]">
                      {alert.metadata?.user_name && (
                        <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400">
                          <User className="w-3 h-3" />
                          {alert.metadata.user_name}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                      </span>
                      <span>{format(new Date(alert.created_at), 'MMM d, h:mm a')}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {!alert.acknowledged && (
                      <button
                        onClick={() => acknowledgeAlert(alert.id)}
                        className="p-2 text-green-600 dark:text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-colors"
                        title="Acknowledge"
                      >
                        <Check className="w-5 h-5" />
                      </button>
                    )}
                    <button
                      onClick={() => dismissAlert(alert.id)}
                      className="p-2 text-gray-400 dark:text-[#666] hover:text-red-600 dark:hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                      title="Dismiss"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
