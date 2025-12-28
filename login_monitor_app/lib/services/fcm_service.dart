import 'dart:convert';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Background message handler - must be top-level function
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  print('[FCM] Background message: ${message.messageId}');

  // Show local notification for background messages
  await FCMService._showLocalNotification(message);
}

/// Service to handle Firebase Cloud Messaging for push notifications
class FCMService {
  static final FCMService _instance = FCMService._internal();
  factory FCMService() => _instance;
  FCMService._internal();

  static final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  bool _isInitialized = false;
  String? _fcmToken;

  /// Initialize FCM service
  Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      // Initialize Firebase
      await Firebase.initializeApp();
      print('[FCM] Firebase initialized');

      // Initialize local notifications for foreground
      await _initLocalNotifications();

      // Set up background message handler
      FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

      // Request permission
      await _requestPermission();

      // Get FCM token
      await _getAndSaveToken();

      // Subscribe to broadcast topic for announcements
      await FirebaseMessaging.instance.subscribeToTopic('all_users');
      print('[FCM] Subscribed to all_users topic');

      // Set foreground notification presentation options
      await FirebaseMessaging.instance.setForegroundNotificationPresentationOptions(
        alert: true,
        badge: true,
        sound: true,
      );
      print('[FCM] Foreground presentation options set');

      // Listen for token refresh
      FirebaseMessaging.instance.onTokenRefresh.listen((token) {
        print('[FCM] Token refreshed');
        _fcmToken = token;
        _saveTokenToSupabase(token);
      });

      // Handle foreground messages
      FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

      // Handle notification tap when app is in background
      FirebaseMessaging.onMessageOpenedApp.listen(_handleNotificationTap);

      _isInitialized = true;
      print('[FCM] Service initialized successfully');
    } catch (e) {
      print('[FCM] Initialization error: $e');
    }
  }

  /// Initialize local notifications
  Future<void> _initLocalNotifications() async {
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const initSettings = InitializationSettings(android: androidSettings);

    await _localNotifications.initialize(
      initSettings,
      onDidReceiveNotificationResponse: (response) {
        print('[FCM] Local notification tapped: ${response.payload}');
      },
    );

    // Create notification channel with custom sound
    final androidPlugin = _localNotifications
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();

    if (androidPlugin != null) {
      const channel = AndroidNotificationChannel(
        'cyvigil_fcm',
        'CyVigil Alerts',
        description: 'Push notifications for Mac security events',
        importance: Importance.max,
        playSound: true,
        enableVibration: true,
        sound: RawResourceAndroidNotificationSound('alert_sound'),
      );
      await androidPlugin.createNotificationChannel(channel);
      print('[FCM] Notification channel created');
    }
  }

  /// Request notification permission
  Future<void> _requestPermission() async {
    final messaging = FirebaseMessaging.instance;

    final settings = await messaging.requestPermission(
      alert: true,
      announcement: false,
      badge: true,
      carPlay: false,
      criticalAlert: true,
      provisional: false,
      sound: true,
    );

    print('[FCM] Permission status: ${settings.authorizationStatus}');
  }

  /// Get FCM token and save to Supabase
  Future<void> _getAndSaveToken() async {
    try {
      final token = await FirebaseMessaging.instance.getToken();
      if (token != null) {
        _fcmToken = token;
        print('[FCM] Token obtained: ${token.substring(0, 20)}...');
        await _saveTokenToSupabase(token);
      }
    } catch (e) {
      print('[FCM] Error getting token: $e');
    }
  }

  /// Save FCM token to Supabase
  Future<void> _saveTokenToSupabase(String token) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedToken = prefs.getString('fcm_token');

      // Only update if token changed
      if (savedToken == token) {
        print('[FCM] Token unchanged, skipping save');
        return;
      }

      final userId = Supabase.instance.client.auth.currentUser?.id;
      if (userId == null) {
        print('[FCM] No user logged in, cannot save token');
        return;
      }

      // Upsert token to Supabase
      await Supabase.instance.client.from('fcm_tokens').upsert({
        'user_id': userId,
        'token': token,
        'platform': 'android',
        'updated_at': DateTime.now().toIso8601String(),
      }, onConflict: 'user_id');

      // Save locally
      await prefs.setString('fcm_token', token);
      print('[FCM] Token saved to Supabase');
    } catch (e) {
      print('[FCM] Error saving token: $e');
    }
  }

  /// Handle foreground messages
  void _handleForegroundMessage(RemoteMessage message) {
    print('[FCM] ========== FOREGROUND MESSAGE ==========');
    print('[FCM] Title: ${message.notification?.title}');
    print('[FCM] Body: ${message.notification?.body}');
    print('[FCM] Data: ${message.data}');
    _showForegroundNotification(message);
  }

  /// Show notification when app is in foreground
  Future<void> _showForegroundNotification(RemoteMessage message) async {
    try {
      final notification = message.notification;

      // Get title/body from notification or data
      String title = notification?.title ?? message.data['title'] ?? 'CyVigil Alert';
      String body = notification?.body ?? message.data['body'] ?? 'New security event';

      print('[FCM] Showing local notification: $title - $body');

      final id = DateTime.now().millisecondsSinceEpoch ~/ 1000;

      await _localNotifications.show(
        id,
        title,
        body,
        const NotificationDetails(
          android: AndroidNotificationDetails(
            'cyvigil_fcm',
            'CyVigil Alerts',
            channelDescription: 'Push notifications for Mac security events',
            importance: Importance.max,
            priority: Priority.max,
            icon: '@mipmap/ic_launcher',
            playSound: true,
            enableVibration: true,
            sound: RawResourceAndroidNotificationSound('alert_sound'),
            fullScreenIntent: true,
            showWhen: true,
            enableLights: true,
          ),
        ),
        payload: jsonEncode(message.data),
      );
      print('[FCM] ✅ Foreground notification shown with id: $id');
    } catch (e, stack) {
      print('[FCM] ❌ Error showing foreground notification: $e');
      print('[FCM] Stack: $stack');
    }
  }

  /// Handle notification tap
  void _handleNotificationTap(RemoteMessage message) {
    print('[FCM] Notification tapped: ${message.data}');
    // Navigate to events screen or specific event
  }

  /// Show local notification
  static Future<void> _showLocalNotification(RemoteMessage message) async {
    final notification = message.notification;
    final android = message.notification?.android;

    if (notification != null) {
      await _localNotifications.show(
        notification.hashCode,
        notification.title ?? 'CyVigil Alert',
        notification.body ?? 'New security event',
        const NotificationDetails(
          android: AndroidNotificationDetails(
            'cyvigil_fcm',
            'CyVigil Alerts',
            channelDescription: 'Push notifications for Mac security events',
            importance: Importance.high,
            priority: Priority.high,
            icon: '@mipmap/ic_launcher',
            playSound: true,
            enableVibration: true,
            sound: RawResourceAndroidNotificationSound('alert_sound'),
          ),
        ),
        payload: jsonEncode(message.data),
      );
    }
  }

  /// Delete token (for logout)
  Future<void> deleteToken() async {
    try {
      final userId = Supabase.instance.client.auth.currentUser?.id;
      if (userId != null) {
        await Supabase.instance.client
            .from('fcm_tokens')
            .delete()
            .eq('user_id', userId);
      }

      await FirebaseMessaging.instance.deleteToken();

      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('fcm_token');

      _fcmToken = null;
      print('[FCM] Token deleted');
    } catch (e) {
      print('[FCM] Error deleting token: $e');
    }
  }

  /// Get current FCM token
  String? get token => _fcmToken;
}
