'use client';

import { useEffect, useState } from 'react';
import { supabase, Event } from '@/lib/supabase';
import {
  Monitor,
  Shield,
  Activity,
  MapPin,
  Battery,
  Wifi,
  Clock,
  ExternalLink,
  Image,
  Power,
  Loader2,
} from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';

export default function EventsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    fetchEvents();

    // Realtime subscription
    const channel = supabase
      .channel('events-realtime')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'events' }, (payload) => {
        setEvents(prev => [payload.new as Event, ...prev]);
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  async function fetchEvents() {
    let query = supabase
      .from('events')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(100);

    if (filter !== 'all') {
      query = query.eq('event_type', filter);
    }

    const { data } = await query;
    if (data) {
      setEvents(data);
    }
    setLoading(false);
  }

  useEffect(() => {
    fetchEvents();
  }, [filter]);

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'Login':
        return <Monitor className="w-5 h-5 text-green-400" />;
      case 'Unlock':
        return <Shield className="w-5 h-5 text-blue-400" />;
      case 'Lock':
        return <Shield className="w-5 h-5 text-[#666]" />;
      case 'Boot':
        return <Power className="w-5 h-5 text-purple-400" />;
      default:
        return <Activity className="w-5 h-5 text-[#666]" />;
    }
  };

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'Login':
        return 'bg-green-500/20 text-green-400 border-green-500/50';
      case 'Unlock':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
      case 'Lock':
        return 'bg-[#333] text-[#888] border-[#444]';
      case 'Boot':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/50';
      default:
        return 'bg-[#333] text-[#888] border-[#444]';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-10 h-10 text-red-500 animate-spin" />
          <p className="text-[#666]">Loading activity...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Activity className="w-7 h-7 text-red-500" />
            Activity Log
          </h1>
          <p className="text-[#666] mt-1">All login, unlock, and boot events</p>
        </div>
        <div className="flex gap-2">
          {['all', 'Login', 'Unlock', 'Lock', 'Boot'].map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                filter === type
                  ? 'bg-red-600 text-white shadow-lg shadow-red-500/20'
                  : 'bg-[#1A1A1A] text-[#888] border border-[#333] hover:border-red-500/50 hover:text-white'
              }`}
            >
              {type === 'all' ? 'All' : type}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Events List */}
        <div className="lg:col-span-2 neon-card overflow-hidden">
          <div className="p-4 border-b border-[#222]">
            <h2 className="font-semibold text-white">Recent Events ({events.length})</h2>
          </div>
          <div className="divide-y divide-[#1A1A1A] max-h-[700px] overflow-auto">
            {events.length === 0 ? (
              <div className="p-12 text-center">
                <Activity className="w-12 h-12 text-[#333] mx-auto mb-4" />
                <p className="text-[#666]">No events recorded yet</p>
              </div>
            ) : (
              events.map((event) => (
                <button
                  key={event.id}
                  onClick={() => setSelectedEvent(event)}
                  className={`w-full p-4 text-left transition-all duration-200 ${
                    selectedEvent?.id === event.id
                      ? 'bg-red-500/10 border-l-2 border-red-500'
                      : 'hover:bg-[#111]'
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 bg-[#1A1A1A] rounded-xl flex items-center justify-center">
                      {getEventIcon(event.event_type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${getEventColor(event.event_type)}`}>
                          {event.event_type}
                        </span>
                        <span className="text-sm text-[#888]">{event.hostname}</span>
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-sm text-[#666]">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {format(new Date(event.created_at), 'MMM d, h:mm a')}
                        </span>
                        {event.location?.city && (
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            {event.location.city}, {event.location.country}
                          </span>
                        )}
                      </div>
                    </div>
                    {event.photo_url && (
                      <div className="w-8 h-8 bg-[#1A1A1A] rounded-lg flex items-center justify-center">
                        <Image className="w-4 h-4 text-[#666]" />
                      </div>
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Event Details */}
        <div className="neon-card overflow-hidden">
          {selectedEvent ? (
            <div className="p-6 space-y-6">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-[#1A1A1A] rounded-xl flex items-center justify-center">
                    {getEventIcon(selectedEvent.event_type)}
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-white">{selectedEvent.event_type} Event</h2>
                    <p className="text-sm text-[#666]">
                      {format(new Date(selectedEvent.created_at), 'MMMM d, yyyy at h:mm:ss a')}
                    </p>
                  </div>
                </div>
              </div>

              {/* Photo */}
              {selectedEvent.photo_url && (
                <div>
                  <h3 className="text-sm font-medium text-[#888] mb-2">Captured Photo</h3>
                  <a href={selectedEvent.photo_url} target="_blank" rel="noopener noreferrer" className="block">
                    <img
                      src={selectedEvent.photo_url}
                      alt="Captured"
                      className="w-full rounded-xl border border-[#333] hover:border-red-500/50 transition-colors"
                    />
                  </a>
                </div>
              )}

              {/* Device Info */}
              <div>
                <h3 className="text-sm font-medium text-[#888] mb-3">Device</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between p-3 bg-[#111] rounded-xl">
                    <span className="text-[#666]">Hostname</span>
                    <span className="font-medium text-white">{selectedEvent.hostname}</span>
                  </div>
                  <div className="flex justify-between p-3 bg-[#111] rounded-xl">
                    <span className="text-[#666]">User</span>
                    <span className="font-medium text-white">{selectedEvent.user}</span>
                  </div>
                </div>
              </div>

              {/* Network */}
              <div>
                <h3 className="text-sm font-medium text-[#888] mb-3">Network</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between p-3 bg-[#111] rounded-xl">
                    <span className="text-[#666]">Public IP</span>
                    <span className="font-medium text-white font-mono">{selectedEvent.public_ip}</span>
                  </div>
                  <div className="flex justify-between p-3 bg-[#111] rounded-xl">
                    <span className="text-[#666]">Local IP</span>
                    <span className="font-medium text-white font-mono">{selectedEvent.local_ip}</span>
                  </div>
                  {selectedEvent.wifi?.ssid && (
                    <div className="flex justify-between p-3 bg-[#111] rounded-xl">
                      <span className="text-[#666] flex items-center gap-2">
                        <Wifi className="w-4 h-4" /> WiFi
                      </span>
                      <span className="font-medium text-white">{selectedEvent.wifi.ssid}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Location */}
              {selectedEvent.location && (
                <div>
                  <h3 className="text-sm font-medium text-[#888] mb-3">Location</h3>
                  <div className="space-y-2 text-sm">
                    {selectedEvent.location.city && (
                      <div className="flex justify-between p-3 bg-[#111] rounded-xl">
                        <span className="text-[#666]">City</span>
                        <span className="font-medium text-white">
                          {selectedEvent.location.city}, {selectedEvent.location.country}
                        </span>
                      </div>
                    )}
                    {selectedEvent.location.latitude && (
                      <div className="flex justify-between p-3 bg-[#111] rounded-xl">
                        <span className="text-[#666]">Coordinates</span>
                        <span className="font-medium text-white font-mono text-xs">
                          {selectedEvent.location.latitude.toFixed(4)}, {selectedEvent.location.longitude?.toFixed(4)}
                        </span>
                      </div>
                    )}
                    {selectedEvent.location.google_maps && (
                      <a
                        href={selectedEvent.location.google_maps}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-center gap-2 p-3 bg-red-500/10 text-red-500 hover:bg-red-500/20 rounded-xl transition-colors font-medium"
                      >
                        <ExternalLink className="w-4 h-4" />
                        View on Google Maps
                      </a>
                    )}
                  </div>
                </div>
              )}

              {/* Battery */}
              {selectedEvent.battery && (
                <div>
                  <h3 className="text-sm font-medium text-[#888] mb-3">Battery</h3>
                  <div className="p-4 bg-[#111] rounded-xl">
                    <div className="flex items-center gap-3">
                      <Battery className={`w-5 h-5 ${
                        (selectedEvent.battery.percentage || 0) > 20 ? 'text-green-400' : 'text-red-500'
                      }`} />
                      <div className="flex-1">
                        <div className="h-3 bg-[#222] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              (selectedEvent.battery.percentage || 0) > 20 ? 'bg-green-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${selectedEvent.battery.percentage || 0}%` }}
                          />
                        </div>
                      </div>
                      <span className="text-white font-bold">{selectedEvent.battery.percentage}%</span>
                    </div>
                    {selectedEvent.battery.charging && (
                      <p className="text-xs text-green-400 mt-2 text-center">Charging</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-12 text-center">
              <div className="w-16 h-16 bg-[#1A1A1A] rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Activity className="w-8 h-8 text-[#333]" />
              </div>
              <p className="text-[#666]">Select an event to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
