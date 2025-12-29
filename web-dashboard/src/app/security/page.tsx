'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import {
  Shield,
  Clock,
  MapPin,
  AlertTriangle,
  Plus,
  Trash2,
  Settings,
  Check,
  X,
} from 'lucide-react';

interface SecurityRule {
  id: string;
  org_id: string | null;
  device_id: string | null;
  rule_type: string;
  enabled: boolean;
  config: Record<string, unknown>;
  severity: string;
  action: string;
  created_at: string;
}

interface KnownLocation {
  id: string;
  device_id: string;
  name: string | null;
  ip_address: string;
  city: string;
  country: string;
  is_trusted: boolean;
  first_seen: string;
}

const RULE_TYPES = [
  {
    id: 'unusual_time',
    label: 'Unusual Time Access',
    icon: Clock,
    description: 'Alert when device accessed during unusual hours',
    defaultConfig: { start_hour: 0, end_hour: 6 },
  },
  {
    id: 'new_location',
    label: 'New Location',
    icon: MapPin,
    description: 'Alert when device accessed from new IP/city',
    defaultConfig: {},
  },
  {
    id: 'after_hours',
    label: 'After Hours Access',
    icon: Clock,
    description: 'Alert when device accessed outside work hours',
    defaultConfig: { work_start: 9, work_end: 18, work_days: [1, 2, 3, 4, 5] },
  },
  {
    id: 'failed_logins',
    label: 'Failed Login Attempts',
    icon: AlertTriangle,
    description: 'Alert after multiple failed login attempts',
    defaultConfig: { threshold: 3, window_minutes: 5 },
  },
];

const SEVERITY_OPTIONS = ['low', 'medium', 'high', 'critical'];
const ACTION_OPTIONS = ['alert', 'screenshot', 'lock'];

