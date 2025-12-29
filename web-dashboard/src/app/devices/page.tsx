'use client';

import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
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
  Send,
  RefreshCw,
  CheckSquare,
  Square,
  Play,
  X,
  Users,
  Zap,
  CheckCircle,
  XCircle,
  Loader2,
  Trash2,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Clock,
  Activity,
  ExternalLink,
  Signal,
  Globe,
  Image,
  BatteryCharging,
  Zap as ZapIcon,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { HackerLoader } from '@/components/HackerLoader';

const COMMANDS = [
  { id: 'photo', label: 'Photo', icon: Camera, description: 'Capture photo' },
  { id: 'screenshot', label: 'Screenshot', icon: Monitor, description: 'Take screenshot' },
  { id: 'location', label: 'Location', icon: MapPin, description: 'Get GPS location' },
  { id: 'battery', label: 'Battery', icon: Battery, description: 'Check battery' },
  { id: 'wifi', label: 'WiFi', icon: Wifi, description: 'Network info' },
  { id: 'lock', label: 'Lock', icon: Lock, description: 'Lock screen' },
  { id: 'alarm', label: 'Alarm', icon: Volume2, description: 'Play alarm' },
  { id: 'findme', label: 'Find Mac', icon: Smartphone, description: 'Find device' },
];

// Helper function to get WiFi signal strength indicator
function getSignalStrength(rssi: string | number): { level: number; color: string; label: string } {
  const rssiNum = typeof rssi === 'string' ? parseInt(rssi) : rssi;
  if (rssiNum >= -50) return { level: 4, color: 'text-green-400', label: 'Excellent' };
  if (rssiNum >= -60) return { level: 3, color: 'text-green-400', label: 'Good' };
  if (rssiNum >= -70) return { level: 2, color: 'text-yellow-400', label: 'Fair' };
  return { level: 1, color: 'text-red-400', label: 'Weak' };
}

