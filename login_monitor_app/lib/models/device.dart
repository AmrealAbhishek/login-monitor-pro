class Device {
  final String id;
  final String? userId;
  final String? deviceCode;
  final String? hostname;
  final String? osVersion;
  final DateTime? lastSeen;
  final bool isActive;
  final DateTime createdAt;

  Device({
    required this.id,
    this.userId,
    this.deviceCode,
    this.hostname,
    this.osVersion,
    this.lastSeen,
    this.isActive = true,
    required this.createdAt,
  });

  factory Device.fromJson(Map<String, dynamic> json) {
    return Device(
      id: json['id'] as String,
      userId: json['user_id'] as String?,
      deviceCode: json['device_code'] as String?,
      hostname: json['hostname'] as String?,
      osVersion: json['os_version'] as String?,
      lastSeen: json['last_seen'] != null
          ? DateTime.parse(json['last_seen'] as String)
          : null,
      isActive: json['is_active'] as bool? ?? true,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'device_code': deviceCode,
      'hostname': hostname,
      'os_version': osVersion,
      'last_seen': lastSeen?.toIso8601String(),
      'is_active': isActive,
      'created_at': createdAt.toIso8601String(),
    };
  }

  bool get isOnline {
    if (lastSeen == null) return false;
    return DateTime.now().difference(lastSeen!).inMinutes < 2;
  }

  Device copyWith({
    String? id,
    String? userId,
    String? deviceCode,
    String? hostname,
    String? osVersion,
    DateTime? lastSeen,
    bool? isActive,
    DateTime? createdAt,
  }) {
    return Device(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      deviceCode: deviceCode ?? this.deviceCode,
      hostname: hostname ?? this.hostname,
      osVersion: osVersion ?? this.osVersion,
      lastSeen: lastSeen ?? this.lastSeen,
      isActive: isActive ?? this.isActive,
      createdAt: createdAt ?? this.createdAt,
    );
  }
}
