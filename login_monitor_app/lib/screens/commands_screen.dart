import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:gal/gal.dart';
import 'package:share_plus/share_plus.dart';
import 'package:photo_view/photo_view.dart';
import 'package:audioplayers/audioplayers.dart';
import '../main.dart';
import '../models/command.dart';
import '../services/supabase_service.dart';
import '../theme/cyber_theme.dart';

DateTime toIST(DateTime utc) {
  return utc.add(const Duration(hours: 5, minutes: 30));
}

class CommandsScreen extends StatefulWidget {
  const CommandsScreen({super.key});

  @override
  State<CommandsScreen> createState() => _CommandsScreenState();
}

class _CommandsScreenState extends State<CommandsScreen> {
  List<DeviceCommand> _commandHistory = [];
  bool _isLoading = false;
  final AudioPlayer _audioPlayer = AudioPlayer();
  bool _isPlayingAudio = false;
  String _searchQuery = '';
  String _selectedCategory = 'All';
  final _searchController = TextEditingController();

  final List<String> _categories = ['All', 'Info', 'Capture', 'Security', 'Control'];

  Map<String, List<CommandDefinition>> get _categorizedCommands => {
    'Info': availableCommands.where((c) =>
        ['status', 'battery', 'wifi', 'ip', 'activity', 'appusage'].contains(c.command)).toList(),
    'Capture': availableCommands.where((c) =>
        ['photo', 'screenshot', 'audio'].contains(c.command)).toList(),
    'Security': availableCommands.where((c) =>
        ['findme', 'alarm', 'lock', 'listusb', 'listnetworks', 'listgeofences', 'generatereport'].contains(c.command)).toList(),
    'Control': availableCommands.where((c) =>
        ['message', 'backup', 'armmotion', 'location'].contains(c.command)).toList(),
  };

  List<DeviceCommand> get _activeCommands =>
      _commandHistory.where((c) =>
          c.status == CommandStatus.pending ||
          c.status == CommandStatus.executing).toList();

  @override
  void initState() {
    super.initState();
    _loadCommandHistory();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }

  String _formatTime(DateTime dt) {
    final ist = toIST(dt.toUtc());
    return DateFormat('dd/MM hh:mm a').format(ist);
  }

