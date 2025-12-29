'use client';

import { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';
import Link from 'next/link';
import { useTheme } from '@/contexts/ThemeContext';
import {
  Usb, Clipboard, UserX, FolderSync, Keyboard, Link2,
  RefreshCw, AlertTriangle, ShieldAlert, Eye, Copy, X,
  HardDrive, FileWarning, Search, Download, Upload, Clock,
  User, Monitor, ArrowLeft, Loader2, Square, Activity
} from 'lucide-react';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || '',
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
);

type Tab = 'usb' | 'clipboard' | 'shadow_it' | 'files' | 'keystrokes' | 'siem';

interface USBEvent {
  id: string;
  device_id: string;
  hostname?: string;
  username?: string;
  event_type: string;
  usb_name: string;
  usb_vendor: string;
  usb_type: string;
  file_name: string;
  file_size: number;
  action_taken: string;
  created_at: string;
}

interface ClipboardEvent {
  id: string;
  device_id: string;
  hostname?: string;
  username?: string;
  content_type: string;
  content_preview: string;
  content_forensic?: string;
  content_length: number;
  source_app: string;
  destination_app: string;
  sensitive_data_detected: boolean;
  sensitive_type: string;
  created_at: string;
}

interface ShadowITDetection {
  id: string;
  device_id: string;
  hostname?: string;
  username?: string;
  app_name: string;
  app_category: string;
  url_accessed: string;
  risk_level: string;
  detection_count: number;
  last_detected: string;
}

interface FileTransfer {
  id: string;
  device_id: string;
  transfer_type: string;
  source_path: string;
  destination: string;
  destination_type: string;
  file_name: string;
  file_size: number;
  sensitive_detected: boolean;
  created_at: string;
}

interface KeystrokeLog {
  id: string;
  device_id: string;
  hostname?: string;
  username?: string;
  app_name: string;
  window_title?: string;
  keystroke_count: number;
  keystrokes?: string;
  start_time: string;
  end_time: string;
}

interface Device {
  id: string;
  hostname: string;
  is_active: boolean;
  last_seen: string;
}

