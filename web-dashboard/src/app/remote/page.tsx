'use client';

import { useEffect, useState, useRef } from 'react';
import { supabase, Device } from '@/lib/supabase';
import {
  Monitor,
  Play,
  Square,
  RefreshCw,
  Maximize2,
  Minimize2,
  ExternalLink,
  Wifi,
  WifiOff,
  AlertCircle,
  CheckCircle,
  Loader2,
  Copy,
  Key,
  User,
  Eye,
  EyeOff,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface VncSession {
  deviceId: string;
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  vncUrl?: string;
  vncUsername?: string;
  vncPassword?: string;
  error?: string;
}

export default function RemoteDesktopPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState<VncSession | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, 30000);
    return () => clearInterval(interval);
  }, []);

  async function fetchDevices() {
    const { data } = await supabase
      .from('devices')
      .select('*')
      .order('last_seen', { ascending: false });

    if (data) {
      setDevices(data);
    }
    setLoading(false);
  }

  const isDeviceOnline = (lastSeen: string) => {
    return new Date(lastSeen) > new Date(Date.now() - 60 * 1000);
  };

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  async function startVncSession(device: Device) {
    setSelectedDevice(device);
    setSession({
      deviceId: device.id,
      status: 'connecting',
    });

    // Send vnc_start command
    const { data: cmdData, error: cmdError } = await supabase
      .from('commands')
      .insert({
        device_id: device.id,
        command: 'vnc_start',
        args: {},
        status: 'pending',
      })
      .select()
      .single();

    if (cmdError) {
      setSession({
        deviceId: device.id,
        status: 'error',
        error: cmdError.message,
      });
      return;
    }

    // Poll for result
    const cmdId = cmdData.id;
    let attempts = 0;
    const maxAttempts = 60; // 60 seconds timeout

    const pollInterval = setInterval(async () => {
      attempts++;

      const { data: result } = await supabase
        .from('commands')
        .select('status, result')
        .eq('id', cmdId)
        .single();

      if (result) {
        if (result.status === 'completed') {
          clearInterval(pollInterval);
          const vncResult = result.result as {
            success?: boolean;
            vnc_url?: string;
            vnc_username?: string;
            vnc_password?: string;
            error?: string
          };

          if (vncResult?.success && vncResult?.vnc_url) {
            setSession({
              deviceId: device.id,
              status: 'connected',
              vncUrl: vncResult.vnc_url,
              vncUsername: vncResult.vnc_username,
              vncPassword: vncResult.vnc_password,
            });
          } else {
            setSession({
              deviceId: device.id,
              status: 'error',
              error: vncResult?.error || 'Failed to start VNC',
            });
          }
        } else if (result.status === 'failed') {
          clearInterval(pollInterval);
          const vncResult = result.result as { error?: string };
          setSession({
            deviceId: device.id,
            status: 'error',
            error: vncResult?.error || 'Command failed',
          });
        }
      }

      if (attempts >= maxAttempts) {
        clearInterval(pollInterval);
        setSession({
          deviceId: device.id,
          status: 'error',
          error: 'Connection timeout',
        });
      }
    }, 1000);
  }

  async function stopVncSession() {
    if (!selectedDevice) return;

    await supabase.from('commands').insert({
      device_id: selectedDevice.id,
      command: 'vnc_stop',
      args: {},
      status: 'pending',
    });

    setSession(null);
    setSelectedDevice(null);
  }

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      iframeRef.current?.parentElement?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  }

  // Generate noVNC URL with scaling options for better resolution
  const getNoVncUrl = (tunnelUrl: string) => {
    const hostname = new URL(tunnelUrl).hostname;
    // noVNC parameters for better experience:
    // - resize=scale: Scale to fit the window
    // - quality=6: Medium quality (0-9, higher = better)
    // - compression=2: Low compression for better quality
    // - autoconnect=true: Auto connect on load
    // - reconnect=true: Auto reconnect on disconnect
    // - show_dot=true: Show cursor
    return `https://novnc.com/noVNC/vnc.html?autoconnect=true&reconnect=true&resize=scale&quality=6&compression=2&show_dot=true&host=${hostname}&port=443&path=websockify&encrypt=true`;
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Monitor className="w-7 h-7 text-red-500" />
            Remote Desktop
          </h1>
          <p className="text-gray-600 dark:text-[#888] mt-1">
            Connect to devices via VNC for full desktop control
          </p>
        </div>
        {session && session.status === 'connected' && (
          <div className="flex gap-2">
            <button
              onClick={toggleFullscreen}
              className="p-2 bg-gray-100 dark:bg-[#222] rounded-lg hover:bg-gray-200 dark:hover:bg-[#333]"
              title="Toggle fullscreen"
            >
              {isFullscreen ? (
                <Minimize2 className="w-5 h-5 text-gray-600 dark:text-[#AAA]" />
              ) : (
                <Maximize2 className="w-5 h-5 text-gray-600 dark:text-[#AAA]" />
              )}
            </button>
            <button
              onClick={stopVncSession}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              <Square className="w-4 h-4" />
              Disconnect
            </button>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Device List */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333]">
            <div className="p-4 border-b border-gray-200 dark:border-[#333]">
              <h2 className="font-semibold text-gray-900 dark:text-white">Devices</h2>
            </div>
            <div className="divide-y divide-gray-100 dark:divide-[#333] max-h-[500px] overflow-auto">
              {devices.map((device) => {
                const online = isDeviceOnline(device.last_seen);
                const isSelected = selectedDevice?.id === device.id;

                return (
                  <div
                    key={device.id}
                    className={`p-4 cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-red-50 dark:bg-red-500/10 border-l-4 border-red-500'
                        : 'hover:bg-gray-50 dark:hover:bg-[#222]'
                    }`}
                    onClick={() => !session && setSelectedDevice(device)}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${online ? 'bg-green-500' : 'bg-gray-300 dark:bg-[#555]'}`} />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 dark:text-white truncate">
                          {device.hostname}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-[#666]">
                          {formatDistanceToNow(new Date(device.last_seen), { addSuffix: true })}
                        </p>
                      </div>
                      {online ? (
                        <Wifi className="w-4 h-4 text-green-500" />
                      ) : (
                        <WifiOff className="w-4 h-4 text-gray-400" />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* VNC Credentials Panel */}
          {session?.status === 'connected' && (session.vncUsername || session.vncPassword) && (
            <div className="mt-4 bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333] p-4">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                <Key className="w-4 h-4 text-red-500" />
                VNC Credentials
              </h3>
              <div className="space-y-3">
                {session.vncUsername && (
                  <div>
                    <label className="text-xs text-gray-500 dark:text-[#666] uppercase tracking-wider">Username</label>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 bg-gray-50 dark:bg-[#222] rounded-lg px-3 py-2 font-mono text-sm text-gray-900 dark:text-white">
                        <User className="w-4 h-4 inline mr-2 text-gray-400" />
                        {session.vncUsername}
                      </div>
                      <button
                        onClick={() => copyToClipboard(session.vncUsername!, 'username')}
                        className="p-2 bg-gray-100 dark:bg-[#333] rounded-lg hover:bg-gray-200 dark:hover:bg-[#444]"
                        title="Copy username"
                      >
                        {copiedField === 'username' ? (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        ) : (
                          <Copy className="w-4 h-4 text-gray-500" />
                        )}
                      </button>
                    </div>
                  </div>
                )}
                {session.vncPassword && (
                  <div>
                    <label className="text-xs text-gray-500 dark:text-[#666] uppercase tracking-wider">VNC Password</label>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 bg-gray-50 dark:bg-[#222] rounded-lg px-3 py-2 font-mono text-sm text-gray-900 dark:text-white">
                        <Key className="w-4 h-4 inline mr-2 text-gray-400" />
                        {showPassword ? session.vncPassword : '••••••••'}
                      </div>
                      <button
                        onClick={() => setShowPassword(!showPassword)}
                        className="p-2 bg-gray-100 dark:bg-[#333] rounded-lg hover:bg-gray-200 dark:hover:bg-[#444]"
                        title={showPassword ? 'Hide password' : 'Show password'}
                      >
                        {showPassword ? (
                          <EyeOff className="w-4 h-4 text-gray-500" />
                        ) : (
                          <Eye className="w-4 h-4 text-gray-500" />
                        )}
                      </button>
                      <button
                        onClick={() => copyToClipboard(session.vncPassword!, 'password')}
                        className="p-2 bg-gray-100 dark:bg-[#333] rounded-lg hover:bg-gray-200 dark:hover:bg-[#444]"
                        title="Copy password"
                      >
                        {copiedField === 'password' ? (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        ) : (
                          <Copy className="w-4 h-4 text-gray-500" />
                        )}
                      </button>
                    </div>
                  </div>
                )}
                <p className="text-xs text-gray-500 dark:text-[#666] mt-2">
                  Use Mac credentials OR VNC password set in Screen Sharing settings
                </p>
              </div>
            </div>
          )}
        </div>

        {/* VNC Viewer */}
        <div className="lg:col-span-3">
          <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333] min-h-[600px]">
            {!selectedDevice ? (
              <div className="flex flex-col items-center justify-center h-[600px] text-center p-8">
                <Monitor className="w-16 h-16 text-gray-300 dark:text-[#444] mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  Select a Device
                </h3>
                <p className="text-gray-500 dark:text-[#888] max-w-md">
                  Choose a device from the list to start a remote desktop session.
                  The device must be online and have Screen Sharing enabled.
                </p>
              </div>
            ) : !session ? (
              <div className="flex flex-col items-center justify-center h-[600px] text-center p-8">
                <div className="w-20 h-20 bg-gray-100 dark:bg-[#222] rounded-2xl flex items-center justify-center mb-6">
                  <Monitor className="w-10 h-10 text-gray-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  {selectedDevice.hostname}
                </h3>
                <p className="text-gray-500 dark:text-[#888] mb-6">
                  Ready to connect via VNC
                </p>
                <button
                  onClick={() => startVncSession(selectedDevice)}
                  disabled={!isDeviceOnline(selectedDevice.last_seen)}
                  className="flex items-center gap-2 px-6 py-3 bg-red-600 text-white rounded-xl hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-red-500/20"
                >
                  <Play className="w-5 h-5" />
                  Start Remote Session
                </button>
                {!isDeviceOnline(selectedDevice.last_seen) && (
                  <p className="text-sm text-red-500 mt-4">
                    Device is offline. Cannot connect.
                  </p>
                )}
              </div>
            ) : session.status === 'connecting' ? (
              <div className="flex flex-col items-center justify-center h-[600px] text-center p-8">
                <Loader2 className="w-12 h-12 text-red-500 animate-spin mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  Connecting...
                </h3>
                <p className="text-gray-500 dark:text-[#888]">
                  Starting VNC tunnel to {selectedDevice.hostname}
                </p>
                <div className="mt-6 flex items-center gap-2 text-sm text-gray-500 dark:text-[#666]">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  This may take up to 30 seconds
                </div>
              </div>
            ) : session.status === 'error' ? (
              <div className="flex flex-col items-center justify-center h-[600px] text-center p-8">
                <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
                  <AlertCircle className="w-8 h-8 text-red-500" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  Connection Failed
                </h3>
                <p className="text-red-500 dark:text-red-400 mb-6 max-w-md">
                  {session.error}
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={() => setSession(null)}
                    className="px-4 py-2 bg-gray-100 dark:bg-[#222] text-gray-700 dark:text-[#AAA] rounded-lg hover:bg-gray-200 dark:hover:bg-[#333]"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => startVncSession(selectedDevice)}
                    className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Retry
                  </button>
                </div>
              </div>
            ) : session.status === 'connected' && session.vncUrl ? (
              <div className="h-[600px] flex flex-col">
                <div className="p-3 bg-gray-50 dark:bg-[#111] border-b border-gray-200 dark:border-[#333] flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      Connected to {selectedDevice.hostname}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-[#666]">
                      (Resolution auto-scales to fit)
                    </span>
                  </div>
                  <a
                    href={getNoVncUrl(session.vncUrl)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Open in new tab (better resolution)
                  </a>
                </div>
                <div className="flex-1 bg-black relative" ref={iframeRef as any}>
                  <iframe
                    src={getNoVncUrl(session.vncUrl)}
                    className="w-full h-full border-0"
                    allow="fullscreen"
                  />
                </div>
              </div>
            ) : null}
          </div>

          {/* Instructions */}
          {!session && selectedDevice && (
            <div className="mt-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl">
              <h4 className="font-medium text-yellow-800 dark:text-yellow-400 mb-2">
                Requirements & Login Options
              </h4>
              <ul className="text-sm text-yellow-700 dark:text-yellow-500 space-y-1">
                <li>• Screen Sharing must be enabled on the Mac (System Settings → Sharing)</li>
                <li>• <strong>Option 1:</strong> Use Mac username + password</li>
                <li>• <strong>Option 2:</strong> Use VNC-only password (set in Computer Settings → VNC viewers may control...)</li>
                <li>• Device must be online and running the CyVigil agent</li>
              </ul>
              <div className="mt-3 p-3 bg-yellow-100 dark:bg-yellow-900/40 rounded-lg">
                <p className="text-xs text-yellow-800 dark:text-yellow-400 font-medium">
                  To set VNC-only password on the Mac:
                </p>
                <p className="text-xs text-yellow-700 dark:text-yellow-500 mt-1">
                  System Settings → General → Sharing → Screen Sharing (i) → Computer Settings → Check "VNC viewers may control screen with password" → Set password
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
