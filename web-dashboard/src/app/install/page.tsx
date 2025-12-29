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
  Loader2,
  Zap,
  CheckCircle,
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
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-10 h-10 text-red-500 animate-spin" />
          <p className="text-gray-600 dark:text-[#666]">Loading...</p>
        </div>
      </div>
    );
  }

  if (!organization) {
    return (
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl shadow-sm border border-gray-200 dark:border-[#333] p-8 text-center max-w-md mx-auto">
        <div className="w-16 h-16 bg-red-100 dark:bg-red-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <AlertCircle className="w-8 h-8 text-red-500" />
        </div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Not Authenticated</h2>
        <p className="text-gray-600 dark:text-[#666]">Please sign in to view installation instructions.</p>
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
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
          <Download className="w-7 h-7 text-red-500" />
          Install CyVigil Agent
        </h1>
        <p className="text-gray-600 dark:text-[#666] mt-1">
          Deploy the monitoring agent on your organization&apos;s devices
        </p>
      </div>

      {/* Organization Info */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl shadow-sm border border-gray-200 dark:border-[#333] p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <p className="text-xs text-gray-500 dark:text-[#666] uppercase tracking-wider mb-1">Organization</p>
            <p className="text-xl font-bold text-gray-900 dark:text-white">{organization.name}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500 dark:text-[#666] uppercase tracking-wider mb-1">Plan</p>
            <span className="inline-block px-4 py-1.5 bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400 rounded-full text-sm font-semibold capitalize border border-red-200 dark:border-red-500/30">
              {organization.plan}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4 p-4 bg-gray-50 dark:bg-[#111] rounded-xl border border-gray-200 dark:border-[#222]">
          <div className="flex-1">
            <p className="text-xs text-gray-500 dark:text-[#666] uppercase tracking-wider mb-2">Install Token</p>
            <code className="text-lg font-mono font-bold text-gray-900 dark:text-white tracking-[0.2em]">
              {installToken}
            </code>
          </div>
          <button
            onClick={() => copyToClipboard(installToken, 'token')}
            className="p-3 text-gray-500 dark:text-[#666] hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-[#222] rounded-xl transition-all duration-200 border border-transparent hover:border-gray-300 dark:hover:border-[#333]"
          >
            {copied === 'token' ? <Check className="w-5 h-5 text-green-500 dark:text-green-400" /> : <Copy className="w-5 h-5" />}
          </button>
          <button
            onClick={regenerateToken}
            disabled={regenerating}
            className="flex items-center gap-2 px-4 py-2.5 text-sm text-red-600 dark:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-xl transition-all duration-200 border border-transparent hover:border-red-200 dark:hover:border-red-500/30"
          >
            <RefreshCw className={`w-4 h-4 ${regenerating ? 'animate-spin' : ''}`} />
            Regenerate
          </button>
        </div>
        <p className="text-xs text-gray-400 dark:text-[#555] mt-3">
          This token links installed agents to your organization. Keep it secure.
        </p>
      </div>

      {/* Quick Install */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl shadow-sm border border-gray-200 dark:border-[#333] overflow-hidden">
        <div className="p-4 bg-gray-50 dark:bg-gradient-to-r dark:from-[#1A1A1A] dark:to-transparent flex items-center gap-3 border-b border-gray-200 dark:border-[#222]">
          <Apple className="w-6 h-6 text-gray-900 dark:text-white" />
          <span className="text-gray-900 dark:text-white font-semibold">macOS Quick Install</span>
          <Zap className="w-4 h-4 text-yellow-500 ml-auto" />
        </div>
        <div className="p-6">
          <p className="text-gray-600 dark:text-[#888] mb-4">
            Run this single command in Terminal to install the agent:
          </p>
          <div className="relative">
            <pre className="bg-gray-100 dark:bg-[#0D0D0D] text-green-600 dark:text-green-400 p-4 rounded-xl overflow-x-auto text-sm font-mono border border-gray-200 dark:border-[#222]">
              {macInstallCommand}
            </pre>
            <button
              onClick={() => copyToClipboard(macInstallCommand, 'mac-install')}
              className="absolute top-3 right-3 p-2 bg-white dark:bg-[#1A1A1A] hover:bg-gray-50 dark:hover:bg-[#222] rounded-lg transition-all duration-200 border border-gray-200 dark:border-[#333]"
            >
              {copied === 'mac-install' ? (
                <Check className="w-4 h-4 text-green-500 dark:text-green-400" />
              ) : (
                <Copy className="w-4 h-4 text-gray-500 dark:text-[#666]" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Manual Install Steps */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl shadow-sm border border-gray-200 dark:border-[#333] overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-[#222] flex items-center gap-3">
          <Terminal className="w-5 h-5 text-gray-500 dark:text-[#666]" />
          <span className="font-semibold text-gray-900 dark:text-white">Manual Installation Steps</span>
        </div>
        <div className="p-6 space-y-6">
          {manualInstallSteps.map((item) => (
            <div key={item.step}>
              <div className="flex items-center gap-3 mb-3">
                <span className="w-7 h-7 bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400 rounded-lg flex items-center justify-center text-sm font-bold border border-red-200 dark:border-red-500/30">
                  {item.step}
                </span>
                <span className="font-medium text-gray-900 dark:text-white">{item.title}</span>
              </div>
              <div className="relative ml-10">
                <pre className="bg-gray-50 dark:bg-[#111] text-gray-700 dark:text-[#AAA] p-4 rounded-xl overflow-x-auto text-sm font-mono border border-gray-200 dark:border-[#222]">
                  {item.command}
                </pre>
                <button
                  onClick={() => copyToClipboard(item.command, `step-${item.step}`)}
                  className="absolute top-3 right-3 p-2 bg-white dark:bg-[#1A1A1A] hover:bg-gray-50 dark:hover:bg-[#222] rounded-lg border border-gray-200 dark:border-[#333] transition-all duration-200"
                >
                  {copied === `step-${item.step}` ? (
                    <Check className="w-3 h-3 text-green-500 dark:text-green-400" />
                  ) : (
                    <Copy className="w-3 h-3 text-gray-500 dark:text-[#666]" />
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Post-Install Steps */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl shadow-sm border border-gray-200 dark:border-[#333] overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-[#222] flex items-center gap-3">
          <Shield className="w-5 h-5 text-gray-500 dark:text-[#666]" />
          <span className="font-semibold text-gray-900 dark:text-white">After Installation</span>
        </div>
        <div className="p-6 space-y-4">
          <div className="flex items-start gap-4 p-4 bg-gray-50 dark:bg-[#111] rounded-xl border border-gray-200 dark:border-[#222]">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-500/20 rounded-xl flex items-center justify-center flex-shrink-0">
              <CheckCircle className="w-5 h-5 text-green-500 dark:text-green-400" />
            </div>
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Grant Permissions</p>
              <p className="text-sm text-gray-500 dark:text-[#666] mt-1">
                When prompted, grant Screen Recording and Location Services permissions in System Settings.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4 p-4 bg-gray-50 dark:bg-[#111] rounded-xl border border-gray-200 dark:border-[#222]">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-500/20 rounded-xl flex items-center justify-center flex-shrink-0">
              <CheckCircle className="w-5 h-5 text-green-500 dark:text-green-400" />
            </div>
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Verify Connection</p>
              <p className="text-sm text-gray-500 dark:text-[#666] mt-1">
                The device will appear in your dashboard within 30 seconds. Check the Devices page to confirm.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4 p-4 bg-gray-50 dark:bg-[#111] rounded-xl border border-gray-200 dark:border-[#222]">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-500/20 rounded-xl flex items-center justify-center flex-shrink-0">
              <CheckCircle className="w-5 h-5 text-green-500 dark:text-green-400" />
            </div>
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Auto-Start</p>
              <p className="text-sm text-gray-500 dark:text-[#666] mt-1">
                The agent will automatically start on login and run in the background.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Windows Coming Soon */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl shadow-sm p-8 text-center border border-dashed border-gray-300 dark:border-[#333]">
        <div className="w-14 h-14 bg-gray-100 dark:bg-[#222] rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Monitor className="w-7 h-7 text-gray-400 dark:text-[#444]" />
        </div>
        <p className="font-semibold text-gray-600 dark:text-[#888]">Windows Agent</p>
        <p className="text-sm text-gray-500 dark:text-[#555] mt-2">
          Windows support is available in the{' '}
          <a
            href="https://github.com/AmrealAbhishek/login-monitor-windows"
            className="text-red-600 dark:text-red-500 hover:text-red-500 dark:hover:text-red-400 transition-colors"
            target="_blank"
            rel="noopener noreferrer"
          >
            login-monitor-windows
          </a>{' '}
          repository.
        </p>
      </div>

      {/* Uninstall Section */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl shadow-sm border border-gray-200 dark:border-[#333] overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-[#222] flex items-center gap-3">
          <Terminal className="w-5 h-5 text-red-500" />
          <span className="font-semibold text-gray-900 dark:text-white">Uninstall Agent</span>
        </div>
        <div className="p-6">
          <p className="text-gray-600 dark:text-[#888] mb-4">
            To completely remove the CyVigil agent from a Mac, run this command:
          </p>
          <div className="relative">
            <pre className="bg-red-50 dark:bg-[#0D0D0D] text-red-600 dark:text-red-400 p-4 rounded-xl overflow-x-auto text-sm font-mono border border-red-200 dark:border-red-500/20">
              curl -fsSL https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-pro/main/uninstall.sh | bash
            </pre>
            <button
              onClick={() => copyToClipboard('curl -fsSL https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-pro/main/uninstall.sh | bash', 'uninstall')}
              className="absolute top-3 right-3 p-2 bg-white dark:bg-[#1A1A1A] hover:bg-gray-50 dark:hover:bg-[#222] rounded-lg transition-all duration-200 border border-gray-200 dark:border-[#333]"
            >
              {copied === 'uninstall' ? (
                <Check className="w-4 h-4 text-green-500 dark:text-green-400" />
              ) : (
                <Copy className="w-4 h-4 text-gray-500 dark:text-[#666]" />
              )}
            </button>
          </div>
          <p className="text-xs text-gray-400 dark:text-[#555] mt-3">
            This will stop all services, remove LaunchAgents, delete configuration files, and clean up logs.
          </p>
        </div>
      </div>
    </div>
  );
}
