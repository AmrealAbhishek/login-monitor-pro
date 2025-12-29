'use client';

import { useEffect, useState, useRef } from 'react';
import { supabase, Device } from '@/lib/supabase';
import {
  Package,
  Download,
  Trash2,
  RefreshCw,
  Search,
  Monitor,
  CheckCircle2,
  XCircle,
  Clock,
  Terminal,
  Globe,
  Play,
  Power,
  RotateCcw,
  Wifi,
  HardDrive,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface Command {
  id: string;
  device_id: string;
  command: string;
  args: Record<string, unknown>;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  result: Record<string, unknown> | null;
  created_at: string;
}

interface InstallJob {
  deviceId: string;
  deviceName: string;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  message?: string;
}

export default function AppManagementPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevices, setSelectedDevices] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [appName, setAppName] = useState('');
  const [installSource, setInstallSource] = useState<'brew' | 'dmg' | 'pkg'>('brew');
  const [downloadUrl, setDownloadUrl] = useState('');
  const [installJobs, setInstallJobs] = useState<InstallJob[]>([]);
  const [showInstallModal, setShowInstallModal] = useState(false);

  // Shell/Command state
  const [activeTab, setActiveTab] = useState<'apps' | 'shell' | 'history'>('apps');
  const [shellCommand, setShellCommand] = useState('');
  const [useSudo, setUseSudo] = useState(false);
  const [commandHistory, setCommandHistory] = useState<Command[]>([]);
  const [expandedCommands, setExpandedCommands] = useState<Set<string>>(new Set());
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const shellInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchDevices();
    fetchCommandHistory();

    // Realtime subscription for command updates
    const channel = supabase
      .channel('commands-realtime')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'commands' }, () => {
        fetchCommandHistory();
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  async function fetchDevices() {
    const { data } = await supabase
      .from('devices')
      .select('*')
      .order('hostname');

    if (data) {
      setDevices(data);
    }
    setLoading(false);
  }

  async function fetchCommandHistory() {
    const { data } = await supabase
      .from('commands')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(50);

    if (data) {
      setCommandHistory(data);
    }
  }

  function toggleDeviceSelection(deviceId: string) {
    setSelectedDevices(prev =>
      prev.includes(deviceId)
        ? prev.filter(id => id !== deviceId)
        : [...prev, deviceId]
    );
  }

  function selectAllDevices() {
    if (selectedDevices.length === devices.length) {
      setSelectedDevices([]);
    } else {
      setSelectedDevices(devices.map(d => d.id));
    }
  }

  async function sendCommand(command: string, args: Record<string, unknown> = {}) {
    if (selectedDevices.length === 0) {
      alert('Please select at least one device');
      return;
    }

    for (const deviceId of selectedDevices) {
      await supabase.from('commands').insert({
        device_id: deviceId,
        command,
        args,
        status: 'pending',
      });
    }

    fetchCommandHistory();
  }

  async function executeShellCommand() {
    if (!shellCommand.trim()) return;
    if (selectedDevices.length === 0) {
      alert('Please select at least one device');
      return;
    }

    await sendCommand('shell', {
      cmd: shellCommand,
      sudo: useSudo,
      timeout: 60,
    });

    setShellCommand('');
    setActiveTab('history');
  }

  async function installApp() {
    if (!appName && !downloadUrl) return;
    if (selectedDevices.length === 0) return;

    const jobs: InstallJob[] = selectedDevices.map(deviceId => ({
      deviceId,
      deviceName: devices.find(d => d.id === deviceId)?.hostname || 'Unknown',
      status: 'pending',
    }));

    setInstallJobs(jobs);

    for (const job of jobs) {
      try {
        const args: Record<string, string> = {
          app_name: appName,
          source: installSource,
        };
        if (downloadUrl) {
          args.url = downloadUrl;
        }

        const { error } = await supabase.from('commands').insert({
          device_id: job.deviceId,
          command: 'install_app',
          args,
          status: 'pending',
        });

        if (error) {
          job.status = 'failed';
          job.message = error.message;
        } else {
          job.status = 'executing';
        }
      } catch (e) {
        job.status = 'failed';
        job.message = String(e);
      }
      setInstallJobs([...jobs]);
    }

    pollJobStatus(jobs);
  }

  async function pollJobStatus(jobs: InstallJob[]) {
    const maxPolls = 60;
    let polls = 0;

    const interval = setInterval(async () => {
      polls++;
      if (polls >= maxPolls) {
        clearInterval(interval);
        return;
      }

      let allDone = true;
      for (const job of jobs) {
        if (job.status === 'executing' || job.status === 'pending') {
          const { data } = await supabase
            .from('commands')
            .select('status, result')
            .eq('device_id', job.deviceId)
            .eq('command', 'install_app')
            .order('created_at', { ascending: false })
            .limit(1)
            .single();

          if (data) {
            if (data.status === 'completed') {
              job.status = 'completed';
              job.message = (data.result as Record<string, string>)?.message || 'Installed successfully';
            } else if (data.status === 'failed') {
              job.status = 'failed';
              job.message = (data.result as Record<string, string>)?.error || 'Installation failed';
            } else {
              allDone = false;
            }
          } else {
            allDone = false;
          }
        }
      }
      setInstallJobs([...jobs]);

      if (allDone) {
        clearInterval(interval);
      }
    }, 5000);
  }

  function toggleCommandExpand(id: string) {
    setExpandedCommands(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  }

  function copyToClipboard(text: string, id: string) {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  const isDeviceOnline = (lastSeen: string) => {
    return new Date(lastSeen) > new Date(Date.now() - 5 * 60 * 1000);
  };

  const getDeviceName = (deviceId: string) => {
    return devices.find(d => d.id === deviceId)?.hostname || 'Unknown';
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
            <Package className="w-7 h-7 text-red-500" />
            App & Shell Management
          </h1>
          <p className="text-gray-600 dark:text-[#888] mt-1">
            Install apps, run commands, and view output remotely
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('apps')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'apps'
                ? 'bg-red-600 text-white'
                : 'bg-gray-100 dark:bg-[#1A1A1A] text-gray-700 dark:text-[#AAA] hover:bg-gray-200 dark:hover:bg-[#222]'
            }`}
          >
            <Package className="w-4 h-4 inline mr-2" />
            Apps
          </button>
          <button
            onClick={() => setActiveTab('shell')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'shell'
                ? 'bg-red-600 text-white'
                : 'bg-gray-100 dark:bg-[#1A1A1A] text-gray-700 dark:text-[#AAA] hover:bg-gray-200 dark:hover:bg-[#222]'
            }`}
          >
            <Terminal className="w-4 h-4 inline mr-2" />
            Shell
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'history'
                ? 'bg-red-600 text-white'
                : 'bg-gray-100 dark:bg-[#1A1A1A] text-gray-700 dark:text-[#AAA] hover:bg-gray-200 dark:hover:bg-[#222]'
            }`}
          >
            <Clock className="w-4 h-4 inline mr-2" />
            History
          </button>
        </div>
      </div>

      {/* Device Selection */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333]">
        <div className="p-4 border-b border-gray-200 dark:border-[#333] flex items-center justify-between">
          <h2 className="font-semibold text-gray-900 dark:text-white">
            Select Devices ({selectedDevices.length} selected)
          </h2>
          <button
            onClick={selectAllDevices}
            className="text-sm text-red-600 dark:text-red-500 hover:text-red-700"
          >
            {selectedDevices.length === devices.length ? 'Deselect All' : 'Select All'}
          </button>
        </div>

        <div className="divide-y divide-gray-100 dark:divide-[#333] max-h-[250px] overflow-auto">
          {devices.map((device) => {
            const online = isDeviceOnline(device.last_seen);
            const selected = selectedDevices.includes(device.id);

            return (
              <div
                key={device.id}
                onClick={() => toggleDeviceSelection(device.id)}
                className={`p-4 cursor-pointer transition-all flex items-center gap-4 ${
                  selected
                    ? 'bg-red-50 dark:bg-red-500/10'
                    : 'hover:bg-gray-50 dark:hover:bg-[#222]'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selected}
                  onChange={() => {}}
                  className="w-5 h-5 rounded border-gray-300 text-red-600 focus:ring-red-500"
                />
                <div className={`w-3 h-3 rounded-full ${online ? 'bg-green-500' : 'bg-gray-300 dark:bg-[#555]'}`} />
                <Monitor className="w-5 h-5 text-gray-400" />
                <div className="flex-1">
                  <p className="font-medium text-gray-900 dark:text-white">{device.hostname}</p>
                  <p className="text-sm text-gray-500 dark:text-[#666]">{device.os_version}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Apps Tab */}
      {activeTab === 'apps' && (
        <>
          {/* Install Jobs Status */}
          {installJobs.length > 0 && (
            <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333]">
              <div className="p-4 border-b border-gray-200 dark:border-[#333]">
                <h2 className="font-semibold text-gray-900 dark:text-white">Installation Progress</h2>
              </div>
              <div className="divide-y divide-gray-100 dark:divide-[#333]">
                {installJobs.map((job) => (
                  <div key={job.deviceId} className="p-4 flex items-center gap-4">
                    {job.status === 'pending' && <Clock className="w-5 h-5 text-gray-400" />}
                    {job.status === 'executing' && (
                      <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />
                    )}
                    {job.status === 'completed' && <CheckCircle2 className="w-5 h-5 text-green-500" />}
                    {job.status === 'failed' && <XCircle className="w-5 h-5 text-red-500" />}
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 dark:text-white">{job.deviceName}</p>
                      <p className="text-sm text-gray-500 dark:text-[#666]">
                        {job.status === 'pending' && 'Waiting...'}
                        {job.status === 'executing' && 'Installing...'}
                        {job.status === 'completed' && job.message}
                        {job.status === 'failed' && job.message}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick Install */}
          <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333]">
            <div className="p-4 border-b border-gray-200 dark:border-[#333] flex items-center justify-between">
              <h2 className="font-semibold text-gray-900 dark:text-white">Quick Install (Homebrew)</h2>
              <button
                onClick={() => setShowInstallModal(true)}
                disabled={selectedDevices.length === 0}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                <Download className="w-4 h-4" />
                Custom Install
              </button>
            </div>
            <div className="p-4 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {[
                { name: 'visual-studio-code', label: 'VS Code' },
                { name: 'google-chrome', label: 'Chrome' },
                { name: 'slack', label: 'Slack' },
                { name: 'zoom', label: 'Zoom' },
                { name: 'discord', label: 'Discord' },
                { name: 'figma', label: 'Figma' },
                { name: 'notion', label: 'Notion' },
                { name: 'spotify', label: 'Spotify' },
                { name: 'docker', label: 'Docker' },
                { name: 'postman', label: 'Postman' },
                { name: 'iterm2', label: 'iTerm2' },
                { name: 'rectangle', label: 'Rectangle' },
              ].map((app) => (
                <button
                  key={app.name}
                  onClick={() => {
                    setAppName(app.name);
                    setInstallSource('brew');
                    setDownloadUrl('');
                    setShowInstallModal(true);
                  }}
                  disabled={selectedDevices.length === 0}
                  className="p-3 rounded-lg border border-gray-200 dark:border-[#333] hover:border-red-500 dark:hover:border-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-all text-center disabled:opacity-50"
                >
                  <span className="text-sm font-medium text-gray-900 dark:text-white">{app.label}</span>
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Shell Tab */}
      {activeTab === 'shell' && (
        <div className="space-y-4">
          {/* Shell Input */}
          <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333]">
            <div className="p-4 border-b border-gray-200 dark:border-[#333]">
              <h2 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Terminal className="w-5 h-5 text-green-500" />
                Remote Shell
              </h2>
              <p className="text-sm text-gray-500 dark:text-[#666] mt-1">
                Execute commands on selected devices. Output will appear in History tab.
              </p>
            </div>
            <div className="p-4 space-y-4">
              <div className="flex gap-3">
                <div className="flex-1 relative">
                  <Terminal className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    ref={shellInputRef}
                    type="text"
                    value={shellCommand}
                    onChange={(e) => setShellCommand(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && executeShellCommand()}
                    placeholder="Enter command (e.g., ifconfig, ping google.com, df -h)"
                    className="w-full pl-10 pr-4 py-3 bg-gray-900 dark:bg-[#0A0A0A] text-green-400 font-mono text-sm rounded-lg border border-gray-700 dark:border-[#333] focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  />
                </div>
                <button
                  onClick={executeShellCommand}
                  disabled={!shellCommand.trim() || selectedDevices.length === 0}
                  className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                >
                  <Play className="w-4 h-4" />
                  Execute
                </button>
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-[#AAA]">
                  <input
                    type="checkbox"
                    checked={useSudo}
                    onChange={(e) => setUseSudo(e.target.checked)}
                    className="rounded border-gray-300 text-red-600 focus:ring-red-500"
                  />
                  Run with sudo
                </label>
                <span className="text-xs text-gray-500 dark:text-[#666]">
                  (Requires NOPASSWD in sudoers file)
                </span>
              </div>
            </div>
          </div>

          {/* Quick Commands */}
          <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333]">
            <div className="p-4 border-b border-gray-200 dark:border-[#333]">
              <h2 className="font-semibold text-gray-900 dark:text-white">Quick Actions</h2>
            </div>
            <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-3">
              <button
                onClick={() => sendCommand('shell', { cmd: 'ifconfig' })}
                disabled={selectedDevices.length === 0}
                className="p-4 rounded-lg border border-gray-200 dark:border-[#333] hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-all text-left disabled:opacity-50"
              >
                <Wifi className="w-5 h-5 text-blue-500 mb-2" />
                <p className="font-medium text-gray-900 dark:text-white">Network Info</p>
                <p className="text-xs text-gray-500 dark:text-[#666]">ifconfig</p>
              </button>
              <button
                onClick={() => sendCommand('shell', { cmd: 'df -h' })}
                disabled={selectedDevices.length === 0}
                className="p-4 rounded-lg border border-gray-200 dark:border-[#333] hover:border-purple-500 hover:bg-purple-50 dark:hover:bg-purple-500/10 transition-all text-left disabled:opacity-50"
              >
                <HardDrive className="w-5 h-5 text-purple-500 mb-2" />
                <p className="font-medium text-gray-900 dark:text-white">Disk Space</p>
                <p className="text-xs text-gray-500 dark:text-[#666]">df -h</p>
              </button>
              <button
                onClick={() => sendCommand('shell', { cmd: 'top -l 1 | head -20' })}
                disabled={selectedDevices.length === 0}
                className="p-4 rounded-lg border border-gray-200 dark:border-[#333] hover:border-orange-500 hover:bg-orange-50 dark:hover:bg-orange-500/10 transition-all text-left disabled:opacity-50"
              >
                <RefreshCw className="w-5 h-5 text-orange-500 mb-2" />
                <p className="font-medium text-gray-900 dark:text-white">System Load</p>
                <p className="text-xs text-gray-500 dark:text-[#666]">top snapshot</p>
              </button>
              <button
                onClick={() => sendCommand('shell', { cmd: 'uptime' })}
                disabled={selectedDevices.length === 0}
                className="p-4 rounded-lg border border-gray-200 dark:border-[#333] hover:border-green-500 hover:bg-green-50 dark:hover:bg-green-500/10 transition-all text-left disabled:opacity-50"
              >
                <Clock className="w-5 h-5 text-green-500 mb-2" />
                <p className="font-medium text-gray-900 dark:text-white">Uptime</p>
                <p className="text-xs text-gray-500 dark:text-[#666]">uptime</p>
              </button>
              <button
                onClick={() => {
                  if (confirm('Are you sure you want to reboot the selected device(s)?')) {
                    sendCommand('reboot', {});
                  }
                }}
                disabled={selectedDevices.length === 0}
                className="p-4 rounded-lg border border-red-200 dark:border-red-900/50 hover:border-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-all text-left disabled:opacity-50"
              >
                <RotateCcw className="w-5 h-5 text-red-500 mb-2" />
                <p className="font-medium text-red-600 dark:text-red-400">Reboot</p>
                <p className="text-xs text-gray-500 dark:text-[#666]">Restart system</p>
              </button>
              <button
                onClick={() => {
                  if (confirm('Are you sure you want to shutdown the selected device(s)?')) {
                    sendCommand('shutdown', {});
                  }
                }}
                disabled={selectedDevices.length === 0}
                className="p-4 rounded-lg border border-red-200 dark:border-red-900/50 hover:border-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-all text-left disabled:opacity-50"
              >
                <Power className="w-5 h-5 text-red-500 mb-2" />
                <p className="font-medium text-red-600 dark:text-red-400">Shutdown</p>
                <p className="text-xs text-gray-500 dark:text-[#666]">Power off</p>
              </button>
              <button
                onClick={() => sendCommand('screenshot', {})}
                disabled={selectedDevices.length === 0}
                className="p-4 rounded-lg border border-gray-200 dark:border-[#333] hover:border-cyan-500 hover:bg-cyan-50 dark:hover:bg-cyan-500/10 transition-all text-left disabled:opacity-50"
              >
                <Monitor className="w-5 h-5 text-cyan-500 mb-2" />
                <p className="font-medium text-gray-900 dark:text-white">Screenshot</p>
                <p className="text-xs text-gray-500 dark:text-[#666]">Capture screen</p>
              </button>
              <button
                onClick={() => sendCommand('lock', {})}
                disabled={selectedDevices.length === 0}
                className="p-4 rounded-lg border border-gray-200 dark:border-[#333] hover:border-yellow-500 hover:bg-yellow-50 dark:hover:bg-yellow-500/10 transition-all text-left disabled:opacity-50"
              >
                <Power className="w-5 h-5 text-yellow-500 mb-2" />
                <p className="font-medium text-gray-900 dark:text-white">Lock Screen</p>
                <p className="text-xs text-gray-500 dark:text-[#666]">Lock device</p>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333]">
          <div className="p-4 border-b border-gray-200 dark:border-[#333] flex items-center justify-between">
            <h2 className="font-semibold text-gray-900 dark:text-white">Command History</h2>
            <button
              onClick={fetchCommandHistory}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-white"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
          <div className="divide-y divide-gray-100 dark:divide-[#333] max-h-[600px] overflow-auto">
            {commandHistory.length === 0 ? (
              <div className="p-12 text-center">
                <Terminal className="w-12 h-12 text-gray-300 dark:text-[#444] mx-auto mb-4" />
                <p className="text-gray-500 dark:text-[#888]">No commands executed yet</p>
              </div>
            ) : (
              commandHistory.map((cmd) => {
                const isExpanded = expandedCommands.has(cmd.id);
                const result = cmd.result as Record<string, unknown> | null;
                const output = result?.output || result?.stdout || result?.message || result?.error || '';
                const hasOutput = output && String(output).length > 0;

                return (
                  <div key={cmd.id} className="hover:bg-gray-50 dark:hover:bg-[#222]">
                    <div
                      className="p-4 cursor-pointer"
                      onClick={() => toggleCommandExpand(cmd.id)}
                    >
                      <div className="flex items-start gap-4">
                        <div className="flex-shrink-0 mt-1">
                          {cmd.status === 'pending' && <Clock className="w-5 h-5 text-gray-400" />}
                          {cmd.status === 'executing' && <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />}
                          {cmd.status === 'completed' && <CheckCircle2 className="w-5 h-5 text-green-500" />}
                          {cmd.status === 'failed' && <XCircle className="w-5 h-5 text-red-500" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <code className="px-2 py-1 bg-gray-100 dark:bg-[#333] rounded text-sm font-mono text-gray-900 dark:text-white">
                              {cmd.command}
                            </code>
                            {cmd.args && Object.keys(cmd.args).length > 0 && (
                              <span className="text-xs text-gray-500 dark:text-[#666] font-mono">
                                {cmd.command === 'shell'
                                  ? (cmd.args as Record<string, string>).cmd?.substring(0, 40) + ((cmd.args as Record<string, string>).cmd?.length > 40 ? '...' : '')
                                  : JSON.stringify(cmd.args).substring(0, 40)}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-4 mt-1 text-xs text-gray-500 dark:text-[#666]">
                            <span className="flex items-center gap-1">
                              <Monitor className="w-3 h-3" />
                              {getDeviceName(cmd.device_id)}
                            </span>
                            <span>{formatDistanceToNow(new Date(cmd.created_at), { addSuffix: true })}</span>
                            <span className={`px-1.5 py-0.5 rounded text-xs ${
                              cmd.status === 'completed' ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400' :
                              cmd.status === 'failed' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400' :
                              cmd.status === 'executing' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400' :
                              'bg-gray-100 dark:bg-[#333] text-gray-600 dark:text-[#888]'
                            }`}>
                              {cmd.status}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {hasOutput && (
                            isExpanded ? (
                              <ChevronUp className="w-5 h-5 text-gray-400" />
                            ) : (
                              <ChevronDown className="w-5 h-5 text-gray-400" />
                            )
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Expanded Output */}
                    {isExpanded && hasOutput && (
                      <div className="px-4 pb-4">
                        <div className="relative">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              copyToClipboard(String(output), cmd.id);
                            }}
                            className="absolute top-2 right-2 p-2 text-gray-400 hover:text-white bg-gray-800 rounded"
                          >
                            {copiedId === cmd.id ? (
                              <Check className="w-4 h-4 text-green-400" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>
                          <pre className="p-4 bg-gray-900 dark:bg-[#0A0A0A] text-green-400 text-sm font-mono rounded-lg overflow-x-auto whitespace-pre-wrap max-h-[400px] overflow-y-auto">
                            {String(output)}
                          </pre>
                        </div>
                        {result?.exit_code !== undefined && (
                          <p className="mt-2 text-xs text-gray-500 dark:text-[#666]">
                            Exit code: {String(result.exit_code)}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Install Modal */}
      {showInstallModal && (
        <div className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-[#1A1A1A] rounded-2xl shadow-2xl w-full max-w-lg m-4 border border-gray-200 dark:border-[#333]">
            <div className="p-6 border-b border-gray-200 dark:border-[#333]">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Download className="w-6 h-6 text-red-500" />
                Install Application
              </h2>
            </div>

            <div className="p-6 space-y-6">
              {/* Source Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">
                  Installation Method
                </label>
                <div className="flex gap-2">
                  {(['brew', 'dmg', 'pkg'] as const).map((source) => (
                    <button
                      key={source}
                      onClick={() => setInstallSource(source)}
                      className={`flex-1 p-3 rounded-lg border transition-all ${
                        installSource === source
                          ? 'border-red-500 bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-500'
                          : 'border-gray-200 dark:border-[#333] text-gray-600 dark:text-[#888] hover:border-gray-300'
                      }`}
                    >
                      {source === 'brew' && <Terminal className="w-5 h-5 mx-auto mb-1" />}
                      {source === 'dmg' && <Package className="w-5 h-5 mx-auto mb-1" />}
                      {source === 'pkg' && <Package className="w-5 h-5 mx-auto mb-1" />}
                      <span className="text-sm font-medium uppercase">{source}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* App Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">
                  {installSource === 'brew' ? 'Homebrew Cask Name' : 'Application Name'}
                </label>
                <input
                  type="text"
                  value={appName}
                  onChange={(e) => setAppName(e.target.value)}
                  placeholder={installSource === 'brew' ? 'e.g., visual-studio-code' : 'e.g., MyApp'}
                  className="w-full px-4 py-2 border border-gray-200 dark:border-[#333] rounded-lg bg-white dark:bg-[#222] text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500"
                />
              </div>

              {/* Download URL (for DMG/PKG) */}
              {(installSource === 'dmg' || installSource === 'pkg') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">
                    Download URL
                  </label>
                  <div className="relative">
                    <Globe className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type="url"
                      value={downloadUrl}
                      onChange={(e) => setDownloadUrl(e.target.value)}
                      placeholder="https://example.com/app.dmg"
                      className="w-full pl-10 pr-4 py-2 border border-gray-200 dark:border-[#333] rounded-lg bg-white dark:bg-[#222] text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500"
                    />
                  </div>
                </div>
              )}

              {/* Selected Devices */}
              <div className="p-4 bg-gray-50 dark:bg-[#111] rounded-lg">
                <p className="text-sm text-gray-500 dark:text-[#666] mb-2">
                  Will install on {selectedDevices.length} device(s):
                </p>
                <div className="flex flex-wrap gap-2">
                  {selectedDevices.map((id) => {
                    const device = devices.find((d) => d.id === id);
                    return (
                      <span
                        key={id}
                        className="px-2 py-1 bg-gray-200 dark:bg-[#333] text-gray-700 dark:text-[#AAA] rounded text-sm"
                      >
                        {device?.hostname}
                      </span>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-gray-200 dark:border-[#333] bg-gray-50 dark:bg-[#111] flex justify-end gap-3">
              <button
                onClick={() => setShowInstallModal(false)}
                className="px-4 py-2 text-gray-700 dark:text-[#AAA] hover:bg-gray-200 dark:hover:bg-[#333] rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  installApp();
                  setShowInstallModal(false);
                }}
                disabled={!appName && !downloadUrl}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                <Download className="w-4 h-4" />
                Install
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
