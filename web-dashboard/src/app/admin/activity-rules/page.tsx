'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import {
  Activity,
  Plus,
  Trash2,
  Edit2,
  Save,
  X,
  AlertTriangle,
  Camera,
  Clock,
  HardDrive,
  Wifi,
  Monitor,
  Upload,
  Lock,
  Printer,
  Mail,
} from 'lucide-react';

interface ActivityRule {
  id: string;
  name: string;
  description: string | null;
  rule_type: string;
  config: Record<string, unknown>;
  severity: 'low' | 'medium' | 'high' | 'critical';
  action: 'alert' | 'alert_screenshot' | 'lock' | 'notify_admin';
  auto_screenshot: boolean;
  notify_immediately: boolean;
  enabled: boolean;
  created_at: string;
}

const ruleTypes = [
  { value: 'unusual_time', label: 'Unusual Time Access', icon: Clock, description: 'Activity outside work hours', configFields: ['start_hour', 'end_hour', 'weekends'] },
  { value: 'high_file_activity', label: 'High File Activity', icon: Activity, description: 'Mass file operations detected', configFields: ['threshold', 'window_minutes'] },
  { value: 'sensitive_app_launch', label: 'Sensitive App Launch', icon: Monitor, description: 'Remote desktop, FTP apps', configFields: ['apps'] },
  { value: 'usb_activity', label: 'USB Activity', icon: HardDrive, description: 'External storage connected', configFields: ['alert_on_connect', 'alert_on_file_copy'] },
  { value: 'large_data_transfer', label: 'Large Data Transfer', icon: Upload, description: 'Bulk upload/download', configFields: ['threshold_mb', 'window_minutes'] },
  { value: 'repeated_failed_access', label: 'Failed Access Attempts', icon: Lock, description: 'Multiple failed file accesses', configFields: ['threshold', 'window_minutes'] },
  { value: 'screen_capture_tool', label: 'Screen Capture Tool', icon: Camera, description: 'Recording software detected', configFields: ['apps'] },
  { value: 'vpn_connection', label: 'VPN Connection', icon: Wifi, description: 'VPN or proxy detected', configFields: [] },
  { value: 'printer_activity', label: 'Printer Activity', icon: Printer, description: 'Printing sensitive docs', configFields: [] },
  { value: 'email_attachment', label: 'Email Attachment', icon: Mail, description: 'External attachments', configFields: ['threshold_mb'] },
];

const severityOptions = [
  { value: 'low', label: 'Low', color: 'bg-blue-500', textColor: 'text-blue-500', bgLight: 'bg-blue-100' },
  { value: 'medium', label: 'Medium', color: 'bg-yellow-500', textColor: 'text-yellow-500', bgLight: 'bg-yellow-100' },
  { value: 'high', label: 'High', color: 'bg-orange-500', textColor: 'text-orange-500', bgLight: 'bg-orange-100' },
  { value: 'critical', label: 'Critical', color: 'bg-red-500', textColor: 'text-red-500', bgLight: 'bg-red-100' },
];

const actionOptions = [
  { value: 'alert', label: 'Alert Only', icon: AlertTriangle, description: 'Send alert notification' },
  { value: 'alert_screenshot', label: 'Alert + Screenshot', icon: Camera, description: 'Alert and capture screen' },
  { value: 'lock', label: 'Lock Device', icon: Lock, description: 'Immediately lock the device' },
  { value: 'notify_admin', label: 'Notify Admin', icon: Mail, description: 'Email admin immediately' },
];

const defaultConfigs: Record<string, Record<string, unknown>> = {
  unusual_time: { start_hour: 0, end_hour: 6, weekends: false },
  high_file_activity: { threshold: 50, window_minutes: 5 },
  sensitive_app_launch: { apps: ['TeamViewer', 'AnyDesk', 'VNC Viewer', 'Remote Desktop'] },
  usb_activity: { alert_on_connect: true, alert_on_file_copy: true },
  large_data_transfer: { threshold_mb: 100, window_minutes: 10 },
  repeated_failed_access: { threshold: 5, window_minutes: 5 },
  screen_capture_tool: { apps: ['OBS', 'QuickTime Player', 'Loom', 'ScreenFlow'] },
  vpn_connection: {},
  printer_activity: {},
  email_attachment: { threshold_mb: 10 },
};