// Component to render command results nicely
function CommandResultDisplay({ command, result, resultUrl }: { command: string; result: Record<string, unknown>; resultUrl?: string }): React.ReactNode {
  const [showImage, setShowImage] = useState(false);

  if (!result || Object.keys(result).length === 0) {
    if (resultUrl) {
      return (
        <div className="mt-3 flex items-center gap-3">
          <div className="w-12 h-12 bg-gray-100 dark:bg-[#1A1A1A] rounded-lg flex items-center justify-center border border-gray-200 dark:border-[#333]">
            <Image className="w-5 h-5 text-gray-400 dark:text-[#666]" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-900 dark:text-white">{command === 'screenshot' ? 'Screenshot' : 'Photo'} captured</p>
            <p className="text-xs text-gray-500 dark:text-[#666]">Click to view</p>
          </div>
          <a
            href={resultUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-2 bg-red-500/10 dark:bg-red-500/10 text-red-600 dark:text-red-400 hover:bg-red-500/20 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            View
          </a>
        </div>
      );
    }
    return null;
  }

  // WiFi result
  if (command === 'wifi' && result.wifi) {
    const wifi = result.wifi as Record<string, unknown>;
    const signal = wifi.rssi ? getSignalStrength(wifi.rssi as string) : null;
    return (
      <div className="mt-3 p-4 bg-gray-50 dark:bg-[#0D0D0D] rounded-xl border border-gray-200 dark:border-[#222] space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-500/20 rounded-xl flex items-center justify-center">
              <Wifi className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="font-semibold text-gray-900 dark:text-white">{wifi.ssid as string || 'Unknown'}</p>
              <p className="text-xs text-gray-500 dark:text-[#666]">Connected Network</p>
            </div>
          </div>
          {signal && (
            <div className="text-right">
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4].map((bar) => (
                  <div
                    key={bar}
                    className={`w-1.5 rounded-full ${bar <= signal.level ? signal.color.replace('text-', 'bg-') : 'bg-gray-200 dark:bg-[#333]'}`}
                    style={{ height: `${8 + bar * 4}px` }}
                  />
                ))}
              </div>
              <p className={`text-xs mt-1 ${signal.color}`}>{signal.label}</p>
            </div>
          )}
        </div>
        {wifi.rssi !== undefined && wifi.rssi !== null && (
          <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-[#888]">
            <span className="flex items-center gap-1.5">
              <Signal className="w-3.5 h-3.5" />
              {String(wifi.rssi)} dBm
            </span>
            {wifi.bssid !== undefined && wifi.bssid !== null && (
              <span className="font-mono text-xs text-gray-400 dark:text-[#555]">
                {String(wifi.bssid)}
              </span>
            )}
          </div>
        )}
      </div>
    );
  }

  // Battery result
  if (command === 'battery' && result.battery) {
    const battery = result.battery as Record<string, unknown>;
    const percentage = battery.percentage as number || 0;
    const isCharging = battery.charging as boolean;
    const isLow = percentage <= 20;
    return (
      <div className="mt-3 p-4 bg-gray-50 dark:bg-[#0D0D0D] rounded-xl border border-gray-200 dark:border-[#222]">
        <div className="flex items-center gap-4">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${isLow ? 'bg-red-100 dark:bg-red-500/20' : 'bg-green-100 dark:bg-green-500/20'}`}>
            {isCharging ? (
              <BatteryCharging className={`w-5 h-5 ${isLow ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`} />
            ) : (
              <Battery className={`w-5 h-5 ${isLow ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`} />
            )}
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              <span className="font-semibold text-gray-900 dark:text-white">{percentage}%</span>
              {isCharging && (
                <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                  <ZapIcon className="w-3 h-3" />
                  Charging
                </span>
              )}
            </div>
            <div className="h-2.5 bg-gray-200 dark:bg-[#222] rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${isLow ? 'bg-red-500' : 'bg-green-500'}`}
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Location result - Enhanced with address details
  if (command === 'location' && result.location) {
    const location = result.location as Record<string, unknown>;
    const lat = location.latitude as number;
    const lng = location.longitude as number;
    const googleMapsUrl = location.google_maps as string || (lat && lng ? `https://www.google.com/maps?q=${lat},${lng}` : null);

    // Extract address details if available
    const address = location.address as Record<string, unknown> | undefined;
    const building = address?.building || address?.name || location.building;
    const road = address?.road || address?.street || location.road || location.street;
    const area = address?.suburb || address?.neighbourhood || address?.area || location.area;
    const city = (location.city || address?.city) as string | undefined;
    const region = (location.region || address?.state || address?.region) as string | undefined;
    const country = (location.country || address?.country) as string | undefined;
    const postcode = address?.postcode || address?.pincode || location.postcode || location.pincode;

    // Determine primary location text
    let locationText = 'Location data available';
    let hasValidLocation = false;
    if (city) {
      locationText = region ? `${city}, ${region}` : String(city);
      hasValidLocation = true;
    } else if (lat && lng) {
      locationText = 'GPS Location';
      hasValidLocation = true;
    }

    return (
      <div className="mt-3 p-4 bg-gray-50 dark:bg-[#0D0D0D] rounded-xl border border-gray-200 dark:border-[#222] space-y-3">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 bg-purple-100 dark:bg-purple-500/20 rounded-xl flex items-center justify-center flex-shrink-0">
            <MapPin className="w-5 h-5 text-purple-600 dark:text-purple-400" />
          </div>
          <div className="flex-1 min-w-0">
            {/* Primary location info */}
            <p className={`font-semibold ${hasValidLocation ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-[#666]'}`}>
              {locationText}
            </p>

            {/* Address details */}
            {Boolean(building || road || area) && (
              <div className="mt-2 space-y-1">
                {Boolean(building) && (
                  <p className="text-sm text-gray-600 dark:text-[#AAA] flex items-center gap-2">
                    <span className="text-xs text-gray-400 dark:text-[#666] w-16">Building</span>
                    {String(building)}
                  </p>
                )}
                {Boolean(road) && (
                  <p className="text-sm text-gray-600 dark:text-[#AAA] flex items-center gap-2">
                    <span className="text-xs text-gray-400 dark:text-[#666] w-16">Street</span>
                    {String(road)}
                  </p>
                )}
                {Boolean(area) && (
                  <p className="text-sm text-gray-600 dark:text-[#AAA] flex items-center gap-2">
                    <span className="text-xs text-gray-400 dark:text-[#666] w-16">Area</span>
                    {String(area)}
                  </p>
                )}
                {Boolean(postcode) && (
                  <p className="text-sm text-gray-600 dark:text-[#AAA] flex items-center gap-2">
                    <span className="text-xs text-gray-400 dark:text-[#666] w-16">Pincode</span>
                    <span className="font-mono">{String(postcode)}</span>
                  </p>
                )}
              </div>
            )}

            {/* Coordinates */}
            {lat && lng && (
              <p className="text-xs text-gray-400 dark:text-[#555] font-mono mt-2">
                {lat.toFixed(6)}, {lng.toFixed(6)}
              </p>
            )}
          </div>
        </div>
        {googleMapsUrl && (
          <a
            href={googleMapsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 p-2.5 bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-500/20 rounded-lg transition-colors text-sm font-medium"
          >
            <Globe className="w-4 h-4" />
            View on Google Maps
            <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    );
  }

  // Screenshot/Photo result with URL - Compact view with View button
  if ((command === 'screenshot' || command === 'photo') && resultUrl) {
    return (
      <div className="mt-3">
        {!showImage ? (
          <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-[#0D0D0D] rounded-xl border border-gray-200 dark:border-[#222]">
            <div className="w-14 h-14 bg-gray-100 dark:bg-[#1A1A1A] rounded-lg flex items-center justify-center border border-gray-200 dark:border-[#333] overflow-hidden">
              <img
                src={resultUrl}
                alt={command === 'screenshot' ? 'Screenshot thumbnail' : 'Photo thumbnail'}
                className="w-full h-full object-cover"
              />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900 dark:text-white">{command === 'screenshot' ? 'Screenshot' : 'Photo'}</p>
              <p className="text-xs text-gray-500 dark:text-[#666]">Captured successfully</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowImage(true)}
                className="px-3 py-2 bg-gray-100 dark:bg-[#1A1A1A] text-gray-700 dark:text-[#AAA] hover:bg-gray-200 dark:hover:bg-[#222] rounded-lg text-sm font-medium flex items-center gap-2 transition-colors border border-gray-200 dark:border-[#333]"
              >
                <Image className="w-4 h-4" />
                Preview
              </button>
              <a
                href={resultUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-2 bg-red-500/10 text-red-600 dark:text-red-400 hover:bg-red-500/20 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
              >
                <ExternalLink className="w-4 h-4" />
                Full Size
              </a>
            </div>
          </div>
        ) : (
          <div className="relative">
            <button
              onClick={() => setShowImage(false)}
              className="absolute top-2 right-2 z-10 p-2 bg-black/50 hover:bg-black/70 text-white rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
            <a
              href={resultUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="block relative group"
            >
              <img
                src={resultUrl}
                alt={command === 'screenshot' ? 'Screenshot' : 'Photo'}
                className="w-full max-w-md rounded-xl border border-gray-200 dark:border-[#333] group-hover:border-red-500/50 transition-colors"
              />
              <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-xl flex items-center justify-center">
                <span className="text-white text-sm font-medium flex items-center gap-2">
                  <ExternalLink className="w-4 h-4" />
                  Open Full Size
                </span>
              </div>
            </a>
          </div>
        )}
      </div>
    );
  }

  // Success/Status result
  if (result.success !== undefined) {
    return (
      <div className={`mt-3 p-3 rounded-xl border ${result.success ? 'bg-green-50 dark:bg-green-500/10 border-green-200 dark:border-green-500/30' : 'bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30'}`}>
        <div className="flex items-center gap-2">
          {result.success ? (
            <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
          ) : (
            <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
          )}
          <span className={result.success ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}>
            {result.message as string || (result.success ? 'Command executed successfully' : 'Command failed')}
          </span>
        </div>
        {result.error !== undefined && result.error !== null && (
          <p className="text-xs text-red-600 dark:text-red-400 mt-2">{String(result.error)}</p>
        )}
      </div>
    );
  }

  // Status/Info result (generic)
  if (result.status || result.info) {
    const data = (result.status || result.info) as Record<string, unknown>;
    return (
      <div className="mt-3 p-4 bg-gray-50 dark:bg-[#0D0D0D] rounded-xl border border-gray-200 dark:border-[#222]">
        <div className="grid grid-cols-2 gap-2 text-sm">
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="flex justify-between">
              <span className="text-gray-500 dark:text-[#666] capitalize">{key.replace(/_/g, ' ')}</span>
              <span className="text-gray-900 dark:text-white font-medium">{String(value)}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Fallback: Show formatted JSON for unknown result types
  return (
    <div className="mt-3 p-3 bg-gray-50 dark:bg-[#0D0D0D] rounded-lg text-xs font-mono text-gray-600 dark:text-[#888] overflow-auto max-h-40 border border-gray-200 dark:border-[#222]">
      <pre>{JSON.stringify(result, null, 2)}</pre>
    </div>
  );
}

interface BulkCommandResult {
  deviceId: string;
  deviceName: string;
  status: 'pending' | 'sending' | 'sent' | 'error';
  error?: string;
}

export default function DevicesPage() {
  const searchParams = useSearchParams();
  const filterParam = searchParams.get('filter') as 'online' | 'offline' | null;

  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [recentCommands, setRecentCommands] = useState<Command[]>([]);
  const [loading, setLoading] = useState(true);
  const [sendingCommand, setSendingCommand] = useState<string | null>(null);

  // Bulk selection state
  const [bulkMode, setBulkMode] = useState(false);
  const [selectedDeviceIds, setSelectedDeviceIds] = useState<Set<string>>(new Set());
  const [showBulkPanel, setShowBulkPanel] = useState(false);
  const [bulkCommand, setBulkCommand] = useState<string | null>(null);
  const [bulkResults, setBulkResults] = useState<BulkCommandResult[]>([]);
  const [bulkExecuting, setBulkExecuting] = useState(false);

  // Delete device state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deviceToDelete, setDeviceToDelete] = useState<Device | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Device filter state (all, online, offline) - derived from URL param
  const [deviceFilter, setDeviceFilter] = useState<'all' | 'online' | 'offline'>(filterParam || 'all');

  // Show split view only when filter is active
  const showSplitView = filterParam !== null;

  // Update filter when URL param changes
  useEffect(() => {
    if (filterParam) {
      setDeviceFilter(filterParam);
    } else {
      setDeviceFilter('all');
    }
  }, [filterParam]);

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedDevice) {
      fetchRecentCommands(selectedDevice.id);

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
      // Deduplicate by hostname - keep only the most recent device per hostname
      const deviceMap = new Map<string, Device>();
      for (const device of data) {
        const key = device.hostname;
        if (!deviceMap.has(key) || new Date(device.last_seen) > new Date(deviceMap.get(key)!.last_seen)) {
          deviceMap.set(key, device);
        }
      }
      const uniqueDevices = Array.from(deviceMap.values());

      setDevices(uniqueDevices);
      if (uniqueDevices.length > 0 && !selectedDevice) {
        setSelectedDevice(uniqueDevices[0]);
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

  async function deleteDevice(device: Device) {
    setDeleting(true);
    try {
      await supabase.from('commands').delete().eq('device_id', device.id);
      await supabase.from('events').delete().eq('device_id', device.id);
      const { error } = await supabase.from('devices').delete().eq('id', device.id);
      if (error) throw error;

      setDevices(prev => prev.filter(d => d.id !== device.id));
      if (selectedDevice?.id === device.id) {
        setSelectedDevice(null);
      }
      setShowDeleteConfirm(false);
      setDeviceToDelete(null);
    } catch (error) {
      console.error('Error deleting device:', error);
    } finally {
      setDeleting(false);
    }
  }

  async function executeBulkCommand(commandName: string) {
    if (selectedDeviceIds.size === 0) return;

    setBulkCommand(commandName);
    setBulkExecuting(true);

    const initialResults: BulkCommandResult[] = Array.from(selectedDeviceIds).map(deviceId => {
      const device = devices.find(d => d.id === deviceId);
      return {
        deviceId,
        deviceName: device?.hostname || 'Unknown',
        status: 'pending' as const,
      };
    });
    setBulkResults(initialResults);

    for (const deviceId of selectedDeviceIds) {
      setBulkResults(prev => prev.map(r =>
        r.deviceId === deviceId ? { ...r, status: 'sending' as const } : r
      ));

      try {
        const { error } = await supabase.from('commands').insert({
          device_id: deviceId,
          command: commandName,
          status: 'pending',
          args: {},
        });

        if (error) throw error;

        setBulkResults(prev => prev.map(r =>
          r.deviceId === deviceId ? { ...r, status: 'sent' as const } : r
        ));
      } catch (error) {
        setBulkResults(prev => prev.map(r =>
          r.deviceId === deviceId ? {
            ...r,
            status: 'error' as const,
            error: error instanceof Error ? error.message : 'Unknown error'
          } : r
        ));
      }
    }

    setBulkExecuting(false);
  }

  function toggleDeviceSelection(deviceId: string) {
    const newSelection = new Set(selectedDeviceIds);
    if (newSelection.has(deviceId)) {
      newSelection.delete(deviceId);
    } else {
      newSelection.add(deviceId);
    }
    setSelectedDeviceIds(newSelection);
  }

  function selectAllDevices() {
    if (selectedDeviceIds.size === devices.length) {
      setSelectedDeviceIds(new Set());
    } else {
      setSelectedDeviceIds(new Set(devices.map(d => d.id)));
    }
  }

  function selectOnlineDevices() {
    const onlineIds = devices.filter(d => isOnline(d)).map(d => d.id);
    setSelectedDeviceIds(new Set(onlineIds));
  }

  // Device is online if last_seen within 1 minute
  const isOnline = (device: Device) => {
    return new Date(device.last_seen) > new Date(Date.now() - 60 * 1000);
  };

  const onlineDevices = devices.filter(isOnline);
  const offlineDevices = devices.filter(d => !isOnline(d));

  // Filtered devices based on current filter
  const filteredDevices = deviceFilter === 'all'
    ? devices
    : deviceFilter === 'online'
      ? onlineDevices
      : offlineDevices;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500/20 text-green-400 border-green-500/50';
      case 'executing':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
      case 'failed':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      default:
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
    }
  };

  if (loading) {
    return <HackerLoader message="Scanning network for devices..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Monitor className="w-7 h-7 text-red-500" />
            Devices
          </h1>
          <p className="text-gray-500 dark:text-[#666] mt-1">
            {devices.length} devices • <span className="text-green-600 dark:text-green-400">{onlineDevices.length} online</span> • <span className="text-gray-500 dark:text-[#666]">{offlineDevices.length} offline</span>
            {bulkMode && selectedDeviceIds.size > 0 && (
              <span className="ml-2 text-red-600 dark:text-red-500 font-medium">
                • {selectedDeviceIds.size} selected
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setBulkMode(!bulkMode);
              if (bulkMode) {
                setSelectedDeviceIds(new Set());
                setShowBulkPanel(false);
              }
            }}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all duration-200 ${
              bulkMode
                ? 'bg-red-600 text-white shadow-lg shadow-red-500/20'
                : 'bg-gray-100 dark:bg-[#1A1A1A] text-gray-700 dark:text-[#AAA] border border-gray-200 dark:border-[#333] hover:border-red-500/50 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <Users className="w-4 h-4" />
            {bulkMode ? 'Exit Bulk' : 'Bulk Commands'}
          </button>
          <button
            onClick={fetchDevices}
            className="flex items-center gap-2 px-4 py-2.5 bg-gray-100 dark:bg-[#1A1A1A] text-gray-700 dark:text-[#AAA] border border-gray-200 dark:border-[#333] hover:border-red-500/50 hover:text-gray-900 dark:hover:text-white rounded-xl font-medium transition-all duration-200"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Bulk Selection Toolbar */}
      {bulkMode && (
        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl p-4 flex items-center justify-between border border-red-200 dark:border-red-500/30 shadow-sm">
          <div className="flex items-center gap-4">
            <button
              onClick={selectAllDevices}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-[#222] border border-gray-200 dark:border-[#333] rounded-lg hover:border-red-500/50 transition-colors"
            >
              {selectedDeviceIds.size === devices.length ? (
                <CheckSquare className="w-4 h-4 text-red-500" />
              ) : (
                <Square className="w-4 h-4 text-gray-400 dark:text-[#666]" />
              )}
              <span className="text-gray-700 dark:text-[#AAA]">Select All</span>
            </button>
            <button
              onClick={selectOnlineDevices}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-[#222] border border-gray-200 dark:border-[#333] rounded-lg hover:border-green-500/50 transition-colors"
            >
              <div className="w-3 h-3 bg-green-500 rounded-full pulse-online" />
              <span className="text-gray-700 dark:text-[#AAA]">Online ({onlineDevices.length})</span>
            </button>
            <button
              onClick={() => setSelectedDeviceIds(new Set())}
              className="px-4 py-2 text-gray-500 dark:text-[#666] hover:text-gray-900 dark:hover:text-white transition-colors"
            >
              Clear
            </button>
          </div>

          {selectedDeviceIds.size > 0 && (
            <button
              onClick={() => setShowBulkPanel(true)}
              className="glow-btn flex items-center gap-2"
            >
              <Zap className="w-4 h-4" />
              Send to {selectedDeviceIds.size} Devices
            </button>
          )}
        </div>
      )}

      {/* Full-width card grid when no filter (main Devices view) */}
      {!showSplitView ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {devices.length === 0 ? (
            <div className="col-span-full p-12 text-center bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333]">
              <Monitor className="w-16 h-16 text-gray-300 dark:text-[#333] mx-auto mb-4" />
              <p className="text-gray-500 dark:text-[#666] text-lg">No devices found</p>
              <p className="text-gray-400 dark:text-[#555] text-sm mt-1">Install the agent to start monitoring</p>
            </div>
          ) : (
            devices.map((device) => {
              const online = isOnline(device);
              return (
                <div
                  key={device.id}
                  onClick={() => setSelectedDevice(device)}
                  className={`bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333] p-5 cursor-pointer transition-all duration-200 hover:border-red-500/50 hover:shadow-lg ${
                    selectedDevice?.id === device.id ? 'ring-2 ring-red-500 border-transparent' : ''
                  } ${!online ? 'opacity-70 hover:opacity-100' : ''}`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                        online ? 'bg-green-100 dark:bg-green-500/20' : 'bg-gray-100 dark:bg-[#222]'
                      }`}>
                        <Monitor className={`w-6 h-6 ${online ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-[#555]'}`} />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900 dark:text-white truncate max-w-[180px]">
                          {device.hostname}
                        </h3>
                        <p className="text-xs text-gray-500 dark:text-[#666]">{device.os_version}</p>
                      </div>
                    </div>
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                      online
                        ? 'bg-green-100 dark:bg-green-500/20 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-500/30'
                        : 'bg-gray-100 dark:bg-[#222] text-gray-500 dark:text-[#666] border border-gray-200 dark:border-[#333]'
                    }`}>
                      {online ? 'Online' : 'Offline'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500 dark:text-[#666]">Last seen</span>
                    <span className={`font-medium ${online ? 'text-green-600 dark:text-green-400' : 'text-gray-600 dark:text-[#888]'}`}>
                      {online ? 'Just now' : formatDistanceToNow(new Date(device.last_seen), { addSuffix: true })}
                    </span>
                  </div>
                  {!online && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeviceToDelete(device);
                        setShowDeleteConfirm(true);
                      }}
                      className="mt-3 w-full px-3 py-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 hover:bg-red-100 dark:hover:bg-red-500/20 rounded-lg transition-colors flex items-center justify-center gap-2"
                    >
                      <Trash2 className="w-4 h-4" />
                      Remove Device
                    </button>
                  )}
                </div>
              );
            })
          )}
        </div>
      ) : (
        /* Split view when filter is active (Online/Offline from sidebar) */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Device List */}
          <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333] overflow-hidden shadow-sm">
            {/* Filter Header */}
            <div className="p-4 border-b border-gray-200 dark:border-[#222] bg-gray-50 dark:bg-[#0D0D0D]">
              <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                {filterParam === 'online' ? (
                  <>
                    <div className="w-2.5 h-2.5 bg-green-500 rounded-full pulse-online" />
                    Online Devices ({onlineDevices.length})
                  </>
                ) : (
                  <>
                    <div className="w-2.5 h-2.5 bg-gray-400 rounded-full" />
                    Offline Devices ({offlineDevices.length})
                  </>
                )}
              </h3>
            </div>

            {/* Device List */}
            <div className="divide-y divide-gray-100 dark:divide-[#1A1A1A] max-h-[600px] overflow-auto">
              {filteredDevices.length === 0 ? (
                <div className="p-12 text-center">
                  <Monitor className="w-12 h-12 text-gray-300 dark:text-[#333] mx-auto mb-3" />
                  <p className="text-gray-500 dark:text-[#666]">
                    {deviceFilter === 'online' ? 'No devices online' : 'No offline devices'}
                  </p>
                </div>
              ) : (
                filteredDevices.map((device) => {
                  const online = isOnline(device);
                  return (
                    <div
                      key={device.id}
                      className={`flex items-center transition-all duration-200 ${
                        selectedDevice?.id === device.id
                          ? 'bg-red-50 dark:bg-red-500/10 border-l-2 border-red-500'
                          : 'hover:bg-gray-50 dark:hover:bg-[#111]'
                      }`}
                    >
                      <button
                        onClick={() => setSelectedDevice(device)}
                        className="flex-1 p-4 text-left"
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                            online ? 'bg-green-100 dark:bg-green-500/20' : 'bg-gray-100 dark:bg-[#222]'
                          }`}>
                            <Monitor className={`w-5 h-5 ${online ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-[#555]'}`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium truncate text-gray-900 dark:text-white">
                              {device.hostname}
                            </p>
                            <p className="text-xs text-gray-400 dark:text-[#555]">{device.os_version}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            {online ? (
                              <span className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
                                <Activity className="w-3 h-3" />
                                Live
                              </span>
                            ) : (
                              <span className="text-xs text-gray-400 dark:text-[#555]">
                                {formatDistanceToNow(new Date(device.last_seen), { addSuffix: true })}
                              </span>
                            )}
                          </div>
                        </div>
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>

        {/* Device Details & Commands */}
        <div className="lg:col-span-2 space-y-6">
          {selectedDevice && !bulkMode ? (
            <>
              {/* Device Info Card */}
              <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333] p-6 shadow-sm">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${
                      isOnline(selectedDevice)
                        ? 'bg-green-100 dark:bg-green-500/20 shadow-lg shadow-green-500/20'
                        : 'bg-gray-100 dark:bg-[#1A1A1A]'
                    }`}>
                      <Monitor className={`w-7 h-7 ${isOnline(selectedDevice) ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-[#444]'}`} />
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-gray-900 dark:text-white">{selectedDevice.hostname}</h2>
                      <p className="text-gray-500 dark:text-[#666]">{selectedDevice.os_version}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1.5 rounded-full text-sm font-medium border ${
                      isOnline(selectedDevice)
                        ? 'status-online'
                        : 'status-offline'
                    }`}>
                      {isOnline(selectedDevice) ? 'Online' : 'Offline'}
                    </span>
                    <button
                      onClick={() => {
                        setDeviceToDelete(selectedDevice);
                        setShowDeleteConfirm(true);
                      }}
                      className="p-2 text-gray-400 dark:text-[#444] hover:text-red-500 hover:bg-red-500/10 rounded-xl transition-colors"
                      title="Remove device"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 mt-6">
                  <div className="p-4 bg-gray-50 dark:bg-[#111] rounded-xl border border-gray-200 dark:border-[#222]">
                    <p className="text-xs text-gray-500 dark:text-[#666] uppercase tracking-wider mb-1">Hostname</p>
                    <p className="font-medium text-gray-900 dark:text-white">{selectedDevice.hostname}</p>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-[#111] rounded-xl border border-gray-200 dark:border-[#222]">
                    <p className="text-xs text-gray-500 dark:text-[#666] uppercase tracking-wider mb-1">Last Seen</p>
                    <p className="font-medium text-gray-900 dark:text-white">
                      {formatDistanceToNow(new Date(selectedDevice.last_seen), { addSuffix: true })}
                    </p>
                  </div>
                </div>
              </div>

              {/* Quick Commands */}
              <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333] p-6 shadow-sm">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <Zap className="w-5 h-5 text-red-500" />
                  Quick Commands
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {COMMANDS.map((cmd) => {
                    const Icon = cmd.icon;
                    const isSending = sendingCommand === cmd.id;
                    const disabled = isSending || !isOnline(selectedDevice);

                    return (
                      <button
                        key={cmd.id}
                        onClick={() => sendCommand(cmd.id)}
                        disabled={disabled}
                        className={`p-4 rounded-xl border text-left transition-all duration-200 group ${
                          isSending
                            ? 'bg-red-50 dark:bg-red-500/10 border-red-300 dark:border-red-500/50'
                            : disabled
                            ? 'bg-gray-50 dark:bg-[#0D0D0D] border-gray-200 dark:border-[#1A1A1A] opacity-40 cursor-not-allowed'
                            : 'bg-gray-50 dark:bg-[#111] border-gray-200 dark:border-[#222] hover:border-red-500/50 hover:bg-gray-100 dark:hover:bg-[#1A1A1A]'
                        }`}
                      >
                        <Icon className={`w-6 h-6 mb-2 transition-colors ${
                          isSending
                            ? 'text-red-500 animate-pulse'
                            : disabled
                            ? 'text-gray-300 dark:text-[#333]'
                            : 'text-gray-500 dark:text-[#666] group-hover:text-red-500'
                        }`} />
                        <p className="font-medium text-sm text-gray-900 dark:text-white">{cmd.label}</p>
                        <p className="text-xs text-gray-500 dark:text-[#666] mt-1">{cmd.description}</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Recent Commands */}
              <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333] overflow-hidden shadow-sm">
                <div className="p-4 border-b border-gray-200 dark:border-[#222]">
                  <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                    <Send className="w-5 h-5 text-red-500" />
                    Recent Commands
                  </h3>
                </div>
                <div className="divide-y divide-gray-100 dark:divide-[#1A1A1A] max-h-80 overflow-auto">
                  {recentCommands.length === 0 ? (
                    <div className="p-8 text-center">
                      <Send className="w-10 h-10 text-gray-200 dark:text-[#222] mx-auto mb-3" />
                      <p className="text-gray-500 dark:text-[#666]">No commands sent yet</p>
                    </div>
                  ) : (
                    recentCommands.map((cmd) => (
                      <div key={cmd.id} className="p-4 hover:bg-gray-50 dark:hover:bg-[#0D0D0D] transition-colors">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-gray-100 dark:bg-[#1A1A1A] rounded-lg flex items-center justify-center">
                              <Send className="w-4 h-4 text-gray-500 dark:text-[#666]" />
                            </div>
                            <div>
                              <p className="font-medium text-gray-900 dark:text-white capitalize">{cmd.command}</p>
                              <p className="text-xs text-gray-500 dark:text-[#666]">
                                {formatDistanceToNow(new Date(cmd.created_at), { addSuffix: true })}
                              </p>
                            </div>
                          </div>
                          <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${getStatusColor(cmd.status)}`}>
                            {cmd.status}
                          </span>
                        </div>
                        <CommandResultDisplay
                          command={cmd.command}
                          result={cmd.result as Record<string, unknown>}
                          resultUrl={cmd.result_url}
                        />
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          ) : bulkMode ? (
            <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333] p-12 text-center shadow-sm">
              <div className="w-16 h-16 bg-red-50 dark:bg-red-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Users className="w-8 h-8 text-red-500" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Bulk Command Mode</h3>
              <p className="text-gray-500 dark:text-[#666] mb-6 max-w-md mx-auto">
                Select devices from the list, then click &quot;Send Command&quot; to execute commands on multiple devices at once.
              </p>
              {selectedDeviceIds.size > 0 && (
                <p className="text-red-600 dark:text-red-500 font-medium">
                  {selectedDeviceIds.size} device{selectedDeviceIds.size !== 1 ? 's' : ''} selected
                </p>
              )}
            </div>
          ) : (
            <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333] p-12 text-center shadow-sm">
              <div className="w-16 h-16 bg-gray-100 dark:bg-[#1A1A1A] rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Monitor className="w-8 h-8 text-gray-300 dark:text-[#333]" />
              </div>
              <p className="text-gray-500 dark:text-[#666]">Select a device to view details and send commands</p>
            </div>
          )}
        </div>
        </div>
      )}

      {/* Bulk Command Modal */}
      {showBulkPanel && (
        <div className="fixed inset-0 bg-black/50 dark:bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333] w-full max-w-2xl m-4 max-h-[90vh] overflow-auto shadow-xl">
            <div className="p-6 border-b border-gray-200 dark:border-[#222] flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">Send Bulk Command</h2>
                <p className="text-gray-500 dark:text-[#666]">
                  Sending to {selectedDeviceIds.size} device{selectedDeviceIds.size !== 1 ? 's' : ''}
                </p>
              </div>
              <button
                onClick={() => {
                  setShowBulkPanel(false);
                  setBulkCommand(null);
                  setBulkResults([]);
                }}
                className="p-2 text-gray-500 dark:text-[#666] hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-[#222] rounded-xl transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {!bulkCommand ? (
              <div className="p-6">
                <p className="text-sm text-gray-500 dark:text-[#666] mb-4">Select a command to execute:</p>
                <div className="grid grid-cols-2 gap-3">
                  {COMMANDS.map((cmd) => {
                    const Icon = cmd.icon;
                    return (
                      <button
                        key={cmd.id}
                        onClick={() => executeBulkCommand(cmd.id)}
                        className="p-4 rounded-xl border border-gray-200 dark:border-[#222] bg-gray-50 dark:bg-[#111] text-left hover:border-red-500/50 hover:bg-gray-100 dark:hover:bg-[#1A1A1A] transition-all duration-200 group"
                      >
                        <Icon className="w-6 h-6 mb-2 text-gray-500 dark:text-[#666] group-hover:text-red-500 transition-colors" />
                        <p className="font-medium text-sm text-gray-900 dark:text-white">{cmd.label}</p>
                        <p className="text-xs text-gray-500 dark:text-[#666] mt-1">{cmd.description}</p>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-3 bg-red-50 dark:bg-red-500/20 rounded-xl">
                    <Play className="w-5 h-5 text-red-500" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">
                      Executing: {COMMANDS.find(c => c.id === bulkCommand)?.label}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-[#666]">
                      {bulkExecuting ? 'Sending commands...' : 'Complete'}
                    </p>
                  </div>
                </div>

                <div className="space-y-2 max-h-64 overflow-auto">
                  {bulkResults.map((result) => (
                    <div
                      key={result.deviceId}
                      className="flex items-center justify-between p-3 bg-gray-50 dark:bg-[#111] rounded-xl border border-gray-200 dark:border-[#222]"
                    >
                      <span className="font-medium text-gray-900 dark:text-white">{result.deviceName}</span>
                      <div className="flex items-center gap-2">
                        {result.status === 'pending' && (
                          <span className="text-gray-500 dark:text-[#666] text-sm">Waiting...</span>
                        )}
                        {result.status === 'sending' && (
                          <Loader2 className="w-4 h-4 text-blue-500 dark:text-blue-400 animate-spin" />
                        )}
                        {result.status === 'sent' && (
                          <CheckCircle className="w-4 h-4 text-green-500 dark:text-green-400" />
                        )}
                        {result.status === 'error' && (
                          <XCircle className="w-4 h-4 text-red-500" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {!bulkExecuting && (
                  <div className="mt-6 flex justify-end gap-3">
                    <button
                      onClick={() => {
                        setBulkCommand(null);
                        setBulkResults([]);
                      }}
                      className="px-4 py-2.5 text-gray-600 dark:text-[#AAA] hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-[#222] rounded-xl transition-colors"
                    >
                      Send Another
                    </button>
                    <button
                      onClick={() => {
                        setShowBulkPanel(false);
                        setBulkCommand(null);
                        setBulkResults([]);
                        setBulkMode(false);
                        setSelectedDeviceIds(new Set());
                      }}
                      className="glow-btn"
                    >
                      Done
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && deviceToDelete && (
        <div className="fixed inset-0 bg-black/50 dark:bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333] w-full max-w-md m-4 shadow-xl">
            <div className="p-6">
              <div className="flex items-center gap-4 mb-4">
                <div className="p-3 bg-red-50 dark:bg-red-500/20 rounded-xl">
                  <AlertTriangle className="w-6 h-6 text-red-500" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900 dark:text-white">Remove Device</h2>
                  <p className="text-gray-500 dark:text-[#666]">This action cannot be undone</p>
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-[#111] rounded-xl p-4 mb-6 border border-gray-200 dark:border-[#222]">
                <p className="font-medium text-gray-900 dark:text-white">{deviceToDelete.hostname}</p>
                <p className="text-sm text-gray-500 dark:text-[#666]">{deviceToDelete.os_version}</p>
                <p className="text-xs text-gray-400 dark:text-[#555] mt-2">
                  Last seen: {formatDistanceToNow(new Date(deviceToDelete.last_seen), { addSuffix: true })}
                </p>
              </div>

              <p className="text-sm text-gray-600 dark:text-[#888] mb-6">
                This will permanently remove the device and all its associated events and commands.
              </p>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowDeleteConfirm(false);
                    setDeviceToDelete(null);
                  }}
                  className="flex-1 px-4 py-3 border border-gray-200 dark:border-[#333] rounded-xl hover:bg-gray-50 dark:hover:bg-[#111] text-gray-600 dark:text-[#AAA] hover:text-gray-900 dark:hover:text-white transition-colors"
                  disabled={deleting}
                >
                  Cancel
                </button>
                <button
                  onClick={() => deleteDevice(deviceToDelete)}
                  disabled={deleting}
                  className="flex-1 glow-btn flex items-center justify-center gap-2"
                >
                  {deleting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Removing...
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4" />
                      Remove
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
