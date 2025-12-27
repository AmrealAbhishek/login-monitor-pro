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

  String get commandIcon {
    switch (command.toLowerCase()) {
      case 'photo':
        return '📷';
      case 'location':
        return '📍';
      case 'audio':
        return '🎙️';
      case 'screenshot':
        return '🖥️';
      case 'status':
        return '📊';
      case 'battery':
        return '🔋';
      case 'wifi':
        return '📶';
      case 'ip':
        return '🌐';
      case 'alarm':
        return '🔔';
      case 'lock':
        return '🔒';
      case 'message':
        return '💬';
      case 'activity':
        return '📝';
      case 'addface':
        return '👤';
      case 'faces':
        return '👥';
      default:
        return '⚡';
    }
  }

  String get statusIcon {
    switch (status) {
      case CommandStatus.pending:
        return '⏳';
      case CommandStatus.executing:
        return '⚙️';
      case CommandStatus.completed:
        return '✅';
      case CommandStatus.failed:
        return '❌';
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
  final String icon;
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
  CommandDefinition(
    command: 'photo',
    name: 'Take Photo',
    description: 'Capture photo from camera',
    icon: '📷',
    defaultArgs: {'count': 1},
  ),
  CommandDefinition(
    command: 'location',
    name: 'Get Location',
    description: 'Get current GPS location',
    icon: '📍',
  ),
  CommandDefinition(
    command: 'screenshot',
    name: 'Screenshot',
    description: 'Capture screen',
    icon: '🖥️',
  ),
  CommandDefinition(
    command: 'status',
    name: 'Device Status',
    description: 'Get full device status',
    icon: '📊',
  ),
  CommandDefinition(
    command: 'battery',
    name: 'Battery',
    description: 'Get battery status',
    icon: '🔋',
  ),
  CommandDefinition(
    command: 'wifi',
    name: 'WiFi Info',
    description: 'Get WiFi network info',
    icon: '📶',
  ),
  CommandDefinition(
    command: 'ip',
    name: 'IP Address',
    description: 'Get IP addresses',
    icon: '🌐',
  ),
  CommandDefinition(
    command: 'audio',
    name: 'Record Audio',
    description: 'Record ambient audio',
    icon: '🎙️',
    defaultArgs: {'duration': 10},
  ),
  CommandDefinition(
    command: 'alarm',
    name: 'Sound Alarm',
    description: 'Play alarm sound',
    icon: '🔔',
    defaultArgs: {'duration': 30},
  ),
  CommandDefinition(
    command: 'lock',
    name: 'Lock Screen',
    description: 'Lock the device screen',
    icon: '🔒',
  ),
  CommandDefinition(
    command: 'message',
    name: 'Show Message',
    description: 'Display message on screen',
    icon: '💬',
    defaultArgs: {'message': 'Alert from Login Monitor', 'title': 'Alert'},
  ),
  CommandDefinition(
    command: 'activity',
    name: 'Recent Activity',
    description: 'Get recent user activity',
    icon: '📝',
  ),
];
