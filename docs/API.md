# API Reference

Database schema and API documentation for Login Monitor PRO.

---

## Overview

Login Monitor PRO uses Supabase as the backend:
- **Database:** PostgreSQL
- **Real-time:** Supabase Realtime
- **Storage:** Supabase Storage
- **Auth:** Supabase Auth

---

## Authentication

### Supabase Auth

```javascript
// Sign up
const { user, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password123'
});

// Sign in
const { user, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password123'
});

// Sign out
await supabase.auth.signOut();
```

---

## Database Tables

### devices

Stores paired Mac computers.

```sql
CREATE TABLE devices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  org_id UUID REFERENCES organizations(id),
  device_code VARCHAR(6) UNIQUE,
  hostname TEXT,
  os_version TEXT,
  mac_address TEXT,
  local_ip TEXT,
  public_ip TEXT,
  last_seen TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT true,
  fcm_token TEXT,
  pairing_code VARCHAR(6),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Owner user |
| org_id | UUID | Organization |
| device_code | VARCHAR(6) | Unique device code |
| hostname | TEXT | Computer name |
| os_version | TEXT | macOS version |
| mac_address | TEXT | Hardware identifier |
| local_ip | TEXT | Internal IP |
| public_ip | TEXT | External IP |
| last_seen | TIMESTAMPTZ | Last activity |
| is_active | BOOLEAN | Device active |
| fcm_token | TEXT | Push token |
| pairing_code | VARCHAR(6) | Pairing code |

---

### events

Stores login/unlock/wake events.

```sql
CREATE TABLE events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  hostname TEXT,
  username TEXT,
  local_ip TEXT,
  public_ip TEXT,
  location JSONB DEFAULT '{}',
  battery JSONB DEFAULT '{}',
  wifi JSONB DEFAULT '{}',
  face_recognition JSONB DEFAULT '{}',
  activity JSONB DEFAULT '{}',
  photos TEXT[] DEFAULT '{}',
  audio_url TEXT,
  is_read BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Location JSONB Structure
```json
{
  "latitude": 28.6139,
  "longitude": 77.2090,
  "accuracy": 10,
  "city": "New Delhi",
  "region": "Delhi",
  "country": "India",
  "source": "gps"
}
```

#### Battery JSONB Structure
```json
{
  "percentage": 85,
  "charging": true,
  "ac_power": true,
  "time_remaining": "2:30"
}
```

#### WiFi JSONB Structure
```json
{
  "ssid": "Office-5G",
  "bssid": "AA:BB:CC:DD:EE:FF",
  "rssi": -45,
  "channel": 36
}
```

---

### commands

Stores remote commands.

```sql
CREATE TABLE commands (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  command TEXT NOT NULL,
  args JSONB DEFAULT '{}',
  status TEXT DEFAULT 'pending',
  result JSONB DEFAULT '{}',
  result_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  executed_at TIMESTAMPTZ
);
```

| Status | Description |
|--------|-------------|
| pending | Waiting for device |
| executing | Currently running |
| completed | Success |
| failed | Error occurred |

---

### security_alerts

Stores security threat alerts.

```sql
CREATE TABLE security_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  alert_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  metadata JSONB DEFAULT '{}',
  acknowledged BOOLEAN DEFAULT false,
  acknowledged_by UUID,
  acknowledged_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

| Severity | Description |
|----------|-------------|
| critical | Immediate action required |
| high | Urgent attention needed |
| medium | Should investigate |
| low | Informational |

---

### file_access_events

Stores file monitoring events.

```sql
CREATE TABLE file_access_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  rule_id UUID REFERENCES sensitive_file_rules(id),
  file_path TEXT,
  file_name TEXT,
  file_extension TEXT,
  file_size_bytes BIGINT,
  access_type TEXT,
  destination TEXT,
  app_name TEXT,
  bundle_id TEXT,
  user_name TEXT,
  hostname TEXT,
  screenshot_url TEXT,
  triggered_alert BOOLEAN DEFAULT false,
  alert_severity TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### clipboard_events

Stores clipboard DLP events.

