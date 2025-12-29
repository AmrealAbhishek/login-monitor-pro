'use client';

import { useEffect, useState } from 'react';
import { supabase, Device, Event, SecurityAlert } from '@/lib/supabase';
import { Monitor, Activity, AlertTriangle, Shield, Clock, MapPin } from 'lucide-react';
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
          setDevices(devicesData);
          const onlineCount = devicesData.filter(d => {
            const lastSeen = new Date(d.last_seen);
            const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
            return lastSeen > fiveMinutesAgo;
          }).length;

          setStats(prev => ({
            ...prev,
            totalDevices: devicesData.length,
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
        return <Monitor className="w-4 h-4 text-green-500" />;
      case 'Unlock':
        return <Shield className="w-4 h-4 text-blue-500" />;
      case 'Lock':
        return <Shield className="w-4 h-4 text-gray-500" />;
      default:
        return <Activity className="w-4 h-4 text-gray-500" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default:
        return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Overview of your security monitoring</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Devices</p>
              <p className="text-3xl font-bold text-gray-900">{stats.totalDevices}</p>
            </div>
            <div className="p-3 bg-blue-100 rounded-lg">
              <Monitor className="w-6 h-6 text-blue-600" />
            </div>
          </div>
          <p className="text-sm text-green-600 mt-2">
            {stats.onlineDevices} online
          </p>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Today&apos;s Events</p>
              <p className="text-3xl font-bold text-gray-900">{stats.todayEvents}</p>
            </div>
            <div className="p-3 bg-green-100 rounded-lg">
              <Activity className="w-6 h-6 text-green-600" />
            </div>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            Login &amp; unlock events
          </p>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Active Alerts</p>
              <p className="text-3xl font-bold text-gray-900">{stats.activeAlerts}</p>
            </div>
            <div className="p-3 bg-red-100 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-red-600" />
            </div>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            Unacknowledged alerts
          </p>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Security Score</p>
              <p className="text-3xl font-bold text-gray-900">
                {stats.activeAlerts === 0 ? '100%' : `${Math.max(0, 100 - stats.activeAlerts * 10)}%`}
              </p>
            </div>
            <div className="p-3 bg-purple-100 rounded-lg">
              <Shield className="w-6 h-6 text-purple-600" />
            </div>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            Based on active alerts
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Events */}
        <div className="bg-white rounded-xl shadow-sm border">
          <div className="p-6 border-b">
            <h2 className="text-lg font-semibold">Recent Activity</h2>
          </div>
          <div className="divide-y max-h-96 overflow-auto">
            {recentEvents.length === 0 ? (
              <div className="p-6 text-center text-gray-500">
                No events today
              </div>
            ) : (
              recentEvents.map((event) => (
                <div key={event.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-center gap-4">
                    {getEventIcon(event.event_type)}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900">
                        {event.event_type} - {event.hostname}
                      </p>
                      <div className="flex items-center gap-4 text-sm text-gray-500">
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
        <div className="bg-white rounded-xl shadow-sm border">
          <div className="p-6 border-b">
            <h2 className="text-lg font-semibold">Security Alerts</h2>
          </div>
          <div className="divide-y max-h-96 overflow-auto">
            {recentAlerts.length === 0 ? (
              <div className="p-6 text-center text-gray-500">
                No active alerts
              </div>
            ) : (
              recentAlerts.map((alert) => (
                <div key={alert.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start gap-4">
                    <AlertTriangle className={`w-5 h-5 mt-0.5 ${
                      alert.severity === 'critical' ? 'text-red-500' :
                      alert.severity === 'high' ? 'text-orange-500' :
                      alert.severity === 'medium' ? 'text-yellow-500' : 'text-blue-500'
                    }`} />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-gray-900">{alert.title}</p>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getSeverityColor(alert.severity)}`}>
                          {alert.severity}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500 mt-1">{alert.description}</p>
                      <p className="text-xs text-gray-400 mt-2">
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
      <div className="bg-white rounded-xl shadow-sm border">
        <div className="p-6 border-b">
          <h2 className="text-lg font-semibold">Devices</h2>
        </div>
        <div className="divide-y">
          {devices.map((device) => {
            const isOnline = new Date(device.last_seen) > new Date(Date.now() - 5 * 60 * 1000);
            return (
              <div key={device.id} className="p-4 hover:bg-gray-50 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-3 h-3 rounded-full ${isOnline ? 'bg-green-500' : 'bg-gray-300'}`} />
                  <div>
                    <p className="font-medium text-gray-900">{device.device_name || device.hostname}</p>
                    <p className="text-sm text-gray-500">{device.os}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-500">
                    Last seen {formatDistanceToNow(new Date(device.last_seen), { addSuffix: true })}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
