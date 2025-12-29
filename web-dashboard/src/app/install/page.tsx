'use client';

import { useEffect, useState } from 'react';
import { supabase, Organization } from '@/lib/supabase';
import {
  Terminal,
  Copy,
  Check,
  Download,
  Apple,
  Monitor,
  Shield,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';

export default function InstallPage() {
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    fetchOrganization();
  }, []);

  async function fetchOrganization() {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      setLoading(false);
      return;
    }

    const { data: memberData } = await supabase
      .from('org_members')
      .select('org_id')
      .eq('user_id', user.id)
      .single();

    if (memberData) {
      const { data: orgData } = await supabase
        .from('organizations')
        .select('*')
        .eq('id', memberData.org_id)
        .single();

      if (orgData) {
        setOrganization(orgData);
      }
    }
    setLoading(false);
  }

  async function regenerateToken() {
    if (!organization) return;
    setRegenerating(true);

    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let newToken = '';
    for (let i = 0; i < 12; i++) {
      newToken += chars.charAt(Math.floor(Math.random() * chars.length));
    }

    const { error } = await supabase
      .from('organizations')
      .update({ install_token: newToken })
      .eq('id', organization.id);

    if (!error) {
      setOrganization({ ...organization, install_token: newToken });
    }
    setRegenerating(false);
  }

  function copyToClipboard(text: string, id: string) {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></div>
      </div>
    );
  }

  if (!organization) {
    return (
      <div className="p-8 text-center">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-gray-900 mb-2">Not Authenticated</h2>
        <p className="text-gray-600">Please sign in to view installation instructions.</p>
      </div>
    );
  }

  const installToken = organization.install_token || 'TOKEN_NOT_SET';
  const orgId = organization.id;

  const macInstallCommand = `curl -fsSL https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-pro/main/install.sh | bash -s -- --org-id="${orgId}" --token="${installToken}"`;

  const manualInstallSteps = [
    {
      step: 1,
      title: 'Download the installer',
      command: `curl -fsSL https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-pro/main/install.sh -o install.sh`,
    },
    {
      step: 2,
      title: 'Make it executable',
      command: 'chmod +x install.sh',
    },
    {
      step: 3,
      title: 'Run with your organization credentials',
      command: `./install.sh --org-id="${orgId}" --token="${installToken}"`,
    },
  ];

  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <Download className="w-7 h-7 text-red-500" />
          Install CyVigil Agent
        </h1>
        <p className="text-gray-600 mt-1">
          Deploy the monitoring agent on your organization&apos;s devices
        </p>
      </div>

      {/* Organization Info */}
      <div className="bg-white rounded-xl border p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-sm text-gray-500">Organization</p>
            <p className="text-xl font-bold text-gray-900">{organization.name}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500">Plan</p>
            <span className="inline-block px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-medium capitalize">
              {organization.plan}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
          <div className="flex-1">
            <p className="text-sm text-gray-500 mb-1">Install Token</p>
            <code className="text-lg font-mono font-bold text-gray-900 tracking-wider">
              {installToken}
            </code>
          </div>
          <button
            onClick={() => copyToClipboard(installToken, 'token')}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
          >
            {copied === 'token' ? <Check className="w-5 h-5 text-green-500" /> : <Copy className="w-5 h-5" />}
          </button>
          <button
            onClick={regenerateToken}
            disabled={regenerating}
            className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${regenerating ? 'animate-spin' : ''}`} />
            Regenerate
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          This token links installed agents to your organization. Keep it secure.
        </p>
      </div>

      {/* Quick Install */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="p-4 bg-gray-900 flex items-center gap-3">
          <Apple className="w-6 h-6 text-white" />
          <span className="text-white font-medium">macOS Quick Install</span>
        </div>
        <div className="p-6">
          <p className="text-gray-600 mb-4">
            Run this single command in Terminal to install the agent:
          </p>
          <div className="relative">
            <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-sm font-mono">
              {macInstallCommand}
            </pre>
            <button
              onClick={() => copyToClipboard(macInstallCommand, 'mac-install')}
              className="absolute top-3 right-3 p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
            >
              {copied === 'mac-install' ? (
                <Check className="w-4 h-4 text-green-400" />
              ) : (
                <Copy className="w-4 h-4 text-gray-300" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Manual Install Steps */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="p-4 border-b flex items-center gap-3">
          <Terminal className="w-5 h-5 text-gray-500" />
          <span className="font-medium text-gray-900">Manual Installation Steps</span>
        </div>
        <div className="p-6 space-y-6">
          {manualInstallSteps.map((item) => (
            <div key={item.step}>
              <div className="flex items-center gap-3 mb-2">
                <span className="w-6 h-6 bg-red-100 text-red-600 rounded-full flex items-center justify-center text-sm font-bold">
                  {item.step}
                </span>
                <span className="font-medium text-gray-900">{item.title}</span>
              </div>
              <div className="relative ml-9">
                <pre className="bg-gray-100 text-gray-800 p-3 rounded-lg overflow-x-auto text-sm font-mono">
                  {item.command}
                </pre>
                <button
                  onClick={() => copyToClipboard(item.command, `step-${item.step}`)}
                  className="absolute top-2 right-2 p-1.5 bg-white hover:bg-gray-50 rounded border transition-colors"
                >
                  {copied === `step-${item.step}` ? (
                    <Check className="w-3 h-3 text-green-500" />
                  ) : (
                    <Copy className="w-3 h-3 text-gray-400" />
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Post-Install Steps */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="p-4 border-b flex items-center gap-3">
          <Shield className="w-5 h-5 text-gray-500" />
          <span className="font-medium text-gray-900">After Installation</span>
        </div>
        <div className="p-6 space-y-4">
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
              <Check className="w-4 h-4 text-green-600" />
            </div>
            <div>
              <p className="font-medium text-gray-900">Grant Permissions</p>
              <p className="text-sm text-gray-600">
                When prompted, grant Screen Recording and Location Services permissions in System Settings.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
              <Check className="w-4 h-4 text-green-600" />
            </div>
            <div>
              <p className="font-medium text-gray-900">Verify Connection</p>
              <p className="text-sm text-gray-600">
                The device will appear in your dashboard within 30 seconds. Check the Devices page to confirm.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
              <Check className="w-4 h-4 text-green-600" />
            </div>
            <div>
              <p className="font-medium text-gray-900">Auto-Start</p>
              <p className="text-sm text-gray-600">
                The agent will automatically start on login and run in the background.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Windows Coming Soon */}
      <div className="bg-gray-50 rounded-xl border border-dashed p-6 text-center">
        <Monitor className="w-12 h-12 text-gray-400 mx-auto mb-3" />
        <p className="font-medium text-gray-700">Windows Agent</p>
        <p className="text-sm text-gray-500">
          Windows support is available in the{' '}
          <a
            href="https://github.com/AmrealAbhishek/login-monitor-windows"
            className="text-red-600 hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            login-monitor-windows
          </a>{' '}
          repository.
        </p>
      </div>

      {/* Uninstall Section */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="p-4 border-b flex items-center gap-3">
          <Terminal className="w-5 h-5 text-red-500" />
          <span className="font-medium text-gray-900">Uninstall Agent</span>
        </div>
        <div className="p-6">
          <p className="text-gray-600 mb-4">
            To completely remove the CyVigil agent from a Mac, run this command:
          </p>
          <div className="relative">
            <pre className="bg-gray-900 text-red-400 p-4 rounded-lg overflow-x-auto text-sm font-mono">
              curl -fsSL https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-pro/main/uninstall.sh | bash
            </pre>
            <button
              onClick={() => copyToClipboard('curl -fsSL https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-pro/main/uninstall.sh | bash', 'uninstall')}
              className="absolute top-3 right-3 p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
            >
              {copied === 'uninstall' ? (
                <Check className="w-4 h-4 text-green-400" />
              ) : (
                <Copy className="w-4 h-4 text-gray-300" />
              )}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-3">
            This will stop all services, remove LaunchAgents, delete configuration files, and clean up logs.
          </p>
        </div>
      </div>
    </div>
  );
}
