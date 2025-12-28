// Supabase Edge Function to send FCM Push Notifications
// Deploy with: supabase functions deploy send-fcm

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
const FCM_SERVER_KEY = Deno.env.get('FCM_SERVER_KEY')!

interface EventPayload {
  type: 'INSERT'
  table: string
  record: {
    id: string
    device_id: string
    event_type: string
    username?: string
    hostname?: string
  }
}

serve(async (req) => {
  try {
    const payload: EventPayload = await req.json()

    // Only process INSERT events on events table
    if (payload.type !== 'INSERT' || payload.table !== 'events') {
      return new Response(JSON.stringify({ message: 'Ignored' }), { status: 200 })
    }

    const event = payload.record
    console.log(`Processing event: ${event.event_type} for device ${event.device_id}`)

    // Create Supabase client
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    // Get FCM tokens for this device's owner
    const { data: tokens, error } = await supabase
      .rpc('get_fcm_tokens_for_device', { device_uuid: event.device_id })

    if (error) {
      console.error('Error getting FCM tokens:', error)
      return new Response(JSON.stringify({ error: error.message }), { status: 500 })
    }

    if (!tokens || tokens.length === 0) {
      console.log('No FCM tokens found for device')
      return new Response(JSON.stringify({ message: 'No tokens' }), { status: 200 })
    }

    // Prepare notification
    const notification = {
      title: getNotificationTitle(event.event_type),
      body: getNotificationBody(event.event_type, event.username, event.hostname),
    }

    // Send FCM notification to all tokens
    const results = await Promise.all(
      tokens.map((t: { token: string }) => sendFCMNotification(t.token, notification, event))
    )

    console.log(`Sent ${results.filter(r => r).length} notifications`)

    return new Response(
      JSON.stringify({ success: true, sent: results.filter(r => r).length }),
      { status: 200 }
    )
  } catch (error) {
    console.error('Error:', error)
    return new Response(JSON.stringify({ error: String(error) }), { status: 500 })
  }
})

function getNotificationTitle(eventType: string): string {
  switch (eventType) {
    case 'Login': return '🔐 Mac Login Detected'
    case 'Unlock': return '🔓 Mac Unlocked'
    case 'Wake': return '💡 Mac Woke Up'
    case 'Intruder': return '🚨 INTRUDER ALERT!'
    default: return '📱 Security Event'
  }
}

function getNotificationBody(eventType: string, username?: string, hostname?: string): string {
  const device = hostname || 'Your Mac'
  const user = username || 'Someone'

  switch (eventType) {
    case 'Login': return `${user} logged into ${device}`
    case 'Unlock': return `${device} was unlocked by ${user}`
    case 'Wake': return `${device} woke from sleep`
    case 'Intruder': return `Failed login attempt detected on ${device}!`
    default: return `New event on ${device}`
  }
}

async function sendFCMNotification(
  token: string,
  notification: { title: string; body: string },
  event: any
): Promise<boolean> {
  try {
    const response = await fetch('https://fcm.googleapis.com/fcm/send', {
      method: 'POST',
      headers: {
        'Authorization': `key=${FCM_SERVER_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        to: token,
        notification: {
          title: notification.title,
          body: notification.body,
          sound: 'default',
          android_channel_id: 'cyvigil_fcm',
        },
        data: {
          event_id: event.id,
          event_type: event.event_type,
          device_id: event.device_id,
          click_action: 'FLUTTER_NOTIFICATION_CLICK',
        },
        priority: 'high',
      }),
    })

    const result = await response.json()
    console.log('FCM response:', result)
    return result.success === 1
  } catch (error) {
    console.error('FCM send error:', error)
    return false
  }
}