export default function DLPPage() {
  const { theme } = useTheme();
  const [activeTab, setActiveTab] = useState<Tab>('usb');
  const [usbEvents, setUsbEvents] = useState<USBEvent[]>([]);
  const [clipboardEvents, setClipboardEvents] = useState<ClipboardEvent[]>([]);
  const [shadowIT, setShadowIT] = useState<ShadowITDetection[]>([]);
  const [fileTransfers, setFileTransfers] = useState<FileTransfer[]>([]);
  const [keystrokeLogs, setKeystrokeLogs] = useState<KeystrokeLog[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [keystrokeCommand, setKeystrokeCommand] = useState({ deviceId: '', duration: 5, fullLog: false, sending: false });
  const [activeKeystrokeSessions, setActiveKeystrokeSessions] = useState<{[deviceId: string]: boolean}>({});
  const [forensicModal, setForensicModal] = useState<{ isOpen: boolean; content: string; type: string; user?: string }>({
    isOpen: false,
    content: '',
    type: '',
    user: ''
  });
  const [stats, setStats] = useState({
    totalUSB: 0,
    blockedUSB: 0,
    sensitiveClipboard: 0,
    shadowITHigh: 0,
    sensitiveFiles: 0
  });

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const { data: usb } = await supabase
        .from('usb_events')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100);
      if (usb) setUsbEvents(usb);

      const { data: clipboard } = await supabase
        .from('clipboard_events')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100);
      if (clipboard) setClipboardEvents(clipboard);

      const { data: shadow } = await supabase
        .from('shadow_it_detections')
        .select('*')
        .order('last_detected', { ascending: false })
        .limit(100);
      if (shadow) setShadowIT(shadow);

      const { data: files } = await supabase
        .from('file_transfer_events')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100);
      if (files) setFileTransfers(files);

      const { data: keystrokes } = await supabase
        .from('keystroke_logs')
        .select('*')
        .order('start_time', { ascending: false })
        .limit(100);
      if (keystrokes) setKeystrokeLogs(keystrokes);

      const { data: deviceList } = await supabase
        .from('devices')
        .select('id, hostname, is_active, last_seen')
        .eq('is_active', true)
        .order('last_seen', { ascending: false });
      if (deviceList) setDevices(deviceList);

      setStats({
        totalUSB: usb?.length || 0,
        blockedUSB: usb?.filter(e => e.action_taken === 'blocked').length || 0,
        sensitiveClipboard: clipboard?.filter(e => e.sensitive_data_detected).length || 0,
        shadowITHigh: shadow?.filter(e => e.risk_level === 'high' || e.risk_level === 'critical').length || 0,
        sensitiveFiles: files?.filter(e => e.sensitive_detected).length || 0
      });
    } catch (error) {
      console.error('Error loading DLP data:', error);
    }
    setLoading(false);
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getSeverityColor = (level: string) => {
    switch (level) {
      case 'critical':
        return 'bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-500/50';
      case 'high':
        return 'bg-orange-100 dark:bg-orange-500/20 text-orange-700 dark:text-orange-400 border-orange-200 dark:border-orange-500/50';
      case 'medium':
        return 'bg-yellow-100 dark:bg-yellow-500/20 text-yellow-700 dark:text-yellow-400 border-yellow-200 dark:border-yellow-500/50';
      case 'low':
        return 'bg-green-100 dark:bg-green-500/20 text-green-700 dark:text-green-400 border-green-200 dark:border-green-500/50';
      default:
        return 'bg-gray-100 dark:bg-gray-500/20 text-gray-700 dark:text-gray-400 border-gray-200 dark:border-gray-500/50';
    }
  };

  const decodeForensic = (base64: string): string => {
    try {
      return atob(base64);
    } catch {
      return '[Unable to decode]';
    }
  };

  const handleRevealContent = (event: ClipboardEvent) => {
    if (event.content_forensic) {
      setForensicModal({
        isOpen: true,
        content: decodeForensic(event.content_forensic),
        type: event.sensitive_type || 'Sensitive Data',
        user: event.username || event.hostname || 'Unknown'
      });
    }
  };

  // Check for active keystroke sessions
  const checkActiveKeystrokeSessions = async () => {
    try {
      const { data } = await supabase
        .from('commands')
        .select('device_id')
        .eq('command', 'keystroke')
        .in('status', ['pending', 'processing']);

      if (data) {
        const activeSessions: {[key: string]: boolean} = {};
        data.forEach(cmd => {
          activeSessions[cmd.device_id] = true;
        });
        setActiveKeystrokeSessions(activeSessions);
      }
    } catch (error) {
      console.error('Error checking active sessions:', error);
    }
  };

  // Load active sessions on tab change
  useEffect(() => {
    if (activeTab === 'keystrokes') {
      checkActiveKeystrokeSessions();
    }
  }, [activeTab]);

  const sendKeystrokeCommand = async () => {
    if (!keystrokeCommand.deviceId) return;

    // Check if already running
    if (activeKeystrokeSessions[keystrokeCommand.deviceId]) {
      alert('Keystroke logging is already active on this device. Stop it first.');
      return;
    }

    setKeystrokeCommand(prev => ({ ...prev, sending: true }));
    try {
      const { error } = await supabase
        .from('commands')
        .insert({
          device_id: keystrokeCommand.deviceId,
          command: 'keystroke',
          args: {
            duration: keystrokeCommand.duration,
            full_log: keystrokeCommand.fullLog
          },
          status: 'pending'
        });

      if (error) throw error;

      // Mark as active
      setActiveKeystrokeSessions(prev => ({ ...prev, [keystrokeCommand.deviceId]: true }));
      alert(`Keystroke logging started for ${keystrokeCommand.duration} minutes!`);
    } catch (error) {
      console.error('Error sending keystroke command:', error);
      alert('Failed to send command');
    }
    setKeystrokeCommand(prev => ({ ...prev, sending: false }));
  };

  const stopKeystrokeCommand = async (deviceId: string) => {
    try {
      const { error } = await supabase
        .from('commands')
        .insert({
          device_id: deviceId,
          command: 'keystroke_stop',
          args: {},
          status: 'pending'
        });

      if (error) throw error;

      // Remove from active sessions
      setActiveKeystrokeSessions(prev => {
        const newSessions = { ...prev };
        delete newSessions[deviceId];
        return newSessions;
      });
      alert('Stop command sent!');
    } catch (error) {
      console.error('Error sending stop command:', error);
      alert('Failed to send stop command');
    }
  };

  const tabs = [
    { id: 'usb' as Tab, label: 'USB & Devices', icon: Usb, count: stats.totalUSB },
    { id: 'clipboard' as Tab, label: 'Clipboard', icon: Clipboard, count: stats.sensitiveClipboard },
    { id: 'shadow_it' as Tab, label: 'Shadow IT', icon: UserX, count: stats.shadowITHigh },
    { id: 'files' as Tab, label: 'File Transfers', icon: FolderSync, count: stats.sensitiveFiles },
    { id: 'keystrokes' as Tab, label: 'Keystrokes', icon: Keyboard, count: 0 },
    { id: 'siem' as Tab, label: 'SIEM/Webhooks', icon: Link2, count: 0 },
  ];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-[#0a0a0a]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-600 dark:text-blue-400 mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading DLP data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#0a0a0a] text-gray-900 dark:text-white p-6 transition-colors">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/" className="text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white text-sm mb-2 flex items-center gap-1">
              <ArrowLeft className="w-4 h-4" />
              Back to Dashboard
            </Link>
            <h1 className="text-2xl font-bold">Data Loss Prevention (DLP)</h1>
            <p className="text-gray-500 dark:text-gray-400">Monitor and protect sensitive data</p>
          </div>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div className="bg-white dark:bg-[#111] rounded-xl p-4 border border-gray-200 dark:border-[#222]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-500/20 rounded-lg">
              <HardDrive className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <div className="text-2xl font-bold">{stats.totalUSB}</div>
              <div className="text-gray-500 dark:text-gray-400 text-sm">USB Events</div>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-[#111] rounded-xl p-4 border border-gray-200 dark:border-[#222]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 dark:bg-red-500/20 rounded-lg">
              <ShieldAlert className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-red-600 dark:text-red-400">{stats.blockedUSB}</div>
              <div className="text-gray-500 dark:text-gray-400 text-sm">Blocked</div>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-[#111] rounded-xl p-4 border border-gray-200 dark:border-[#222]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 dark:bg-orange-500/20 rounded-lg">
              <Clipboard className="w-5 h-5 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">{stats.sensitiveClipboard}</div>
              <div className="text-gray-500 dark:text-gray-400 text-sm">Sensitive Clipboard</div>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-[#111] rounded-xl p-4 border border-gray-200 dark:border-[#222]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-100 dark:bg-yellow-500/20 rounded-lg">
              <UserX className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{stats.shadowITHigh}</div>
              <div className="text-gray-500 dark:text-gray-400 text-sm">High-Risk Shadow IT</div>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-[#111] rounded-xl p-4 border border-gray-200 dark:border-[#222]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-500/20 rounded-lg">
              <FileWarning className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{stats.sensitiveFiles}</div>
              <div className="text-gray-500 dark:text-gray-400 text-sm">Sensitive Transfers</div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 mb-6 border-b border-gray-200 dark:border-[#222] pb-4">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-white dark:bg-[#111] text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-[#1a1a1a] border border-gray-200 dark:border-[#222]'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
              {tab.count > 0 && (
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  activeTab === tab.id
                    ? 'bg-white/20 text-white'
                    : 'bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400'
                }`}>
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {/* USB Events Tab */}
      {activeTab === 'usb' && (
        <div className="bg-white dark:bg-[#111] rounded-xl overflow-hidden border border-gray-200 dark:border-[#222]">
          <div className="p-4 border-b border-gray-200 dark:border-[#222]">
            <h2 className="font-semibold flex items-center gap-2">
              <Usb className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              USB Device Events
            </h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm">Track USB connections and file transfers</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-[#0a0a0a]">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Time</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">User</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Event</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Device</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">File</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Size</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Action</th>
                </tr>
              </thead>
              <tbody>
                {usbEvents.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                      No USB events recorded yet
                    </td>
                  </tr>
                ) : (
                  usbEvents.map(event => (
                    <tr key={event.id} className="border-t border-gray-100 dark:border-[#1a1a1a] hover:bg-gray-50 dark:hover:bg-[#0a0a0a]">
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatTime(event.created_at)}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <div className="flex flex-col">
                          <span className="font-medium">{event.username || '-'}</span>
                          <span className="text-xs text-gray-400">{event.hostname || ''}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded text-xs border ${
                          event.event_type === 'blocked' ? 'bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-500/50' :
                          event.event_type === 'file_copied' ? 'bg-yellow-100 dark:bg-yellow-500/20 text-yellow-700 dark:text-yellow-400 border-yellow-200 dark:border-yellow-500/50' :
                          'bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-500/50'
                        }`}>
                          {event.event_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-medium">{event.usb_name || '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{event.file_name || '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                        {event.file_size ? formatBytes(event.file_size) : '-'}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded text-xs ${
                          event.action_taken === 'blocked' ? 'bg-red-600 text-white' :
                          event.action_taken === 'alerted' ? 'bg-orange-600 text-white' :
                          'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                        }`}>
                          {event.action_taken}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Clipboard Tab */}
      {activeTab === 'clipboard' && (
        <div className="bg-white dark:bg-[#111] rounded-xl overflow-hidden border border-gray-200 dark:border-[#222]">
          <div className="p-4 border-b border-gray-200 dark:border-[#222]">
            <h2 className="font-semibold flex items-center gap-2">
              <Clipboard className="w-5 h-5 text-orange-600 dark:text-orange-400" />
              Clipboard Monitoring
            </h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm">Track copy/paste of sensitive data</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-[#0a0a0a]">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Time</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">User</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Sensitive</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">App</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Length</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Preview</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody>
                {clipboardEvents.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                      No clipboard events recorded yet
                    </td>
                  </tr>
                ) : (
                  clipboardEvents.map(event => (
                    <tr key={event.id} className="border-t border-gray-100 dark:border-[#1a1a1a] hover:bg-gray-50 dark:hover:bg-[#0a0a0a]">
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatTime(event.created_at)}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <div className="flex flex-col">
                          <span className="font-medium flex items-center gap-1">
                            <User className="w-3 h-3" />
                            {event.username || '-'}
                          </span>
                          <span className="text-xs text-gray-400 flex items-center gap-1">
                            <Monitor className="w-3 h-3" />
                            {event.hostname || ''}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {event.sensitive_data_detected ? (
                          <span className="px-2 py-1 bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400 rounded text-xs border border-red-200 dark:border-red-500/50 flex items-center gap-1 w-fit">
                            <AlertTriangle className="w-3 h-3" />
                            {event.sensitive_type || 'Sensitive'}
                          </span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm">{event.destination_app || '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                        {event.content_length} chars
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 max-w-xs truncate">
                        {event.content_preview?.substring(0, 50) || '-'}
                      </td>
                      <td className="px-4 py-3">
                        {event.sensitive_data_detected && event.content_forensic ? (
                          <button
                            onClick={() => handleRevealContent(event)}
                            className="px-2 py-1 bg-yellow-600 hover:bg-yellow-500 text-white rounded text-xs flex items-center gap-1"
                            title="Reveal content for forensic investigation"
                          >
                            <Eye className="w-3 h-3" />
                            Reveal
                          </button>
                        ) : (
                          <span className="text-gray-400 text-xs">-</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Shadow IT Tab */}
      {activeTab === 'shadow_it' && (
        <div className="bg-white dark:bg-[#111] rounded-xl overflow-hidden border border-gray-200 dark:border-[#222]">
          <div className="p-4 border-b border-gray-200 dark:border-[#222]">
            <h2 className="font-semibold flex items-center gap-2">
              <UserX className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
              Shadow IT & AI Detection
            </h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm">Unauthorized apps, AI tools, and services</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-[#0a0a0a]">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Last Seen</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">User</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Risk</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Category</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">App/URL</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Count</th>
                </tr>
              </thead>
              <tbody>
                {shadowIT.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                      No Shadow IT detected yet
                    </td>
                  </tr>
                ) : (
                  shadowIT.map(item => (
                    <tr key={item.id} className="border-t border-gray-100 dark:border-[#1a1a1a] hover:bg-gray-50 dark:hover:bg-[#0a0a0a]">
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatTime(item.last_detected)}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <div className="flex flex-col">
                          <span className="font-medium">{item.username || '-'}</span>
                          <span className="text-xs text-gray-400">{item.hostname || ''}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded text-xs border ${getSeverityColor(item.risk_level)}`}>
                          {item.risk_level?.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                          {item.app_category?.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-medium">{item.app_name}</div>
                        {item.url_accessed && (
                          <div className="text-xs text-gray-400 truncate max-w-xs">
                            {item.url_accessed}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm">{item.detection_count}x</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* File Transfers Tab */}
      {activeTab === 'files' && (
        <div className="bg-white dark:bg-[#111] rounded-xl overflow-hidden border border-gray-200 dark:border-[#222]">
          <div className="p-4 border-b border-gray-200 dark:border-[#222]">
            <h2 className="font-semibold flex items-center gap-2">
              <FolderSync className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              File Transfer Monitoring
            </h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm">Track uploads, downloads, and file movements</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-[#0a0a0a]">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Time</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Type</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">File</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Destination</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Size</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Sensitive</th>
                </tr>
              </thead>
              <tbody>
                {fileTransfers.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                      No file transfers recorded yet
                    </td>
                  </tr>
                ) : (
                  fileTransfers.map(transfer => (
                    <tr key={transfer.id} className="border-t border-gray-100 dark:border-[#1a1a1a] hover:bg-gray-50 dark:hover:bg-[#0a0a0a]">
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                        {formatTime(transfer.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded text-xs border flex items-center gap-1 w-fit ${
                          transfer.transfer_type === 'upload' ? 'bg-orange-100 dark:bg-orange-500/20 text-orange-700 dark:text-orange-400 border-orange-200 dark:border-orange-500/50' :
                          transfer.transfer_type === 'download' ? 'bg-green-100 dark:bg-green-500/20 text-green-700 dark:text-green-400 border-green-200 dark:border-green-500/50' :
                          'bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-500/50'
                        }`}>
                          {transfer.transfer_type === 'upload' ? <Upload className="w-3 h-3" /> : <Download className="w-3 h-3" />}
                          {transfer.transfer_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">{transfer.file_name || '-'}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                          {transfer.destination_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                        {transfer.file_size ? formatBytes(transfer.file_size) : '-'}
                      </td>
                      <td className="px-4 py-3">
                        {transfer.sensitive_detected ? (
                          <span className="px-2 py-1 bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400 rounded text-xs border border-red-200 dark:border-red-500/50 flex items-center gap-1 w-fit">
                            <AlertTriangle className="w-3 h-3" />
                            Sensitive
                          </span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Keystrokes Tab */}
      {activeTab === 'keystrokes' && (
        <div className="space-y-6">
          {/* Quick Command Card */}
          <div className="bg-white dark:bg-[#111] rounded-xl p-6 border border-gray-200 dark:border-[#222]">
            <h2 className="font-semibold mb-4 flex items-center gap-2">
              <Keyboard className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              Start Keystroke Logging
            </h2>
            <div className="grid md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm text-gray-500 dark:text-gray-400 mb-1">Device</label>
                <select
                  value={keystrokeCommand.deviceId}
                  onChange={(e) => setKeystrokeCommand(prev => ({ ...prev, deviceId: e.target.value }))}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-[#0a0a0a] border border-gray-200 dark:border-[#222] rounded-lg text-sm"
                >
                  <option value="">Select device...</option>
                  {devices.map(d => {
                    const lastSeen = new Date(d.last_seen);
                    const minutesAgo = Math.floor((Date.now() - lastSeen.getTime()) / 60000);
                    const isOnline = minutesAgo < 5;
                    const isCapturing = activeKeystrokeSessions[d.id];
                    return (
                      <option key={d.id} value={d.id}>
                        {isCapturing ? '[CAPTURING] ' : isOnline ? '[Online] ' : `[${minutesAgo}m ago] `}{d.hostname}
                      </option>
                    );
                  })}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-500 dark:text-gray-400 mb-1">Duration (minutes)</label>
                <select
                  value={keystrokeCommand.duration}
                  onChange={(e) => setKeystrokeCommand(prev => ({ ...prev, duration: parseInt(e.target.value) }))}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-[#0a0a0a] border border-gray-200 dark:border-[#222] rounded-lg text-sm"
                >
                  <option value={1}>1 min</option>
                  <option value={5}>5 mins</option>
                  <option value={10}>10 mins</option>
                  <option value={15}>15 mins</option>
                  <option value={30}>30 mins</option>
                  <option value={60}>60 mins</option>
                </select>
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={keystrokeCommand.fullLog}
                    onChange={(e) => setKeystrokeCommand(prev => ({ ...prev, fullLog: e.target.checked }))}
                    className="w-4 h-4 rounded border-gray-300 dark:border-gray-600"
                  />
                  <span className="text-sm">Full logging (investigation mode)</span>
                </label>
              </div>
              <div className="flex items-end gap-2">
                {keystrokeCommand.deviceId && activeKeystrokeSessions[keystrokeCommand.deviceId] ? (
                  <button
                    onClick={() => stopKeystrokeCommand(keystrokeCommand.deviceId)}
                    className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg flex items-center justify-center gap-2 transition-colors"
                  >
                    <Square className="w-4 h-4" />
                    Stop Logging
                  </button>
                ) : (
                  <button
                    onClick={sendKeystrokeCommand}
                    disabled={!keystrokeCommand.deviceId || keystrokeCommand.sending}
                    className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg flex items-center justify-center gap-2 transition-colors"
                  >
                    {keystrokeCommand.sending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Keyboard className="w-4 h-4" />
                    )}
                    Start Logging
                  </button>
                )}
              </div>
            </div>
            {keystrokeCommand.fullLog && (
              <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg">
                <p className="text-sm text-yellow-700 dark:text-yellow-400 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Full logging enabled: All keystrokes will be captured. Use only for investigations.
                </p>
              </div>
            )}
          </div>

          {/* Keystroke Logs Table */}
          <div className="bg-white dark:bg-[#111] rounded-xl overflow-hidden border border-gray-200 dark:border-[#222]">
            <div className="p-4 border-b border-gray-200 dark:border-[#222]">
              <h2 className="font-semibold flex items-center gap-2">
                <Keyboard className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                Keystroke Logs
              </h2>
              <p className="text-gray-500 dark:text-gray-400 text-sm">Recent keystroke sessions by application</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-[#0a0a0a]">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Time</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">User</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Application</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Keystrokes</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Content</th>
                  </tr>
                </thead>
                <tbody>
                  {keystrokeLogs.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                        No keystroke logs recorded yet. Use the form above to start logging.
                      </td>
                    </tr>
                  ) : (
                    keystrokeLogs.map(log => (
                      <tr key={log.id} className="border-t border-gray-100 dark:border-[#1a1a1a] hover:bg-gray-50 dark:hover:bg-[#0a0a0a]">
                        <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {formatTime(log.start_time)}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <div className="flex flex-col">
                            <span className="font-medium">{log.username || '-'}</span>
                            <span className="text-xs text-gray-400">{log.hostname || ''}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="font-medium">{log.app_name || '-'}</div>
                          {log.window_title && (
                            <div className="text-xs text-gray-400 truncate max-w-xs">{log.window_title}</div>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-1 bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 rounded text-sm font-mono">
                            {log.keystroke_count}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {log.keystrokes ? (
                            <button
                              onClick={() => setForensicModal({
                                isOpen: true,
                                content: log.keystrokes || '',
                                type: 'Keystroke Log',
                                user: log.username || log.hostname || 'Unknown'
                              })}
                              className="px-2 py-1 bg-yellow-600 hover:bg-yellow-500 text-white rounded text-xs flex items-center gap-1"
                            >
                              <Eye className="w-3 h-3" />
                              View
                            </button>
                          ) : (
                            <span className="text-gray-400 text-xs">Count only</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Requirements Note */}
          <div className="bg-gray-50 dark:bg-[#0a0a0a] rounded-lg p-4 border border-gray-200 dark:border-[#222]">
            <h3 className="font-medium mb-2 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-yellow-600" />
              Requirements
            </h3>
            <div className="grid md:grid-cols-2 gap-4 text-sm text-gray-600 dark:text-gray-300">
              <div>
                <span className="text-gray-500">Install:</span>{' '}
                <code className="bg-gray-200 dark:bg-gray-800 px-2 py-1 rounded">pip3 install pynput</code>
              </div>
              <div>
                <span className="text-gray-500">Permission:</span>{' '}
                <span className="text-yellow-600 dark:text-yellow-400">System Settings &gt; Privacy &gt; Accessibility</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SIEM Tab */}
      {activeTab === 'siem' && (
        <div className="bg-white dark:bg-[#111] rounded-xl p-6 border border-gray-200 dark:border-[#222]">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Link2 className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            SIEM & Webhook Integrations
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mb-6">
            Export security events to external systems in real-time.
          </p>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { name: 'Splunk', sub: 'HTTP Event Collector', color: 'bg-green-600', letter: 'S' },
              { name: 'Microsoft Sentinel', sub: 'Log Analytics', color: 'bg-blue-600', letter: 'MS' },
              { name: 'Elasticsearch', sub: 'Index events', color: 'bg-yellow-500 text-black', letter: 'E' },
              { name: 'Slack', sub: 'Webhook', color: 'bg-purple-600', letter: '#' },
              { name: 'Microsoft Teams', sub: 'Incoming Webhook', color: 'bg-indigo-600', letter: 'T' },
              { name: 'Custom Webhook', sub: 'HTTP POST', color: 'bg-gray-500', letter: '' },
            ].map((item, i) => (
              <div key={i} className="bg-gray-50 dark:bg-[#0a0a0a] rounded-lg p-4 border border-gray-200 dark:border-[#222]">
                <div className="flex items-center gap-3 mb-3">
                  <div className={`w-10 h-10 ${item.color} rounded flex items-center justify-center font-bold text-white`}>
                    {item.letter || <Link2 className="w-5 h-5" />}
                  </div>
                  <div>
                    <div className="font-medium">{item.name}</div>
                    <div className="text-xs text-gray-400">{item.sub}</div>
                  </div>
                </div>
                <button className="w-full py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded text-sm transition-colors">
                  Configure
                </button>
              </div>
            ))}
          </div>

          <div className="mt-6 p-4 bg-gray-50 dark:bg-[#0a0a0a] rounded-lg border border-gray-200 dark:border-[#222]">
            <h3 className="font-medium mb-2">Configuration</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Add integrations to your <code className="bg-gray-200 dark:bg-gray-800 px-2 py-1 rounded">config.json</code>:
            </p>
            <pre className="mt-3 bg-gray-900 text-gray-100 p-4 rounded text-sm overflow-x-auto">
{`"siem_integrations": [
  {
    "integration_type": "slack",
    "name": "Security Alerts",
    "endpoint_url": "https://hooks.slack.com/services/...",
    "enabled": true
  }
]`}
            </pre>
          </div>
        </div>
      )}

      {/* Forensic Reveal Modal */}
      {forensicModal.isOpen && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-[#111] rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden border border-gray-200 dark:border-[#222]">
            <div className="p-4 border-b border-gray-200 dark:border-[#222] flex justify-between items-center">
              <div>
                <h3 className="font-bold text-lg text-red-600 dark:text-red-400 flex items-center gap-2">
                  <Search className="w-5 h-5" />
                  Forensic Content Reveal
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Sensitive data copied by: <span className="text-gray-900 dark:text-white font-medium">{forensicModal.user}</span>
                </p>
              </div>
              <button
                onClick={() => setForensicModal({ ...forensicModal, isOpen: false })}
                className="text-gray-400 hover:text-gray-900 dark:hover:text-white p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 border-b border-gray-200 dark:border-[#222] bg-red-50 dark:bg-red-900/20">
              <div className="flex items-center gap-2 text-red-600 dark:text-red-400 mb-2">
                <AlertTriangle className="w-5 h-5" />
                <span className="font-semibold">WARNING: Sensitive Data</span>
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                This content contains <span className="font-bold text-red-600 dark:text-red-300">{forensicModal.type}</span>.
                This information is being revealed for forensic investigation purposes only.
                Access to this data is logged for audit compliance.
              </p>
            </div>
            <div className="p-4 overflow-auto max-h-[50vh]">
              <pre className="bg-gray-100 dark:bg-[#0a0a0a] p-4 rounded text-sm whitespace-pre-wrap break-all font-mono text-yellow-700 dark:text-yellow-200 border border-gray-200 dark:border-[#222]">
                {forensicModal.content}
              </pre>
            </div>
            <div className="p-4 border-t border-gray-200 dark:border-[#222] flex justify-end gap-3">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(forensicModal.content);
                }}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-lg text-sm flex items-center gap-2 transition-colors"
              >
                <Copy className="w-4 h-4" />
                Copy to Clipboard
              </button>
              <button
                onClick={() => setForensicModal({ ...forensicModal, isOpen: false })}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
