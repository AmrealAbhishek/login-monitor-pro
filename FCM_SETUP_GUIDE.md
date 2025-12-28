# FCM Push Notifications Setup Guide

## Step 1: Firebase Console Setup

1. Go to https://console.firebase.google.com/
2. Create project: "CyVigil"
3. Add Android app:
   - Package name: `com.loginmonitor.login_monitor_app`
   - App nickname: CyVigil
4. Download `google-services.json`
5. Copy to: `login_monitor_app/android/app/google-services.json`

## Step 2: Get FCM Server Key

1. In Firebase Console → Project Settings (gear icon)
2. Go to "Cloud Messaging" tab
3. Under "Cloud Messaging API (Legacy)" - Enable it if disabled
4. Copy the "Server key" - you'll need this for Supabase

## Step 3: Supabase Database Setup

Run this SQL in Supabase SQL Editor:

```sql
-- Create FCM tokens table
CREATE TABLE IF NOT EXISTS fcm_tokens (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    token TEXT NOT NULL,
    platform TEXT DEFAULT 'android',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE fcm_tokens ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Users can manage their own tokens"
    ON fcm_tokens FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Create function to get tokens for device
CREATE OR REPLACE FUNCTION get_fcm_tokens_for_device(device_uuid UUID)
RETURNS TABLE(token TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT ft.token FROM fcm_tokens ft
    JOIN devices d ON d.user_id = ft.user_id
    WHERE d.id = device_uuid;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

## Step 4: Set Up Database Webhook

1. In Supabase Dashboard → Database → Webhooks
2. Create new webhook:
   - Name: `send_fcm_on_event`
   - Table: `events`
   - Events: INSERT
   - Type: Supabase Edge Function
   - Function: `send-fcm`

## Step 5: Deploy Edge Function

```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Link project
supabase link --project-ref uldaniwnnwuiyyfygsxa

# Set FCM Server Key secret
supabase secrets set FCM_SERVER_KEY=your_fcm_server_key_here

# Deploy function
supabase functions deploy send-fcm
```

## Step 6: Build & Test

```bash
cd login_monitor_app
flutter build apk --release
```

Install APK, login, and test by triggering an event on your Mac.

## Alternative: Simple Python Approach

If Edge Functions are complex, use this Python script on your Mac:

```python
# fcm_notifier.py - Run on Mac
import asyncio
from supabase import create_client
import requests

SUPABASE_URL = "https://uldaniwnnwuiyyfygsxa.supabase.co"
SUPABASE_KEY = "your_service_role_key"
FCM_SERVER_KEY = "your_fcm_server_key"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def send_fcm(token, title, body):
    requests.post(
        'https://fcm.googleapis.com/fcm/send',
        headers={
            'Authorization': f'key={FCM_SERVER_KEY}',
            'Content-Type': 'application/json'
        },
        json={
            'to': token,
            'notification': {'title': title, 'body': body, 'sound': 'default'},
            'priority': 'high'
        }
    )

# Add to screen_watcher.py after creating event
```