  Future<void> _loadCommandHistory() async {
    final deviceId = context.read<AppState>().selectedDeviceId;
    if (deviceId == null) return;

    setState(() => _isLoading = true);

    try {
      final commands = await SupabaseService.getCommands(deviceId: deviceId);
      setState(() {
        _commandHistory = commands;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _sendCommand(CommandDefinition cmd, {Map<String, dynamic>? customArgs}) async {
    final deviceId = context.read<AppState>().selectedDeviceId;
    if (deviceId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No device selected'),
          backgroundColor: CyberColors.alertRed,
        ),
      );
      return;
    }

    try {
      await SupabaseService.sendCommand(
        deviceId: deviceId,
        command: cmd.command,
        args: customArgs ?? cmd.defaultArgs,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${cmd.icon} ${cmd.name} sent!'),
            backgroundColor: CyberColors.successGreen,
          ),
        );
        _loadCommandHistory();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: CyberColors.alertRed,
          ),
        );
      }
    }
  }

  Future<void> _sendStopCommand() async {
    final deviceId = context.read<AppState>().selectedDeviceId;
    if (deviceId == null) return;

    try {
      await SupabaseService.sendCommand(
        deviceId: deviceId,
        command: 'stop',
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Stop command sent!'),
            backgroundColor: CyberColors.successGreen,
          ),
        );
        await Future.delayed(const Duration(seconds: 2));
        _loadCommandHistory();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: CyberColors.alertRed),
        );
      }
    }
  }

  List<CommandDefinition> get _filteredCommands {
    var commands = _selectedCategory == 'All'
        ? availableCommands
        : _categorizedCommands[_selectedCategory] ?? [];

    if (_searchQuery.isNotEmpty) {
      commands = commands.where((c) =>
          c.name.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          c.command.toLowerCase().contains(_searchQuery.toLowerCase())).toList();
    }

    return commands;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('COMMANDS'),
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            onPressed: () => _showHistorySheet(),
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadCommandHistory,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadCommandHistory,
        color: CyberColors.primaryRed,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Search bar
            _buildSearchBar(),
            const SizedBox(height: 16),

            // Category filters
            _buildCategoryFilters(),
            const SizedBox(height: 20),

            // Active commands (if any)
            if (_activeCommands.isNotEmpty) ...[
              _buildActiveCommandsSection(),
              const SizedBox(height: 24),
            ],

            // Commands grid
            _buildCommandsSection(),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchBar() {
    return Container(
      decoration: BoxDecoration(
        color: CyberColors.surfaceColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: CyberColors.borderColor),
      ),
      child: TextField(
        controller: _searchController,
        onChanged: (value) => setState(() => _searchQuery = value),
        decoration: InputDecoration(
          hintText: 'Search commands...',
          prefixIcon: const Icon(Icons.search, color: CyberColors.textMuted),
          suffixIcon: _searchQuery.isNotEmpty
              ? IconButton(
                  icon: const Icon(Icons.clear, color: CyberColors.textMuted),
                  onPressed: () {
                    _searchController.clear();
                    setState(() => _searchQuery = '');
                  },
                )
              : null,
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        ),
      ),
    );
  }

  Widget _buildCategoryFilters() {
    return SizedBox(
      height: 40,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: _categories.length,
        itemBuilder: (context, index) {
          final category = _categories[index];
          final isSelected = _selectedCategory == category;
          return Padding(
            padding: EdgeInsets.only(right: index < _categories.length - 1 ? 8 : 0),
            child: GestureDetector(
              onTap: () => setState(() => _selectedCategory = category),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  color: isSelected ? CyberColors.primaryRed : CyberColors.surfaceColor,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: isSelected ? CyberColors.primaryRed : CyberColors.borderColor,
                  ),
                ),
                child: Center(
                  child: Text(
                    category,
                    style: TextStyle(
                      color: isSelected ? CyberColors.pureWhite : CyberColors.textSecondary,
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildActiveCommandsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                    color: CyberColors.warningOrange,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                const Text(
                  'Active Commands',
                  style: TextStyle(
                    color: CyberColors.textPrimary,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            TextButton.icon(
              onPressed: _sendStopCommand,
              icon: const Icon(Icons.stop, color: CyberColors.alertRed, size: 18),
              label: const Text('STOP ALL', style: TextStyle(color: CyberColors.alertRed)),
            ),
          ],
        ),
        const SizedBox(height: 12),
        ..._activeCommands.map((cmd) => Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: CyberColors.surfaceColor,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: CyberColors.warningOrange.withOpacity(0.5)),
          ),
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: CyberColors.warningOrange.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Center(
                  child: Text(cmd.commandIcon, style: const TextStyle(fontSize: 20)),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      cmd.command.toUpperCase(),
                      style: const TextStyle(
                        color: CyberColors.textPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      cmd.status == CommandStatus.executing ? 'Executing...' : 'Pending...',
                      style: const TextStyle(
                        color: CyberColors.warningOrange,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: CyberColors.warningOrange,
                ),
              ),
            ],
          ),
        )),
      ],
    );
  }

  Widget _buildCommandsSection() {
    final commands = _filteredCommands;

    if (commands.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(32),
        decoration: BoxDecoration(
          color: CyberColors.surfaceColor,
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Column(
          children: [
            Icon(Icons.search_off, size: 48, color: CyberColors.textMuted),
            SizedBox(height: 12),
            Text(
              'No commands found',
              style: TextStyle(color: CyberColors.textPrimary, fontWeight: FontWeight.bold),
            ),
          ],
        ),
      );
    }

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: 0.85,
      ),
      itemCount: commands.length,
      itemBuilder: (context, index) {
        final cmd = commands[index];
        return _buildCommandCard(cmd);
      },
    );
  }

  Widget _buildCommandCard(CommandDefinition cmd) {
    return GestureDetector(
      onTap: () => _handleCommandTap(cmd),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: CyberColors.surfaceColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: CyberColors.borderColor),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(cmd.icon, style: const TextStyle(fontSize: 28)),
            const SizedBox(height: 8),
            Text(
              cmd.name,
              style: const TextStyle(
                color: CyberColors.textPrimary,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }

  void _handleCommandTap(CommandDefinition cmd) {
    // Commands with options
    if (cmd.command == 'message') {
      _showMessageDialog();
    } else if (cmd.command == 'audio') {
      _showAudioDialog();
    } else if (cmd.command == 'photo') {
      _showPhotoDialog();
    } else if (cmd.command == 'alarm' || cmd.command == 'findme') {
      _showDurationDialog(cmd);
    } else {
      _sendCommand(cmd);
    }
  }

  void _showDurationDialog(CommandDefinition cmd) {
    int duration = cmd.defaultArgs?['duration'] ?? 30;

    showModalBottomSheet(
      context: context,
      backgroundColor: CyberColors.darkBackground,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                cmd.name,
                style: const TextStyle(
                  color: CyberColors.textPrimary,
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 24),
              Text(
                'Duration: ${duration}s',
                style: const TextStyle(color: CyberColors.textSecondary),
              ),
              Slider(
                value: duration.toDouble(),
                min: 10,
                max: 300,
                divisions: 29,
                activeColor: CyberColors.primaryRed,
                onChanged: (value) => setState(() => duration = value.round()),
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [10, 30, 60, 120, 300].map((d) {
                  final label = d < 60 ? '${d}s' : '${d ~/ 60}m';
                  return GestureDetector(
                    onTap: () => setState(() => duration = d),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: duration == d ? CyberColors.primaryRed : CyberColors.surfaceColor,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        label,
                        style: TextStyle(
                          color: duration == d ? CyberColors.pureWhite : CyberColors.textSecondary,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 24),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.pop(context),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: CyberColors.textMuted),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      child: const Text('Cancel', style: TextStyle(color: CyberColors.textMuted)),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: () {
                        Navigator.pop(context);
                        _sendCommand(cmd, customArgs: {'duration': duration});
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: CyberColors.primaryRed,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      child: const Text('Start', style: TextStyle(color: CyberColors.pureWhite)),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showMessageDialog() {
    final messageController = TextEditingController(text: 'Alert from Login Monitor');
    final titleController = TextEditingController(text: 'Alert');

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: CyberColors.darkBackground,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => Padding(
        padding: EdgeInsets.fromLTRB(24, 24, 24, MediaQuery.of(context).viewInsets.bottom + 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Show Message',
              style: TextStyle(color: CyberColors.textPrimary, fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 24),
            TextField(
              controller: titleController,
              decoration: const InputDecoration(labelText: 'Title'),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: messageController,
              decoration: const InputDecoration(labelText: 'Message'),
              maxLines: 3,
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Cancel'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () {
                      Navigator.pop(context);
                      _sendCommand(
                        const CommandDefinition(command: 'message', name: 'Message', description: '', icon: '💬'),
                        customArgs: {'title': titleController.text, 'message': messageController.text},
                      );
                    },
                    style: ElevatedButton.styleFrom(backgroundColor: CyberColors.primaryRed),
                    child: const Text('Send', style: TextStyle(color: CyberColors.pureWhite)),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _showAudioDialog() {
    int duration = 10;

    showModalBottomSheet(
      context: context,
      backgroundColor: CyberColors.darkBackground,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Record Audio',
                style: TextStyle(color: CyberColors.textPrimary, fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 24),
              Text('Duration: ${duration}s', style: const TextStyle(color: CyberColors.textSecondary)),
              Slider(
                value: duration.toDouble(),
                min: 5,
                max: 120,
                divisions: 23,
                activeColor: CyberColors.primaryRed,
                onChanged: (value) => setState(() => duration = value.round()),
              ),
              const SizedBox(height: 24),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('Cancel'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: () {
                        Navigator.pop(context);
                        _sendCommand(
                          const CommandDefinition(command: 'audio', name: 'Audio', description: '', icon: '🎙️'),
                          customArgs: {'duration': duration},
                        );
                      },
                      style: ElevatedButton.styleFrom(backgroundColor: CyberColors.primaryRed),
                      child: const Text('Record', style: TextStyle(color: CyberColors.pureWhite)),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showPhotoDialog() {
    int count = 1;

    showModalBottomSheet(
      context: context,
      backgroundColor: CyberColors.darkBackground,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Take Photo',
                style: TextStyle(color: CyberColors.textPrimary, fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 24),
              Text('Count: $count photo(s)', style: const TextStyle(color: CyberColors.textSecondary)),
              Slider(
                value: count.toDouble(),
                min: 1,
                max: 5,
                divisions: 4,
                activeColor: CyberColors.primaryRed,
                onChanged: (value) => setState(() => count = value.round()),
              ),
              const SizedBox(height: 24),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('Cancel'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: () {
                        Navigator.pop(context);
                        _sendCommand(
                          const CommandDefinition(command: 'photo', name: 'Photo', description: '', icon: '📷'),
                          customArgs: {'count': count},
                        );
                      },
                      style: ElevatedButton.styleFrom(backgroundColor: CyberColors.primaryRed),
                      child: const Text('Capture', style: TextStyle(color: CyberColors.pureWhite)),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showHistorySheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: CyberColors.darkBackground,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.7,
        minChildSize: 0.5,
        maxChildSize: 0.95,
        expand: false,
        builder: (context, scrollController) => Column(
          children: [
            Container(
              margin: const EdgeInsets.only(top: 8),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: CyberColors.textMuted,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text(
                'Command History',
                style: TextStyle(
                  color: CyberColors.textPrimary,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            Expanded(
              child: _commandHistory.isEmpty
                  ? const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.history, size: 48, color: CyberColors.textMuted),
                          SizedBox(height: 12),
                          Text('No commands sent yet', style: TextStyle(color: CyberColors.textSecondary)),
                        ],
                      ),
                    )
                  : ListView.builder(
                      controller: scrollController,
                      padding: const EdgeInsets.all(16),
                      itemCount: _commandHistory.length,
                      itemBuilder: (context, index) {
                        final cmd = _commandHistory[index];
                        return _buildHistoryItem(cmd);
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHistoryItem(DeviceCommand cmd) {
    Color statusColor;
    IconData statusIcon;

    switch (cmd.status) {
      case CommandStatus.completed:
        statusColor = CyberColors.successGreen;
        statusIcon = Icons.check_circle;
        break;
      case CommandStatus.failed:
        statusColor = CyberColors.alertRed;
        statusIcon = Icons.error;
        break;
      case CommandStatus.executing:
        statusColor = CyberColors.warningOrange;
        statusIcon = Icons.sync;
        break;
      default:
        statusColor = CyberColors.textMuted;
        statusIcon = Icons.pending;
    }

    return GestureDetector(
      onTap: () => _showResultDialog(cmd),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: CyberColors.surfaceColor,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: CyberColors.borderColor),
        ),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: statusColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Center(child: Text(cmd.commandIcon, style: const TextStyle(fontSize: 20))),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    cmd.command.toUpperCase(),
                    style: const TextStyle(
                      color: CyberColors.textPrimary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    _formatTime(cmd.createdAt),
                    style: const TextStyle(color: CyberColors.textSecondary, fontSize: 12),
                  ),
                ],
              ),
            ),
            Icon(statusIcon, color: statusColor, size: 20),
          ],
        ),
      ),
    );
  }

  void _showResultDialog(DeviceCommand cmd) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: CyberColors.darkBackground,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.6,
        minChildSize: 0.4,
        maxChildSize: 0.95,
        expand: false,
        builder: (context, scrollController) => SingleChildScrollView(
          controller: scrollController,
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(cmd.commandIcon, style: const TextStyle(fontSize: 32)),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          cmd.command.toUpperCase(),
                          style: const TextStyle(
                            color: CyberColors.textPrimary,
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          _formatTime(cmd.createdAt),
                          style: const TextStyle(color: CyberColors.textSecondary, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  _buildStatusBadge(cmd.status),
                ],
              ),
              const SizedBox(height: 24),

              if (cmd.status == CommandStatus.pending || cmd.status == CommandStatus.executing)
                const Center(
                  child: Column(
                    children: [
                      CircularProgressIndicator(color: CyberColors.primaryRed),
                      SizedBox(height: 16),
                      Text('Waiting for response...', style: TextStyle(color: CyberColors.textSecondary)),
                    ],
                  ),
                )
              else if (cmd.result != null)
                _buildResultContent(cmd)
              else if (cmd.resultUrl != null && cmd.command != 'audio')
                _buildImageResult(cmd)
              else
                Text(
                  cmd.status == CommandStatus.completed ? 'Command completed' : 'Command failed',
                  style: TextStyle(
                    color: cmd.status == CommandStatus.completed ? CyberColors.successGreen : CyberColors.alertRed,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatusBadge(CommandStatus status) {
    Color color;
    String label;

    switch (status) {
      case CommandStatus.completed:
        color = CyberColors.successGreen;
        label = 'Done';
        break;
      case CommandStatus.failed:
        color = CyberColors.alertRed;
        label = 'Failed';
        break;
      case CommandStatus.executing:
        color = CyberColors.warningOrange;
        label = 'Running';
        break;
      default:
        color = CyberColors.textMuted;
        label = 'Pending';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.5)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.bold),
      ),
    );
  }

  Widget _buildResultContent(DeviceCommand cmd) {
    final result = cmd.result!;
    final widgets = <Widget>[];

    // Handle images
    if (result['photo_urls'] != null) {
      widgets.add(_buildPhotoResults(result['photo_urls'] as List));
    }

    // Handle screenshot
    if (cmd.resultUrl != null && cmd.command != 'audio') {
      widgets.add(_buildImageResult(cmd));
    }

    // Handle audio
    if (result['audio_url'] != null || (cmd.command == 'audio' && cmd.resultUrl != null)) {
      widgets.add(_buildAudioResult(cmd));
    }

    // Handle location
    if (result['location'] != null) {
      widgets.add(_buildLocationResult(result['location']));
    }

    // Handle other data
    result.forEach((key, value) {
      if (!['success', 'photo_urls', 'audio_url', 'screenshot_url', 'location', 'google_maps'].contains(key)) {
        widgets.add(_buildDataRow(key, value));
      }
    });

    if (widgets.isEmpty) {
      widgets.add(const Text('No data', style: TextStyle(color: CyberColors.textSecondary)));
    }

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: widgets);
  }

  Widget _buildPhotoResults(List photos) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Photos', style: TextStyle(color: CyberColors.textPrimary, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        ...photos.map((url) => Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Image.network(url, fit: BoxFit.cover),
          ),
        )),
      ],
    );
  }

  Widget _buildImageResult(DeviceCommand cmd) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: Image.network(
            cmd.resultUrl!,
            fit: BoxFit.contain,
            loadingBuilder: (context, child, progress) {
              if (progress == null) return child;
              return const Center(child: CircularProgressIndicator(color: CyberColors.primaryRed));
            },
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: ElevatedButton.icon(
                onPressed: () => _saveToGallery(cmd.resultUrl!, 'screenshot_${DateTime.now().millisecondsSinceEpoch}.png'),
                icon: const Icon(Icons.save, size: 18),
                label: const Text('Save'),
                style: ElevatedButton.styleFrom(backgroundColor: CyberColors.primaryRed),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _showFullscreenImage(cmd.resultUrl!),
                icon: const Icon(Icons.fullscreen, size: 18),
                label: const Text('View'),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildAudioResult(DeviceCommand cmd) {
    final audioUrl = cmd.result?['audio_url'] ?? cmd.resultUrl;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: CyberColors.surfaceColor,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          IconButton(
            onPressed: () => _playAudio(audioUrl),
            icon: Icon(
              _isPlayingAudio ? Icons.stop : Icons.play_arrow,
              color: CyberColors.primaryRed,
              size: 32,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Audio Recording', style: TextStyle(color: CyberColors.textPrimary, fontWeight: FontWeight.bold)),
                if (cmd.result?['duration'] != null)
                  Text('Duration: ${cmd.result!['duration']}s', style: const TextStyle(color: CyberColors.textSecondary, fontSize: 12)),
              ],
            ),
          ),
          IconButton(
            onPressed: () => _saveAudioFile(audioUrl, 'audio_${DateTime.now().millisecondsSinceEpoch}.m4a'),
            icon: const Icon(Icons.download, color: CyberColors.textMuted),
          ),
        ],
      ),
    );
  }

  Widget _buildLocationResult(Map<String, dynamic> location) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: CyberColors.surfaceColor,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Location', style: TextStyle(color: CyberColors.textPrimary, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          if (location['city'] != null)
            Text('${location['city']}, ${location['country'] ?? ''}', style: const TextStyle(color: CyberColors.textSecondary)),
          if (location['latitude'] != null)
            Text('${location['latitude']}, ${location['longitude']}', style: const TextStyle(color: CyberColors.textMuted, fontSize: 12)),
          const SizedBox(height: 12),
          ElevatedButton.icon(
            onPressed: () {
              final url = location['google_maps'] ?? 'https://www.google.com/maps?q=${location['latitude']},${location['longitude']}';
              _openMaps(url);
            },
            icon: const Icon(Icons.map, size: 18),
            label: const Text('Open in Maps'),
            style: ElevatedButton.styleFrom(backgroundColor: CyberColors.primaryRed),
          ),
        ],
      ),
    );
  }

  Widget _buildDataRow(String key, dynamic value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              _formatKey(key),
              style: const TextStyle(color: CyberColors.textMuted, fontSize: 12),
            ),
          ),
          Expanded(
            child: Text(
              value is Map || value is List ? const JsonEncoder.withIndent('  ').convert(value) : value.toString(),
              style: const TextStyle(color: CyberColors.textPrimary),
            ),
          ),
        ],
      ),
    );
  }

  String _formatKey(String key) {
    return key.replaceAll('_', ' ').split(' ').map((w) => w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : '').join(' ');
  }

  // Helper methods from original file
  Future<void> _saveToGallery(String url, String filename) async {
    try {
      await Permission.photos.request();
      final response = await http.get(Uri.parse(url));
      if (response.statusCode == 200) {
        final tempDir = await getTemporaryDirectory();
        final tempPath = '${tempDir.path}/$filename';
        final file = File(tempPath);
        await file.writeAsBytes(response.bodyBytes);
        await Gal.putImage(tempPath);
        await file.delete();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Saved to Gallery!'), backgroundColor: CyberColors.successGreen),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: $e'), backgroundColor: CyberColors.alertRed),
        );
      }
    }
  }

  Future<void> _saveAudioFile(String url, String filename) async {
    try {
      final response = await http.get(Uri.parse(url));
      if (response.statusCode == 200) {
        final directory = await getApplicationDocumentsDirectory();
        final path = '${directory.path}/$filename';
        await File(path).writeAsBytes(response.bodyBytes);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Audio saved: $filename'), backgroundColor: CyberColors.successGreen),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: $e'), backgroundColor: CyberColors.alertRed),
        );
      }
    }
  }

  void _showFullscreenImage(String imageUrl) {
    Navigator.push(context, MaterialPageRoute(
      builder: (context) => Scaffold(
        backgroundColor: Colors.black,
        appBar: AppBar(backgroundColor: Colors.black),
        body: PhotoView(
          imageProvider: NetworkImage(imageUrl),
          minScale: PhotoViewComputedScale.contained,
          maxScale: PhotoViewComputedScale.covered * 3,
        ),
      ),
    ));
  }

  Future<void> _playAudio(String url) async {
    try {
      if (_isPlayingAudio) {
        await _audioPlayer.stop();
        setState(() => _isPlayingAudio = false);
      } else {
        await _audioPlayer.play(UrlSource(url));
        setState(() => _isPlayingAudio = true);
        _audioPlayer.onPlayerComplete.listen((_) {
          if (mounted) setState(() => _isPlayingAudio = false);
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Audio error: $e'), backgroundColor: CyberColors.alertRed),
        );
      }
    }
  }

  Future<void> _openMaps(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}
