'use client';

import { useEffect, useState } from 'react';
import { supabase, Device, Event, SecurityAlert } from '@/lib/supabase';
import { Monitor, Activity, AlertTriangle, Shield, Clock, MapPin, Loader2, TrendingUp, Zap } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface Stats {
  totalDevices: number;
  onlineDevices: number;
  todayEvents: number;
  activeAlerts: number;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats>({
    totalDevices: 0,
    onlineDevices: 0,
    todayEvents: 0,
    activeAlerts: 0,
  });
  const [recentEvents, setRecentEvents] = useState<Event[]>([]);
  const [recentAlerts, setRecentAlerts] = useState<SecurityAlert[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        // Fetch devices
        const { data: devicesData } = await supabase
          .from('devices')
          .select('*')
          .order('last_seen', { ascending: false });

        if (devicesData) {
          // Deduplicate by hostname
          const deviceMap = new Map<string, Device>();
          for (const device of devicesData) {
            if (!deviceMap.has(device.hostname) ||
                new Date(device.last_seen) > new Date(deviceMap.get(device.hostname)!.last_seen)) {
              deviceMap.set(device.hostname, device);
            }
          }
          const uniqueDevices = Array.from(deviceMap.values());

          setDevices(uniqueDevices);
          const onlineCount = uniqueDevices.filter(d => {
            const lastSeen = new Date(d.last_seen);
            const oneMinuteAgo = new Date(Date.now() - 60 * 1000);
            return lastSeen > oneMinuteAgo;
          }).length;

          setStats(prev => ({
            ...prev,
            totalDevices: uniqueDevices.length,
            onlineDevices: onlineCount,
          }));
        }

        // Fetch today's events
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const { data: eventsData, count: eventsCount } = await supabase
          .from('events')
          .select('*', { count: 'exact' })
          .gte('created_at', today.toISOString())
          .order('created_at', { ascending: false })
          .limit(10);

        if (eventsData) {
          setRecentEvents(eventsData);
          setStats(prev => ({ ...prev, todayEvents: eventsCount || 0 }));
        }

        // Fetch unacknowledged alerts
        const { data: alertsData, count: alertsCount } = await supabase
          .from('security_alerts')
          .select('*', { count: 'exact' })
          .eq('acknowledged', false)
          .order('created_at', { ascending: false })
          .limit(5);

        if (alertsData) {
          setRecentAlerts(alertsData);
          setStats(prev => ({ ...prev, activeAlerts: alertsCount || 0 }));
        }
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchData();

    // Set up realtime subscription for events
    const eventsChannel = supabase
      .channel('dashboard-events')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'events' }, (payload) => {
        setRecentEvents(prev => [payload.new as Event, ...prev.slice(0, 9)]);
        setStats(prev => ({ ...prev, todayEvents: prev.todayEvents + 1 }));
      })
      .subscribe();

    // Realtime for alerts
    const alertsChannel = supabase
      .channel('dashboard-alerts')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'security_alerts' }, (payload) => {
        setRecentAlerts(prev => [payload.new as SecurityAlert, ...prev.slice(0, 4)]);
        setStats(prev => ({ ...prev, activeAlerts: prev.activeAlerts + 1 }));
      })
      .subscribe();

    return () => {
      supabase.removeChannel(eventsChannel);
      supabase.removeChannel(alertsChannel);
    };
  }, []);

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'Login':
        return <Monitor className="w-4 h-4 text-green-400" />;
      case 'Unlock':
        return <Shield className="w-4 h-4 text-blue-400" />;
      case 'Lock':
        return <Shield className="w-4 h-4 text-[#666]" />;
      default:
        return <Activity className="w-4 h-4 text-[#666]" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      case 'high':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/50';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      default:
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
    }
  };

  const securityScore = stats.activeAlerts === 0 ? 100 : Math.max(0, 100 - stats.activeAlerts * 10);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-10 h-10 text-red-500 animate-spin" />
          <p className="text-[#666]">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Shield className="w-7 h-7 text-red-500" />
          Dashboard
        </h1>
        <p className="text-[#666] mt-1">Overview of your security monitoring</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Devices */}
        <div className="neon-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[#666] uppercase tracking-wider">Total Devices</p>
              <p className="text-3xl font-bold text-white mt-1">{stats.totalDevices}</p>
            </div>
            <div className="w-12 h-12 bg-blue-500/20 rounded-xl flex items-center justify-center">
              <Monitor className="w-6 h-6 text-blue-400" />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full pulse-online" />
            <p className="text-sm text-green-400">{stats.onlineDevices} online</p>
          </div>
        </div>

        {/* Today's Events */}
        <div className="neon-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[#666] uppercase tracking-wider">Today&apos;s Events</p>
              <p className="text-3xl font-bold text-white mt-1">{stats.todayEvents}</p>
            </div>
            <div className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center">
              <Activity className="w-6 h-6 text-green-400" />
            </div>
          </div>
          <p className="text-sm text-[#666] mt-4 flex items-center gap-2">
            <Zap className="w-3 h-3" />
            Login & unlock events
          </p>
        </div>

        {/* Active Alerts */}
        <div className={`neon-card p-6 ${stats.activeAlerts > 0 ? 'border-red-500/50' : ''}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[#666] uppercase tracking-wider">Active Alerts</p>
              <p className="text-3xl font-bold text-white mt-1">{stats.activeAlerts}</p>
            </div>
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
              stats.activeAlerts > 0 ? 'bg-red-500/20' : 'bg-[#1A1A1A]'
            }`}>
              <AlertTriangle className={`w-6 h-6 ${stats.activeAlerts > 0 ? 'text-red-500' : 'text-[#666]'}`} />
            </div>
          </div>
          <p className="text-sm text-[#666] mt-4">
            {stats.activeAlerts === 0 ? 'All clear' : 'Requires attention'}
          </p>
        </div>

        {/* Security Score */}
        <div className={`neon-card p-6 ${securityScore === 100 ? 'neon-card-success' : ''}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[#666] uppercase tracking-wider">Security Score</p>
              <p className={`text-3xl font-bold mt-1 ${
                securityScore === 100 ? 'text-green-400' :
                securityScore >= 70 ? 'text-yellow-400' : 'text-red-500'
              }`}>{securityScore}%</p>
            </div>
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
              securityScore === 100 ? 'bg-green-500/20' : 'bg-purple-500/20'
            }`}>
              <TrendingUp className={`w-6 h-6 ${securityScore === 100 ? 'text-green-400' : 'text-purple-400'}`} />
            </div>
          </div>
          <p className="text-sm text-[#666] mt-4">Based on active alerts</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Events */}
        <div className="neon-card overflow-hidden">
          <div className="p-4 border-b border-[#222] flex items-center justify-between">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-red-500" />
              Recent Activity
            </h2>
            <span className="text-xs text-[#666] bg-[#1A1A1A] px-2 py-1 rounded-lg">{stats.todayEvents} today</span>
          </div>
          <div className="divide-y divide-[#1A1A1A] max-h-96 overflow-auto">
            {recentEvents.length === 0 ? (
              <div className="p-8 text-center">
                <Activity className="w-10 h-10 text-[#222] mx-auto mb-3" />
                <p className="text-[#666]">No events today</p>
              </div>
            ) : (
              recentEvents.map((event) => (
                <div key={event.id} className="p-4 hover:bg-[#0D0D0D] transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="w-8 h-8 bg-[#1A1A1A] rounded-lg flex items-center justify-center">
                      {getEventIcon(event.event_type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-white">
                        {event.event_type} - <span className="text-[#AAA]">{event.hostname}</span>
                      </p>
                      <div className="flex items-center gap-4 text-xs text-[#666] mt-1">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDistanceToNow(new Date(event.created_at), { addSuffix: true })}
                        </span>
                        {event.location?.city && (
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            {event.location.city}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Security Alerts */}
        <div className={`neon-card overflow-hidden ${stats.activeAlerts > 0 ? 'border-red-500/30' : ''}`}>
          <div className="p-4 border-b border-[#222] flex items-center justify-between">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <AlertTriangle className={`w-5 h-5 ${stats.activeAlerts > 0 ? 'text-red-500' : 'text-[#666]'}`} />
              Security Alerts
            </h2>
            {stats.activeAlerts > 0 && (
              <span className="text-xs text-red-400 bg-red-500/10 px-2 py-1 rounded-lg border border-red-500/30">
                {stats.activeAlerts} active
              </span>
            )}
          </div>
          <div className="divide-y divide-[#1A1A1A] max-h-96 overflow-auto">
            {recentAlerts.length === 0 ? (
              <div className="p-8 text-center">
                <Shield className="w-10 h-10 text-green-500/30 mx-auto mb-3" />
                <p className="text-green-400">All clear - No active alerts</p>
              </div>
            ) : (
              recentAlerts.map((alert) => (
                <div key={alert.id} className="p-4 hover:bg-[#0D0D0D] transition-colors">
                  <div className="flex items-start gap-4">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      alert.severity === 'critical' ? 'bg-red-500/20' :
                      alert.severity === 'high' ? 'bg-orange-500/20' :
                      alert.severity === 'medium' ? 'bg-yellow-500/20' : 'bg-blue-500/20'
                    }`}>
                      <AlertTriangle className={`w-4 h-4 ${
                        alert.severity === 'critical' ? 'text-red-500' :
                        alert.severity === 'high' ? 'text-orange-400' :
                        alert.severity === 'medium' ? 'text-yellow-400' : 'text-blue-400'
                      }`} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-medium text-white">{alert.title}</p>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getSeverityColor(alert.severity)}`}>
                          {alert.severity}
                        </span>
                      </div>
                      <p className="text-sm text-[#666] mt-1">{alert.description}</p>
                      <p className="text-xs text-[#555] mt-2">
                        {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Devices List */}
      <div className="neon-card overflow-hidden">
        <div className="p-4 border-b border-[#222] flex items-center justify-between">
          <h2 className="font-semibold text-white flex items-center gap-2">
            <Monitor className="w-5 h-5 text-red-500" />
            Devices
          </h2>
          <span className="text-xs text-[#666] bg-[#1A1A1A] px-2 py-1 rounded-lg">
            {stats.onlineDevices}/{stats.totalDevices} online
          </span>
        </div>
        <div className="divide-y divide-[#1A1A1A]">
          {devices.length === 0 ? (
            <div className="p-8 text-center">
              <Monitor className="w-10 h-10 text-[#222] mx-auto mb-3" />
              <p className="text-[#666]">No devices registered</p>
            </div>
          ) : (
            devices.slice(0, 5).map((device) => {
              const isOnline = new Date(device.last_seen) > new Date(Date.now() - 60 * 1000);
              return (
                <div key={device.id} className="p-4 hover:bg-[#0D0D0D] transition-colors flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                      isOnline ? 'bg-green-500/20' : 'bg-[#1A1A1A]'
                    }`}>
                      <Monitor className={`w-5 h-5 ${isOnline ? 'text-green-400' : 'text-[#444]'}`} />
                    </div>
                    <div>
                      <p className="font-medium text-white">{device.hostname}</p>
                      <p className="text-sm text-[#666]">{device.os_version}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${
                      isOnline ? 'status-online' : 'status-offline'
                    }`}>
                      {isOnline ? 'Online' : 'Offline'}
                    </span>
                    <p className="text-xs text-[#555] mt-2">
                      {formatDistanceToNow(new Date(device.last_seen), { addSuffix: true })}
                    </p>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
