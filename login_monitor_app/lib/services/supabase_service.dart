import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/device.dart';
import '../models/event.dart';
import '../models/command.dart';

class SupabaseService {
  static const String supabaseUrl = 'https://uldaniwnnwuiyyfygsxa.supabase.co';
  static const String supabaseAnonKey =
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsZGFuaXdubnd1aXl5Znlnc3hhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY4NDY4NjEsImV4cCI6MjA4MjQyMjg2MX0._9OU-el7-1I7aS_VLLdhjjexOFQdg0TQ7LI3KI6a2a4';

  static SupabaseClient get client => Supabase.instance.client;

  static Future<void> initialize() async {
    await Supabase.initialize(
      url: supabaseUrl,
      anonKey: supabaseAnonKey,
    );
  }

  // =========================================================================
  // AUTHENTICATION
  // =========================================================================

  static User? get currentUser => client.auth.currentUser;
  static bool get isLoggedIn => currentUser != null;

  static Future<AuthResponse> signUp(String email, String password) async {
    return await client.auth.signUp(
      email: email,
      password: password,
    );
  }

  static Future<AuthResponse> signIn(String email, String password) async {
    return await client.auth.signInWithPassword(
      email: email,
      password: password,
    );
  }

  static Future<void> signOut() async {
    await client.auth.signOut();
  }

  static Future<void> resetPassword(String email) async {
    await client.auth.resetPasswordForEmail(email);
  }

  // =========================================================================
  // DEVICES
  // =========================================================================

  static Future<List<Device>> getDevices() async {
    final response = await client
        .from('devices')
        .select()
        .eq('user_id', currentUser!.id)
        .order('created_at', ascending: false);

    return (response as List).map((e) => Device.fromJson(e)).toList();
  }

  static Future<Device?> getDevice(String deviceId) async {
    final response =
        await client.from('devices').select().eq('id', deviceId).maybeSingle();

    return response != null ? Device.fromJson(response) : null;
  }

  static Future<Device?> pairDevice(String pairingCode) async {
    // Find device by pairing code
    final device = await client
        .from('devices')
        .select()
        .eq('device_code', pairingCode)
        .maybeSingle();

    if (device == null) {
      throw Exception('Device not found. Check the pairing code.');
    }

    if (device['user_id'] != null) {
      throw Exception('Device is already paired to another account.');
    }

    // Link device to current user
    final updated = await client
        .from('devices')
        .update({'user_id': currentUser!.id})
        .eq('id', device['id'])
        .select()
        .single();

    return Device.fromJson(updated);
  }

  static Future<void> unpairDevice(String deviceId) async {
    await client
        .from('devices')
        .update({'user_id': null})
        .eq('id', deviceId)
        .eq('user_id', currentUser!.id);
  }

  static Stream<List<Device>> streamDevices() {
    return client
        .from('devices')
        .stream(primaryKey: ['id'])
        .eq('user_id', currentUser!.id)
        .map((data) => data.map((e) => Device.fromJson(e)).toList());
  }

  // =========================================================================
  // EVENTS
  // =========================================================================

  static Future<List<MonitorEvent>> getEvents({
    required String deviceId,
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await client
        .from('events')
        .select()
        .eq('device_id', deviceId)
        .order('timestamp', ascending: false)
        .range(offset, offset + limit - 1);

    return (response as List).map((e) => MonitorEvent.fromJson(e)).toList();
  }

  static Future<MonitorEvent?> getEvent(String eventId) async {
    final response =
        await client.from('events').select().eq('id', eventId).maybeSingle();

    return response != null ? MonitorEvent.fromJson(response) : null;
  }

  static Future<void> markEventAsRead(String eventId) async {
    await client.from('events').update({'is_read': true}).eq('id', eventId);
  }

  static Future<int> getUnreadCount(String deviceId) async {
    final response = await client
        .from('events')
        .select('id')
        .eq('device_id', deviceId)
        .eq('is_read', false);

    return (response as List).length;
  }

  static Stream<List<MonitorEvent>> streamEvents(String deviceId) {
    return client
        .from('events')
        .stream(primaryKey: ['id'])
        .eq('device_id', deviceId)
        .order('timestamp', ascending: false)
        .limit(50)
        .map((data) => data.map((e) => MonitorEvent.fromJson(e)).toList());
  }

  // =========================================================================
  // COMMANDS
  // =========================================================================

  static Future<DeviceCommand> sendCommand({
    required String deviceId,
    required String command,
    Map<String, dynamic>? args,
  }) async {
    final response = await client
        .from('commands')
        .insert({
          'device_id': deviceId,
          'command': command,
          'args': args,
          'status': 'pending',
        })
        .select()
        .single();

    return DeviceCommand.fromJson(response);
  }

  static Future<List<DeviceCommand>> getCommands({
    required String deviceId,
    int limit = 20,
  }) async {
    final response = await client
        .from('commands')
        .select()
        .eq('device_id', deviceId)
        .order('created_at', ascending: false)
        .limit(limit);

    return (response as List).map((e) => DeviceCommand.fromJson(e)).toList();
  }

  static Future<DeviceCommand?> getCommand(String commandId) async {
    final response = await client
        .from('commands')
        .select()
        .eq('id', commandId)
        .maybeSingle();

    return response != null ? DeviceCommand.fromJson(response) : null;
  }

  static Stream<List<DeviceCommand>> streamCommands(String deviceId) {
    return client
        .from('commands')
        .stream(primaryKey: ['id'])
        .eq('device_id', deviceId)
        .order('created_at', ascending: false)
        .limit(20)
        .map((data) => data.map((e) => DeviceCommand.fromJson(e)).toList());
  }

  // =========================================================================
  // STORAGE
  // =========================================================================

  static String getPhotoUrl(String path) {
    return client.storage.from('photos').getPublicUrl(path);
  }

  static String getAudioUrl(String path) {
    return client.storage.from('audio').getPublicUrl(path);
  }
}
