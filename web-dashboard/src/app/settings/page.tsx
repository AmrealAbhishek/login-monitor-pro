'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import {
  Settings,
  Bell,
  Shield,
  Mail,
  Save,
  Users,
  Building,
  Trash2,
  Copy,
  Check,
} from 'lucide-react';

interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: string;
  settings: Record<string, unknown>;
}

interface ScheduledReport {
  id: string;
  org_id: string;
  report_type: string;
  recipients: string[];
  enabled: boolean;
  last_sent_at: string | null;
}

export default function SettingsPage() {
  const [org, setOrg] = useState<Organization | null>(null);
  const [reports, setReports] = useState<ScheduledReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);

  // Form states
  const [orgName, setOrgName] = useState('');
  const [emailRecipients, setEmailRecipients] = useState('');
  const [alertsEnabled, setAlertsEnabled] = useState(true);
  const [screenshotsEnabled, setScreenshotsEnabled] = useState(true);
  const [locationTrackingEnabled, setLocationTrackingEnabled] = useState(true);

  useEffect(() => {
    fetchSettings();
  }, []);

  async function fetchSettings() {
    // Fetch organization (use first one for now)
    const { data: orgs } = await supabase.from('organizations').select('*').limit(1);

    if (orgs && orgs.length > 0) {
      setOrg(orgs[0]);
      setOrgName(orgs[0].name);

      const settings = orgs[0].settings || {};
      setAlertsEnabled(settings.alerts_enabled !== false);
      setScreenshotsEnabled(settings.screenshots_enabled !== false);
      setLocationTrackingEnabled(settings.location_tracking !== false);

      // Fetch scheduled reports
      const { data: reportsData } = await supabase
        .from('scheduled_reports')
        .select('*')
        .eq('org_id', orgs[0].id);

      if (reportsData) {
        setReports(reportsData);
        if (reportsData.length > 0) {
          setEmailRecipients(reportsData[0].recipients?.join(', ') || '');
        }
      }
    }

    setLoading(false);
  }

  async function saveSettings() {
    if (!org) return;

    // Update organization settings
    await supabase
      .from('organizations')
      .update({
        name: orgName,
        settings: {
          alerts_enabled: alertsEnabled,
          screenshots_enabled: screenshotsEnabled,
          location_tracking: locationTrackingEnabled,
        },
      })
      .eq('id', org.id);

    // Update or create scheduled report
    const recipients = emailRecipients
      .split(',')
      .map((e) => e.trim())
      .filter((e) => e);

    if (recipients.length > 0) {
      if (reports.length > 0) {
        await supabase
          .from('scheduled_reports')
          .update({ recipients })
          .eq('id', reports[0].id);
      } else {
        await supabase.from('scheduled_reports').insert({
          org_id: org.id,
          report_type: 'weekly',
          recipients,
          enabled: true,
        });
      }
    }

    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function copyApiKey() {
    if (!org) return;
    await navigator.clipboard.writeText(org.id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const getPlanBadge = (plan: string) => {
    switch (plan) {
      case 'enterprise':
        return 'bg-purple-100 text-purple-800';
      case 'pro':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
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
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-600">Manage organization and notification preferences</p>
        </div>
        <button
          onClick={saveSettings}
          className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
        >
          {saved ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
          {saved ? 'Saved!' : 'Save Changes'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Organization */}
        <div className="bg-white rounded-xl shadow-sm border">
          <div className="p-4 border-b">
            <h2 className="font-semibold flex items-center gap-2">
              <Building className="w-5 h-5" />
              Organization
            </h2>
          </div>
          <div className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Organization Name
              </label>
              <input
                type="text"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="My Organization"
              />
            </div>

            {org && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Organization ID
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={org.id}
                      readOnly
                      className="flex-1 px-3 py-2 border rounded-lg bg-gray-50 text-sm font-mono"
                    />
                    <button
                      onClick={copyApiKey}
                      className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                    >
                      {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Use this ID when setting up devices
                  </p>
                </div>

                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <p className="font-medium">Current Plan</p>
                    <p className="text-sm text-gray-500">Access to all features</p>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-sm font-medium ${getPlanBadge(
                      org.plan
                    )}`}
                  >
                    {org.plan.charAt(0).toUpperCase() + org.plan.slice(1)}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Notifications */}
        <div className="bg-white rounded-xl shadow-sm border">
          <div className="p-4 border-b">
            <h2 className="font-semibold flex items-center gap-2">
              <Bell className="w-5 h-5" />
              Notifications
            </h2>
          </div>
          <div className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Report Recipients
              </label>
              <input
                type="text"
                value={emailRecipients}
                onChange={(e) => setEmailRecipients(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="admin@company.com, manager@company.com"
              />
              <p className="text-xs text-gray-500 mt-1">
                Comma-separated email addresses for weekly reports
              </p>
            </div>

            <div className="space-y-3">
              <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-pointer">
                <div>
                  <p className="font-medium">Security Alerts</p>
                  <p className="text-sm text-gray-500">Get notified of security events</p>
                </div>
                <input
                  type="checkbox"
                  checked={alertsEnabled}
                  onChange={(e) => setAlertsEnabled(e.target.checked)}
                  className="w-5 h-5 text-red-600 rounded"
                />
              </label>

              <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-pointer">
                <div>
                  <p className="font-medium">Auto Screenshots</p>
                  <p className="text-sm text-gray-500">Capture screenshots on events</p>
                </div>
                <input
                  type="checkbox"
                  checked={screenshotsEnabled}
                  onChange={(e) => setScreenshotsEnabled(e.target.checked)}
                  className="w-5 h-5 text-red-600 rounded"
                />
              </label>

              <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-pointer">
                <div>
                  <p className="font-medium">Location Tracking</p>
                  <p className="text-sm text-gray-500">Track device locations</p>
                </div>
                <input
                  type="checkbox"
                  checked={locationTrackingEnabled}
                  onChange={(e) => setLocationTrackingEnabled(e.target.checked)}
                  className="w-5 h-5 text-red-600 rounded"
                />
              </label>
            </div>
          </div>
        </div>

        {/* Data Retention */}
        <div className="bg-white rounded-xl shadow-sm border">
          <div className="p-4 border-b">
            <h2 className="font-semibold flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Data Retention
            </h2>
          </div>
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div>
                <p className="font-medium">Events</p>
                <p className="text-sm text-gray-500">Login, unlock, and boot events</p>
              </div>
              <span className="text-sm text-gray-600">90 days</span>
            </div>

            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div>
                <p className="font-medium">Screenshots</p>
                <p className="text-sm text-gray-500">Captured images</p>
              </div>
              <span className="text-sm text-gray-600">30 days</span>
            </div>

            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div>
                <p className="font-medium">Commands</p>
                <p className="text-sm text-gray-500">Remote command history</p>
              </div>
              <span className="text-sm text-gray-600">30 days</span>
            </div>

            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div>
                <p className="font-medium">App Usage</p>
                <p className="text-sm text-gray-500">Productivity tracking data</p>
              </div>
              <span className="text-sm text-gray-600">90 days</span>
            </div>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-white rounded-xl shadow-sm border border-red-200">
          <div className="p-4 border-b border-red-200 bg-red-50">
            <h2 className="font-semibold flex items-center gap-2 text-red-800">
              <Trash2 className="w-5 h-5" />
              Danger Zone
            </h2>
          </div>
          <div className="p-6 space-y-4">
            <div className="p-4 border border-red-200 rounded-lg">
              <h3 className="font-medium text-red-800">Delete All Data</h3>
              <p className="text-sm text-gray-600 mt-1">
                Permanently delete all events, commands, and device data. This action cannot be
                undone.
              </p>
              <button className="mt-3 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors text-sm font-medium">
                Delete All Data
              </button>
            </div>

            <div className="p-4 border border-red-200 rounded-lg">
              <h3 className="font-medium text-red-800">Delete Organization</h3>
              <p className="text-sm text-gray-600 mt-1">
                Permanently delete this organization and all associated data.
              </p>
              <button className="mt-3 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors text-sm font-medium">
                Delete Organization
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
