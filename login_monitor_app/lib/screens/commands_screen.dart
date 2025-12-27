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
import '../main.dart';
import '../models/command.dart';
import '../services/supabase_service.dart';
import '../widgets/command_button.dart';
import 'package:audioplayers/audioplayers.dart';

// India Standard Time offset (UTC+5:30)
DateTime toIST(DateTime utc) {
  return utc.add(const Duration(hours: 5, minutes: 30));
}

class CommandsScreen extends StatefulWidget {
  const CommandsScreen({super.key});

  @override
  State<CommandsScreen> createState() => _CommandsScreenState();
}

class _CommandsScreenState extends State<CommandsScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  List<DeviceCommand> _commandHistory = [];
  bool _isLoading = false;
  final AudioPlayer _audioPlayer = AudioPlayer();
  bool _isPlayingAudio = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadCommandHistory();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }

  Future<void> _saveToGallery(String url, String filename) async {
    try {
      // Request permissions
      await Permission.photos.request();
      await Permission.storage.request();

      // Show loading
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Saving to gallery...'), duration: Duration(seconds: 1)),
        );
      }

      final response = await http.get(Uri.parse(url));
      if (response.statusCode == 200) {
        // Save to temp first
        final tempDir = await getTemporaryDirectory();
        final tempPath = '${tempDir.path}/$filename';
        final file = File(tempPath);
        await file.writeAsBytes(response.bodyBytes);

        // Save to gallery using Gal
        await Gal.putImage(tempPath);

        // Clean up temp file
        await file.delete();

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Row(
                children: [
                  Icon(Icons.check_circle, color: Colors.white),
                  SizedBox(width: 8),
                  Text('Saved to Gallery!'),
                ],
              ),
              backgroundColor: Colors.green,
              duration: Duration(seconds: 2),
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to save: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  Future<void> _saveAudioFile(String url, String filename) async {
    try {
      await Permission.storage.request();

      final response = await http.get(Uri.parse(url));
      if (response.statusCode == 200) {
        final directory = await getApplicationDocumentsDirectory();
        final path = '${directory.path}/$filename';
        final file = File(path);
        await file.writeAsBytes(response.bodyBytes);

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Audio saved: $filename'),
              backgroundColor: Colors.green,
              action: SnackBarAction(
                label: 'Share',
                textColor: Colors.white,
                onPressed: () => Share.shareXFiles([XFile(path)]),
              ),
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to save: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  void _showFullscreenImage(String imageUrl) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => Scaffold(
          backgroundColor: Colors.black,
          appBar: AppBar(
            backgroundColor: Colors.black,
            iconTheme: const IconThemeData(color: Colors.white),
            actions: [
              IconButton(
                icon: const Icon(Icons.save_alt),
                onPressed: () {
                  final filename = 'screenshot_${DateTime.now().millisecondsSinceEpoch}.png';
                  _saveToGallery(imageUrl, filename);
                },
              ),
              IconButton(
                icon: const Icon(Icons.share),
                onPressed: () async {
                  final response = await http.get(Uri.parse(imageUrl));
                  if (response.statusCode == 200) {
                    final tempDir = await getTemporaryDirectory();
                    final path = '${tempDir.path}/share_image.png';
                    await File(path).writeAsBytes(response.bodyBytes);
                    await Share.shareXFiles([XFile(path)]);
                  }
                },
              ),
            ],
          ),
          body: PhotoView(
            imageProvider: NetworkImage(imageUrl),
            minScale: PhotoViewComputedScale.contained,
            maxScale: PhotoViewComputedScale.covered * 3,
            backgroundDecoration: const BoxDecoration(color: Colors.black),
          ),
        ),
      ),
    );
  }

  Future<void> _playAudio(String url) async {
    try {
      debugPrint('Audio URL: $url');
      if (_isPlayingAudio) {
        await _audioPlayer.stop();
        setState(() => _isPlayingAudio = false);
      } else {
        // Set release mode to stop when done
        await _audioPlayer.setReleaseMode(ReleaseMode.stop);
        await _audioPlayer.play(UrlSource(url));
        setState(() => _isPlayingAudio = true);

        // Listen for completion
        _audioPlayer.onPlayerComplete.listen((_) {
          if (mounted) {
            setState(() => _isPlayingAudio = false);
          }
        });

        // Listen for errors
        _audioPlayer.onLog.listen((msg) {
          debugPrint('AudioPlayer: $msg');
        });
      }
    } catch (e) {
      debugPrint('Audio error: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Audio error: $e'), backgroundColor: Colors.red),
        );
        setState(() => _isPlayingAudio = false);
      }
    }
  }

  Future<void> _exportActivity(Map<String, dynamic> activity, String format) async {
    try {
      String content;
      String filename;
      final timestamp = DateFormat('yyyyMMdd_HHmmss').format(DateTime.now());

      if (format == 'json') {
        content = const JsonEncoder.withIndent('  ').convert(activity);
        filename = 'activity_$timestamp.json';
      } else {
        // TXT format
        final buffer = StringBuffer();
        buffer.writeln('='.padRight(50, '='));
        buffer.writeln('ACTIVITY REPORT');
        buffer.writeln('Generated: ${_formatTime(DateTime.now())}');
        buffer.writeln('='.padRight(50, '='));
        buffer.writeln();

        void writeSection(String title, dynamic data) {
          buffer.writeln('--- $title ---');
          if (data is List) {
            for (var item in data) {
              buffer.writeln('  - ${item is Map ? (item['name'] ?? item['title'] ?? item.toString()) : item}');
            }
          } else if (data is Map) {
            data.forEach((key, value) {
              buffer.writeln('  $key: $value');
            });
          } else {
            buffer.writeln('  $data');
          }
          buffer.writeln();
        }

        if (activity['running_apps'] != null) {
          writeSection('Running Applications', activity['running_apps']);
        }
        if (activity['browser_history'] != null) {
          writeSection('Browser History', activity['browser_history']);
        }
        if (activity['recent_files'] != null) {
          writeSection('Recent Files', activity['recent_files']);
        }
        if (activity['active_window'] != null) {
          writeSection('Active Window', activity['active_window']);
        }

        content = buffer.toString();
        filename = 'activity_$timestamp.txt';
      }

      // Save and share
      final directory = await getTemporaryDirectory();
      final path = '${directory.path}/$filename';
      await File(path).writeAsString(content);

      await Share.shareXFiles(
        [XFile(path)],
        subject: 'Activity Report - $timestamp',
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Export failed: $e'), backgroundColor: Colors.red),
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

  // Format time in IST (India Standard Time)
  String _formatTime(DateTime dt) {
    final ist = toIST(dt.toUtc());
    return DateFormat('dd/MM/yyyy hh:mm:ss a').format(ist) + ' IST';
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
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  Future<void> _sendCommand(CommandDefinition cmd,
      {Map<String, dynamic>? customArgs}) async {
    final deviceId = context.read<AppState>().selectedDeviceId;
    if (deviceId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No device selected')),
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
            backgroundColor: Colors.green,
          ),
        );
        // Reload history
        _loadCommandHistory();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  void _showMessageDialog() {
    final messageController = TextEditingController(text: 'Alert from Login Monitor');
    final titleController = TextEditingController(text: 'Alert');

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Show Message'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: titleController,
              decoration: const InputDecoration(
                labelText: 'Title',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: messageController,
              decoration: const InputDecoration(
                labelText: 'Message',
                border: OutlineInputBorder(),
              ),
              maxLines: 3,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(context);
              _sendCommand(
                const CommandDefinition(
                  command: 'message',
                  name: 'Show Message',
                  description: 'Display message on screen',
                  icon: '💬',
                ),
                customArgs: {
                  'title': titleController.text,
                  'message': messageController.text,
                },
              );
            },
            child: const Text('Send'),
          ),
        ],
      ),
    );
  }

  void _showAudioDialog() {
    int duration = 10;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Record Audio'),
        content: StatefulBuilder(
          builder: (context, setState) => Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Duration: $duration seconds'),
              Slider(
                value: duration.toDouble(),
                min: 5,
                max: 60,
                divisions: 11,
                label: '$duration s',
                onChanged: (value) {
                  setState(() => duration = value.round());
                },
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(context);
              _sendCommand(
                const CommandDefinition(
                  command: 'audio',
                  name: 'Record Audio',
                  description: 'Record ambient audio',
                  icon: '🎙️',
                ),
                customArgs: {'duration': duration},
              );
            },
            child: const Text('Record'),
          ),
        ],
      ),
    );
  }

  void _showPhotoDialog() {
    int count = 1;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Take Photo'),
        content: StatefulBuilder(
          builder: (context, setState) => Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Number of photos: $count'),
              Slider(
                value: count.toDouble(),
                min: 1,
                max: 5,
                divisions: 4,
                label: '$count',
                onChanged: (value) {
                  setState(() => count = value.round());
                },
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(context);
              _sendCommand(
                const CommandDefinition(
                  command: 'photo',
                  name: 'Take Photo',
                  description: 'Capture photo from camera',
                  icon: '📷',
                ),
                customArgs: {'count': count},
              );
            },
            child: const Text('Capture'),
          ),
        ],
      ),
    );
  }

  void _showResultDialog(DeviceCommand cmd) {
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Row(
            children: [
              Text(cmd.commandIcon, style: const TextStyle(fontSize: 24)),
              const SizedBox(width: 8),
              Expanded(child: Text(cmd.command.toUpperCase())),
              Text(cmd.statusIcon, style: const TextStyle(fontSize: 20)),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                // Show created time
                Text(
                  'Sent: ${_formatTime(cmd.createdAt)}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey),
                ),
                const SizedBox(height: 8),

                if (cmd.status == CommandStatus.pending ||
                    cmd.status == CommandStatus.executing)
                  const Padding(
                    padding: EdgeInsets.all(16.0),
                    child: Center(
                      child: Column(
                        children: [
                          CircularProgressIndicator(),
                          SizedBox(height: 16),
                          Text('Waiting for response...'),
                        ],
                      ),
                    ),
                  )
                else ...[
                  // Show image if resultUrl exists AND it's not an audio command
                  if (cmd.resultUrl != null &&
                      cmd.resultUrl!.isNotEmpty &&
                      cmd.command.toLowerCase() != 'audio' &&
                      (cmd.result == null || cmd.result!['audio_url'] == null)) ...[
                    GestureDetector(
                      onTap: () => _showFullscreenImage(cmd.resultUrl!),
                      child: Stack(
                        alignment: Alignment.center,
                        children: [
                          ClipRRect(
                            borderRadius: BorderRadius.circular(8),
                            child: Image.network(
                              cmd.resultUrl!,
                              fit: BoxFit.contain,
                              loadingBuilder: (context, child, loadingProgress) {
                                if (loadingProgress == null) return child;
                                return const Center(
                                  child: Padding(
                                    padding: EdgeInsets.all(20),
                                    child: CircularProgressIndicator(),
                                  ),
                                );
                              },
                              errorBuilder: (context, error, stackTrace) {
                                return const Text('Failed to load image');
                              },
                            ),
                          ),
                          Positioned(
                            bottom: 8,
                            right: 8,
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: Colors.black54,
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: const Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.fullscreen, color: Colors.white, size: 16),
                                  SizedBox(width: 4),
                                  Text('Tap to view', style: TextStyle(color: Colors.white, fontSize: 12)),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    // Save and Share buttons
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton.icon(
                            onPressed: () {
                              final filename = 'screenshot_${cmd.createdAt.millisecondsSinceEpoch}.png';
                              _saveToGallery(cmd.resultUrl!, filename);
                            },
                            icon: const Icon(Icons.photo_library, size: 18),
                            label: const Text('Save to Gallery'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        IconButton(
                          onPressed: () => _showFullscreenImage(cmd.resultUrl!),
                          icon: const Icon(Icons.fullscreen),
                          tooltip: 'Fullscreen',
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                  ],

                  // Show photo URLs if present in result
                  if (cmd.result != null && cmd.result!['photo_urls'] != null)
                    ...((cmd.result!['photo_urls'] as List).asMap().entries.map((entry) => Column(
                      children: [
                        GestureDetector(
                          onTap: () => _showFullscreenImage(entry.value.toString()),
                          child: Stack(
                            alignment: Alignment.center,
                            children: [
                              ClipRRect(
                                borderRadius: BorderRadius.circular(8),
                                child: Image.network(
                                  entry.value.toString(),
                                  fit: BoxFit.contain,
                                  height: 200,
                                  errorBuilder: (context, error, stackTrace) {
                                    return const Text('Failed to load image');
                                  },
                                ),
                              ),
                              Positioned(
                                bottom: 4,
                                right: 4,
                                child: Container(
                                  padding: const EdgeInsets.all(4),
                                  decoration: BoxDecoration(
                                    color: Colors.black54,
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: const Icon(Icons.fullscreen, color: Colors.white, size: 16),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton.icon(
                                onPressed: () {
                                  final filename = 'photo_${cmd.createdAt.millisecondsSinceEpoch}_${entry.key}.jpg';
                                  _saveToGallery(entry.value.toString(), filename);
                                },
                                icon: const Icon(Icons.photo_library, size: 16),
                                label: const Text('Save to Gallery'),
                              ),
                            ),
                            const SizedBox(width: 8),
                            IconButton(
                              onPressed: () => _showFullscreenImage(entry.value.toString()),
                              icon: const Icon(Icons.fullscreen, size: 20),
                              tooltip: 'Fullscreen',
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                      ],
                    ))),

                  // Show audio player if audio URL exists (from result or resultUrl)
                  if ((cmd.result != null && cmd.result!['audio_url'] != null) ||
                      (cmd.command.toLowerCase() == 'audio' && cmd.resultUrl != null)) ...[
                    Card(
                      elevation: 3,
                      color: Colors.blue.shade50,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: Colors.blue.shade100,
                                    shape: BoxShape.circle,
                                  ),
                                  child: Icon(
                                    _isPlayingAudio ? Icons.volume_up : Icons.audiotrack,
                                    size: 32,
                                    color: Colors.blue.shade700,
                                  ),
                                ),
                                const SizedBox(width: 16),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'Audio Recording',
                                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                    if (cmd.result?['duration'] != null)
                                      Text(
                                        'Duration: ${cmd.result!['duration']} seconds',
                                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                          color: Colors.grey.shade700,
                                        ),
                                      ),
                                  ],
                                ),
                              ],
                            ),
                            const SizedBox(height: 20),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                              children: [
                                // Play/Stop button
                                SizedBox(
                                  width: 120,
                                  child: ElevatedButton.icon(
                                    onPressed: () {
                                      final audioUrl = cmd.result?['audio_url'] ?? cmd.resultUrl;
                                      if (audioUrl != null) {
                                        _playAudio(audioUrl);
                                        setDialogState(() {});
                                      }
                                    },
                                    icon: Icon(_isPlayingAudio ? Icons.stop : Icons.play_arrow, size: 24),
                                    label: Text(_isPlayingAudio ? 'Stop' : 'Play'),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: _isPlayingAudio ? Colors.red : Colors.green,
                                      foregroundColor: Colors.white,
                                      padding: const EdgeInsets.symmetric(vertical: 12),
                                    ),
                                  ),
                                ),
                                // Download button
                                SizedBox(
                                  width: 120,
                                  child: OutlinedButton.icon(
                                    onPressed: () {
                                      final audioUrl = cmd.result?['audio_url'] ?? cmd.resultUrl;
                                      if (audioUrl != null) {
                                        final filename = 'audio_${cmd.createdAt.millisecondsSinceEpoch}.m4a';
                                        _saveAudioFile(audioUrl, filename);
                                      }
                                    },
                                    icon: const Icon(Icons.download, size: 20),
                                    label: const Text('Save'),
                                    style: OutlinedButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(vertical: 12),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            if (_isPlayingAudio) ...[
                              const SizedBox(height: 12),
                              const LinearProgressIndicator(),
                              const SizedBox(height: 4),
                              const Text('Playing...', style: TextStyle(fontSize: 12, color: Colors.grey)),
                            ],
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // Show other result data
                  if (cmd.result != null)
                    ..._buildResultContent(cmd.result!),

                  // Show Google Maps button for location
                  if (cmd.result != null && cmd.result!['location'] != null) ...[
                    const SizedBox(height: 8),
                    ElevatedButton.icon(
                      onPressed: () {
                        final location = cmd.result!['location'] as Map<String, dynamic>;
                        final mapsUrl = location['google_maps'] ??
                          'https://www.google.com/maps?q=${location['latitude']},${location['longitude']}';
                        _openMaps(mapsUrl);
                      },
                      icon: const Icon(Icons.map),
                      label: const Text('Open in Google Maps'),
                    ),
                  ],

                  if (cmd.result == null && cmd.resultUrl == null)
                    if (cmd.status == CommandStatus.failed)
                      const Text(
                        'Command failed',
                        style: TextStyle(color: Colors.red),
                      )
                    else
                      const Text('Command completed'),
                ],

                if (cmd.executedAt != null) ...[
                  const Divider(),
                  Text(
                    'Executed: ${_formatTime(cmd.executedAt!)}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Close'),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildResultContent(Map<String, dynamic> result) {
    final widgets = <Widget>[];

    // Check if there's nested status data
    final data = result['status'] ?? result;
    final success = result['success'] ?? true;

    if (!success) {
      widgets.add(
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.red.shade50,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              const Icon(Icons.error_outline, color: Colors.red),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  result['error']?.toString() ?? 'Unknown error',
                  style: const TextStyle(color: Colors.red),
                ),
              ),
            ],
          ),
        ),
      );
      return widgets;
    }

    // Skip keys we handle separately
    final skipKeys = {'success', 'photo_urls', 'audio_url', 'screenshot_url', 'google_maps'};

    // Build formatted output
    if (data is Map<String, dynamic>) {
      data.forEach((key, value) {
        if (skipKeys.contains(key)) return;

        // Special handling for activity data
        if (key == 'activity') {
          widgets.add(_buildActivitySection(value));
          return;
        }

        widgets.add(
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: _buildResultRow(key, value),
          ),
        );
      });
    } else {
      widgets.add(Text(data.toString()));
    }

    return widgets;
  }

  Widget _buildActivitySection(dynamic activity) {
    if (activity is! Map) {
      return Text(activity.toString());
    }

    final activityMap = activity as Map<String, dynamic>;
    final sections = <Widget>[];

    // Section builder helper
    Widget buildSection(String title, IconData icon, List<Widget> content) {
      return Card(
        margin: const EdgeInsets.only(bottom: 12),
        child: ExpansionTile(
          leading: Icon(icon, size: 20),
          title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
          childrenPadding: const EdgeInsets.all(12),
          children: content,
        ),
      );
    }

    // Running Applications
    if (activityMap['running_apps'] != null) {
      final apps = activityMap['running_apps'];
      if (apps is List && apps.isNotEmpty) {
        sections.add(buildSection(
          'Running Apps (${apps.length})',
          Icons.apps,
          apps.take(10).map<Widget>((app) {
            final appName = app is Map ? (app['name'] ?? app.toString()) : app.toString();
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(
                children: [
                  const Icon(Icons.circle, size: 6, color: Colors.green),
                  const SizedBox(width: 8),
                  Expanded(child: Text(appName, style: const TextStyle(fontSize: 13))),
                ],
              ),
            );
          }).toList(),
        ));
      }
    }

    // Browser History
    if (activityMap['browser_history'] != null) {
      final history = activityMap['browser_history'];
      if (history is Map) {
        final allHistory = <Widget>[];
        history.forEach((browser, urls) {
          if (urls is List && urls.isNotEmpty) {
            allHistory.add(Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(browser.toString().toUpperCase(),
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.grey)),
            ));
            for (var url in urls.take(5)) {
              final urlStr = url is Map ? (url['url'] ?? url['title'] ?? url.toString()) : url.toString();
              allHistory.add(Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text(
                  urlStr,
                  style: const TextStyle(fontSize: 12, color: Colors.blue),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ));
            }
          }
        });
        if (allHistory.isNotEmpty) {
          sections.add(buildSection('Browser History', Icons.history, allHistory));
        }
      }
    }

    // Recent Files
    if (activityMap['recent_files'] != null) {
      final files = activityMap['recent_files'];
      if (files is List && files.isNotEmpty) {
        sections.add(buildSection(
          'Recent Files (${files.length})',
          Icons.folder_open,
          files.take(10).map<Widget>((file) {
            final fileName = file is Map ? (file['name'] ?? file['path'] ?? file.toString()) : file.toString();
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(
                children: [
                  const Icon(Icons.insert_drive_file, size: 14, color: Colors.grey),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      fileName.toString().split('/').last,
                      style: const TextStyle(fontSize: 13),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
        ));
      }
    }

    // Active Window
    if (activityMap['active_window'] != null) {
      final window = activityMap['active_window'];
      sections.add(Card(
        margin: const EdgeInsets.only(bottom: 12),
        child: ListTile(
          leading: const Icon(Icons.window, size: 20),
          title: const Text('Active Window', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
          subtitle: Text(
            window is Map ? (window['title'] ?? window['app'] ?? window.toString()) : window.toString(),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ));
    }

    // Screenshot info
    if (activityMap['screenshot'] != null) {
      sections.add(Card(
        margin: const EdgeInsets.only(bottom: 12),
        color: Colors.green.shade50,
        child: const ListTile(
          leading: Icon(Icons.screenshot, size: 20, color: Colors.green),
          title: Text('Screenshot Captured', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
        ),
      ));
    }

    if (sections.isEmpty) {
      // Fallback: just show raw data nicely formatted
      sections.add(Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Activity Data', style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Text(
                _formatJson(activityMap),
                style: const TextStyle(fontSize: 12, fontFamily: 'monospace'),
              ),
            ],
          ),
        ),
      ));
    }

    // Add export buttons at the end
    sections.add(
      Card(
        color: Colors.grey.shade100,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Export Activity Report', style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () => _exportActivity(activityMap, 'json'),
                      icon: const Icon(Icons.code, size: 18),
                      label: const Text('Export JSON'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.blue,
                        foregroundColor: Colors.white,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _exportActivity(activityMap, 'txt'),
                      icon: const Icon(Icons.description, size: 18),
                      label: const Text('Export TXT'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );

    return Column(children: sections);
  }

  String _formatJson(Map<String, dynamic> json) {
    final buffer = StringBuffer();
    json.forEach((key, value) {
      if (value is Map || value is List) {
        buffer.writeln('$key: ${value.runtimeType}');
      } else {
        buffer.writeln('$key: $value');
      }
    });
    return buffer.toString();
  }

  Widget _buildResultRow(String key, dynamic value) {
    final formattedKey = _formatKey(key);
    String formattedValue;
    Widget? trailing;

    if (value is Map) {
      // Handle nested objects like battery, location
      if (key == 'battery') {
        final pct = value['percentage'] ?? 0;
        final charging = value['charging'] ?? false;
        formattedValue = '$pct%${charging ? ' (Charging)' : ''}';
        trailing = Icon(
          charging ? Icons.battery_charging_full : Icons.battery_full,
          color: pct > 20 ? Colors.green : Colors.red,
        );
      } else if (key == 'location') {
        final lat = value['latitude'] ?? value['lat'];
        final lon = value['longitude'] ?? value['lon'];
        final city = value['city'] ?? '';
        formattedValue = city.isNotEmpty ? city : '$lat, $lon';
        trailing = const Icon(Icons.location_on, color: Colors.blue);
      } else {
        formattedValue = value.entries
            .map((e) => '${_formatKey(e.key)}: ${e.value}')
            .join('\n');
      }
    } else if (value is List) {
      formattedValue = value.join(', ');
    } else {
      formattedValue = value?.toString() ?? 'N/A';
    }

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 100,
          child: Text(
            formattedKey,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              color: Colors.grey,
            ),
          ),
        ),
        Expanded(
          child: Text(formattedValue),
        ),
        if (trailing != null) trailing,
      ],
    );
  }

  String _formatKey(String key) {
    // Convert snake_case to Title Case
    return key
        .replaceAll('_', ' ')
        .split(' ')
        .map((word) => word.isNotEmpty
            ? '${word[0].toUpperCase()}${word.substring(1)}'
            : '')
        .join(' ');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Commands'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Send Command'),
            Tab(text: 'History'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildCommandsGrid(),
          _buildHistoryList(),
        ],
      ),
    );
  }

  Widget _buildCommandsGrid() {
    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: 0.9,
      ),
      itemCount: availableCommands.length,
      itemBuilder: (context, index) {
        final cmd = availableCommands[index];
        return CommandButton(
          command: cmd,
          large: true,
          onPressed: () {
            // Special handling for commands with options
            if (cmd.command == 'message') {
              _showMessageDialog();
            } else if (cmd.command == 'audio') {
              _showAudioDialog();
            } else if (cmd.command == 'photo') {
              _showPhotoDialog();
            } else {
              _sendCommand(cmd);
            }
          },
        );
      },
    );
  }

  Widget _buildHistoryList() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_commandHistory.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.history,
              size: 64,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 16),
            const Text('No commands sent yet'),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadCommandHistory,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _commandHistory.length,
        itemBuilder: (context, index) {
          final cmd = _commandHistory[index];
          return Card(
            child: ListTile(
              onTap: () => _showResultDialog(cmd),
              leading: Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Center(
                  child: Text(
                    cmd.commandIcon,
                    style: const TextStyle(fontSize: 20),
                  ),
                ),
              ),
              title: Row(
                children: [
                  Text(
                    cmd.command.toUpperCase(),
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    cmd.statusIcon,
                    style: const TextStyle(fontSize: 16),
                  ),
                ],
              ),
              subtitle: Text(_formatTime(cmd.createdAt)),
              trailing: Icon(
                Icons.chevron_right,
                color: Theme.of(context).colorScheme.outline,
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildStatusChip(CommandStatus status) {
    Color bgColor;
    Color textColor;
    String label;

    switch (status) {
      case CommandStatus.pending:
        bgColor = Colors.orange.shade100;
        textColor = Colors.orange.shade800;
        label = 'Pending';
        break;
      case CommandStatus.executing:
        bgColor = Colors.blue.shade100;
        textColor = Colors.blue.shade800;
        label = 'Running';
        break;
      case CommandStatus.completed:
        bgColor = Colors.green.shade100;
        textColor = Colors.green.shade800;
        label = 'Done';
        break;
      case CommandStatus.failed:
        bgColor = Colors.red.shade100;
        textColor = Colors.red.shade800;
        label = 'Failed';
        break;
    }

    return Chip(
      label: Text(label),
      backgroundColor: bgColor,
      labelStyle: TextStyle(color: textColor, fontSize: 12),
      padding: EdgeInsets.zero,
      visualDensity: VisualDensity.compact,
    );
  }
}
