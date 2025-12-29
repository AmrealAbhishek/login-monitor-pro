'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import {
  Globe,
  Plus,
  Trash2,
  Edit2,
  Save,
  X,
  AlertTriangle,
  Camera,
  Eye,
  Ban,
  Link2,
  Tag,
} from 'lucide-react';

interface UrlRule {
  id: string;
  name: string;
  description: string | null;
  rule_type: 'domain_block' | 'domain_alert' | 'domain_allow' | 'category_block' | 'category_alert' | 'keyword_alert';
  pattern: string;
  category: string | null;
  severity: 'low' | 'medium' | 'high' | 'critical';
  action: 'alert' | 'alert_screenshot' | 'block' | 'log_only';
  enabled: boolean;
  created_at: string;
}

const ruleTypes = [
  { value: 'domain_block', label: 'Block Domain', icon: Ban, description: 'Block access to specific domains' },
  { value: 'domain_alert', label: 'Alert on Domain', icon: AlertTriangle, description: 'Alert when domain is visited' },
  { value: 'domain_allow', label: 'Allow Domain', icon: Eye, description: 'Whitelist trusted domains' },
  { value: 'category_block', label: 'Block Category', icon: Tag, description: 'Block entire category (social, gambling)' },
  { value: 'category_alert', label: 'Alert on Category', icon: Tag, description: 'Alert on category visits' },
  { value: 'keyword_alert', label: 'Keyword Alert', icon: Link2, description: 'Alert on URL keywords' },
];

const categoryOptions = [
  'social_media', 'streaming', 'gambling', 'shopping', 'news',
  'entertainment', 'adult', 'job_sites', 'cloud_storage', 'file_sharing'
];

const severityOptions = [
  { value: 'low', label: 'Low', color: 'bg-blue-500', textColor: 'text-blue-500', bgLight: 'bg-blue-100' },
  { value: 'medium', label: 'Medium', color: 'bg-yellow-500', textColor: 'text-yellow-500', bgLight: 'bg-yellow-100' },
  { value: 'high', label: 'High', color: 'bg-orange-500', textColor: 'text-orange-500', bgLight: 'bg-orange-100' },
  { value: 'critical', label: 'Critical', color: 'bg-red-500', textColor: 'text-red-500', bgLight: 'bg-red-100' },
];

const actionOptions = [
  { value: 'log_only', label: 'Log Only', icon: Eye, description: 'Record visit without alerting' },
  { value: 'alert', label: 'Alert', icon: AlertTriangle, description: 'Send notification to admin' },
  { value: 'alert_screenshot', label: 'Alert + Screenshot', icon: Camera, description: 'Alert and capture screen' },
  { value: 'block', label: 'Block Access', icon: Ban, description: 'Prevent page from loading' },
];

