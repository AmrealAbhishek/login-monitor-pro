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
