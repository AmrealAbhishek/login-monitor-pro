'use client';

import { useEffect, useState } from 'react';
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
} from 'lucide-react';

interface AppInfo {
  name: string;
  path?: string;
  source: 'app' | 'brew';
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

  useEffect(() => {
    fetchDevices();
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

  async function installApp() {
    if (!appName && !downloadUrl) return;
    if (selectedDevices.length === 0) return;

    const jobs: InstallJob[] = selectedDevices.map(deviceId => ({
      deviceId,
      deviceName: devices.find(d => d.id === deviceId)?.hostname || 'Unknown',
      status: 'pending',
    }));

    setInstallJobs(jobs);

    // Send install command to each device
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

    // Poll for completion
    pollJobStatus(jobs);
  }

  async function pollJobStatus(jobs: InstallJob[]) {
    const maxPolls = 60; // 5 minutes
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
          // Check command status
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
              job.message = data.result?.message || 'Installed successfully';
            } else if (data.status === 'failed') {
              job.status = 'failed';
              job.message = data.result?.error || 'Installation failed';
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

  async function uninstallApp(deviceId: string, appName: string) {
    await supabase.from('commands').insert({
      device_id: deviceId,
      command: 'uninstall_app',
      args: { app_name: appName },
      status: 'pending',
    });
  }

  async function listApps(deviceId: string) {
    await supabase.from('commands').insert({
      device_id: deviceId,
      command: 'list_apps',
      args: {},
      status: 'pending',
    });
  }

  const isDeviceOnline = (lastSeen: string) => {
    return new Date(lastSeen) > new Date(Date.now() - 5 * 60 * 1000);
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
            App Management
          </h1>
          <p className="text-gray-600 dark:text-[#888] mt-1">
            Install and manage applications across devices
          </p>
        </div>
        <button
          onClick={() => setShowInstallModal(true)}
          disabled={selectedDevices.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors shadow-lg shadow-red-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Download className="w-5 h-5" />
          Install App
        </button>
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

        <div className="divide-y divide-gray-100 dark:divide-[#333] max-h-[400px] overflow-auto">
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
                <div className="flex gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      listApps(device.id);
                    }}
                    className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-500/10 rounded-lg"
                    title="List installed apps"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

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

      {/* Common Apps Quick Install */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333]">
        <div className="p-4 border-b border-gray-200 dark:border-[#333]">
          <h2 className="font-semibold text-gray-900 dark:text-white">Quick Install (Homebrew)</h2>
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