export default function UrlRulesPage() {
  const [rules, setRules] = useState<UrlRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingRule, setEditingRule] = useState<UrlRule | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    rule_type: 'domain_alert' as UrlRule['rule_type'],
    pattern: '',
    category: '',
    severity: 'medium' as UrlRule['severity'],
    action: 'alert' as UrlRule['action'],
    enabled: true,
  });

  useEffect(() => {
    fetchRules();
  }, []);

  async function fetchRules() {
    const { data, error } = await supabase
      .from('url_rules')
      .select('*')
      .order('severity', { ascending: false })
      .order('created_at', { ascending: false });

    if (data) setRules(data);
    if (error) console.error('Error fetching rules:', error);
    setLoading(false);
  }

  async function saveRule() {
    if (!formData.name || !formData.pattern) return;

    const ruleData = {
      name: formData.name,
      description: formData.description || null,
      rule_type: formData.rule_type,
      pattern: formData.pattern,
      category: formData.category || null,
      severity: formData.severity,
      action: formData.action,
      enabled: formData.enabled,
    };

    if (editingRule) {
      const { error } = await supabase
        .from('url_rules')
        .update(ruleData)
        .eq('id', editingRule.id);

      if (error) {
        console.error('Error updating rule:', error);
        return;
      }
    } else {
      const { error } = await supabase
        .from('url_rules')
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
      .from('url_rules')
      .delete()
      .eq('id', id);

    if (!error) fetchRules();
  }

  async function toggleRule(id: string, enabled: boolean) {
    const { error } = await supabase
      .from('url_rules')
      .update({ enabled })
      .eq('id', id);

    if (!error) {
      setRules(rules.map(r => r.id === id ? { ...r, enabled } : r));
    }
  }

  function openEdit(rule: UrlRule) {
    setEditingRule(rule);
    setFormData({
      name: rule.name,
      description: rule.description || '',
      rule_type: rule.rule_type,
      pattern: rule.pattern,
      category: rule.category || '',
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
      rule_type: 'domain_alert',
      pattern: '',
      category: '',
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

  function getRuleTypeBadge(ruleType: string) {
    const type = ruleTypes.find(t => t.value === ruleType);
    const Icon = type?.icon || Globe;
    let bgColor = 'bg-gray-100 text-gray-700';
    if (ruleType.includes('block')) bgColor = 'bg-red-100 text-red-700';
    else if (ruleType.includes('alert')) bgColor = 'bg-yellow-100 text-yellow-700';
    else if (ruleType.includes('allow')) bgColor = 'bg-green-100 text-green-700';

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-sm ${bgColor}`}>
        <Icon className="w-3 h-3" />
        {type?.label}
      </span>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></div>
      </div>
    );
  }

  const isCategory = formData.rule_type.includes('category');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Globe className="w-7 h-7 text-red-500" />
            URL Monitoring Rules
          </h1>
          <p className="text-gray-600 dark:text-[#888] mt-1">Configure URL blocking, alerting, and tracking rules</p>
        </div>
        <button
          onClick={() => { resetForm(); setEditingRule(null); setShowModal(true); }}
          className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors shadow-lg shadow-red-500/20"
        >
          <Plus className="w-5 h-5" />
          Add Rule
        </button>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-[#1A1A1A] p-4 rounded-lg border border-gray-200 dark:border-[#333]">
          <p className="text-sm text-gray-500 dark:text-[#666]">Total Rules</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{rules.length}</p>
        </div>
        <div className="bg-white dark:bg-[#1A1A1A] p-4 rounded-lg border border-gray-200 dark:border-[#333]">
          <p className="text-sm text-gray-500 dark:text-[#666]">Blocking Rules</p>
          <p className="text-2xl font-bold text-red-600 dark:text-red-500">{rules.filter(r => r.rule_type.includes('block')).length}</p>
        </div>
        <div className="bg-white dark:bg-[#1A1A1A] p-4 rounded-lg border border-gray-200 dark:border-[#333]">
          <p className="text-sm text-gray-500 dark:text-[#666]">Alert Rules</p>
          <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-500">{rules.filter(r => r.rule_type.includes('alert')).length}</p>
        </div>
        <div className="bg-white dark:bg-[#1A1A1A] p-4 rounded-lg border border-gray-200 dark:border-[#333]">
          <p className="text-sm text-gray-500 dark:text-[#666]">Active Rules</p>
          <p className="text-2xl font-bold text-green-600 dark:text-green-500">{rules.filter(r => r.enabled).length}</p>
        </div>
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
                  {getRuleTypeBadge(rule.rule_type)}
                </td>
                <td className="px-6 py-4">
                  <code className="px-2 py-1 bg-gray-100 dark:bg-[#333] rounded text-sm font-mono text-gray-800 dark:text-gray-200">
                    {rule.pattern}
                  </code>
                </td>
                <td className="px-6 py-4">
                  {getSeverityBadge(rule.severity)}
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
                <td colSpan={6} className="px-6 py-12 text-center text-gray-500 dark:text-[#666]">
                  No URL rules configured. Click &quot;Add Rule&quot; to create your first rule.
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
                {editingRule ? 'Edit URL Rule' : 'Add New URL Rule'}
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
                  placeholder="e.g., Block Social Media"
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
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">Rule Type</label>
                <div className="grid grid-cols-2 gap-3">
                  {ruleTypes.map((type) => {
                    const Icon = type.icon;
                    return (
                      <button
                        key={type.value}
                        onClick={() => setFormData({ ...formData, rule_type: type.value as UrlRule['rule_type'] })}
                        className={`p-4 border rounded-lg text-left transition-colors ${
                          formData.rule_type === type.value
                            ? 'border-red-500 bg-red-50 dark:bg-red-500/10'
                            : 'border-gray-200 dark:border-[#333] hover:border-gray-300 dark:hover:border-[#444]'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Icon className={`w-4 h-4 ${formData.rule_type === type.value ? 'text-red-500' : 'text-gray-400 dark:text-[#666]'}`} />
                          <p className="font-medium text-gray-900 dark:text-white">{type.label}</p>
                        </div>
                        <p className="text-sm text-gray-500 dark:text-[#666] mt-1">{type.description}</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Pattern / Category */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">
                  {isCategory ? 'Category' : 'Domain Pattern'}
                </label>
                {isCategory ? (
                  <select
                    value={formData.pattern}
                    onChange={(e) => setFormData({ ...formData, pattern: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-200 dark:border-[#333] rounded-lg bg-white dark:bg-[#222] text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-red-500"
                  >
                    <option value="">Select a category...</option>
                    {categoryOptions.map(cat => (
                      <option key={cat} value={cat}>{cat.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={formData.pattern}
                    onChange={(e) => setFormData({ ...formData, pattern: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-200 dark:border-[#333] rounded-lg font-mono bg-white dark:bg-[#222] text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-red-500"
                    placeholder="facebook.com,twitter.com,instagram.com"
                  />
                )}
                <p className="text-sm text-gray-500 dark:text-[#666] mt-2">
                  {isCategory
                    ? 'Select a category to apply this rule to all matching domains'
                    : 'Enter domains without http://. Separate multiple domains with commas.'}
                </p>
              </div>

              {/* Severity */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-2">Severity</label>
                <div className="flex gap-3">
                  {severityOptions.map((sev) => (
                    <button
                      key={sev.value}
                      onClick={() => setFormData({ ...formData, severity: sev.value as UrlRule['severity'] })}
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
                <div className="grid grid-cols-2 gap-2">
                  {actionOptions.map((act) => {
                    const Icon = act.icon;
                    return (
                      <button
                        key={act.value}
                        onClick={() => setFormData({ ...formData, action: act.value as UrlRule['action'] })}
                        className={`p-3 border rounded-lg text-left flex items-center gap-3 transition-colors ${
                          formData.action === act.value
                            ? 'border-red-500 bg-red-50 dark:bg-red-500/10'
                            : 'border-gray-200 dark:border-[#333] hover:border-gray-300 dark:hover:border-[#444]'
                        }`}
                      >
                        <Icon className={`w-5 h-5 ${formData.action === act.value ? 'text-red-500' : 'text-gray-400 dark:text-[#666]'}`} />
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white text-sm">{act.label}</p>
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
