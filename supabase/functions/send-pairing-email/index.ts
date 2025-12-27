// Supabase Edge Function: send-pairing-email
// Deploy: supabase functions deploy send-pairing-email
//
// This function sends pairing codes via email using Resend API
// Set your RESEND_API_KEY in Supabase Edge Function secrets

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY");
const FROM_EMAIL = Deno.env.get("FROM_EMAIL") || "Login Monitor PRO <noreply@loginmonitor.app>";

interface PairingEmailRequest {
  email: string;
  pairing_code: string;
  hostname: string;
  device_id: string;
}

serve(async (req: Request) => {
  // Handle CORS
  if (req.method === "OPTIONS") {
    return new Response("ok", {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
      },
    });
  }

  try {
    const { email, pairing_code, hostname, device_id }: PairingEmailRequest = await req.json();

    if (!email || !pairing_code) {
      return new Response(
        JSON.stringify({ success: false, error: "Missing required fields" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    if (!RESEND_API_KEY) {
      console.error("RESEND_API_KEY not configured");
      return new Response(
        JSON.stringify({ success: false, error: "Email service not configured" }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      );
    }

    // Send email via Resend
    const emailResponse = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: FROM_EMAIL,
        to: [email],
        subject: `Your Login Monitor PRO Pairing Code: ${pairing_code}`,
        html: `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background-color: #f5f5f5; }
    .container { max-width: 500px; margin: 0 auto; padding: 20px; }
    .card { background: white; border-radius: 16px; padding: 32px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .logo { text-align: center; margin-bottom: 24px; }
    .logo-text { font-size: 24px; font-weight: bold; color: #1a1a1a; }
    .code-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 24px; text-align: center; margin: 24px 0; }
    .code { font-size: 42px; font-weight: bold; color: white; letter-spacing: 8px; font-family: 'SF Mono', Monaco, monospace; }
    .expires { color: rgba(255,255,255,0.8); font-size: 14px; margin-top: 8px; }
    .device-info { background: #f8f9fa; border-radius: 8px; padding: 16px; margin: 16px 0; }
    .device-row { display: flex; justify-content: space-between; margin: 8px 0; }
    .label { color: #666; }
    .value { color: #1a1a1a; font-weight: 500; }
    .instructions { color: #666; font-size: 14px; line-height: 1.6; }
    .footer { text-align: center; color: #999; font-size: 12px; margin-top: 24px; }
    .warning { background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 12px; margin-top: 16px; font-size: 13px; color: #856404; }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <div class="logo">
        <div class="logo-text">Login Monitor PRO</div>
      </div>

      <p style="text-align: center; color: #666; margin-bottom: 24px;">
        Your device pairing code is ready
      </p>

      <div class="code-box">
        <div class="code">${pairing_code}</div>
        <div class="expires">Valid for 5 minutes</div>
      </div>

      <div class="device-info">
        <div class="device-row">
          <span class="label">Device:</span>
          <span class="value">${hostname || 'Mac'}</span>
        </div>
        <div class="device-row">
          <span class="label">Device ID:</span>
          <span class="value" style="font-size: 11px; font-family: monospace;">${device_id?.substring(0, 8) || ''}...</span>
        </div>
      </div>

      <div class="instructions">
        <strong>To connect your device:</strong>
        <ol style="margin: 12px 0; padding-left: 20px;">
          <li>Open the Login Monitor PRO app on your phone</li>
          <li>Tap "Pair Device" or go to Settings</li>
          <li>Enter the 6-digit code above</li>
        </ol>
      </div>

      <div class="warning">
        <strong>Security Notice:</strong> Never share this code with anyone. Login Monitor PRO will never ask for your code via phone or text.
      </div>

      <div class="footer">
        <p>This is an automated message from Login Monitor PRO</p>
        <p>If you didn't request this code, please ignore this email.</p>
      </div>
    </div>
  </div>
</body>
</html>
        `,
        text: `
Login Monitor PRO - Pairing Code

Your pairing code is: ${pairing_code}

This code is valid for 5 minutes.

Device: ${hostname || 'Mac'}
Device ID: ${device_id?.substring(0, 8) || ''}...

To connect your device:
1. Open the Login Monitor PRO app on your phone
2. Tap "Pair Device" or go to Settings
3. Enter the 6-digit code above

Security Notice: Never share this code with anyone.

If you didn't request this code, please ignore this email.
        `,
      }),
    });

    if (!emailResponse.ok) {
      const error = await emailResponse.text();
      console.error("Resend API error:", error);
      return new Response(
        JSON.stringify({ success: false, error: "Failed to send email" }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      );
    }

    const result = await emailResponse.json();
    console.log("Email sent successfully:", result.id);

    return new Response(
      JSON.stringify({ success: true, message_id: result.id }),
      {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        }
      }
    );

  } catch (error) {
    console.error("Error:", error);
    return new Response(
      JSON.stringify({ success: false, error: error.message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
});
