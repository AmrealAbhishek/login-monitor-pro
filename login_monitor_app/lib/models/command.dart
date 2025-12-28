import 'package:flutter/material.dart';
import 'package:iconly/iconly.dart';

enum CommandStatus { pending, executing, completed, failed }

class DeviceCommand {
  final String id;
  final String deviceId;
  final String command;
  final Map<String, dynamic>? args;
  final CommandStatus status;
  final Map<String, dynamic>? result;
  final String? resultUrl;
  final DateTime createdAt;
  final DateTime? executedAt;

  DeviceCommand({
    required this.id,
    required this.deviceId,
    required this.command,
    this.args,
    this.status = CommandStatus.pending,
    this.result,
    this.resultUrl,
    required this.createdAt,
    this.executedAt,
  });

  factory DeviceCommand.fromJson(Map<String, dynamic> json) {
    return DeviceCommand(
      id: json['id'] as String,
      deviceId: json['device_id'] as String,
      command: json['command'] as String,
      args: json['args'] as Map<String, dynamic>?,
      status: _parseStatus(json['status'] as String?),
      result: json['result'] as Map<String, dynamic>?,
      resultUrl: json['result_url'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      executedAt: json['executed_at'] != null
          ? DateTime.parse(json['executed_at'] as String)
          : null,
    );
  }

  static CommandStatus _parseStatus(String? status) {
    switch (status?.toLowerCase()) {
      case 'pending':
        return CommandStatus.pending;
      case 'executing':
        return CommandStatus.executing;
      case 'completed':
        return CommandStatus.completed;
      case 'failed':
        return CommandStatus.failed;
      default:
        return CommandStatus.pending;
    }
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'device_id': deviceId,
      'command': command,
      'args': args,
      'status': status.name,
      'result': result,
      'result_url': resultUrl,
      'created_at': createdAt.toIso8601String(),
      'executed_at': executedAt?.toIso8601String(),
    };
  }

  IconData get commandIcon {
    switch (command.toLowerCase()) {
      case 'photo':
        return IconlyBold.camera;
      case 'location':
        return IconlyBold.location;
      case 'audio':
        return IconlyBold.voice;
      case 'screenshot':
        return IconlyBold.image;
      case 'status':
        return IconlyBold.info_circle;
      case 'battery':
        return Icons.battery_full;  // Material icon for battery
      case 'wifi':
        return Icons.wifi;  // Material icon for wifi
      case 'ip':
        return IconlyBold.graph;
      case 'alarm':
        return IconlyBold.notification;
      case 'lock':
        return IconlyBold.lock;
      case 'message':
        return IconlyBold.message;
      case 'activity':
        return IconlyBold.time_circle;
      case 'addface':
        return IconlyBold.add_user;
      case 'faces':
        return IconlyBold.user_3;
      case 'findme':
        return IconlyBold.volume_up;
      case 'listusb':
        return Icons.usb;  // Material icon for USB
      case 'listnetworks':
        return Icons.cell_tower;  // Material icon for networks
      case 'listgeofences':
        return IconlyBold.discovery;
      case 'appusage':
        return IconlyBold.category;
      case 'generatereport':
        return IconlyBold.document;
      case 'backup':
        return IconlyBold.upload;
      case 'armmotion':
        return IconlyBold.shield_done;
      default:
        return IconlyBold.star;
    }
  }

  IconData get statusIcon {
    switch (status) {
      case CommandStatus.pending:
        return IconlyBold.time_circle;
      case CommandStatus.executing:
        return IconlyBold.swap;
      case CommandStatus.completed:
        return IconlyBold.tick_square;
      case CommandStatus.failed:
        return IconlyBold.close_square;
    }
  }

  bool get isSuccess => status == CommandStatus.completed;
  bool get isPending =>
      status == CommandStatus.pending || status == CommandStatus.executing;
}

// Command definitions for UI
class CommandDefinition {
  final String command;
  final String name;
  final String description;
  final IconData icon;
  final Map<String, dynamic>? defaultArgs;

