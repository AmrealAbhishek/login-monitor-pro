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
import 'package:iconly/iconly.dart';
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
            content: Row(
              children: [
                Icon(cmd.icon, color: CyberColors.pureWhite, size: 18),
                const SizedBox(width: 8),
                Text('${cmd.name} sent!'),
              ],
            ),
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
                  child: Icon(cmd.commandIcon, color: CyberColors.warningOrange, size: 22),
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
            Icon(cmd.icon, color: CyberColors.primaryRed, size: 28),
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
                        const CommandDefinition(command: 'message', name: 'Message', description: '', icon: IconlyBold.message),
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
                          const CommandDefinition(command: 'audio', name: 'Audio', description: '', icon: IconlyBold.voice),
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
                          const CommandDefinition(command: 'photo', name: 'Photo', description: '', icon: IconlyBold.camera),
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
              child: Center(child: Icon(cmd.commandIcon, color: statusColor, size: 22)),
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
                  Icon(cmd.commandIcon, color: CyberColors.primaryRed, size: 32),
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

    // Route to specialized builders based on command type
    switch (cmd.command.toLowerCase()) {
      case 'battery':
        return _buildBatteryResult(result);
      case 'wifi':
        return _buildWifiResult(result);
      case 'status':
        return _buildStatusResult(result);
      case 'ip':
        return _buildIpResult(result);
      case 'activity':
        return _buildActivityResult(result);
      case 'appusage':
        return _buildAppUsageResult(result);
      case 'listusb':
        return _buildUsbResult(result);
      case 'listnetworks':
        return _buildNetworksResult(result);
      case 'listgeofences':
        return _buildGeofencesResult(result);
      default:
        return _buildGenericResult(cmd, result);
    }
  }

  Widget _buildBatteryResult(Map<String, dynamic> result) {
    // Handle nested battery object
    final batteryData = result['battery'] as Map<String, dynamic>? ?? result;
    final percentage = batteryData['percentage'] ?? batteryData['level'] ?? result['percentage'] ?? 0;
    final isCharging = batteryData['charging'] ?? batteryData['is_charging'] ?? result['charging'] ?? false;
    final powerSource = batteryData['status'] ?? batteryData['power_source'] ?? (isCharging ? 'AC Power' : 'Battery');

    IconData batteryIcon;
    Color batteryColor;

    if (percentage >= 80) {
      batteryIcon = isCharging ? Icons.battery_charging_full : Icons.battery_full;
      batteryColor = CyberColors.successGreen;
    } else if (percentage >= 50) {
      batteryIcon = isCharging ? Icons.battery_charging_full : Icons.battery_5_bar;
      batteryColor = CyberColors.successGreen;
    } else if (percentage >= 20) {
      batteryIcon = isCharging ? Icons.battery_charging_full : Icons.battery_3_bar;
      batteryColor = CyberColors.warningOrange;
    } else {
      batteryIcon = isCharging ? Icons.battery_charging_full : Icons.battery_1_bar;
      batteryColor = CyberColors.alertRed;
    }

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [batteryColor.withOpacity(0.1), CyberColors.surfaceColor],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: batteryColor.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Icon(batteryIcon, size: 64, color: batteryColor),
          const SizedBox(height: 16),
          Text(
            '$percentage%',
            style: TextStyle(
              fontSize: 48,
              fontWeight: FontWeight.bold,
              color: batteryColor,
            ),
          ),
          const SizedBox(height: 8),
          Container(
            height: 8,
            decoration: BoxDecoration(
              color: CyberColors.borderColor,
              borderRadius: BorderRadius.circular(4),
            ),
            child: FractionallySizedBox(
              alignment: Alignment.centerLeft,
              widthFactor: percentage / 100,
              child: Container(
                decoration: BoxDecoration(
                  color: batteryColor,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                isCharging ? Icons.power : Icons.power_off,
                size: 16,
                color: CyberColors.textSecondary,
              ),
              const SizedBox(width: 6),
              Text(
                powerSource,
                style: const TextStyle(color: CyberColors.textSecondary),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildWifiResult(Map<String, dynamic> result) {
    // Handle nested wifi object
    final wifiData = result['wifi'] as Map<String, dynamic>? ?? result;
    final ssid = wifiData['ssid'] ?? wifiData['network'] ?? 'Unknown';
    final bssid = wifiData['bssid'] ?? '';
    final channel = wifiData['channel'] ?? '';
    final rssi = wifiData['rssi'] ?? '';
    final security = wifiData['security'] ?? rssi;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: CyberColors.surfaceColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: CyberColors.primaryRed.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          const Icon(Icons.wifi, size: 56, color: CyberColors.primaryRed),
          const SizedBox(height: 16),
          Text(
            ssid,
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: CyberColors.textPrimary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 20),
          _buildInfoTile(IconlyLight.shield_done, 'Security', security.toString()),
          if (channel.toString().isNotEmpty)
            _buildInfoTile(IconlyLight.graph, 'Channel', channel.toString()),
          if (bssid.toString().isNotEmpty)
            _buildInfoTile(IconlyLight.discovery, 'BSSID', bssid.toString()),
        ],
      ),
    );
  }

  Widget _buildStatusResult(Map<String, dynamic> result) {
    // Handle nested status object
    final statusData = result['status'] as Map<String, dynamic>? ?? result;
    final batteryData = statusData['battery'] as Map<String, dynamic>? ?? {};
    final wifiData = statusData['wifi'] as Map<String, dynamic>? ?? {};

    return Container(
      decoration: BoxDecoration(
        color: CyberColors.surfaceColor,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          if (statusData['hostname'] != null)
            _buildStatusTile(IconlyBold.home, 'Hostname', statusData['hostname'].toString().replaceAll('.local', '')),
          if (statusData['user'] != null)
            _buildStatusTile(IconlyBold.profile, 'User', statusData['user'].toString()),
          if (statusData['platform'] != null)
            _buildStatusTile(IconlyBold.info_circle, 'Platform', statusData['platform'].toString().split('-').first),
          if (statusData['local_ip'] != null)
            _buildStatusTile(IconlyBold.graph, 'Local IP', statusData['local_ip'].toString()),
          if (statusData['public_ip'] != null)
            _buildStatusTile(IconlyBold.discovery, 'Public IP', statusData['public_ip'].toString()),
          if (wifiData['ssid'] != null)
            _buildStatusTile(Icons.wifi, 'WiFi', wifiData['ssid'].toString()),
          if (batteryData['percentage'] != null)
            _buildProgressTile(Icons.battery_full, 'Battery', batteryData['percentage']),
          if (statusData['cpu_usage'] != null)
            _buildProgressTile(IconlyBold.chart, 'CPU', statusData['cpu_usage']),
          if (statusData['memory_usage'] != null)
            _buildProgressTile(IconlyBold.activity, 'Memory', statusData['memory_usage']),
        ],
      ),
    );
  }

  Widget _buildIpResult(Map<String, dynamic> result) {
    final localIp = result['local_ip'] ?? result['ip'] ?? '';
    final publicIp = result['public_ip'] ?? '';
    final interfaces = result['interfaces'] as List? ?? [];

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: CyberColors.surfaceColor,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (localIp.toString().isNotEmpty)
            _buildIpTile('Local IP', localIp.toString(), IconlyBold.home),
          if (publicIp.toString().isNotEmpty)
            _buildIpTile('Public IP', publicIp.toString(), IconlyBold.graph),
          if (interfaces.isNotEmpty) ...[
            const SizedBox(height: 16),
            const Text('Interfaces', style: TextStyle(color: CyberColors.textMuted, fontSize: 12)),
            const SizedBox(height: 8),
            ...interfaces.map((iface) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: CyberColors.darkBackground,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.lan, size: 16, color: CyberColors.textMuted),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        iface.toString(),
                        style: const TextStyle(color: CyberColors.textPrimary, fontFamily: 'monospace'),
                      ),
                    ),
                  ],
                ),
              ),
            )),
          ],
        ],
      ),
    );
  }

  Widget _buildActivityResult(Map<String, dynamic> result) {
    final activities = result['activities'] as List? ?? result['recent'] as List? ?? [];

    if (activities.isEmpty) {
      return const Center(
        child: Text('No recent activity', style: TextStyle(color: CyberColors.textSecondary)),
      );
    }

    return Column(
      children: activities.take(10).map((activity) {
        final time = activity['time'] ?? activity['timestamp'] ?? '';
        final action = activity['action'] ?? activity['event'] ?? activity.toString();
        return Container(
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
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: CyberColors.primaryRed,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      action.toString(),
                      style: const TextStyle(color: CyberColors.textPrimary),
                    ),
                    if (time.toString().isNotEmpty)
                      Text(
                        time.toString(),
                        style: const TextStyle(color: CyberColors.textMuted, fontSize: 11),
                      ),
                  ],
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  Widget _buildAppUsageResult(Map<String, dynamic> result) {
    final apps = result['apps'] as List? ?? result['usage'] as List? ?? [];

    if (apps.isEmpty) {
      return const Center(
        child: Text('No app usage data', style: TextStyle(color: CyberColors.textSecondary)),
      );
    }

    return Column(
      children: apps.take(10).map((app) {
        final name = app['name'] ?? app['app'] ?? 'Unknown';
        final duration = app['duration'] ?? app['time'] ?? 0;
        final percentage = app['percentage'] ?? 0;

        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      name.toString(),
                      style: const TextStyle(color: CyberColors.textPrimary, fontWeight: FontWeight.w500),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Text(
                    duration is int ? '${duration}m' : duration.toString(),
                    style: const TextStyle(color: CyberColors.textSecondary, fontSize: 12),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: (percentage is int ? percentage : 0) / 100,
                  backgroundColor: CyberColors.borderColor,
                  valueColor: const AlwaysStoppedAnimation<Color>(CyberColors.primaryRed),
                  minHeight: 6,
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  Widget _buildUsbResult(Map<String, dynamic> result) {
    final devices = result['devices'] as List? ?? result['usb'] as List? ?? [];

    if (devices.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(32),
        child: const Column(
          children: [
            Icon(Icons.usb_off, size: 48, color: CyberColors.textMuted),
            SizedBox(height: 12),
            Text('No USB devices connected', style: TextStyle(color: CyberColors.textSecondary)),
          ],
        ),
      );
    }

    return Column(
      children: devices.map((device) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: CyberColors.surfaceColor,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: CyberColors.borderColor),
        ),
        child: Row(
          children: [
            const Icon(Icons.usb, color: CyberColors.primaryRed),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                device.toString(),
                style: const TextStyle(color: CyberColors.textPrimary),
              ),
            ),
          ],
        ),
      )).toList(),
    );
  }

  Widget _buildNetworksResult(Map<String, dynamic> result) {
    final currentNetwork = result['current_network'] as Map<String, dynamic>?;
    final whitelisted = result['whitelisted_networks'] as List? ?? result['networks'] as List? ?? [];
    final tip = result['tip'] as String?;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Current Network Section
        if (currentNetwork != null) ...[
          const Text('Current Network', style: TextStyle(color: CyberColors.textMuted, fontSize: 12, fontWeight: FontWeight.w500)),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [CyberColors.primaryRed.withOpacity(0.1), CyberColors.surfaceColor],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: CyberColors.primaryRed.withOpacity(0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.wifi, color: CyberColors.primaryRed, size: 28),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        currentNetwork['ssid']?.toString() ?? 'Unknown',
                        style: const TextStyle(color: CyberColors.textPrimary, fontWeight: FontWeight.bold, fontSize: 18),
                      ),
                    ),
                    if (currentNetwork['is_whitelisted'] == true)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: CyberColors.successGreen.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: CyberColors.successGreen.withOpacity(0.3)),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.check_circle, color: CyberColors.successGreen, size: 14),
                            SizedBox(width: 4),
                            Text('Trusted', style: TextStyle(color: CyberColors.successGreen, fontSize: 11)),
                          ],
                        ),
                      ),
                  ],
                ),
                if (currentNetwork['channel']?.toString().isNotEmpty == true ||
                    currentNetwork['bssid']?.toString().isNotEmpty == true) ...[
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 12,
                    runSpacing: 8,
                    children: [
                      if (currentNetwork['channel']?.toString().isNotEmpty == true)
                        _buildNetworkChip(Icons.settings_input_antenna, 'Ch ${currentNetwork['channel']}'),
                      if (currentNetwork['rssi']?.toString().isNotEmpty == true)
                        _buildNetworkChip(Icons.signal_cellular_alt, currentNetwork['rssi'].toString()),
                      if (currentNetwork['security']?.toString().isNotEmpty == true)
                        _buildNetworkChip(Icons.lock, currentNetwork['security'].toString()),
                    ],
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 20),
        ],

        // Whitelisted Networks Section
        Row(
          children: [
            const Text('Whitelisted Networks', style: TextStyle(color: CyberColors.textMuted, fontSize: 12, fontWeight: FontWeight.w500)),
            const Spacer(),
            Text('${whitelisted.length}', style: const TextStyle(color: CyberColors.primaryRed, fontSize: 12, fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 8),
        if (whitelisted.isEmpty)
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: CyberColors.surfaceColor,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: CyberColors.borderColor),
            ),
            child: Column(
              children: [
                const Icon(Icons.wifi_protected_setup, size: 40, color: CyberColors.textMuted),
                const SizedBox(height: 12),
                const Text('No whitelisted networks', style: TextStyle(color: CyberColors.textSecondary)),
                if (tip != null) ...[
                  const SizedBox(height: 8),
                  Text(tip, style: const TextStyle(color: CyberColors.textMuted, fontSize: 11), textAlign: TextAlign.center),
                ],
              ],
            ),
          )
        else
          ...whitelisted.map((network) => Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: CyberColors.surfaceColor,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: CyberColors.borderColor),
            ),
            child: Row(
              children: [
                Icon(
                  network.toString() == currentNetwork?['ssid'] ? Icons.wifi : Icons.wifi_outlined,
                  color: network.toString() == currentNetwork?['ssid'] ? CyberColors.successGreen : CyberColors.textMuted,
                  size: 20,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    network.toString(),
                    style: TextStyle(
                      color: network.toString() == currentNetwork?['ssid'] ? CyberColors.textPrimary : CyberColors.textSecondary,
                      fontWeight: network.toString() == currentNetwork?['ssid'] ? FontWeight.w500 : FontWeight.normal,
                    ),
                  ),
                ),
                if (network.toString() == currentNetwork?['ssid'])
                  const Text('Connected', style: TextStyle(color: CyberColors.successGreen, fontSize: 11)),
              ],
            ),
          )),
      ],
    );
  }

  Widget _buildNetworkChip(IconData icon, String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: CyberColors.darkBackground,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: CyberColors.textMuted),
          const SizedBox(width: 6),
          Text(label, style: const TextStyle(color: CyberColors.textSecondary, fontSize: 12)),
        ],
      ),
    );
  }

  Widget _buildGeofencesResult(Map<String, dynamic> result) {
    final geofences = result['geofences'] as List? ?? [];

    if (geofences.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(32),
        child: const Column(
          children: [
            Icon(IconlyLight.location, size: 48, color: CyberColors.textMuted),
            SizedBox(height: 12),
            Text('No geofences configured', style: TextStyle(color: CyberColors.textSecondary)),
          ],
        ),
      );
    }

    return Column(
      children: geofences.map((fence) {
        final name = fence['name'] ?? 'Unnamed';
        final radius = fence['radius'] ?? 0;
        return Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: CyberColors.surfaceColor,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: CyberColors.borderColor),
          ),
          child: Row(
            children: [
              const Icon(IconlyBold.location, color: CyberColors.primaryRed),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(name.toString(), style: const TextStyle(color: CyberColors.textPrimary, fontWeight: FontWeight.w500)),
                    Text('Radius: ${radius}m', style: const TextStyle(color: CyberColors.textMuted, fontSize: 12)),
                  ],
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  Widget _buildGenericResult(DeviceCommand cmd, Map<String, dynamic> result) {
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

    // Handle other data with nice cards
    result.forEach((key, value) {
      if (!['success', 'photo_urls', 'audio_url', 'screenshot_url', 'location', 'google_maps'].contains(key)) {
        widgets.add(_buildModernDataRow(key, value));
      }
    });

    if (widgets.isEmpty) {
      widgets.add(const Text('Command completed', style: TextStyle(color: CyberColors.successGreen)));
    }

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: widgets);
  }

  // Helper widgets for result display
  Widget _buildInfoTile(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, size: 18, color: CyberColors.textMuted),
          const SizedBox(width: 12),
          Text(label, style: const TextStyle(color: CyberColors.textMuted, fontSize: 13)),
          const Spacer(),
          Text(value, style: const TextStyle(color: CyberColors.textPrimary, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }

  Widget _buildStatusTile(IconData icon, String label, String value) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: CyberColors.borderColor, width: 0.5)),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: CyberColors.primaryRed.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: CyberColors.primaryRed, size: 20),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(color: CyberColors.textMuted, fontSize: 12)),
                const SizedBox(height: 2),
                Text(value, style: const TextStyle(color: CyberColors.textPrimary, fontWeight: FontWeight.w500)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressTile(IconData icon, String label, dynamic value) {
    final numValue = value is int ? value : (value is double ? value.toInt() : int.tryParse(value.toString().replaceAll('%', '')) ?? 0);
    final percentage = numValue.clamp(0, 100);

    Color progressColor;
    if (percentage < 50) {
      progressColor = CyberColors.successGreen;
    } else if (percentage < 80) {
      progressColor = CyberColors.warningOrange;
    } else {
      progressColor = CyberColors.alertRed;
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: CyberColors.borderColor, width: 0.5)),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: progressColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: progressColor, size: 20),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(label, style: const TextStyle(color: CyberColors.textMuted, fontSize: 12)),
                    Text('$percentage%', style: TextStyle(color: progressColor, fontWeight: FontWeight.bold)),
                  ],
                ),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: percentage / 100,
                    backgroundColor: CyberColors.borderColor,
                    valueColor: AlwaysStoppedAnimation<Color>(progressColor),
                    minHeight: 6,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildIpTile(String label, String value, IconData icon) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: CyberColors.darkBackground,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: CyberColors.borderColor),
      ),
      child: Row(
        children: [
          Icon(icon, color: CyberColors.primaryRed, size: 24),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(color: CyberColors.textMuted, fontSize: 11)),
                const SizedBox(height: 4),
                Text(
                  value,
                  style: const TextStyle(
                    color: CyberColors.textPrimary,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    fontFamily: 'monospace',
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.copy, size: 18, color: CyberColors.textMuted),
            onPressed: () {
              // Copy to clipboard functionality would go here
            },
          ),
        ],
      ),
    );
  }

  Widget _buildModernDataRow(String key, dynamic value) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: CyberColors.surfaceColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: CyberColors.borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _formatKey(key),
            style: const TextStyle(color: CyberColors.textMuted, fontSize: 11, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 6),
          Text(
            value is Map || value is List ? const JsonEncoder.withIndent('  ').convert(value) : value.toString(),
            style: const TextStyle(color: CyberColors.textPrimary, fontSize: 14),
          ),
        ],
      ),
    );
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
            onPressed: () => _saveAudioFile(audioUrl, 'audio_${DateTime.now().millisecondsSinceEpoch}.wav'),
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
        // Show loading indicator
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Row(
                children: [
                  SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: CyberColors.pureWhite)),
                  SizedBox(width: 12),
                  Text('Loading audio...'),
                ],
              ),
              duration: Duration(seconds: 1),
              backgroundColor: CyberColors.surfaceColor,
            ),
          );
        }

        await _audioPlayer.setSourceUrl(url);
        await _audioPlayer.resume();
        setState(() => _isPlayingAudio = true);

        _audioPlayer.onPlayerComplete.listen((_) {
          if (mounted) setState(() => _isPlayingAudio = false);
        });

        _audioPlayer.onPlayerStateChanged.listen((state) {
          if (state == PlayerState.stopped || state == PlayerState.completed) {
            if (mounted) setState(() => _isPlayingAudio = false);
          }
        });
      }
    } catch (e) {
      setState(() => _isPlayingAudio = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Audio playback error: ${e.toString().split('\n').first}'),
            backgroundColor: CyberColors.alertRed,
            action: SnackBarAction(
              label: 'Open URL',
              textColor: CyberColors.pureWhite,
              onPressed: () => launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication),
            ),
          ),
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
