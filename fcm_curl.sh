#!/bin/bash
# FCM Notification Sender via Curl
# Usage: ./fcm_curl.sh "Title" "Message" [token|broadcast]

TITLE="${1:-Test Notification}"
BODY="${2:-This is a test message}"
TARGET="${3:-broadcast}"

# Get access token
ACCESS_TOKEN=$(cd "$(dirname "$0")" && python3 -c "
from fcm_sender import get_access_token
print(get_access_token())
" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Failed to get access token"
    exit 1
fi

FCM_URL="https://fcm.googleapis.com/v1/projects/cyvigil-monitor/messages:send"

if [ "$TARGET" == "broadcast" ]; then
    # Send to all users
    echo "📢 Sending broadcast to all users..."
    curl -s -X POST "$FCM_URL" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"message\": {
          \"topic\": \"all_users\",
          \"notification\": {
            \"title\": \"$TITLE\",
            \"body\": \"$BODY\"
          },
          \"android\": {
            \"priority\": \"high\",
            \"notification\": {
              \"sound\": \"alert_sound\"
            }
          }
        }
      }"
else
    # Send to specific token
    echo "📱 Sending to device..."
    curl -s -X POST "$FCM_URL" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"message\": {
          \"token\": \"$TARGET\",
          \"notification\": {
            \"title\": \"$TITLE\",
            \"body\": \"$BODY\"
          },
          \"android\": {
            \"priority\": \"high\",
            \"notification\": {
              \"sound\": \"alert_sound\"
            }
          }
        }
      }"
fi

echo ""
echo "✅ Done!"
