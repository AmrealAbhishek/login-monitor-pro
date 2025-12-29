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

  useEffect(() => {
    fetchDevices();
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

  async function executeBulkCommand(commandName: string) {
    if (selectedDeviceIds.size === 0) return;

    setBulkCommand(commandName);
    setBulkExecuting(true);

    // Initialize results
    const initialResults: BulkCommandResult[] = Array.from(selectedDeviceIds).map(deviceId => {
      const device = devices.find(d => d.id === deviceId);
      return {
        deviceId,
        deviceName: device?.hostname || 'Unknown',
        status: 'pending' as const,
      };
    });
    setBulkResults(initialResults);

    // Create a bulk command job record
    const { data: jobData, error: jobError } = await supabase
      .from('bulk_command_jobs')
      .insert({
        command: commandName,
        target_type: 'selected',
        target_ids: Array.from(selectedDeviceIds),
        status: 'executing',
        total_devices: selectedDeviceIds.size,
        completed_devices: 0,
        failed_devices: 0,
      })
      .select()
      .single();

    if (jobError) {
      console.error('Error creating bulk job:', jobError);
    }

    // Send command to each device
    for (const deviceId of selectedDeviceIds) {
      const device = devices.find(d => d.id === deviceId);

      // Update status to sending
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

    // Update job status
    if (jobData) {
      const sentCount = initialResults.filter(r => r.status !== 'error').length;
      const failedCount = initialResults.filter(r => r.status === 'error').length;

      await supabase
        .from('bulk_command_jobs')
        .update({
          status: failedCount > 0 ? 'partial' : 'completed',
          completed_devices: sentCount,
          failed_devices: failedCount,
          completed_at: new Date().toISOString(),
        })
        .eq('id', jobData.id);
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

  const onlineCount = devices.filter(isOnline).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Devices</h1>
          <p className="text-gray-600">
            {devices.length} devices ({onlineCount} online)
            {bulkMode && selectedDeviceIds.size > 0 && (
              <span className="ml-2 text-red-600 font-medium">
                • {selectedDeviceIds.size} selected
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setBulkMode(!bulkMode);
              if (bulkMode) {
                setSelectedDeviceIds(new Set());
                setShowBulkPanel(false);
              }
            }}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              bulkMode
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Users className="w-4 h-4" />
            {bulkMode ? 'Exit Bulk Mode' : 'Bulk Commands'}
          </button>
          <button
            onClick={fetchDevices}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Bulk Selection Toolbar */}
      {bulkMode && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={selectAllDevices}
              className="flex items-center gap-2 px-3 py-1.5 bg-white border rounded-lg hover:bg-gray-50"
            >
              {selectedDeviceIds.size === devices.length ? (
                <CheckSquare className="w-4 h-4 text-red-600" />
              ) : (
                <Square className="w-4 h-4" />
              )}
              Select All
            </button>
            <button
              onClick={selectOnlineDevices}
              className="flex items-center gap-2 px-3 py-1.5 bg-white border rounded-lg hover:bg-gray-50"
            >
              <div className="w-3 h-3 bg-green-500 rounded-full" />
              Select Online ({onlineCount})
            </button>
            <button
              onClick={() => setSelectedDeviceIds(new Set())}
              className="px-3 py-1.5 text-gray-600 hover:text-gray-900"
            >
              Clear Selection
            </button>
          </div>

          {selectedDeviceIds.size > 0 && (
            <button
              onClick={() => setShowBulkPanel(true)}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              <Zap className="w-4 h-4" />
              Send Command to {selectedDeviceIds.size} Devices
            </button>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Device List */}
        <div className="bg-white rounded-xl shadow-sm border">
          <div className="p-4 border-b">
            <h2 className="font-semibold">All Devices ({devices.length})</h2>
          </div>
          <div className="divide-y max-h-[600px] overflow-auto">
            {devices.map((device) => (
              <div
                key={device.id}
                className={`flex items-center ${
                  !bulkMode && selectedDevice?.id === device.id ? 'bg-red-50 border-l-4 border-red-500' : ''
                }`}
              >
                {bulkMode && (
                  <button
                    onClick={() => toggleDeviceSelection(device.id)}
                    className="p-4 hover:bg-gray-50"
                  >
                    {selectedDeviceIds.has(device.id) ? (
                      <CheckSquare className="w-5 h-5 text-red-600" />
                    ) : (
                      <Square className="w-5 h-5 text-gray-400" />
                    )}
                  </button>
                )}
                <button
                  onClick={() => !bulkMode && setSelectedDevice(device)}
                  className={`flex-1 p-4 text-left hover:bg-gray-50 transition-colors ${
                    bulkMode ? '' : 'cursor-pointer'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${isOnline(device) ? 'bg-green-500' : 'bg-gray-300'}`} />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 truncate">
                        {device.hostname}
                      </p>
                      <p className="text-sm text-gray-500">{device.os_version}</p>
                    </div>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">
                    {formatDistanceToNow(new Date(device.last_seen), { addSuffix: true })}
                  </p>
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Device Details & Commands */}
        <div className="lg:col-span-2 space-y-6">
          {selectedDevice && !bulkMode ? (
            <>
              {/* Device Info */}
              <div className="bg-white rounded-xl shadow-sm border p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">
                      {selectedDevice.hostname}
                    </h2>
                    <p className="text-gray-500">{selectedDevice.os_version}</p>
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
          ) : bulkMode ? (
            <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
              <Users className="w-12 h-12 text-red-500 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-gray-900 mb-2">Bulk Command Mode</h3>
              <p className="text-gray-500 mb-6">
                Select devices from the list, then click &quot;Send Command&quot; to execute commands on multiple devices at once.
              </p>
              {selectedDeviceIds.size > 0 && (
                <p className="text-red-600 font-medium">
                  {selectedDeviceIds.size} device{selectedDeviceIds.size !== 1 ? 's' : ''} selected
                </p>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
              <Monitor className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Select a device to view details and send commands</p>
            </div>
          )}
        </div>
      </div>

      {/* Bulk Command Modal */}
      {showBulkPanel && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl m-4 max-h-[90vh] overflow-auto">
            <div className="p-6 border-b flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Send Bulk Command</h2>
                <p className="text-gray-500">
                  Sending to {selectedDeviceIds.size} device{selectedDeviceIds.size !== 1 ? 's' : ''}
                </p>
              </div>
              <button
                onClick={() => {
                  setShowBulkPanel(false);
                  setBulkCommand(null);
                  setBulkResults([]);
                }}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {!bulkCommand ? (
              <div className="p-6">
                <p className="text-sm text-gray-600 mb-4">Select a command to execute:</p>
                <div className="grid grid-cols-2 gap-3">
                  {COMMANDS.map((cmd) => {
                    const Icon = cmd.icon;
                    return (
                      <button
                        key={cmd.id}
                        onClick={() => executeBulkCommand(cmd.id)}
                        className="p-4 rounded-lg border text-left hover:bg-gray-50 hover:border-gray-300 transition-all"
                      >
                        <Icon className="w-5 h-5 mb-2 text-red-500" />
                        <p className="font-medium text-sm">{cmd.label}</p>
                        <p className="text-xs text-gray-500 mt-1">{cmd.description}</p>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-2 bg-red-100 rounded-lg">
                    <Play className="w-5 h-5 text-red-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">
                      Executing: {COMMANDS.find(c => c.id === bulkCommand)?.label}
                    </p>
                    <p className="text-sm text-gray-500">
                      {bulkExecuting ? 'Sending commands...' : 'Complete'}
                    </p>
                  </div>
                </div>

                <div className="space-y-2 max-h-64 overflow-auto">
                  {bulkResults.map((result) => (
                    <div
                      key={result.deviceId}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <span className="font-medium text-gray-900">{result.deviceName}</span>
                      <div className="flex items-center gap-2">
                        {result.status === 'pending' && (
                          <span className="text-gray-500 text-sm">Waiting...</span>
                        )}
                        {result.status === 'sending' && (
                          <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                        )}
                        {result.status === 'sent' && (
                          <CheckCircle className="w-4 h-4 text-green-500" />
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
                      className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                    >
                      Send Another Command
                    </button>
                    <button
                      onClick={() => {
                        setShowBulkPanel(false);
                        setBulkCommand(null);
                        setBulkResults([]);
                        setBulkMode(false);
                        setSelectedDeviceIds(new Set());
                      }}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
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
    </div>
  );
}