```sql
CREATE TABLE clipboard_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  hostname TEXT,
  username TEXT,
  content_type TEXT,
  content_preview TEXT,
  content_forensic TEXT,
  content_length INTEGER,
  source_app TEXT,
  destination_app TEXT,
  sensitive_data_detected BOOLEAN DEFAULT false,
  sensitive_type TEXT,
  action_taken TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### usb_events

Stores USB monitoring events.

```sql
CREATE TABLE usb_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  hostname TEXT,
  username TEXT,
  event_type TEXT,
  usb_name TEXT,
  usb_vendor TEXT,
  usb_type TEXT,
  file_name TEXT,
  file_path TEXT,
  file_size BIGINT,
  file_extension TEXT,
  action_taken TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### shadow_it_detections

Stores shadow IT detections.

```sql
CREATE TABLE shadow_it_detections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  hostname TEXT,
  username TEXT,
  app_name TEXT,
  app_category TEXT,
  url_accessed TEXT,
  risk_level TEXT,
  action_taken TEXT,
  detection_count INTEGER DEFAULT 1,
  first_detected TIMESTAMPTZ DEFAULT NOW(),
  last_detected TIMESTAMPTZ DEFAULT NOW()
);
```

---

### productivity_scores

Stores daily productivity metrics.

```sql
CREATE TABLE productivity_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  productive_seconds INTEGER DEFAULT 0,
  unproductive_seconds INTEGER DEFAULT 0,
  neutral_seconds INTEGER DEFAULT 0,
  idle_seconds INTEGER DEFAULT 0,
  productivity_score DECIMAL(5,2),
  first_activity TIME,
  last_activity TIME,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(device_id, date)
);
```

---

### keystroke_logs

Stores keystroke logging sessions.

```sql
CREATE TABLE keystroke_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  hostname TEXT,
  username TEXT,
  app_name TEXT,
  window_title TEXT,
  keystroke_count INTEGER DEFAULT 0,
  keystrokes TEXT,
  start_time TIMESTAMPTZ,
  end_time TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API Endpoints

### REST API (Supabase)

Base URL: `https://<project>.supabase.co/rest/v1`

#### Get Devices
```http
GET /devices?user_id=eq.<user_id>
Authorization: Bearer <token>
```

#### Get Events
```http
GET /events?device_id=eq.<device_id>&order=created_at.desc&limit=50
Authorization: Bearer <token>
```

#### Send Command
```http
POST /commands
Authorization: Bearer <token>
Content-Type: application/json

{
  "device_id": "uuid",
  "command": "photo",
  "args": {"count": 3},
  "status": "pending"
}
```

#### Get Alerts
```http
GET /security_alerts?device_id=eq.<device_id>&acknowledged=eq.false
Authorization: Bearer <token>
```

---

## Real-time Subscriptions

### Subscribe to Events

```javascript
const subscription = supabase
  .channel('events')
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'events',
    filter: `device_id=eq.${deviceId}`
  }, (payload) => {
    console.log('New event:', payload.new);
  })
  .subscribe();
```

### Subscribe to Commands

```javascript
const subscription = supabase
  .channel('commands')
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'commands',
    filter: `device_id=eq.${deviceId}`
  }, (payload) => {
    console.log('New command:', payload.new);
  })
  .subscribe();
```

---

## Storage Buckets

### Photos Bucket

```javascript
// Upload photo
const { data, error } = await supabase.storage
  .from('photos')
  .upload(`${deviceId}/${eventId}/photo_1.jpg`, file);

// Get public URL
const { data } = supabase.storage
  .from('photos')
  .getPublicUrl(`${deviceId}/${eventId}/photo_1.jpg`);
```

### Audio Bucket

```javascript
// Upload audio
const { data, error } = await supabase.storage
  .from('audio')
  .upload(`${deviceId}/${eventId}/audio.wav`, file);
```

---

## Row Level Security (RLS)

### Device Access

```sql
-- Users can only see their own devices
CREATE POLICY "Users see own devices" ON devices
  FOR SELECT USING (user_id = auth.uid());

-- Devices can update themselves
CREATE POLICY "Devices update themselves" ON devices
  FOR UPDATE USING (id = current_setting('device.id')::uuid);
```

### Event Access

```sql
-- Users see events from their devices
CREATE POLICY "Users see own events" ON events
  FOR SELECT USING (
    device_id IN (SELECT id FROM devices WHERE user_id = auth.uid())
  );
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| REST API | 1000 req/min |
| Realtime | 100 connections |
| Storage Upload | 50MB/file |
| Storage Download | Unlimited |
