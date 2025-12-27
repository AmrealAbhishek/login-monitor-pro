class EventLocation {
  final double? latitude;
  final double? longitude;
  final double? accuracy;
  final String? city;
  final String? region;
  final String? country;
  final String? source;

  EventLocation({
    this.latitude,
    this.longitude,
    this.accuracy,
    this.city,
    this.region,
    this.country,
    this.source,
  });

  factory EventLocation.fromJson(Map<String, dynamic>? json) {
    if (json == null) return EventLocation();
    return EventLocation(
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      accuracy: (json['accuracy'] as num?)?.toDouble(),
      city: json['city'] as String?,
      region: json['region'] as String?,
      country: json['country'] as String?,
      source: json['source'] as String?,
    );
  }

  String get displayLocation {
    List<String> parts = [];
    if (city != null) parts.add(city!);
    if (region != null) parts.add(region!);
    if (country != null) parts.add(country!);
    return parts.isNotEmpty ? parts.join(', ') : 'Unknown location';
  }

  bool get hasCoordinates => latitude != null && longitude != null;
}

class BatteryInfo {
  final int? percentage;
  final bool? charging;
  final String? status;

  BatteryInfo({this.percentage, this.charging, this.status});

  factory BatteryInfo.fromJson(Map<String, dynamic>? json) {
    if (json == null) return BatteryInfo();
    return BatteryInfo(
      percentage: json['percentage'] as int?,
      charging: json['charging'] as bool?,
      status: json['status'] as String?,
    );
  }
}

class WifiInfo {
  final String? ssid;
  final String? bssid;
  final int? signal;

  WifiInfo({this.ssid, this.bssid, this.signal});

  factory WifiInfo.fromJson(Map<String, dynamic>? json) {
    if (json == null) return WifiInfo();
    return WifiInfo(
      ssid: json['ssid'] as String?,
      bssid: json['bssid'] as String?,
      signal: json['signal'] as int?,
    );
  }
}

class FaceRecognitionResult {
  final int facesDetected;
  final List<String> knownFaces;
  final List<String> unknownFaces;

  FaceRecognitionResult({
    this.facesDetected = 0,
    this.knownFaces = const [],
    this.unknownFaces = const [],
  });

  factory FaceRecognitionResult.fromJson(Map<String, dynamic>? json) {
    if (json == null) return FaceRecognitionResult();
    return FaceRecognitionResult(
      facesDetected: json['faces_detected'] as int? ?? 0,
      knownFaces: (json['known_faces'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      unknownFaces: (json['unknown_faces'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
    );
  }

  bool get hasUnknownFaces => unknownFaces.isNotEmpty;
}

class MonitorEvent {
  final String id;
  final String deviceId;
  final String eventType;
  final DateTime timestamp;
  final String? hostname;
  final String? username;
  final String? localIp;
  final String? publicIp;
  final EventLocation location;
  final BatteryInfo battery;
  final WifiInfo wifi;
  final FaceRecognitionResult faceRecognition;
  final Map<String, dynamic>? activity;
  final List<String> photos;
  final String? audioUrl;
  final bool isRead;
  final DateTime createdAt;

  MonitorEvent({
    required this.id,
    required this.deviceId,
    required this.eventType,
    required this.timestamp,
    this.hostname,
    this.username,
    this.localIp,
    this.publicIp,
    required this.location,
    required this.battery,
    required this.wifi,
    required this.faceRecognition,
    this.activity,
    this.photos = const [],
    this.audioUrl,
    this.isRead = false,
    required this.createdAt,
  });

  factory MonitorEvent.fromJson(Map<String, dynamic> json) {
    return MonitorEvent(
      id: json['id'] as String,
      deviceId: json['device_id'] as String,
      eventType: json['event_type'] as String? ?? 'Unknown',
      timestamp: DateTime.parse(json['timestamp'] as String),
      hostname: json['hostname'] as String?,
      username: json['username'] as String?,
      localIp: json['local_ip'] as String?,
      publicIp: json['public_ip'] as String?,
      location: EventLocation.fromJson(json['location'] as Map<String, dynamic>?),
      battery: BatteryInfo.fromJson(json['battery'] as Map<String, dynamic>?),
      wifi: WifiInfo.fromJson(json['wifi'] as Map<String, dynamic>?),
      faceRecognition: FaceRecognitionResult.fromJson(
          json['face_recognition'] as Map<String, dynamic>?),
      activity: json['activity'] as Map<String, dynamic>?,
      photos: (json['photos'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      audioUrl: json['audio_url'] as String?,
      isRead: json['is_read'] as bool? ?? false,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  String get eventIcon {
    switch (eventType.toLowerCase()) {
      case 'login':
        return '🔐';
      case 'unlock':
        return '🔓';
      case 'wake':
        return '💡';
      case 'test':
        return '🧪';
      default:
        return '📱';
    }
  }

  bool get hasPhotos => photos.isNotEmpty;
  bool get hasAudio => audioUrl != null && audioUrl!.isNotEmpty;
  bool get hasLocation => location.hasCoordinates;
}
