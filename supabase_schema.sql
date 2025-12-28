-- Login Monitor PRO - Supabase Database Schema
-- Run this in Supabase SQL Editor (https://supabase.com/dashboard/project/YOUR_PROJECT/sql)

-- ============================================================================
-- TABLES
-- ============================================================================

-- Devices table (Mac computers being monitored)
CREATE TABLE IF NOT EXISTS devices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  device_code VARCHAR(6) UNIQUE,  -- 6-digit pairing code
  hostname TEXT,
  os_version TEXT,
  mac_address TEXT,
  last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_active BOOLEAN DEFAULT true,
  fcm_token TEXT,  -- For push notifications to this device's owner
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Events table (login/unlock/wake notifications)
CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,  -- Login, Unlock, Wake, Test
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  hostname TEXT,
  username TEXT,
  local_ip TEXT,
  public_ip TEXT,
  location JSONB DEFAULT '{}',   -- {latitude, longitude, accuracy, city, region, country, source}
  battery JSONB DEFAULT '{}',    -- {percentage, charging, status}
  wifi JSONB DEFAULT '{}',       -- {ssid, bssid, signal_strength}
  face_recognition JSONB DEFAULT '{}',  -- {face_count, has_unknown, faces: [...]}
  activity JSONB DEFAULT '{}',   -- {browser_history_count, recent_files, running_apps}
  photos TEXT[] DEFAULT '{}',    -- Array of storage URLs
  audio_url TEXT,                -- Storage URL for audio recording
  is_read BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Commands table (remote commands from app to Mac)
CREATE TABLE IF NOT EXISTS commands (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  command TEXT NOT NULL,     -- photo, location, audio, alarm, lock, status, etc.
  args JSONB DEFAULT '{}',   -- {duration: 10, message: "text", count: 3}
  status TEXT DEFAULT 'pending',  -- pending, executing, completed, failed
  result JSONB DEFAULT '{}',      -- {success: true, data: {...}, error: "..."}
  result_url TEXT,           -- Storage URL for result (photo/audio)
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  executed_at TIMESTAMP WITH TIME ZONE
);

-- User profiles (extends auth.users)
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT,
  display_name TEXT,
  phone_number TEXT,
  avatar_url TEXT,
  fcm_token TEXT,  -- Firebase Cloud Messaging token for push notifications
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- INDEXES (for faster queries)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_events_device_id ON events(device_id);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_commands_device_id ON commands(device_id);
CREATE INDEX IF NOT EXISTS idx_commands_status ON commands(status);
CREATE INDEX IF NOT EXISTS idx_devices_device_code ON devices(device_code);
CREATE INDEX IF NOT EXISTS idx_devices_user_id ON devices(user_id);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Devices: Users can only see/manage their own devices
CREATE POLICY "Users can view own devices" ON devices
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own devices" ON devices
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own devices" ON devices
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own devices" ON devices
  FOR DELETE USING (auth.uid() = user_id);

-- Allow devices to register themselves (before user_id is set)
CREATE POLICY "Devices can register with code" ON devices
  FOR INSERT WITH CHECK (user_id IS NULL AND device_code IS NOT NULL);

-- Allow updating device to link to user
CREATE POLICY "Anyone can claim unclaimed device" ON devices
  FOR UPDATE USING (user_id IS NULL);

-- Events: Users can only see events from their devices
CREATE POLICY "Users can view own events" ON events
  FOR SELECT USING (
    device_id IN (SELECT id FROM devices WHERE user_id = auth.uid())
  );

CREATE POLICY "Devices can insert events" ON events
  FOR INSERT WITH CHECK (
    device_id IN (SELECT id FROM devices WHERE user_id IS NOT NULL)
  );

-- Commands: Users can manage commands for their devices
CREATE POLICY "Users can view own commands" ON commands
  FOR SELECT USING (
    device_id IN (SELECT id FROM devices WHERE user_id = auth.uid())
  );

CREATE POLICY "Users can insert commands" ON commands
  FOR INSERT WITH CHECK (
    device_id IN (SELECT id FROM devices WHERE user_id = auth.uid())
  );

CREATE POLICY "Users can update own commands" ON commands
  FOR UPDATE USING (
    device_id IN (SELECT id FROM devices WHERE user_id = auth.uid())
  );

-- Profiles: Users can only manage their own profile
CREATE POLICY "Users can view own profile" ON profiles
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
  FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile" ON profiles
  FOR INSERT WITH CHECK (auth.uid() = id);

-- ============================================================================
-- STORAGE BUCKETS
-- ============================================================================

-- Create storage buckets for photos, audio, and avatars
INSERT INTO storage.buckets (id, name, public)
VALUES ('photos', 'photos', false)
ON CONFLICT (id) DO NOTHING;

INSERT INTO storage.buckets (id, name, public)
VALUES ('audio', 'audio', false)
ON CONFLICT (id) DO NOTHING;

INSERT INTO storage.buckets (id, name, public)
VALUES ('avatars', 'avatars', true)
ON CONFLICT (id) DO NOTHING;

-- Storage policies for photos bucket
CREATE POLICY "Users can upload photos" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'photos' AND
    auth.uid() IS NOT NULL
  );

