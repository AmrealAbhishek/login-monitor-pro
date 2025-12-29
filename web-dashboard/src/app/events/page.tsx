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
        return <Monitor className="w-5 h-5 text-green-500" />;
      case 'Unlock':
        return <Shield className="w-5 h-5 text-blue-500" />;
      case 'Lock':
        return <Shield className="w-5 h-5 text-gray-500" />;
      case 'Boot':
        return <Activity className="w-5 h-5 text-purple-500" />;
      default:
        return <Activity className="w-5 h-5 text-gray-500" />;
    }
  };

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'Login':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'Unlock':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'Lock':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      case 'Boot':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Activity Log</h1>
          <p className="text-gray-600">All login, unlock, and boot events</p>
        </div>
        <div className="flex gap-2">
          {['all', 'Login', 'Unlock', 'Lock', 'Boot'].map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === type
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {type === 'all' ? 'All' : type}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Events List */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border">
          <div className="p-4 border-b">
            <h2 className="font-semibold">Recent Events ({events.length})</h2>
          </div>
          <div className="divide-y max-h-[700px] overflow-auto">
            {events.map((event) => (
              <button
                key={event.id}
                onClick={() => setSelectedEvent(event)}
                className={`w-full p-4 text-left hover:bg-gray-50 transition-colors ${
                  selectedEvent?.id === event.id ? 'bg-red-50' : ''
                }`}
              >
                <div className="flex items-start gap-4">
                  {getEventIcon(event.event_type)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getEventColor(event.event_type)}`}>
                        {event.event_type}
                      </span>
                      <span className="text-sm text-gray-500">{event.hostname}</span>
                    </div>
                    <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
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
                    <Image className="w-5 h-5 text-gray-400" />
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Event Details */}
        <div className="bg-white rounded-xl shadow-sm border">
          {selectedEvent ? (
            <div className="p-6 space-y-6">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  {getEventIcon(selectedEvent.event_type)}
                  <h2 className="text-lg font-semibold">{selectedEvent.event_type} Event</h2>
                </div>
                <p className="text-sm text-gray-500">
                  {format(new Date(selectedEvent.created_at), 'MMMM d, yyyy at h:mm:ss a')}
                </p>
              </div>

              {/* Photo */}
              {selectedEvent.photo_url && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Captured Photo</h3>
                  <a href={selectedEvent.photo_url} target="_blank" rel="noopener noreferrer">
                    <img
                      src={selectedEvent.photo_url}
                      alt="Captured"
                      className="w-full rounded-lg border"
                    />
                  </a>
                </div>
              )}

              {/* Device Info */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Device</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Hostname</span>
                    <span className="font-medium">{selectedEvent.hostname}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">User</span>
                    <span className="font-medium">{selectedEvent.user}</span>
                  </div>
                </div>
              </div>

              {/* Network */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Network</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Public IP</span>
                    <span className="font-medium">{selectedEvent.public_ip}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Local IP</span>
                    <span className="font-medium">{selectedEvent.local_ip}</span>
                  </div>
                  {selectedEvent.wifi?.ssid && (
                    <div className="flex justify-between">
                      <span className="text-gray-500 flex items-center gap-1">
                        <Wifi className="w-3 h-3" /> WiFi
                      </span>
                      <span className="font-medium">{selectedEvent.wifi.ssid}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Location */}
              {selectedEvent.location && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Location</h3>
                  <div className="space-y-2 text-sm">
                    {selectedEvent.location.city && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">City</span>
                        <span className="font-medium">
                          {selectedEvent.location.city}, {selectedEvent.location.country}
                        </span>
                      </div>
                    )}
                    {selectedEvent.location.latitude && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Coordinates</span>
                        <span className="font-medium">
                          {selectedEvent.location.latitude.toFixed(4)}, {selectedEvent.location.longitude?.toFixed(4)}
                        </span>
                      </div>
                    )}
                    {selectedEvent.location.google_maps && (
                      <a
                        href={selectedEvent.location.google_maps}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-red-600 hover:underline"
                      >
                        <ExternalLink className="w-3 h-3" />
                        View on Google Maps
                      </a>
                    )}
                  </div>
                </div>
              )}

              {/* Battery */}
              {selectedEvent.battery && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Battery</h3>
                  <div className="flex items-center gap-2">
                    <Battery className="w-4 h-4 text-gray-500" />
                    <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          (selectedEvent.battery.percentage || 0) > 20 ? 'bg-green-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${selectedEvent.battery.percentage || 0}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium">{selectedEvent.battery.percentage}%</span>
                    {selectedEvent.battery.charging && (
                      <span className="text-xs text-green-600">Charging</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-12 text-center">
              <Activity className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Select an event to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
