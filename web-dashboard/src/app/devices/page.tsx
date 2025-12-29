'use client';

import { useEffect, useState } from 'react';
import { supabase, Device, Command } from '@/lib/supabase';
import {
  Monitor,
  Camera,
  MapPin,
  Volume2,
  Lock,
  Smartphone,
  Battery,
  Wifi,
  MoreVertical,
  Send,
  RefreshCw,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const COMMANDS = [
  { id: 'photo', label: 'Take Photo', icon: Camera, description: 'Capture a photo from the camera' },
  { id: 'screenshot', label: 'Screenshot', icon: Monitor, description: 'Take a screenshot' },
  { id: 'location', label: 'Get Location', icon: MapPin, description: 'Get current GPS location' },
  { id: 'battery', label: 'Battery Status', icon: Battery, description: 'Check battery level' },
  { id: 'wifi', label: 'WiFi Info', icon: Wifi, description: 'Get WiFi network info' },
  { id: 'lock', label: 'Lock Device', icon: Lock, description: 'Lock the screen' },
  { id: 'alarm', label: 'Play Alarm', icon: Volume2, description: 'Play alarm sound' },
  { id: 'findme', label: 'Find My Mac', icon: Smartphone, description: 'Play alarm and stream location' },
];

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [recentCommands, setRecentCommands] = useState<Command[]>([]);
  const [loading, setLoading] = useState(true);
  const [sendingCommand, setSendingCommand] = useState<string | null>(null);

  useEffect(() => {
    fetchDevices();
  }, []);

  useEffect(() => {
    if (selectedDevice) {
      fetchRecentCommands(selectedDevice.id);

      // Subscribe to command updates
      const channel = supabase
        .channel(`commands-${selectedDevice.id}`)
        .on('postgres_changes', {
          event: '*',
          schema: 'public',
          table: 'commands',
          filter: `device_id=eq.${selectedDevice.id}`,
        }, (payload) => {
          if (payload.eventType === 'INSERT') {
            setRecentCommands(prev => [payload.new as Command, ...prev.slice(0, 9)]);
          } else if (payload.eventType === 'UPDATE') {
            setRecentCommands(prev =>
              prev.map(cmd => cmd.id === payload.new.id ? payload.new as Command : cmd)
            );
          }
        })
        .subscribe();

      return () => {
        supabase.removeChannel(channel);
      };
    }
  }, [selectedDevice]);

  async function fetchDevices() {
    const { data } = await supabase
      .from('devices')
      .select('*')
      .order('last_seen', { ascending: false });

    if (data) {
      setDevices(data);
      if (data.length > 0 && !selectedDevice) {
        setSelectedDevice(data[0]);
      }
    }
    setLoading(false);
  }

  async function fetchRecentCommands(deviceId: string) {
    const { data } = await supabase
      .from('commands')
      .select('*')
      .eq('device_id', deviceId)
      .order('created_at', { ascending: false })
      .limit(10);

    if (data) {
      setRecentCommands(data);
    }
  }

  async function sendCommand(commandName: string) {
    if (!selectedDevice) return;

    setSendingCommand(commandName);

    try {
      const { error } = await supabase.from('commands').insert({
        device_id: selectedDevice.id,
        command: commandName,
        status: 'pending',
        args: {},
      });

      if (error) throw error;
    } catch (error) {
      console.error('Error sending command:', error);
    } finally {
      setSendingCommand(null);
    }
  }

  const isOnline = (device: Device) => {
    return new Date(device.last_seen) > new Date(Date.now() - 5 * 60 * 1000);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'executing':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-yellow-100 text-yellow-800';
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
          <h1 className="text-2xl font-bold text-gray-900">Devices</h1>
          <p className="text-gray-600">Manage and control your monitored devices</p>
        </div>
        <button
          onClick={fetchDevices}
          className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Device List */}
        <div className="bg-white rounded-xl shadow-sm border">
          <div className="p-4 border-b">
            <h2 className="font-semibold">All Devices ({devices.length})</h2>
          </div>
          <div className="divide-y max-h-[600px] overflow-auto">
            {devices.map((device) => (
              <button
                key={device.id}
                onClick={() => setSelectedDevice(device)}
                className={`w-full p-4 text-left hover:bg-gray-50 transition-colors ${
                  selectedDevice?.id === device.id ? 'bg-red-50 border-l-4 border-red-500' : ''
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${isOnline(device) ? 'bg-green-500' : 'bg-gray-300'}`} />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">
                      {device.device_name || device.hostname}
                    </p>
                    <p className="text-sm text-gray-500">{device.os}</p>
                  </div>
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  {formatDistanceToNow(new Date(device.last_seen), { addSuffix: true })}
                </p>
              </button>
            ))}
          </div>
        </div>

        {/* Device Details & Commands */}
        <div className="lg:col-span-2 space-y-6">
          {selectedDevice ? (
            <>
              {/* Device Info */}
              <div className="bg-white rounded-xl shadow-sm border p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">
                      {selectedDevice.device_name || selectedDevice.hostname}
                    </h2>
                    <p className="text-gray-500">{selectedDevice.os}</p>
                  </div>
                  <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                    isOnline(selectedDevice)
                      ? 'bg-green-100 text-green-800'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {isOnline(selectedDevice) ? 'Online' : 'Offline'}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 mt-6">
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500">Hostname</p>
                    <p className="font-medium">{selectedDevice.hostname}</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500">Last Seen</p>
                    <p className="font-medium">
                      {formatDistanceToNow(new Date(selectedDevice.last_seen), { addSuffix: true })}
                    </p>
                  </div>
                </div>
              </div>

              {/* Quick Commands */}
              <div className="bg-white rounded-xl shadow-sm border p-6">
                <h3 className="font-semibold mb-4">Quick Commands</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {COMMANDS.map((cmd) => {
                    const Icon = cmd.icon;
                    const isSending = sendingCommand === cmd.id;

                    return (
                      <button
                        key={cmd.id}
                        onClick={() => sendCommand(cmd.id)}
                        disabled={isSending || !isOnline(selectedDevice)}
                        className={`p-4 rounded-lg border text-left transition-all ${
                          isSending
                            ? 'bg-red-50 border-red-200'
                            : isOnline(selectedDevice)
                            ? 'hover:bg-gray-50 hover:border-gray-300'
                            : 'opacity-50 cursor-not-allowed'
                        }`}
                      >
                        <Icon className={`w-5 h-5 mb-2 ${isSending ? 'text-red-500 animate-pulse' : 'text-gray-600'}`} />
                        <p className="font-medium text-sm">{cmd.label}</p>
                        <p className="text-xs text-gray-500 mt-1">{cmd.description}</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Recent Commands */}
              <div className="bg-white rounded-xl shadow-sm border">
                <div className="p-4 border-b">
                  <h3 className="font-semibold">Recent Commands</h3>
                </div>
                <div className="divide-y max-h-80 overflow-auto">
                  {recentCommands.length === 0 ? (
                    <div className="p-6 text-center text-gray-500">
                      No commands sent yet
                    </div>
                  ) : (
                    recentCommands.map((cmd) => (
                      <div key={cmd.id} className="p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <Send className="w-4 h-4 text-gray-400" />
                            <div>
                              <p className="font-medium">{cmd.command}</p>
                              <p className="text-xs text-gray-500">
                                {formatDistanceToNow(new Date(cmd.created_at), { addSuffix: true })}
                              </p>
                            </div>
                          </div>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(cmd.status)}`}>
                            {cmd.status}
                          </span>
                        </div>
                        {cmd.result && Object.keys(cmd.result).length > 0 && (
                          <div className="mt-2 p-2 bg-gray-50 rounded text-xs font-mono overflow-auto">
                            {JSON.stringify(cmd.result, null, 2)}
                          </div>
                        )}
                        {cmd.result_url && (
                          <a
                            href={cmd.result_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-2 inline-block text-sm text-red-600 hover:underline"
                          >
                            View Result
                          </a>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
              <Monitor className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Select a device to view details and send commands</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
