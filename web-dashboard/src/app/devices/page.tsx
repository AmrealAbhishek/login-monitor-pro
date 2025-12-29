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
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

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

interface BulkCommandResult {
  deviceId: string;
  deviceName: string;
  status: 'pending' | 'sending' | 'sent' | 'error';
  error?: string;
}

export default function DevicesPage() {
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

  // Offline section collapsed state
  const [offlineCollapsed, setOfflineCollapsed] = useState(true);

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
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-10 h-10 text-red-500 animate-spin" />
          <p className="text-[#666]">Loading devices...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Monitor className="w-7 h-7 text-red-500" />
            Devices
          </h1>
          <p className="text-[#666] mt-1">
            {devices.length} devices • <span className="text-green-400">{onlineDevices.length} online</span> • <span className="text-[#666]">{offlineDevices.length} offline</span>
            {bulkMode && selectedDeviceIds.size > 0 && (
              <span className="ml-2 text-red-500 font-medium">
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
                : 'bg-[#1A1A1A] text-[#AAA] border border-[#333] hover:border-red-500/50 hover:text-white'
            }`}
          >
            <Users className="w-4 h-4" />
            {bulkMode ? 'Exit Bulk' : 'Bulk Commands'}
          </button>
          <button
            onClick={fetchDevices}
            className="flex items-center gap-2 px-4 py-2.5 bg-[#1A1A1A] text-[#AAA] border border-[#333] hover:border-red-500/50 hover:text-white rounded-xl font-medium transition-all duration-200"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Bulk Selection Toolbar */}
      {bulkMode && (
        <div className="neon-card p-4 flex items-center justify-between border-red-500/30">
          <div className="flex items-center gap-4">
            <button
              onClick={selectAllDevices}
              className="flex items-center gap-2 px-4 py-2 bg-[#222] border border-[#333] rounded-lg hover:border-red-500/50 transition-colors"
            >
              {selectedDeviceIds.size === devices.length ? (
                <CheckSquare className="w-4 h-4 text-red-500" />
              ) : (
                <Square className="w-4 h-4 text-[#666]" />
              )}
              <span className="text-[#AAA]">Select All</span>
            </button>
            <button
              onClick={selectOnlineDevices}
              className="flex items-center gap-2 px-4 py-2 bg-[#222] border border-[#333] rounded-lg hover:border-green-500/50 transition-colors"
            >
              <div className="w-3 h-3 bg-green-500 rounded-full pulse-online" />
              <span className="text-[#AAA]">Online ({onlineDevices.length})</span>
            </button>
            <button
              onClick={() => setSelectedDeviceIds(new Set())}
              className="px-4 py-2 text-[#666] hover:text-white transition-colors"
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Device List */}
        <div className="neon-card overflow-hidden">
          {/* Online Devices Section */}
          <div className="p-4 border-b border-[#222] bg-gradient-to-r from-green-500/10 to-transparent">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-green-500 rounded-full pulse-online" />
              <h2 className="font-semibold text-green-400">Online ({onlineDevices.length})</h2>
            </div>
          </div>
          <div className="divide-y divide-[#222] max-h-[300px] overflow-auto">
            {onlineDevices.length === 0 ? (
              <div className="p-8 text-center">
                <Monitor className="w-10 h-10 text-[#333] mx-auto mb-3" />
                <p className="text-[#666]">No devices online</p>
              </div>
            ) : (
              onlineDevices.map((device) => (
                <div
                  key={device.id}
                  className={`flex items-center transition-all duration-200 ${
                    !bulkMode && selectedDevice?.id === device.id
                      ? 'bg-red-500/10 border-l-2 border-red-500'
                      : 'hover:bg-[#111]'
                  }`}
                >
                  {bulkMode && (
                    <button
                      onClick={() => toggleDeviceSelection(device.id)}
                      className="p-4 hover:bg-[#111]"
                    >
                      {selectedDeviceIds.has(device.id) ? (
                        <CheckSquare className="w-5 h-5 text-red-500" />
                      ) : (
                        <Square className="w-5 h-5 text-[#444]" />
                      )}
                    </button>
                  )}
                  <button
                    onClick={() => !bulkMode && setSelectedDevice(device)}
                    className="flex-1 p-4 text-left"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-green-500/20 rounded-xl flex items-center justify-center">
                        <Monitor className="w-5 h-5 text-green-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-white truncate">{device.hostname}</p>
                        <p className="text-xs text-[#666]">{device.os_version}</p>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-green-400">
                        <Activity className="w-3 h-3" />
                        <span>Live</span>
                      </div>
                    </div>
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Offline Devices Section */}
          {offlineDevices.length > 0 && (
            <>
              <button
                onClick={() => setOfflineCollapsed(!offlineCollapsed)}
                className="w-full p-4 border-t border-[#222] bg-[#0D0D0D] hover:bg-[#111] transition-colors flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 bg-[#444] rounded-full" />
                  <h2 className="font-semibold text-[#666]">Offline ({offlineDevices.length})</h2>
                </div>
                {offlineCollapsed ? (
                  <ChevronRight className="w-5 h-5 text-[#444]" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-[#444]" />
                )}
              </button>
              {!offlineCollapsed && (
                <div className="divide-y divide-[#1A1A1A] max-h-[200px] overflow-auto bg-[#0A0A0A]">
                  {offlineDevices.map((device) => (
                    <div
                      key={device.id}
                      className={`flex items-center opacity-50 hover:opacity-100 transition-all duration-200 ${
                        !bulkMode && selectedDevice?.id === device.id
                          ? 'bg-red-500/10 border-l-2 border-red-500 opacity-100'
                          : ''
                      }`}
                    >
                      {bulkMode && (
                        <button
                          onClick={() => toggleDeviceSelection(device.id)}
                          className="p-4 hover:bg-[#111]"
                        >
                          {selectedDeviceIds.has(device.id) ? (
                            <CheckSquare className="w-5 h-5 text-red-500" />
                          ) : (
                            <Square className="w-5 h-5 text-[#333]" />
                          )}
                        </button>
                      )}
                      <button
                        onClick={() => !bulkMode && setSelectedDevice(device)}
                        className="flex-1 p-4 text-left"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-[#1A1A1A] rounded-xl flex items-center justify-center">
                            <Monitor className="w-5 h-5 text-[#444]" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-[#888] truncate">{device.hostname}</p>
                            <p className="text-xs text-[#555]">{device.os_version}</p>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeviceToDelete(device);
                              setShowDeleteConfirm(true);
                            }}
                            className="p-2 text-[#444] hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                            title="Remove device"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                        <p className="text-xs text-[#444] mt-2 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDistanceToNow(new Date(device.last_seen), { addSuffix: true })}
                        </p>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Device Details & Commands */}
        <div className="lg:col-span-2 space-y-6">
          {selectedDevice && !bulkMode ? (
            <>
              {/* Device Info Card */}
              <div className="neon-card p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${
                      isOnline(selectedDevice)
                        ? 'bg-green-500/20 shadow-lg shadow-green-500/20'
                        : 'bg-[#1A1A1A]'
                    }`}>
                      <Monitor className={`w-7 h-7 ${isOnline(selectedDevice) ? 'text-green-400' : 'text-[#444]'}`} />
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-white">{selectedDevice.hostname}</h2>
                      <p className="text-[#666]">{selectedDevice.os_version}</p>
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
                      className="p-2 text-[#444] hover:text-red-500 hover:bg-red-500/10 rounded-xl transition-colors"
                      title="Remove device"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 mt-6">
                  <div className="p-4 bg-[#111] rounded-xl border border-[#222]">
                    <p className="text-xs text-[#666] uppercase tracking-wider mb-1">Hostname</p>
                    <p className="font-medium text-white">{selectedDevice.hostname}</p>
                  </div>
                  <div className="p-4 bg-[#111] rounded-xl border border-[#222]">
                    <p className="text-xs text-[#666] uppercase tracking-wider mb-1">Last Seen</p>
                    <p className="font-medium text-white">
                      {formatDistanceToNow(new Date(selectedDevice.last_seen), { addSuffix: true })}
                    </p>
                  </div>
                </div>
              </div>

              {/* Quick Commands */}
              <div className="neon-card p-6">
                <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
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
                            ? 'bg-red-500/10 border-red-500/50'
                            : disabled
                            ? 'bg-[#0D0D0D] border-[#1A1A1A] opacity-40 cursor-not-allowed'
                            : 'bg-[#111] border-[#222] hover:border-red-500/50 hover:bg-[#1A1A1A]'
                        }`}
                      >
                        <Icon className={`w-6 h-6 mb-2 transition-colors ${
                          isSending
                            ? 'text-red-500 animate-pulse'
                            : disabled
                            ? 'text-[#333]'
                            : 'text-[#666] group-hover:text-red-500'
                        }`} />
                        <p className="font-medium text-sm text-white">{cmd.label}</p>
                        <p className="text-xs text-[#666] mt-1">{cmd.description}</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Recent Commands */}
              <div className="neon-card overflow-hidden">
                <div className="p-4 border-b border-[#222]">
                  <h3 className="font-semibold text-white flex items-center gap-2">
                    <Send className="w-5 h-5 text-red-500" />
                    Recent Commands
                  </h3>
                </div>
                <div className="divide-y divide-[#1A1A1A] max-h-80 overflow-auto">
                  {recentCommands.length === 0 ? (
                    <div className="p-8 text-center">
                      <Send className="w-10 h-10 text-[#222] mx-auto mb-3" />
                      <p className="text-[#666]">No commands sent yet</p>
                    </div>
                  ) : (
                    recentCommands.map((cmd) => (
                      <div key={cmd.id} className="p-4 hover:bg-[#0D0D0D] transition-colors">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-[#1A1A1A] rounded-lg flex items-center justify-center">
                              <Send className="w-4 h-4 text-[#666]" />
                            </div>
                            <div>
                              <p className="font-medium text-white capitalize">{cmd.command}</p>
                              <p className="text-xs text-[#666]">
                                {formatDistanceToNow(new Date(cmd.created_at), { addSuffix: true })}
                              </p>
                            </div>
                          </div>
                          <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${getStatusColor(cmd.status)}`}>
                            {cmd.status}
                          </span>
                        </div>
                        {cmd.result && Object.keys(cmd.result).length > 0 && (
                          <div className="mt-3 p-3 bg-[#0D0D0D] rounded-lg text-xs font-mono text-[#888] overflow-auto">
                            {JSON.stringify(cmd.result, null, 2)}
                          </div>
                        )}
                        {cmd.result_url && (
                          <a
                            href={cmd.result_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-2 inline-block text-sm text-red-500 hover:text-red-400 transition-colors"
                          >
                            View Result →
                          </a>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          ) : bulkMode ? (
            <div className="neon-card p-12 text-center">
              <div className="w-16 h-16 bg-red-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Users className="w-8 h-8 text-red-500" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Bulk Command Mode</h3>
              <p className="text-[#666] mb-6 max-w-md mx-auto">
                Select devices from the list, then click &quot;Send Command&quot; to execute commands on multiple devices at once.
              </p>
              {selectedDeviceIds.size > 0 && (
                <p className="text-red-500 font-medium">
                  {selectedDeviceIds.size} device{selectedDeviceIds.size !== 1 ? 's' : ''} selected
                </p>
              )}
            </div>
          ) : (
            <div className="neon-card p-12 text-center">
              <div className="w-16 h-16 bg-[#1A1A1A] rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Monitor className="w-8 h-8 text-[#333]" />
              </div>
              <p className="text-[#666]">Select a device to view details and send commands</p>
            </div>
          )}
        </div>
      </div>

      {/* Bulk Command Modal */}
      {showBulkPanel && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="neon-card w-full max-w-2xl m-4 max-h-[90vh] overflow-auto">
            <div className="p-6 border-b border-[#222] flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-white">Send Bulk Command</h2>
                <p className="text-[#666]">
                  Sending to {selectedDeviceIds.size} device{selectedDeviceIds.size !== 1 ? 's' : ''}
                </p>
              </div>
              <button
                onClick={() => {
                  setShowBulkPanel(false);
                  setBulkCommand(null);
                  setBulkResults([]);
                }}
                className="p-2 text-[#666] hover:text-white hover:bg-[#222] rounded-xl transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {!bulkCommand ? (
              <div className="p-6">
                <p className="text-sm text-[#666] mb-4">Select a command to execute:</p>
                <div className="grid grid-cols-2 gap-3">
                  {COMMANDS.map((cmd) => {
                    const Icon = cmd.icon;
                    return (
                      <button
                        key={cmd.id}
                        onClick={() => executeBulkCommand(cmd.id)}
                        className="p-4 rounded-xl border border-[#222] bg-[#111] text-left hover:border-red-500/50 hover:bg-[#1A1A1A] transition-all duration-200 group"
                      >
                        <Icon className="w-6 h-6 mb-2 text-[#666] group-hover:text-red-500 transition-colors" />
                        <p className="font-medium text-sm text-white">{cmd.label}</p>
                        <p className="text-xs text-[#666] mt-1">{cmd.description}</p>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-3 bg-red-500/20 rounded-xl">
                    <Play className="w-5 h-5 text-red-500" />
                  </div>
                  <div>
                    <p className="font-medium text-white">
                      Executing: {COMMANDS.find(c => c.id === bulkCommand)?.label}
                    </p>
                    <p className="text-sm text-[#666]">
                      {bulkExecuting ? 'Sending commands...' : 'Complete'}
                    </p>
                  </div>
                </div>

                <div className="space-y-2 max-h-64 overflow-auto">
                  {bulkResults.map((result) => (
                    <div
                      key={result.deviceId}
                      className="flex items-center justify-between p-3 bg-[#111] rounded-xl border border-[#222]"
                    >
                      <span className="font-medium text-white">{result.deviceName}</span>
                      <div className="flex items-center gap-2">
                        {result.status === 'pending' && (
                          <span className="text-[#666] text-sm">Waiting...</span>
                        )}
                        {result.status === 'sending' && (
                          <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                        )}
                        {result.status === 'sent' && (
                          <CheckCircle className="w-4 h-4 text-green-400" />
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
                      className="px-4 py-2.5 text-[#AAA] hover:text-white hover:bg-[#222] rounded-xl transition-colors"
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
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="neon-card w-full max-w-md m-4">
            <div className="p-6">
              <div className="flex items-center gap-4 mb-4">
                <div className="p-3 bg-red-500/20 rounded-xl">
                  <AlertTriangle className="w-6 h-6 text-red-500" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">Remove Device</h2>
                  <p className="text-[#666]">This action cannot be undone</p>
                </div>
              </div>

              <div className="bg-[#111] rounded-xl p-4 mb-6 border border-[#222]">
                <p className="font-medium text-white">{deviceToDelete.hostname}</p>
                <p className="text-sm text-[#666]">{deviceToDelete.os_version}</p>
                <p className="text-xs text-[#555] mt-2">
                  Last seen: {formatDistanceToNow(new Date(deviceToDelete.last_seen), { addSuffix: true })}
                </p>
              </div>

              <p className="text-sm text-[#888] mb-6">
                This will permanently remove the device and all its associated events and commands.
              </p>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowDeleteConfirm(false);
                    setDeviceToDelete(null);
                  }}
                  className="flex-1 px-4 py-3 border border-[#333] rounded-xl hover:bg-[#111] text-[#AAA] hover:text-white transition-colors"
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
