'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import {
  FileText,
  Plus,
  Trash2,
  Edit2,
  Save,
  X,
  Shield,
  AlertTriangle,
  Camera,
  Eye,
  Ban,
} from 'lucide-react';

interface FileRule {
  id: string;
  name: string;
  description: string | null;
  rule_type: 'path_pattern' | 'extension' | 'filename_pattern' | 'content_keyword';
  pattern: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  action: 'alert' | 'alert_screenshot' | 'block' | 'log_only';
  enabled: boolean;
  created_at: string;
}

const ruleTypes = [
  { value: 'path_pattern', label: 'Path Pattern', description: 'Match file paths (e.g., /Documents/Confidential/*)' },
  { value: 'extension', label: 'File Extension', description: 'Match file extensions (.docx, .xlsx, .pdf)' },
  { value: 'filename_pattern', label: 'Filename Pattern', description: 'Match filenames (*password*, *secret*)' },
  { value: 'content_keyword', label: 'Content Keyword', description: 'Match content inside files' },
];

const severityOptions = [
  { value: 'low', label: 'Low', color: 'bg-blue-500', textColor: 'text-blue-500', bgLight: 'bg-blue-100' },
  { value: 'medium', label: 'Medium', color: 'bg-yellow-500', textColor: 'text-yellow-500', bgLight: 'bg-yellow-100' },
  { value: 'high', label: 'High', color: 'bg-orange-500', textColor: 'text-orange-500', bgLight: 'bg-orange-100' },
  { value: 'critical', label: 'Critical', color: 'bg-red-500', textColor: 'text-red-500', bgLight: 'bg-red-100' },
];

const actionOptions = [
  { value: 'log_only', label: 'Log Only', icon: Eye, description: 'Record access without alerting' },
  { value: 'alert', label: 'Alert', icon: AlertTriangle, description: 'Send notification to admin' },
  { value: 'alert_screenshot', label: 'Alert + Screenshot', icon: Camera, description: 'Alert and capture screen' },
  { value: 'block', label: 'Block Access', icon: Ban, description: 'Prevent file access (requires agent support)' },
];

