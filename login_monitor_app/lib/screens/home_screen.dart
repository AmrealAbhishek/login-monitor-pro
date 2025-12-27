import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../main.dart';
import '../models/device.dart';
import '../models/event.dart';
import '../models/command.dart';
import '../services/supabase_service.dart';
import '../widgets/event_card.dart';
import '../widgets/command_button.dart';
import '../theme/cyber_theme.dart';
import '../widgets/neon_card.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

// India Standard Time offset (UTC+5:30)
DateTime _toIST(DateTime dt) {
  return dt.toUtc().add(const Duration(hours: 5, minutes: 30));
}

class _HomeScreenState extends State<HomeScreen> {
  List<Device> _devices = [];
  Device? _selectedDevice;
  List<MonitorEvent> _recentEvents = [];
  List<DeviceCommand> _recentCommands = [];
  bool _isLoading = true;

  // Format time in IST (India Standard Time)
  String _formatTime(DateTime dt) {
    final ist = _toIST(dt);
    return DateFormat('dd/MM/yyyy hh:mm:ss a').format(ist) + ' IST';
  }

  @override
  void initState() {
    super.initState();
    _loadDevices();
  }

  Future<void> _loadDevices() async {
    try {
      final devices = await SupabaseService.getDevices();
      setState(() {
        _devices = devices;
        if (devices.isNotEmpty) {
          _selectedDevice = devices.first;
          context.read<AppState>().setSelectedDevice(devices.first.id);
        }
        _isLoading = false;
      });
      if (_selectedDevice != null) {
        _loadEvents();
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading devices: $e')),
        );
      }
    }
  }

  Future<void> _loadEvents() async {
    if (_selectedDevice == null) return;
    try {
      final events =
          await SupabaseService.getEvents(deviceId: _selectedDevice!.id, limit: 5);
      final commands =
          await SupabaseService.getCommands(deviceId: _selectedDevice!.id, limit: 5);
      setState(() {
        _recentEvents = events;
        _recentCommands = commands;
      });
    } catch (e) {
      debugPrint('Error loading events: $e');
    }
  }

  Future<void> _sendCommand(CommandDefinition cmd) async {
    if (_selectedDevice == null) return;

    try {
      await SupabaseService.sendCommand(
        deviceId: _selectedDevice!.id,
        command: cmd.command,
        args: cmd.defaultArgs,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${cmd.name} command sent!')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (_devices.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text('Login Monitor PRO')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.devices_other,
                size: 80,
                color: Theme.of(context).colorScheme.outline,
              ),
              const SizedBox(height: 16),
              const Text(
                'No devices paired',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text('Pair your Mac to get started'),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: () => Navigator.pushNamed(context, '/pairing'),
                icon: const Icon(Icons.add),
                label: const Text('Pair Device'),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Login Monitor PRO'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: 'Add Device',
            onPressed: () => Navigator.pushNamed(context, '/pairing'),
          ),
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => Navigator.pushNamed(context, '/settings'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await _loadDevices();
          await _loadEvents();
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Device selector (if multiple devices)
            if (_devices.length > 1) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(8),
                  child: DropdownButton<Device>(
                    value: _selectedDevice,
                    isExpanded: true,
                    underline: const SizedBox(),
                    items: _devices.map((device) {
                      return DropdownMenuItem(
                        value: device,
                        child: Row(
                          children: [
                            Icon(
                              Icons.laptop_mac,
                              color: device.isOnline
                                  ? Colors.green
                                  : Colors.grey,
                            ),
                            const SizedBox(width: 12),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  device.hostname ?? 'Unknown Mac',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                Text(
                                  device.isOnline
                                      ? 'Online'
                                      : 'Last seen ${_formatTime(device.lastSeen ?? DateTime.now())}',
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: Theme.of(context)
                                        .colorScheme
                                        .onSurfaceVariant,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                    onChanged: (device) {
                      setState(() => _selectedDevice = device);
                      context.read<AppState>().setSelectedDevice(device?.id);
                      _loadEvents();
                    },
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Device status card
            if (_selectedDevice != null) _buildDeviceStatusCard(),
            const SizedBox(height: 16),

            // PRO Features
            _buildProFeatures(),
            const SizedBox(height: 24),

            // Quick commands
            Text(
              'Quick Commands',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 12),
            _buildQuickCommands(),
            const SizedBox(height: 24),

            // Recent commands
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Recent Commands',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                TextButton(
                  onPressed: () => Navigator.pushNamed(context, '/commands'),
                  child: const Text('View All'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            _buildRecentCommands(),
            const SizedBox(height: 24),

            // Recent events
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Recent Events',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                TextButton(
                  onPressed: () => Navigator.pushNamed(context, '/events'),
                  child: const Text('View All'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            _buildRecentEvents(),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: 0,
        onDestinationSelected: (index) {
          switch (index) {
            case 0:
              break;
            case 1:
              Navigator.pushNamed(context, '/events');
              break;
            case 2:
              Navigator.pushNamed(context, '/commands');
              break;
            case 3:
              Navigator.pushNamed(context, '/settings');
              break;
          }
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.notifications_outlined),
            selectedIcon: Icon(Icons.notifications),
            label: 'Events',
          ),
          NavigationDestination(
            icon: Icon(Icons.terminal_outlined),
            selectedIcon: Icon(Icons.terminal),
            label: 'Commands',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
    );
  }

  Widget _buildDeviceStatusCard() {
    final device = _selectedDevice!;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Row(
              children: [
                Container(
                  width: 60,
                  height: 60,
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primaryContainer,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.laptop_mac, size: 30),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        device.hostname ?? 'Unknown Mac',
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          Container(
                            width: 10,
                            height: 10,
                            decoration: BoxDecoration(
                              color: device.isOnline
                                  ? Colors.green
                                  : Colors.grey,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            device.isOnline
                                ? 'Online'
                                : 'Offline',
                            style: TextStyle(
                              color: device.isOnline
                                  ? Colors.green
                                  : Colors.grey,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (device.lastSeen != null) ...[
              const Divider(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Last seen'),
                  Text(
                    _formatTime(device.lastSeen!),
                    style: const TextStyle(fontWeight: FontWeight.w500),
                  ),
                ],
              ),
            ],
            if (device.osVersion != null) ...[
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('OS Version'),
                  Flexible(
                    child: Text(
                      device.osVersion!,
                      style: const TextStyle(fontWeight: FontWeight.w500),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildQuickCommands() {
    final quickCommands = availableCommands.take(4).toList();
    return Row(
      children: quickCommands.map((cmd) {
        return Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: CommandButton(
              command: cmd,
              onPressed: () => _sendCommand(cmd),
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildRecentCommands() {
    if (_recentCommands.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Center(
            child: Column(
              children: [
                Icon(
                  Icons.terminal,
                  size: 40,
                  color: Theme.of(context).colorScheme.outline,
                ),
                const SizedBox(height: 8),
                const Text('No commands yet'),
                Text(
                  'Send a command from the Commands tab',
                  style: TextStyle(
                    fontSize: 12,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Column(
      children: _recentCommands.map((cmd) {
        IconData icon;
        Color statusColor;

        switch (cmd.status) {
          case 'completed':
            icon = Icons.check_circle;
            statusColor = Colors.green;
            break;
          case 'failed':
            icon = Icons.error;
            statusColor = Colors.red;
            break;
          case 'executing':
            icon = Icons.sync;
            statusColor = Colors.orange;
            break;
          default:
            icon = Icons.pending;
            statusColor = Colors.grey;
        }

        // Get brief result summary
        String resultSummary = '';
        if (cmd.result != null) {
          if (cmd.result!['success'] == true) {
            if (cmd.command == 'location' && cmd.result!['location'] != null) {
              final loc = cmd.result!['location'];
              resultSummary = '${loc['city'] ?? ''}, ${loc['country'] ?? ''}';
            } else if (cmd.command == 'battery' && cmd.result!['battery'] != null) {
              final bat = cmd.result!['battery'];
              resultSummary = '${bat['percentage']}% - ${bat['status']}';
            } else if (cmd.command == 'status' && cmd.result!['status'] != null) {
              resultSummary = 'Online';
            } else if (cmd.command == 'photo') {
              resultSummary = '${cmd.result!['photo_count'] ?? 1} photo(s) captured';
            } else if (cmd.command == 'screenshot') {
              resultSummary = 'Screenshot captured';
            } else if (cmd.command == 'wifi' && cmd.result!['wifi'] != null) {
              resultSummary = cmd.result!['wifi']['ssid'] ?? 'Connected';
            }
          } else if (cmd.result!['error'] != null) {
            resultSummary = cmd.result!['error'].toString();
          }
        }

        return Card(
          child: ListTile(
            leading: Icon(icon, color: statusColor),
            title: Text(
              cmd.command.toUpperCase(),
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (resultSummary.isNotEmpty)
                  Text(
                    resultSummary,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                Text(
                  _formatTime(cmd.createdAt),
                  style: TextStyle(
                    fontSize: 11,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
            trailing: cmd.resultUrl != null
                ? const Icon(Icons.image, size: 20)
                : null,
            onTap: () => Navigator.pushNamed(context, '/commands'),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildRecentEvents() {
    if (_recentEvents.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Center(
            child: Column(
              children: [
                Icon(
                  Icons.event_available,
                  size: 48,
                  color: Theme.of(context).colorScheme.outline,
                ),
                const SizedBox(height: 12),
                const Text('No events yet'),
                const SizedBox(height: 4),
                Text(
                  'Events will appear here when\nsomeone logs into your Mac',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Column(
      children: _recentEvents.map((event) {
        return EventCard(
          event: event,
          onTap: () {
            Navigator.pushNamed(context, '/event-detail', arguments: event.id);
          },
        );
      }).toList(),
    );
  }

  Widget _buildProFeatures() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(
              Icons.star,
              color: CyberColors.neonCyan,
              size: 20,
            ),
            const SizedBox(width: 8),
            Text(
              'PRO Features',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: CyberColors.neonCyan,
                  ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _buildFeatureCard(
                icon: Icons.security,
                title: 'Security',
                subtitle: 'Dashboard',
                color: CyberColors.neonCyan,
                onTap: () => Navigator.pushNamed(context, '/security'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildFeatureCard(
                icon: Icons.volume_up,
                title: 'Find',
                subtitle: 'My Mac',
                color: CyberColors.alertRed,
                onTap: () => Navigator.pushNamed(context, '/findmac'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildFeatureCard(
                icon: Icons.assessment,
                title: 'Security',
                subtitle: 'Reports',
                color: CyberColors.infoBlue,
                onTap: () => Navigator.pushNamed(context, '/reports'),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildFeatureCard({
    required IconData icon,
    required String title,
    required String subtitle,
    required Color color,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: CyberColors.cardBackground,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.5)),
          boxShadow: [
            BoxShadow(
              color: color.withOpacity(0.2),
              blurRadius: 8,
              spreadRadius: 0,
            ),
          ],
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 8),
            Text(
              title,
              style: TextStyle(
                color: color,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
            Text(
              subtitle,
              style: const TextStyle(
                color: CyberColors.textSecondary,
                fontSize: 10,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