export default function SecurityPage() {
  const [rules, setRules] = useState<SecurityRule[]>([]);
  const [locations, setLocations] = useState<KnownLocation[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddRule, setShowAddRule] = useState(false);
  const [newRule, setNewRule] = useState({
    rule_type: 'unusual_time',
    severity: 'medium',
    action: 'alert',
    enabled: true,
    config: {},
  });

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    const [rulesRes, locationsRes] = await Promise.all([
      supabase.from('security_rules').select('*').order('created_at', { ascending: false }),
      supabase.from('known_locations').select('*').order('first_seen', { ascending: false }),
    ]);

    if (rulesRes.data) setRules(rulesRes.data);
    if (locationsRes.data) setLocations(locationsRes.data);
    setLoading(false);
  }

  async function createRule() {
    const ruleType = RULE_TYPES.find((r) => r.id === newRule.rule_type);
    const { error } = await supabase.from('security_rules').insert({
      ...newRule,
      config: ruleType?.defaultConfig || {},
    });

    if (!error) {
      setShowAddRule(false);
      fetchData();
    }
  }

  async function toggleRule(ruleId: string, enabled: boolean) {
    await supabase.from('security_rules').update({ enabled }).eq('id', ruleId);
    setRules((prev) => prev.map((r) => (r.id === ruleId ? { ...r, enabled } : r)));
  }

  async function deleteRule(ruleId: string) {
    await supabase.from('security_rules').delete().eq('id', ruleId);
    setRules((prev) => prev.filter((r) => r.id !== ruleId));
  }

  async function toggleLocationTrust(locationId: string, isTrusted: boolean) {
    await supabase.from('known_locations').update({ is_trusted: isTrusted }).eq('id', locationId);
    setLocations((prev) =>
      prev.map((l) => (l.id === locationId ? { ...l, is_trusted: isTrusted } : l))
    );
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400';
      case 'high':
        return 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-400';
      case 'medium':
        return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400';
      default:
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400';
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'lock':
        return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400';
      case 'screenshot':
        return 'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-400';
      default:
        return 'bg-gray-100 dark:bg-[#333] text-gray-800 dark:text-[#AAA]';
    }
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Security Rules</h1>
          <p className="text-gray-600 dark:text-[#888]">Configure threat detection and automatic responses</p>
        </div>
        <button
          onClick={() => setShowAddRule(true)}
          className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors shadow-lg shadow-red-500/20"
        >
          <Plus className="w-4 h-4" />
          Add Rule
        </button>
      </div>

      {/* Add Rule Modal */}
      {showAddRule && (
        <div className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-[#1A1A1A] rounded-xl p-6 w-full max-w-md border border-gray-200 dark:border-[#333]">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Add Security Rule</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-1">Rule Type</label>
                <select
                  value={newRule.rule_type}
                  onChange={(e) => setNewRule({ ...newRule, rule_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-[#333] rounded-lg bg-white dark:bg-[#222] text-gray-900 dark:text-white"
                >
                  {RULE_TYPES.map((type) => (
                    <option key={type.id} value={type.id}>
                      {type.label}
                    </option>
                  ))}
                </select>
                <p className="text-sm text-gray-500 dark:text-[#888] mt-1">
                  {RULE_TYPES.find((r) => r.id === newRule.rule_type)?.description}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-1">Severity</label>
                <select
                  value={newRule.severity}
                  onChange={(e) => setNewRule({ ...newRule, severity: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-[#333] rounded-lg bg-white dark:bg-[#222] text-gray-900 dark:text-white"
                >
                  {SEVERITY_OPTIONS.map((sev) => (
                    <option key={sev} value={sev}>
                      {sev.charAt(0).toUpperCase() + sev.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-[#AAA] mb-1">Action</label>
                <select
                  value={newRule.action}
                  onChange={(e) => setNewRule({ ...newRule, action: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-[#333] rounded-lg bg-white dark:bg-[#222] text-gray-900 dark:text-white"
                >
                  {ACTION_OPTIONS.map((act) => (
                    <option key={act} value={act}>
                      {act.charAt(0).toUpperCase() + act.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowAddRule(false)}
                className="px-4 py-2 text-gray-700 dark:text-[#AAA] hover:bg-gray-100 dark:hover:bg-[#333] rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={createRule}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Create Rule
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Active Rules */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl shadow-sm border border-gray-200 dark:border-[#333]">
        <div className="p-4 border-b border-gray-200 dark:border-[#333]">
          <h2 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Security Rules ({rules.length})
          </h2>
        </div>
        <div className="divide-y divide-gray-100 dark:divide-[#333]">
          {rules.length === 0 ? (
            <div className="p-12 text-center">
              <Shield className="w-12 h-12 text-gray-300 dark:text-[#444] mx-auto mb-4" />
              <p className="text-gray-500 dark:text-[#888]">No security rules configured</p>
              <p className="text-sm text-gray-400 dark:text-[#666]">
                Add rules to automatically detect threats
              </p>
            </div>
          ) : (
            rules.map((rule) => {
              const ruleType = RULE_TYPES.find((r) => r.id === rule.rule_type);
              const Icon = ruleType?.icon || Shield;

              return (
                <div
                  key={rule.id}
                  className={`p-4 flex items-center gap-4 hover:bg-gray-50 dark:hover:bg-[#222] transition-colors ${!rule.enabled ? 'opacity-50' : ''}`}
                >
                  <Icon className="w-5 h-5 text-gray-600 dark:text-[#888]" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-gray-900 dark:text-white">{ruleType?.label || rule.rule_type}</h3>
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${getSeverityColor(
                          rule.severity
                        )}`}
                      >
                        {rule.severity}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${getActionColor(
                          rule.action
                        )}`}
                      >
                        {rule.action}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-[#888]">{ruleType?.description}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => toggleRule(rule.id, !rule.enabled)}
                      className={`p-2 rounded-lg transition-colors ${
                        rule.enabled
                          ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400'
                          : 'bg-gray-100 dark:bg-[#333] text-gray-400 dark:text-[#666]'
                      }`}
                    >
                      {rule.enabled ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => deleteRule(rule.id)}
                      className="p-2 text-gray-400 dark:text-[#666] hover:text-red-600 dark:hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Known Locations */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl shadow-sm border border-gray-200 dark:border-[#333]">
        <div className="p-4 border-b border-gray-200 dark:border-[#333]">
          <h2 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <MapPin className="w-5 h-5" />
            Known Locations ({locations.length})
          </h2>
        </div>
        <div className="divide-y divide-gray-100 dark:divide-[#333]">
          {locations.length === 0 ? (
            <div className="p-12 text-center">
              <MapPin className="w-12 h-12 text-gray-300 dark:text-[#444] mx-auto mb-4" />
              <p className="text-gray-500 dark:text-[#888]">No locations recorded yet</p>
              <p className="text-sm text-gray-400 dark:text-[#666]">
                Locations are automatically saved when devices connect
              </p>
            </div>
          ) : (
            locations.map((location) => (
              <div key={location.id} className="p-4 flex items-center gap-4 hover:bg-gray-50 dark:hover:bg-[#222] transition-colors">
                <MapPin
                  className={`w-5 h-5 ${
                    location.is_trusted ? 'text-green-500' : 'text-gray-400 dark:text-[#666]'
                  }`}
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      {location.name || `${location.city}, ${location.country}`}
                    </h3>
                    {location.is_trusted && (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400">
                        Trusted
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-500 dark:text-[#888]">{location.ip_address}</p>
                </div>
                <button
                  onClick={() => toggleLocationTrust(location.id, !location.is_trusted)}
                  className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                    location.is_trusted
                      ? 'bg-gray-100 dark:bg-[#333] text-gray-600 dark:text-[#AAA] hover:bg-gray-200 dark:hover:bg-[#444]'
                      : 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-900/50'
                  }`}
                >
                  {location.is_trusted ? 'Remove Trust' : 'Mark Trusted'}
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
