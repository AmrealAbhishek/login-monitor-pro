import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// Service to handle real-time alerts for Mac unlock/login events
class AlertService {
  static final AlertService _instance = AlertService._internal();
  factory AlertService() => _instance;
  AlertService._internal();

  final FlutterLocalNotificationsPlugin _notifications = FlutterLocalNotificationsPlugin();
  final AudioPlayer _audioPlayer = AudioPlayer();
  RealtimeChannel? _eventsChannel;
  String? _currentDeviceId;
  bool _isInitialized = false;
  bool _soundEnabled = true;
  bool _vibrationEnabled = true;

  /// Initialize the alert service
  Future<void> initialize() async {
    if (_isInitialized) return;

    // Initialize local notifications
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const initSettings = InitializationSettings(android: androidSettings);

    await _notifications.initialize(
      initSettings,
      onDidReceiveNotificationResponse: _onNotificationTap,
    );

    // Request notification permission for Android 13+
    final androidPlugin = _notifications
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();

    if (androidPlugin != null) {
      await androidPlugin.requestNotificationsPermission();

      // Create notification channel for alerts with custom sound
      const androidChannel = AndroidNotificationChannel(
        'cyvigil_alerts',
        'CyVigil Security Alerts',
        description: 'Alerts for Mac unlock and login events',
        importance: Importance.high,
        playSound: true,
        enableVibration: true,
        sound: RawResourceAndroidNotificationSound('alert_sound'),
      );
      await androidPlugin.createNotificationChannel(androidChannel);
    }

    _isInitialized = true;
    print('[AlertService] Initialized successfully');
  }

  /// Subscribe to real-time events for a specific device
  Future<void> subscribeToDevice(String deviceId) async {
    if (!_isInitialized) await initialize();

    // Unsubscribe from previous device
    await unsubscribe();

    _currentDeviceId = deviceId;

    // Subscribe to events table for this device
    _eventsChannel = Supabase.instance.client
        .channel('events_$deviceId')
        .onPostgresChanges(
          event: PostgresChangeEvent.insert,
          schema: 'public',
          table: 'events',
          filter: PostgresChangeFilter(
            type: PostgresChangeFilterType.eq,
            column: 'device_id',
            value: deviceId,
          ),
          callback: _onNewEvent,
        )
        .subscribe();

    print('[AlertService] Subscribed to events for device: $deviceId');
  }

  /// Handle new event from real-time subscription
  void _onNewEvent(PostgresChangePayload payload) {
    final newRecord = payload.newRecord;
    if (newRecord == null) return;

    final eventType = newRecord['event_type'] as String?;
    final username = newRecord['username'] as String?;
    final hostname = newRecord['hostname'] as String?;

    print('[AlertService] New event received: $eventType');

    // Alert for Login, Unlock, Wake, or Intruder events
    if (['Login', 'Unlock', 'Wake', 'Intruder'].contains(eventType)) {
      _showAlert(
        eventType: eventType!,
        username: username,
        hostname: hostname,
      );
    }
  }

  /// Show alert with sound and notification
  Future<void> _showAlert({
    required String eventType,
    String? username,
    String? hostname,
  }) async {
    // Play sound
    if (_soundEnabled) {
      await _playAlertSound(eventType);
    }

    // Vibrate
    if (_vibrationEnabled) {
      HapticFeedback.heavyImpact();
    }

    // Show notification
    final title = _getNotificationTitle(eventType);
    final body = _getNotificationBody(eventType, username, hostname);

    await _notifications.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000,
      title,
      body,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'cyvigil_alerts',
          'CyVigil Security Alerts',
          channelDescription: 'Alerts for Mac unlock and login events',
          importance: Importance.high,
          priority: Priority.high,
          icon: '@mipmap/ic_launcher',
          color: Color(0xFFFF0000),
          playSound: true,
          enableVibration: true,
          visibility: NotificationVisibility.public,
          category: AndroidNotificationCategory.alarm,
          sound: RawResourceAndroidNotificationSound('alert_sound'),
        ),
      ),
    );
    print('[AlertService] Notification shown: $title');
  }

  /// Play alert sound based on event type
  Future<void> _playAlertSound(String eventType) async {
    try {
      // Use system alarm/notification sound
      await _audioPlayer.setReleaseMode(ReleaseMode.release);
      // Play a system-like beep using a short audio tone
      // For now, just trigger vibration as sound fallback
      HapticFeedback.heavyImpact();
      await Future.delayed(const Duration(milliseconds: 100));
      HapticFeedback.heavyImpact();
      await Future.delayed(const Duration(milliseconds: 100));
      HapticFeedback.heavyImpact();
      print('[AlertService] Alert sound played (vibration pattern)');
    } catch (e) {
      print('[AlertService] Could not play sound: $e');
      HapticFeedback.vibrate();
    }
  }

  String _getNotificationTitle(String eventType) {
    switch (eventType) {
      case 'Login':
        return 'Mac Login Detected';
      case 'Unlock':
        return 'Mac Unlocked';
      case 'Wake':
        return 'Mac Woke Up';
      case 'Intruder':
        return 'INTRUDER ALERT!';
      default:
        return 'Security Event';
    }
  }

  String _getNotificationBody(String eventType, String? username, String? hostname) {
    final device = hostname ?? 'Your Mac';
    final user = username ?? 'Someone';

    switch (eventType) {
      case 'Login':
        return '$user logged into $device';
      case 'Unlock':
        return '$device was unlocked by $user';
      case 'Wake':
        return '$device woke from sleep';
      case 'Intruder':
        return 'Failed login attempt detected on $device!';
      default:
        return 'New event on $device';
    }
  }

  void _onNotificationTap(NotificationResponse response) {
    // Navigate to events screen when notification is tapped
    // This will be handled by the app's navigation
    print('[AlertService] Notification tapped: ${response.payload}');
  }

  /// Enable/disable sound alerts
  void setSoundEnabled(bool enabled) {
    _soundEnabled = enabled;
  }

  /// Enable/disable vibration
  void setVibrationEnabled(bool enabled) {
    _vibrationEnabled = enabled;
  }

  /// Unsubscribe from real-time events
  Future<void> unsubscribe() async {
    if (_eventsChannel != null) {
      await Supabase.instance.client.removeChannel(_eventsChannel!);
      _eventsChannel = null;
      _currentDeviceId = null;
      print('[AlertService] Unsubscribed from events');
    }
  }

  /// Dispose resources
  Future<void> dispose() async {
    await unsubscribe();
    await _audioPlayer.dispose();
  }
}