export default function FileRulesPage() {
  const [rules, setRules] = useState<FileRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingRule, setEditingRule] = useState<FileRule | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    rule_type: 'filename_pattern' as FileRule['rule_type'],
    pattern: '',
    severity: 'medium' as FileRule['severity'],
    action: 'alert' as FileRule['action'],
    enabled: true,
  });

  useEffect(() => {
    fetchRules();
  }, []);

  async function fetchRules() {
    const { data, error } = await supabase
      .from('sensitive_file_rules')
      .select('*')
      .order('severity', { ascending: false })
      .order('created_at', { ascending: false });

    if (data) setRules(data);
    if (error) console.error('Error fetching rules:', error);
    setLoading(false);
  }

  async function saveRule() {
    if (!formData.name || !formData.pattern) return;

    if (editingRule) {
      const { error } = await supabase
        .from('sensitive_file_rules')
        .update({
          name: formData.name,
          description: formData.description || null,
          rule_type: formData.rule_type,
          pattern: formData.pattern,
          severity: formData.severity,
          action: formData.action,
          enabled: formData.enabled,
          updated_at: new Date().toISOString(),
        })
        .eq('id', editingRule.id);

      if (error) {
        console.error('Error updating rule:', error);
        return;
      }
    } else {
      const { error } = await supabase
        .from('sensitive_file_rules')
        .insert({
          name: formData.name,
          description: formData.description || null,
          rule_type: formData.rule_type,
          pattern: formData.pattern,
          severity: formData.severity,
          action: formData.action,
          enabled: formData.enabled,
        });

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
      .from('sensitive_file_rules')
      .delete()
      .eq('id', id);

    if (!error) fetchRules();
  }

  async function toggleRule(id: string, enabled: boolean) {
    const { error } = await supabase
      .from('sensitive_file_rules')
      .update({ enabled })
      .eq('id', id);

    if (!error) {
      setRules(rules.map(r => r.id === id ? { ...r, enabled } : r));
    }
  }

  function openEdit(rule: FileRule) {
    setEditingRule(rule);
    setFormData({
      name: rule.name,
      description: rule.description || '',
      rule_type: rule.rule_type,
      pattern: rule.pattern,
      severity: rule.severity,
      action: rule.action,
      enabled: rule.enabled,
    });
    setShowModal(true);
  }

  function resetForm() {
    setFormData({
      name: '',
      description: '',
      rule_type: 'filename_pattern',
      pattern: '',
      severity: 'medium',
      action: 'alert',
      enabled: true,
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

  function getActionIcon(action: string) {
    const opt = actionOptions.find(a => a.value === action);
    const Icon = opt?.icon || Eye;
    return <Icon className="w-4 h-4" />;
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
            <FileText className="w-7 h-7 text-red-500" />
            Sensitive File Rules
          </h1>
          <p className="text-gray-600 dark:text-[#888] mt-1">Configure which file accesses trigger alerts and screenshots</p>
        </div>
        <button
          onClick={() => { resetForm(); setEditingRule(null); setShowModal(true); }}
          className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors shadow-lg shadow-red-500/20"
        >
          <Plus className="w-5 h-5" />
          Add Rule
        </button>
      </div>

      {/* Rules Table */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl shadow-sm border border-gray-200 dark:border-[#333] overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-[#111] border-b border-gray-200 dark:border-[#333]">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-[#666] uppercase tracking-wider">Status</th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-[#666] uppercase tracking-wider">Rule</th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-[#666] uppercase tracking-wider">Type</th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-[#666] uppercase tracking-wider">Pattern</th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-[#666] uppercase tracking-wider">Severity</th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-[#666] uppercase tracking-wider">Action</th>
              <th className="px-6 py-4 text-right text-xs font-medium text-gray-500 dark:text-[#666] uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-[#333]">
            {rules.map((rule) => (
              <tr key={rule.id} className={`hover:bg-gray-50 dark:hover:bg-[#222] ${!rule.enabled ? 'opacity-50' : ''}`}>
                <td className="px-6 py-4">
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
                </td>
                <td className="px-6 py-4">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">{rule.name}</p>
                    {rule.description && (
                      <p className="text-sm text-gray-500 dark:text-[#666] mt-0.5">{rule.description}</p>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="px-2 py-1 bg-gray-100 dark:bg-[#333] rounded text-sm text-gray-700 dark:text-[#AAA]">
                    {ruleTypes.find(t => t.value === rule.rule_type)?.label}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <code className="px-2 py-1 bg-gray-100 dark:bg-[#333] rounded text-sm font-mono text-gray-800 dark:text-gray-200">
                    {rule.pattern}
                  </code>
                </td>
                <td className="px-6 py-4">
                  {getSeverityBadge(rule.severity)}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2 text-gray-700 dark:text-[#AAA]">
                    {getActionIcon(rule.action)}
                    <span className="text-sm">{actionOptions.find(a => a.value === rule.action)?.label}</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
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
                </td>
              </tr>
            ))}
            {rules.length === 0 && (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-500 dark:text-[#666]">
                  No file rules configured. Click &quot;Add Rule&quot; to create your first rule.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-[#1A1A1A] rounded-2xl shadow-2xl w-full max-w-2xl m-4 max-h-[90vh] overflow-auto border border-gray-200 dark:border-[#333]">
            <div className="p-6 border-b border-gray-200 dark:border-[#333] flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                {editingRule ? 'Edit Rule' : 'Add New Rule'}
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
                  placeholder="e.g., Password Files"
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
                  placeholder="Brief description of what this rule detects"
                />
              </div>

              {/* Rule Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">Rule Type</label>
                <div className="grid grid-cols-2 gap-3">
                  {ruleTypes.map((type) => (
                    <button
                      key={type.value}
                      onClick={() => setFormData({ ...formData, rule_type: type.value as FileRule['rule_type'] })}
                      className={`p-4 border rounded-lg text-left transition-colors ${
                        formData.rule_type === type.value
                          ? 'border-red-500 bg-red-50 dark:bg-red-500/10'
                          : 'border-gray-200 dark:border-[#333] hover:border-gray-300 dark:hover:border-[#444]'
                      }`}
                    >
                      <p className="font-medium text-gray-900 dark:text-white">{type.label}</p>
                      <p className="text-sm text-gray-500 dark:text-[#666] mt-1">{type.description}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Pattern */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">Pattern</label>
                <input
                  type="text"
                  value={formData.pattern}
                  onChange={(e) => setFormData({ ...formData, pattern: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 dark:border-[#333] rounded-lg font-mono bg-white dark:bg-[#222] text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-red-500"
                  placeholder={
                    formData.rule_type === 'path_pattern' ? '*/Confidential/*' :
                    formData.rule_type === 'extension' ? '.xlsx,.docx,.pdf' :
                    formData.rule_type === 'filename_pattern' ? '*password*,*secret*' :
                    'confidential,secret,password'
                  }
                />
                <p className="text-sm text-gray-500 dark:text-[#666] mt-2">
                  {formData.rule_type === 'path_pattern' && 'Use * for wildcards. Separate multiple patterns with commas.'}
                  {formData.rule_type === 'extension' && 'Include the dot. Separate multiple extensions with commas.'}
                  {formData.rule_type === 'filename_pattern' && 'Use * for wildcards. Separate multiple patterns with commas.'}
                  {formData.rule_type === 'content_keyword' && 'Enter keywords to search for inside files. Separate with commas.'}
                </p>
              </div>

              {/* Severity */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">Severity</label>
                <div className="flex gap-3">
                  {severityOptions.map((sev) => (
                    <button
                      key={sev.value}
                      onClick={() => setFormData({ ...formData, severity: sev.value as FileRule['severity'] })}
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
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">Action on Match</label>
                <div className="space-y-2">
                  {actionOptions.map((act) => {
                    const Icon = act.icon;
                    return (
                      <button
                        key={act.value}
                        onClick={() => setFormData({ ...formData, action: act.value as FileRule['action'] })}
                        className={`w-full p-4 border rounded-lg text-left flex items-center gap-4 transition-colors ${
                          formData.action === act.value
                            ? 'border-red-500 bg-red-50 dark:bg-red-500/10'
                            : 'border-gray-200 dark:border-[#333] hover:border-gray-300 dark:hover:border-[#444]'
                        }`}
                      >
                        <Icon className={`w-5 h-5 ${formData.action === act.value ? 'text-red-500' : 'text-gray-400 dark:text-[#666]'}`} />
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">{act.label}</p>
                          <p className="text-sm text-gray-500 dark:text-[#666]">{act.description}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Enabled */}
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

            <div className="p-6 border-t border-gray-200 dark:border-[#333] bg-gray-50 dark:bg-[#111] flex justify-end gap-3">
              <button
                onClick={() => { setShowModal(false); setEditingRule(null); }}
                className="px-4 py-2 text-gray-700 dark:text-[#AAA] hover:bg-gray-200 dark:hover:bg-[#333] rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={saveRule}
                disabled={!formData.name || !formData.pattern}
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
