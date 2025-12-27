# Supabase Setup Guide for Login Monitor PRO

## Quick Setup (5 minutes)

### Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in
2. Click **New Project**
3. Choose your organization
4. Enter project name: `login-monitor-pro`
5. Set a strong database password
6. Select region closest to you
7. Click **Create new project**

Wait ~2 minutes for the project to initialize.

### Step 2: Run Database Schema

1. In Supabase Dashboard, go to **SQL Editor**
2. Click **New Query**
3. Copy the entire contents of `schema.sql` and paste it
4. Click **Run** (or press Ctrl+Enter)

You should see "Success" for all statements.

### Step 3: Get API Credentials

1. Go to **Project Settings** (gear icon)
2. Click **API** in the sidebar
3. Copy these values:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon public key**: `eyJhbGciOiJIUzI1NiIs...`

### Step 4: Set Up Email (Resend)

For sending pairing codes via email:

1. Go to [resend.com](https://resend.com) and create an account
2. Add and verify your domain (or use their test domain)
3. Go to **API Keys** → Create API Key
4. Copy the API key

### Step 5: Deploy Edge Function

1. Install Supabase CLI:
   ```bash
   npm install -g supabase
   ```

2. Login to Supabase:
   ```bash
   supabase login
   ```

3. Link your project:
   ```bash
   cd /path/to/login-monitor/supabase
   supabase link --project-ref YOUR_PROJECT_REF
   ```
   (Get project ref from Dashboard URL: `supabase.com/project/YOUR_PROJECT_REF`)

4. Set Resend API key as secret:
   ```bash
   supabase secrets set RESEND_API_KEY=re_xxxxxxxxxxxx
   supabase secrets set FROM_EMAIL="Login Monitor PRO <noreply@yourdomain.com>"
   ```

5. Deploy the function:
   ```bash
   supabase functions deploy send-pairing-email
   ```

### Step 6: Update install.sh

Edit `install.sh` and replace the default credentials:

```bash
# ============================================
# DEFAULT SUPABASE CREDENTIALS (Your Project)
# ============================================
DEFAULT_SUPABASE_URL="https://YOUR_PROJECT.supabase.co"
DEFAULT_SUPABASE_KEY="YOUR_ANON_KEY_HERE"
# ============================================
```

---

## Testing

### Test Email Function

```bash
curl -X POST 'https://YOUR_PROJECT.supabase.co/functions/v1/send-pairing-email' \
  -H 'Authorization: Bearer YOUR_ANON_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "your@email.com",
    "pairing_code": "123456",
    "hostname": "Test-Mac",
    "device_id": "test-id"
  }'
```

Expected response:
```json
{"success": true, "message_id": "..."}
```

### Test Device Registration

```bash
curl -X POST 'https://YOUR_PROJECT.supabase.co/rest/v1/devices' \
  -H 'apikey: YOUR_ANON_KEY' \
  -H 'Authorization: Bearer YOUR_ANON_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "hostname": "Test-Mac",
    "os_version": "macOS 15.0",
    "pairing_code": "123456",
    "user_email": "test@example.com"
  }'
```

---

## Free Tier Limits

| Resource | Free Limit | Expected Usage |
|----------|------------|----------------|
| Database | 500 MB | ~50 MB/month |
| Storage | 1 GB | ~500 MB/month |
| Bandwidth | 5 GB | ~1 GB/month |
| Edge Functions | 500K invocations | ~1K/month |
| Real-time | Unlimited | Minimal |

**Verdict**: Free tier is sufficient for personal use with multiple devices.

---

## Troubleshooting

### Email not sending

1. Check Resend API key is set correctly:
   ```bash
   supabase secrets list
   ```

2. Check Edge Function logs:
   ```bash
   supabase functions logs send-pairing-email
   ```

3. Verify domain is verified in Resend dashboard

### Pairing code not working

1. Check if code expired (5 min validity)
2. Verify device exists in database:
   ```sql
   SELECT * FROM devices WHERE pairing_code = '123456';
   ```

### RLS blocking requests

If getting permission errors, check Row Level Security policies in SQL Editor.

---

## Security Notes

1. **anon key** is safe for client-side use (RLS protects data)
2. **service_role key** should NEVER be exposed to clients
3. All API calls are over HTTPS
4. Pairing codes expire in 5 minutes
5. Each device has a unique UUID

---

## File Structure

```
supabase/
├── schema.sql                     # Database schema
├── SETUP.md                       # This file
└── functions/
    └── send-pairing-email/
        └── index.ts               # Email sending function
```
