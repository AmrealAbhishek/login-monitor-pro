'use client';

import { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';
import Link from 'next/link';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || '',
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
);

type Tab = 'usb' | 'clipboard' | 'shadow_it' | 'files' | 'keystrokes' | 'siem';

interface USBEvent {
  id: string;
  device_id: string;
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
  content_type: string;
  content_preview: string;
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

export default function DLPPage() {
  const [activeTab, setActiveTab] = useState<Tab>('usb');
  const [usbEvents, setUsbEvents] = useState<USBEvent[]>([]);
  const [clipboardEvents, setClipboardEvents] = useState<ClipboardEvent[]>([]);
  const [shadowIT, setShadowIT] = useState<ShadowITDetection[]>([]);
  const [fileTransfers, setFileTransfers] = useState<FileTransfer[]>([]);
  const [loading, setLoading] = useState(true);
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
      // Load USB events
      const { data: usb } = await supabase
        .from('usb_events')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100);
      if (usb) setUsbEvents(usb);

      // Load clipboard events
      const { data: clipboard } = await supabase
        .from('clipboard_events')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100);
      if (clipboard) setClipboardEvents(clipboard);

      // Load Shadow IT
      const { data: shadow } = await supabase
        .from('shadow_it_detections')
        .select('*')
        .order('last_detected', { ascending: false })
        .limit(100);
      if (shadow) setShadowIT(shadow);

      // Load file transfers
      const { data: files } = await supabase
        .from('file_transfer_events')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100);
      if (files) setFileTransfers(files);

      // Calculate stats
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
      case 'critical': return 'bg-red-500';
      case 'high': return 'bg-orange-500';
      case 'medium': return 'bg-yellow-500';
      case 'low': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  const tabs = [
    { id: 'usb' as Tab, label: 'USB & Devices', icon: '💾', count: stats.totalUSB },
    { id: 'clipboard' as Tab, label: 'Clipboard', icon: '📋', count: stats.sensitiveClipboard },
    { id: 'shadow_it' as Tab, label: 'Shadow IT', icon: '👤', count: stats.shadowITHigh },
    { id: 'files' as Tab, label: 'File Transfers', icon: '📁', count: stats.sensitiveFiles },
    { id: 'keystrokes' as Tab, label: 'Keystrokes', icon: '⌨️', count: 0 },
    { id: 'siem' as Tab, label: 'SIEM/Webhooks', icon: '🔗', count: 0 },
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/" className="text-gray-400 hover:text-white text-sm mb-2 block">
              ← Back to Dashboard
            </Link>
            <h1 className="text-2xl font-bold">Data Loss Prevention (DLP)</h1>
            <p className="text-gray-400">Monitor and protect sensitive data</p>
          </div>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-3xl font-bold">{stats.totalUSB}</div>
          <div className="text-gray-400 text-sm">USB Events</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-3xl font-bold text-red-400">{stats.blockedUSB}</div>
          <div className="text-gray-400 text-sm">Blocked</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-3xl font-bold text-orange-400">{stats.sensitiveClipboard}</div>
          <div className="text-gray-400 text-sm">Sensitive Clipboard</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-3xl font-bold text-yellow-400">{stats.shadowITHigh}</div>
          <div className="text-gray-400 text-sm">High-Risk Shadow IT</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-3xl font-bold text-purple-400">{stats.sensitiveFiles}</div>
          <div className="text-gray-400 text-sm">Sensitive Transfers</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 mb-6 border-b border-gray-700 pb-4">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
              activeTab === tab.id
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
            {tab.count > 0 && (
              <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin text-4xl mb-4">⏳</div>
          <p className="text-gray-400">Loading DLP data...</p>
        </div>
      ) : (
        <>
          {/* USB Events Tab */}
          {activeTab === 'usb' && (
            <div className="bg-gray-800 rounded-lg overflow-hidden">
              <div className="p-4 border-b border-gray-700">
                <h2 className="font-semibold">USB Device Events</h2>
                <p className="text-gray-400 text-sm">Track USB connections and file transfers</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-900">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm">Time</th>
                      <th className="px-4 py-3 text-left text-sm">Event</th>
                      <th className="px-4 py-3 text-left text-sm">Device</th>
                      <th className="px-4 py-3 text-left text-sm">File</th>
                      <th className="px-4 py-3 text-left text-sm">Size</th>
                      <th className="px-4 py-3 text-left text-sm">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usbEvents.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                          No USB events recorded yet
                        </td>
                      </tr>
                    ) : (
                      usbEvents.map(event => (
                        <tr key={event.id} className="border-t border-gray-700 hover:bg-gray-750">
                          <td className="px-4 py-3 text-sm text-gray-400">
                            {formatTime(event.created_at)}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded text-xs ${
                              event.event_type === 'blocked' ? 'bg-red-500/20 text-red-400' :
                              event.event_type === 'file_copied' ? 'bg-yellow-500/20 text-yellow-400' :
                              'bg-blue-500/20 text-blue-400'
                            }`}>
                              {event.event_type}
                            </span>
                          </td>
                          <td className="px-4 py-3">{event.usb_name || '-'}</td>
                          <td className="px-4 py-3 text-sm">{event.file_name || '-'}</td>
                          <td className="px-4 py-3 text-sm text-gray-400">
                            {event.file_size ? formatBytes(event.file_size) : '-'}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded text-xs ${
                              event.action_taken === 'blocked' ? 'bg-red-500 text-white' :
                              event.action_taken === 'alerted' ? 'bg-orange-500 text-white' :
                              'bg-gray-600 text-gray-300'
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
            <div className="bg-gray-800 rounded-lg overflow-hidden">
              <div className="p-4 border-b border-gray-700">
                <h2 className="font-semibold">Clipboard Monitoring</h2>
                <p className="text-gray-400 text-sm">Track copy/paste of sensitive data</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-900">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm">Time</th>
                      <th className="px-4 py-3 text-left text-sm">Sensitive</th>
                      <th className="px-4 py-3 text-left text-sm">Type</th>
                      <th className="px-4 py-3 text-left text-sm">App</th>
                      <th className="px-4 py-3 text-left text-sm">Length</th>
                      <th className="px-4 py-3 text-left text-sm">Preview</th>
                    </tr>
                  </thead>
                  <tbody>
                    {clipboardEvents.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                          No clipboard events recorded yet
                        </td>
                      </tr>
                    ) : (
                      clipboardEvents.map(event => (
                        <tr key={event.id} className="border-t border-gray-700 hover:bg-gray-750">
                          <td className="px-4 py-3 text-sm text-gray-400">
                            {formatTime(event.created_at)}
                          </td>
                          <td className="px-4 py-3">
                            {event.sensitive_data_detected ? (
                              <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs">
                                {event.sensitive_type || 'Sensitive'}
                              </span>
                            ) : (
                              <span className="text-gray-500">-</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm">{event.content_type}</td>
                          <td className="px-4 py-3 text-sm">{event.destination_app || '-'}</td>
                          <td className="px-4 py-3 text-sm text-gray-400">
                            {event.content_length} chars
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-400 max-w-xs truncate">
                            {event.content_preview?.substring(0, 50) || '-'}
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
            <div className="bg-gray-800 rounded-lg overflow-hidden">
              <div className="p-4 border-b border-gray-700">
                <h2 className="font-semibold">Shadow IT & AI Detection</h2>
                <p className="text-gray-400 text-sm">Unauthorized apps, AI tools, and services</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-900">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm">Last Seen</th>
                      <th className="px-4 py-3 text-left text-sm">Risk</th>
                      <th className="px-4 py-3 text-left text-sm">Category</th>
                      <th className="px-4 py-3 text-left text-sm">App/URL</th>
                      <th className="px-4 py-3 text-left text-sm">Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shadowIT.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                          No Shadow IT detected yet
                        </td>
                      </tr>
                    ) : (
                      shadowIT.map(item => (
                        <tr key={item.id} className="border-t border-gray-700 hover:bg-gray-750">
                          <td className="px-4 py-3 text-sm text-gray-400">
                            {formatTime(item.last_detected)}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded text-xs text-white ${getSeverityColor(item.risk_level)}`}>
                              {item.risk_level?.toUpperCase()}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-1 bg-gray-700 rounded text-xs">
                              {item.app_category?.replace('_', ' ')}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="font-medium">{item.app_name}</div>
                            {item.url_accessed && (
                              <div className="text-xs text-gray-500 truncate max-w-xs">
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
            <div className="bg-gray-800 rounded-lg overflow-hidden">
              <div className="p-4 border-b border-gray-700">
                <h2 className="font-semibold">File Transfer Monitoring</h2>
                <p className="text-gray-400 text-sm">Track uploads, downloads, and file movements</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-900">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm">Time</th>
                      <th className="px-4 py-3 text-left text-sm">Type</th>
                      <th className="px-4 py-3 text-left text-sm">File</th>
                      <th className="px-4 py-3 text-left text-sm">Destination</th>
                      <th className="px-4 py-3 text-left text-sm">Size</th>
                      <th className="px-4 py-3 text-left text-sm">Sensitive</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fileTransfers.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                          No file transfers recorded yet
                        </td>
                      </tr>
                    ) : (
                      fileTransfers.map(transfer => (
                        <tr key={transfer.id} className="border-t border-gray-700 hover:bg-gray-750">
                          <td className="px-4 py-3 text-sm text-gray-400">
                            {formatTime(transfer.created_at)}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded text-xs ${
                              transfer.transfer_type === 'upload' ? 'bg-orange-500/20 text-orange-400' :
                              transfer.transfer_type === 'download' ? 'bg-green-500/20 text-green-400' :
                              'bg-blue-500/20 text-blue-400'
                            }`}>
                              {transfer.transfer_type}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm">{transfer.file_name || '-'}</td>
                          <td className="px-4 py-3 text-sm">
                            <span className="px-2 py-1 bg-gray-700 rounded text-xs">
                              {transfer.destination_type}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-400">
                            {transfer.file_size ? formatBytes(transfer.file_size) : '-'}
                          </td>
                          <td className="px-4 py-3">
                            {transfer.sensitive_detected ? (
                              <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs">
                                Sensitive
                              </span>
                            ) : (
                              <span className="text-gray-500">-</span>
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
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="font-semibold mb-4">Keystroke Monitoring</h2>
              <div className="text-center py-12">
                <div className="text-6xl mb-4">⌨️</div>
                <p className="text-gray-400 mb-4">
                  Keystroke logging captures typing patterns for security investigation.
                </p>
                <p className="text-sm text-gray-500 mb-6">
                  Privacy Mode: Only keystroke counts are logged by default.<br/>
                  Full logging can be enabled for specific devices during investigations.
                </p>
                <div className="bg-gray-700 rounded-lg p-4 max-w-md mx-auto text-left">
                  <p className="text-sm font-mono text-gray-300">
                    Requires: <span className="text-blue-400">pip3 install pynput</span>
                  </p>
                  <p className="text-sm font-mono text-gray-300 mt-2">
                    Permission: <span className="text-yellow-400">Accessibility</span>
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* SIEM Tab */}
          {activeTab === 'siem' && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="font-semibold mb-4">SIEM & Webhook Integrations</h2>
              <p className="text-gray-400 mb-6">
                Export security events to external systems in real-time.
              </p>

              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Splunk */}
                <div className="bg-gray-700 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-green-600 rounded flex items-center justify-center font-bold">
                      S
                    </div>
                    <div>
                      <div className="font-medium">Splunk</div>
                      <div className="text-xs text-gray-400">HTTP Event Collector</div>
                    </div>
                  </div>
                  <p className="text-sm text-gray-400 mb-3">
                    Send events to Splunk HEC endpoint
                  </p>
                  <button className="w-full py-2 bg-gray-600 hover:bg-gray-500 rounded text-sm">
                    Configure
                  </button>
                </div>

                {/* Microsoft Sentinel */}
                <div className="bg-gray-700 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-blue-600 rounded flex items-center justify-center font-bold">
                      MS
                    </div>
                    <div>
                      <div className="font-medium">Microsoft Sentinel</div>
                      <div className="text-xs text-gray-400">Log Analytics</div>
                    </div>
                  </div>
                  <p className="text-sm text-gray-400 mb-3">
                    Export to Azure Log Analytics workspace
                  </p>
                  <button className="w-full py-2 bg-gray-600 hover:bg-gray-500 rounded text-sm">
                    Configure
                  </button>
                </div>

                {/* Elastic */}
                <div className="bg-gray-700 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-yellow-500 rounded flex items-center justify-center font-bold text-black">
                      E
                    </div>
                    <div>
                      <div className="font-medium">Elasticsearch</div>
                      <div className="text-xs text-gray-400">Index events</div>
                    </div>
                  </div>
                  <p className="text-sm text-gray-400 mb-3">
                    Send events to Elasticsearch cluster
                  </p>
                  <button className="w-full py-2 bg-gray-600 hover:bg-gray-500 rounded text-sm">
                    Configure
                  </button>
                </div>

                {/* Slack */}
                <div className="bg-gray-700 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-purple-600 rounded flex items-center justify-center text-xl">
                      #
                    </div>
                    <div>
                      <div className="font-medium">Slack</div>
                      <div className="text-xs text-gray-400">Webhook</div>
                    </div>
                  </div>
                  <p className="text-sm text-gray-400 mb-3">
                    Post alerts to Slack channel
                  </p>
                  <button className="w-full py-2 bg-gray-600 hover:bg-gray-500 rounded text-sm">
                    Configure
                  </button>
                </div>

                {/* Teams */}
                <div className="bg-gray-700 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-indigo-600 rounded flex items-center justify-center font-bold">
                      T
                    </div>
                    <div>
                      <div className="font-medium">Microsoft Teams</div>
                      <div className="text-xs text-gray-400">Incoming Webhook</div>
                    </div>
                  </div>
                  <p className="text-sm text-gray-400 mb-3">
                    Post alerts to Teams channel
                  </p>
                  <button className="w-full py-2 bg-gray-600 hover:bg-gray-500 rounded text-sm">
                    Configure
                  </button>
                </div>

                {/* Custom Webhook */}
                <div className="bg-gray-700 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-gray-500 rounded flex items-center justify-center text-xl">
                      🔗
                    </div>
                    <div>
                      <div className="font-medium">Custom Webhook</div>
                      <div className="text-xs text-gray-400">HTTP POST</div>
                    </div>
                  </div>
                  <p className="text-sm text-gray-400 mb-3">
                    Send JSON events to any endpoint
                  </p>
                  <button className="w-full py-2 bg-gray-600 hover:bg-gray-500 rounded text-sm">
                    Configure
                  </button>
                </div>
              </div>

              <div className="mt-6 p-4 bg-gray-700 rounded-lg">
                <h3 className="font-medium mb-2">Configuration</h3>
                <p className="text-sm text-gray-400">
                  Add integrations to your <code className="bg-gray-800 px-2 py-1 rounded">config.json</code>:
                </p>
                <pre className="mt-3 bg-gray-900 p-4 rounded text-sm overflow-x-auto">
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
        </>
      )}
    </div>
  );
}