export default function ActivityRulesPage() {
  const [rules, setRules] = useState<ActivityRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingRule, setEditingRule] = useState<ActivityRule | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    rule_type: 'unusual_time',
    config: defaultConfigs.unusual_time as Record<string, unknown>,
    severity: 'high' as ActivityRule['severity'],
    action: 'alert_screenshot' as ActivityRule['action'],
    auto_screenshot: true,
    notify_immediately: true,
    enabled: true,
  });

  useEffect(() => {
    fetchRules();
  }, []);

  async function fetchRules() {
    const { data, error } = await supabase
      .from('suspicious_activity_rules')
      .select('*')
      .order('severity', { ascending: false })
      .order('created_at', { ascending: false });

    if (data) setRules(data);
    if (error) console.error('Error fetching rules:', error);
    setLoading(false);
  }

  async function saveRule() {
    if (!formData.name) return;

    const ruleData = {
      name: formData.name,
      description: formData.description || null,
      rule_type: formData.rule_type,
      config: formData.config,
      severity: formData.severity,
      action: formData.action,
      auto_screenshot: formData.auto_screenshot,
      notify_immediately: formData.notify_immediately,
      enabled: formData.enabled,
    };

    if (editingRule) {
      const { error } = await supabase
        .from('suspicious_activity_rules')
        .update(ruleData)
        .eq('id', editingRule.id);

      if (error) {
        console.error('Error updating rule:', error);
        return;
      }
    } else {
      const { error } = await supabase
        .from('suspicious_activity_rules')
        .insert(ruleData);

      if (error) {
        console.error('Error creating rule:', error);
        return;
      }
    }

    setShowModal(false);
    setEditingRule(null);
    resetForm();
    fetchRules();
  }

  async function deleteRule(id: string) {
    if (!confirm('Are you sure you want to delete this rule?')) return;

    const { error } = await supabase
      .from('suspicious_activity_rules')
      .delete()
      .eq('id', id);

    if (!error) fetchRules();
  }

  async function toggleRule(id: string, enabled: boolean) {
    const { error } = await supabase
      .from('suspicious_activity_rules')
      .update({ enabled })
      .eq('id', id);

    if (!error) {
      setRules(rules.map(r => r.id === id ? { ...r, enabled } : r));
    }
  }

  function openEdit(rule: ActivityRule) {
    setEditingRule(rule);
    setFormData({
      name: rule.name,
      description: rule.description || '',
      rule_type: rule.rule_type,
      config: rule.config || {},
      severity: rule.severity,
      action: rule.action,
      auto_screenshot: rule.auto_screenshot,
      notify_immediately: rule.notify_immediately,
      enabled: rule.enabled,
    });
    setShowModal(true);
  }

  function resetForm() {
    setFormData({
      name: '',
      description: '',
      rule_type: 'unusual_time',
      config: defaultConfigs.unusual_time,
      severity: 'high',
      action: 'alert_screenshot',
      auto_screenshot: true,
      notify_immediately: true,
      enabled: true,
    });
  }

  function handleRuleTypeChange(ruleType: string) {
    setFormData({
      ...formData,
      rule_type: ruleType,
      config: defaultConfigs[ruleType] || {},
    });
  }

  function updateConfig(key: string, value: unknown) {
    setFormData({
      ...formData,
      config: { ...formData.config, [key]: value },
    });
  }

  function getSeverityBadge(severity: string) {
    const opt = severityOptions.find(s => s.value === severity);
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${opt?.bgLight} ${opt?.textColor}`}>
        {opt?.label}
      </span>
    );
  }

  function getRuleIcon(ruleType: string) {
    const type = ruleTypes.find(t => t.value === ruleType);
    const Icon = type?.icon || Activity;
    return <Icon className="w-5 h-5" />;
  }

  function renderConfigEditor() {
    const ruleType = ruleTypes.find(t => t.value === formData.rule_type);
    if (!ruleType?.configFields.length) {
      return <p className="text-sm text-gray-500 dark:text-[#666]">No additional configuration needed for this rule type.</p>;
    }

    return (
      <div className="space-y-4">
        {ruleType.configFields.includes('start_hour') && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-1">Start Hour</label>
              <input
                type="number"
                min="0"
                max="23"
                value={formData.config.start_hour as number || 0}
                onChange={(e) => updateConfig('start_hour', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-200 dark:border-[#333] rounded-lg bg-white dark:bg-[#222] text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-1">End Hour</label>
              <input
                type="number"
                min="0"
                max="23"
                value={formData.config.end_hour as number || 6}
                onChange={(e) => updateConfig('end_hour', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-200 dark:border-[#333] rounded-lg bg-white dark:bg-[#222] text-gray-900 dark:text-white"
              />
            </div>
          </div>
        )}

        {ruleType.configFields.includes('weekends') && (
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={formData.config.weekends as boolean || false}
              onChange={(e) => updateConfig('weekends', e.target.checked)}
              className="w-4 h-4 text-red-600 rounded focus:ring-red-500"
            />
            <label className="text-sm text-gray-700 dark:text-[#AAA]">Include weekends</label>
          </div>
        )}

        {ruleType.configFields.includes('threshold') && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-1">Threshold (operations)</label>
            <input
              type="number"
              min="1"
              value={formData.config.threshold as number || 50}
              onChange={(e) => updateConfig('threshold', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-200 dark:border-[#333] rounded-lg bg-white dark:bg-[#222] text-gray-900 dark:text-white"
            />
          </div>
        )}

        {ruleType.configFields.includes('threshold_mb') && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-1">Threshold (MB)</label>
            <input
              type="number"
              min="1"
              value={formData.config.threshold_mb as number || 100}
              onChange={(e) => updateConfig('threshold_mb', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-200 dark:border-[#333] rounded-lg bg-white dark:bg-[#222] text-gray-900 dark:text-white"
            />
          </div>
        )}

        {ruleType.configFields.includes('window_minutes') && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-1">Time Window (minutes)</label>
            <input
              type="number"
              min="1"
              value={formData.config.window_minutes as number || 5}
              onChange={(e) => updateConfig('window_minutes', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-200 dark:border-[#333] rounded-lg bg-white dark:bg-[#222] text-gray-900 dark:text-white"
            />
          </div>
        )}

        {ruleType.configFields.includes('apps') && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-1">Applications (comma-separated)</label>
            <input
              type="text"
              value={(formData.config.apps as string[])?.join(', ') || ''}
              onChange={(e) => updateConfig('apps', e.target.value.split(',').map(s => s.trim()))}
              className="w-full px-3 py-2 border border-gray-200 dark:border-[#333] rounded-lg bg-white dark:bg-[#222] text-gray-900 dark:text-white"
              placeholder="TeamViewer, AnyDesk, VNC Viewer"
            />
          </div>
        )}

        {ruleType.configFields.includes('alert_on_connect') && (
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={formData.config.alert_on_connect as boolean || false}
                onChange={(e) => updateConfig('alert_on_connect', e.target.checked)}
                className="w-4 h-4 text-red-600 rounded focus:ring-red-500"
              />
              <label className="text-sm text-gray-700 dark:text-[#AAA]">Alert on USB connect</label>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={formData.config.alert_on_file_copy as boolean || false}
                onChange={(e) => updateConfig('alert_on_file_copy', e.target.checked)}
                className="w-4 h-4 text-red-600 rounded focus:ring-red-500"
              />
              <label className="text-sm text-gray-700 dark:text-[#AAA]">Alert on file copy to USB</label>
            </div>
          </div>
        )}
      </div>
    );
  }

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
            <Activity className="w-7 h-7 text-red-500" />
            Suspicious Activity Rules
          </h1>
          <p className="text-gray-600 dark:text-[#888] mt-1">Configure rules to detect and respond to suspicious behavior</p>
        </div>
        <button
          onClick={() => { resetForm(); setEditingRule(null); setShowModal(true); }}
          className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors shadow-lg shadow-red-500/20"
        >
          <Plus className="w-5 h-5" />
          Add Rule
        </button>
      </div>

      {/* Rule Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {rules.map((rule) => {
          const ruleType = ruleTypes.find(t => t.value === rule.rule_type);
          return (
            <div
              key={rule.id}
              className={`bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333] p-5 ${!rule.enabled ? 'opacity-50' : ''}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${rule.enabled ? 'bg-red-100 dark:bg-red-500/20' : 'bg-gray-100 dark:bg-[#333]'}`}>
                    {getRuleIcon(rule.rule_type)}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">{rule.name}</h3>
                    <p className="text-sm text-gray-500 dark:text-[#666]">{ruleType?.label}</p>
                  </div>
                </div>
                <button
                  onClick={() => toggleRule(rule.id, !rule.enabled)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    rule.enabled ? 'bg-green-500' : 'bg-gray-300 dark:bg-[#444]'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      rule.enabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>

              {rule.description && (
                <p className="text-sm text-gray-600 dark:text-[#888] mt-3">{rule.description}</p>
              )}

              <div className="flex items-center gap-2 mt-4">
                {getSeverityBadge(rule.severity)}
                {rule.auto_screenshot && (
                  <span className="px-2 py-1 bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-400 rounded-full text-xs font-medium flex items-center gap-1">
                    <Camera className="w-3 h-3" /> Screenshot
                  </span>
                )}
                {rule.notify_immediately && (
                  <span className="px-2 py-1 bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 rounded-full text-xs font-medium">
                    Instant
                  </span>
                )}
              </div>

              <div className="flex items-center justify-end gap-2 mt-4 pt-4 border-t border-gray-200 dark:border-[#333]">
                <button
                  onClick={() => openEdit(rule)}
                  className="p-2 text-gray-500 dark:text-[#666] hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-500/10 rounded-lg transition-colors"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => deleteRule(rule.id)}
                  className="p-2 text-gray-500 dark:text-[#666] hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}

        {rules.length === 0 && (
          <div className="col-span-full text-center py-12 bg-white dark:bg-[#1A1A1A] rounded-xl border border-gray-200 dark:border-[#333]">
            <Activity className="w-12 h-12 text-gray-300 dark:text-[#444] mx-auto mb-4" />
            <p className="text-gray-500 dark:text-[#666]">No activity rules configured</p>
            <button
              onClick={() => { resetForm(); setShowModal(true); }}
              className="mt-4 text-red-600 dark:text-red-500 hover:text-red-700 dark:hover:text-red-400 font-medium"
            >
              Create your first rule
            </button>
          </div>
        )}
      </div>

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-[#1A1A1A] rounded-2xl shadow-2xl w-full max-w-2xl m-4 max-h-[90vh] overflow-auto border border-gray-200 dark:border-[#333]">
            <div className="p-6 border-b border-gray-200 dark:border-[#333] flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                {editingRule ? 'Edit Activity Rule' : 'Add Activity Rule'}
              </h2>
              <button
                onClick={() => { setShowModal(false); setEditingRule(null); }}
                className="p-2 text-gray-500 dark:text-[#666] hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-[#333] rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">Rule Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 dark:border-[#333] rounded-lg bg-white dark:bg-[#222] text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-red-500"
                  placeholder="e.g., After Hours Access Alert"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">Description (optional)</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 dark:border-[#333] rounded-lg bg-white dark:bg-[#222] text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-red-500"
                  placeholder="Brief description of this rule"
                />
              </div>

              {/* Rule Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">Detection Type</label>
                <div className="grid grid-cols-2 gap-2 max-h-48 overflow-auto">
                  {ruleTypes.map((type) => {
                    const Icon = type.icon;
                    return (
                      <button
                        key={type.value}
                        onClick={() => handleRuleTypeChange(type.value)}
                        className={`p-3 border rounded-lg text-left flex items-center gap-3 transition-colors ${
                          formData.rule_type === type.value
                            ? 'border-red-500 bg-red-50 dark:bg-red-500/10'
                            : 'border-gray-200 dark:border-[#333] hover:border-gray-300 dark:hover:border-[#444]'
                        }`}
                      >
                        <Icon className={`w-5 h-5 ${formData.rule_type === type.value ? 'text-red-500' : 'text-gray-400 dark:text-[#666]'}`} />
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white text-sm">{type.label}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Configuration */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">Configuration</label>
                <div className="bg-gray-50 dark:bg-[#111] p-4 rounded-lg border border-gray-100 dark:border-[#222]">
                  {renderConfigEditor()}
                </div>
              </div>

              {/* Severity */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">Severity</label>
                <div className="flex gap-3">
                  {severityOptions.map((sev) => (
                    <button
                      key={sev.value}
                      onClick={() => setFormData({ ...formData, severity: sev.value as ActivityRule['severity'] })}
                      className={`flex-1 py-2 px-4 rounded-lg border-2 font-medium transition-colors ${
                        formData.severity === sev.value
                          ? `${sev.color} text-white border-transparent`
                          : `${sev.bgLight} ${sev.textColor} border-transparent hover:border-current`
                      }`}
                    >
                      {sev.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Action */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">Response Action</label>
                <div className="grid grid-cols-2 gap-2">
                  {actionOptions.map((act) => {
                    const Icon = act.icon;
                    return (
                      <button
                        key={act.value}
                        onClick={() => setFormData({ ...formData, action: act.value as ActivityRule['action'] })}
                        className={`p-3 border rounded-lg text-left flex items-center gap-3 transition-colors ${
                          formData.action === act.value
                            ? 'border-red-500 bg-red-50 dark:bg-red-500/10'
                            : 'border-gray-200 dark:border-[#333] hover:border-gray-300 dark:hover:border-[#444]'
                        }`}
                      >
                        <Icon className={`w-5 h-5 ${formData.action === act.value ? 'text-red-500' : 'text-gray-400 dark:text-[#666]'}`} />
                        <p className="font-medium text-gray-900 dark:text-white text-sm">{act.label}</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Options */}
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={formData.auto_screenshot}
                    onChange={(e) => setFormData({ ...formData, auto_screenshot: e.target.checked })}
                    className="w-4 h-4 text-red-600 rounded focus:ring-red-500"
                  />
                  <label className="text-sm text-gray-700 dark:text-[#AAA]">Auto-capture screenshot on detection</label>
                </div>
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={formData.notify_immediately}
                    onChange={(e) => setFormData({ ...formData, notify_immediately: e.target.checked })}
                    className="w-4 h-4 text-red-600 rounded focus:ring-red-500"
                  />
                  <label className="text-sm text-gray-700 dark:text-[#AAA]">Send immediate push notification</label>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setFormData({ ...formData, enabled: !formData.enabled })}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      formData.enabled ? 'bg-green-500' : 'bg-gray-300 dark:bg-[#444]'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        formData.enabled ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                  <label className="text-sm text-gray-700 dark:text-[#AAA]">Rule is active</label>
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-gray-200 dark:border-[#333] bg-gray-50 dark:bg-[#111] flex justify-end gap-3">
              <button
                onClick={() => { setShowModal(false); setEditingRule(null); }}
                className="px-4 py-2 text-gray-700 dark:text-[#AAA] hover:bg-gray-200 dark:hover:bg-[#333] rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={saveRule}
                disabled={!formData.name}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Save className="w-4 h-4" />
                {editingRule ? 'Update Rule' : 'Create Rule'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