CREATE POLICY "Users can view own photos" ON storage.objects
  FOR SELECT USING (
    bucket_id = 'photos' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );

CREATE POLICY "Users can delete own photos" ON storage.objects
  FOR DELETE USING (
    bucket_id = 'photos' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );

-- Storage policies for audio bucket
CREATE POLICY "Users can upload audio" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'audio' AND
    auth.uid() IS NOT NULL
  );

CREATE POLICY "Users can view own audio" ON storage.objects
  FOR SELECT USING (
    bucket_id = 'audio' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );

CREATE POLICY "Users can delete own audio" ON storage.objects
  FOR DELETE USING (
    bucket_id = 'audio' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );

-- Storage policies for avatars bucket (public read, authenticated write)
CREATE POLICY "Anyone can view avatars" ON storage.objects
  FOR SELECT USING (bucket_id = 'avatars');

CREATE POLICY "Users can upload avatars" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'avatars' AND
    auth.uid() IS NOT NULL
  );

CREATE POLICY "Users can update avatars" ON storage.objects
  FOR UPDATE USING (
    bucket_id = 'avatars' AND
    auth.uid() IS NOT NULL
  );

CREATE POLICY "Users can delete avatars" ON storage.objects
  FOR DELETE USING (
    bucket_id = 'avatars' AND
    auth.uid() IS NOT NULL
  );

-- ============================================================================
-- REALTIME
-- ============================================================================

-- Enable realtime for events (Flutter app listens for new events)
ALTER PUBLICATION supabase_realtime ADD TABLE events;

-- Enable realtime for commands (Mac app listens for new commands)
ALTER PUBLICATION supabase_realtime ADD TABLE commands;

-- Enable realtime for devices (status updates)
ALTER PUBLICATION supabase_realtime ADD TABLE devices;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to create user profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email)
  VALUES (NEW.id, NEW.email);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to auto-create profile
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Function to update device last_seen
CREATE OR REPLACE FUNCTION public.update_device_last_seen()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE devices SET last_seen = NOW() WHERE id = NEW.device_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to update last_seen on new event
DROP TRIGGER IF EXISTS on_event_created ON events;
CREATE TRIGGER on_event_created
  AFTER INSERT ON events
  FOR EACH ROW EXECUTE FUNCTION public.update_device_last_seen();

-- ============================================================================
-- DONE!
-- ============================================================================

-- After running this schema:
-- 1. Go to Authentication → Settings → Enable Email auth
-- 2. Go to Database → Replication → Enable realtime for: events, commands, devices
-- 3. Note your Project URL and anon key from Settings → API