  const CommandDefinition({
    required this.command,
    required this.name,
    required this.description,
    required this.icon,
    this.defaultArgs,
  });
}

const List<CommandDefinition> availableCommands = [
  // Core Commands
  CommandDefinition(
    command: 'photo',
    name: 'Take Photo',
    description: 'Capture photo from camera',
    icon: IconlyBold.camera,
    defaultArgs: {'count': 1},
  ),
  CommandDefinition(
    command: 'location',
    name: 'Get Location',
    description: 'Get current GPS location',
    icon: IconlyBold.location,
  ),
  CommandDefinition(
    command: 'screenshot',
    name: 'Screenshot',
    description: 'Capture screen',
    icon: IconlyBold.image,
  ),
  CommandDefinition(
    command: 'status',
    name: 'Device Status',
    description: 'Get full device status',
    icon: IconlyBold.info_circle,
  ),
  CommandDefinition(
    command: 'battery',
    name: 'Battery',
    description: 'Get battery status',
    icon: Icons.battery_full,
  ),
  CommandDefinition(
    command: 'wifi',
    name: 'WiFi Info',
    description: 'Get WiFi network info',
    icon: Icons.wifi,
  ),
  CommandDefinition(
    command: 'ip',
    name: 'IP Address',
    description: 'Get IP addresses',
    icon: IconlyBold.graph,
  ),
  CommandDefinition(
    command: 'audio',
    name: 'Record Audio',
    description: 'Record ambient audio',
    icon: IconlyBold.voice,
    defaultArgs: {'duration': 10},
  ),
  CommandDefinition(
    command: 'alarm',
    name: 'Sound Alarm',
    description: 'Play alarm sound',
    icon: IconlyBold.notification,
    defaultArgs: {'duration': 30},
  ),
  CommandDefinition(
    command: 'lock',
    name: 'Lock Screen',
    description: 'Lock the device screen',
    icon: IconlyBold.lock,
  ),
  CommandDefinition(
    command: 'message',
    name: 'Show Message',
    description: 'Display message on screen',
    icon: IconlyBold.message,
    defaultArgs: {'message': 'Alert from Login Monitor', 'title': 'Alert'},
  ),
  CommandDefinition(
    command: 'activity',
    name: 'Recent Activity',
    description: 'Get recent user activity',
    icon: IconlyBold.time_circle,
  ),

  // New v3.0 Security Commands
  CommandDefinition(
    command: 'findme',
    name: 'Find My Mac',
    description: 'Play alarm and track location',
    icon: IconlyBold.volume_up,
    defaultArgs: {'duration': 60},
  ),
  CommandDefinition(
    command: 'listusb',
    name: 'List USB',
    description: 'List connected USB devices',
    icon: Icons.usb,
  ),
  CommandDefinition(
    command: 'listnetworks',
    name: 'List Networks',
    description: 'List known WiFi networks',
    icon: Icons.cell_tower,
  ),
  CommandDefinition(
    command: 'listgeofences',
    name: 'List Geofences',
    description: 'List configured geofences',
    icon: IconlyBold.discovery,
  ),
  CommandDefinition(
    command: 'appusage',
    name: 'App Usage',
    description: 'Get app usage statistics',
    icon: IconlyBold.category,
    defaultArgs: {'hours': 24},
  ),
  CommandDefinition(
    command: 'generatereport',
    name: 'Generate Report',
    description: 'Generate security report',
    icon: IconlyBold.document,
    defaultArgs: {'type': 'daily'},
  ),
  CommandDefinition(
    command: 'backup',
    name: 'Backup Now',
    description: 'Create manual backup',
    icon: IconlyBold.upload,
  ),
  CommandDefinition(
    command: 'armmotion',
    name: 'Arm Motion',
    description: 'Enable motion detection',
    icon: IconlyBold.shield_done,
    defaultArgs: {'enabled': true},
  ),
];
