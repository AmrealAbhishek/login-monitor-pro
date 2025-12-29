import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Types for our database tables
export interface Device {
  id: string;
  user_id: string;
  device_name: string;
  hostname: string;
  os: string;
  last_seen: string;
  is_online: boolean;
  pairing_code?: string;
  created_at: string;
}

export interface Event {
  id: string;
  device_id: string;
  event_type: string;
  timestamp: string;
  hostname: string;
  user: string;
  public_ip: string;
  local_ip: string;
  location: {
    latitude?: number;
    longitude?: number;
    city?: string;
    country?: string;
    google_maps?: string;
  };
  battery: {
    percentage?: number;
    charging?: boolean;
  };
  wifi: {
    ssid?: string;
  };
  photo_url?: string;
  created_at: string;
}

export interface SecurityAlert {
  id: string;
  device_id: string;
  alert_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  metadata: Record<string, unknown>;
  acknowledged: boolean;
  created_at: string;
}

export interface Command {
  id: string;
  device_id: string;
  command: string;
  args: Record<string, unknown>;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  result: Record<string, unknown>;
  result_url?: string;
  created_at: string;
  executed_at?: string;
}

// UAM Tables
export interface SensitiveFileRule {
  id: string;
  org_id: string | null;
  name: string;
  description: string | null;
  rule_type: 'path_pattern' | 'extension' | 'filename_pattern' | 'content_keyword';
  pattern: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  action: 'alert' | 'alert_screenshot' | 'block' | 'log_only';
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface FileAccessEvent {
  id: string;
  device_id: string;
  rule_id: string | null;
  file_path: string;
  file_name: string;
  file_extension: string | null;
  file_size_bytes: number | null;
  access_type: 'open' | 'read' | 'modify' | 'create' | 'delete' | 'copy' | 'move' | 'rename' | 'print' | 'upload' | 'download';
  destination: string | null;
  app_name: string | null;
  bundle_id: string | null;
  user_name: string | null;
  screenshot_url: string | null;
  triggered_alert: boolean;
  alert_severity: string | null;
  created_at: string;
}

export interface UrlRule {
  id: string;
  org_id: string | null;
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

export interface UrlVisit {
  id: string;
  device_id: string;
  url: string;
  domain: string | null;
  title: string | null;
  browser: string | null;
  source_app: string | null;
  source_bundle_id: string | null;
  category: 'productive' | 'unproductive' | 'social' | 'news' | 'shopping' | 'entertainment' | 'communication' | 'neutral';
  duration_seconds: number;
  is_incognito: boolean;
  triggered_rule_id: string | null;
  screenshot_url: string | null;
  created_at: string;
}

export interface SuspiciousActivityRule {
  id: string;
  org_id: string | null;
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

export interface ActivityTimeline {
  id: string;
  device_id: string;
  minute_timestamp: string;
  status: 'active' | 'idle' | 'away' | 'locked' | 'offline';
  active_app: string | null;
  active_app_bundle: string | null;
  active_window_title: string | null;
  active_url: string | null;
  active_domain: string | null;
  keyboard_events: number;
  mouse_events: number;
  category: 'productive' | 'unproductive' | 'communication' | 'neutral' | null;
}

export interface ProductivityTrend {
  id: string;
  device_id: string;
  week_start: string;
  avg_productivity_score: number | null;
  total_active_hours: number | null;
  total_idle_hours: number | null;
  total_unproductive_hours: number | null;
  top_productive_apps: Record<string, unknown>[] | null;
  top_unproductive_apps: Record<string, unknown>[] | null;
  top_domains: Record<string, unknown>[] | null;
  total_files_accessed: number;
  sensitive_files_accessed: number;
  login_count: number;
  alerts_triggered: number;
  trend_vs_prev_week: number | null;
  trend_direction: 'improving' | 'declining' | 'stable' | null;
}

export interface DeviceGroup {
  id: string;
  org_id: string | null;
  name: string;
  description: string | null;
  color: string;
  icon: string;
  created_at: string;
}

export interface BulkCommandJob {
  id: string;
  org_id: string | null;
  name: string | null;
  command: string;
  args: Record<string, unknown>;
  target_type: 'all' | 'group' | 'selected' | 'online_only';
  target_ids: string[] | null;
  status: 'pending' | 'executing' | 'completed' | 'partial' | 'failed' | 'cancelled';
  total_devices: number;
  completed_devices: number;
  failed_devices: number;
  results: Record<string, unknown>[];
  created_by: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}
