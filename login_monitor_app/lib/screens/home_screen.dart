import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../main.dart';
import '../models/device.dart';
import '../models/event.dart';
import '../models/command.dart';
import '../services/supabase_service.dart';
import '../widgets/event_card.dart';
import '../widgets/command_button.dart';
import '../theme/cyber_theme.dart';
import '../widgets/neon_card.dart';
import '../widgets/custom_toast.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

// India Standard Time offset (UTC+5:30)
DateTime _toIST(DateTime dt) {
  return dt.toUtc().add(const Duration(hours: 5, minutes: 30));
}

class _HomeScreenState extends State<HomeScreen> with WidgetsBindingObserver {
  List<Device> _devices = [];
  Device? _selectedDevice;
  List<MonitorEvent> _recentEvents = [];
  List<DeviceCommand> _recentCommands = [];
  bool _isLoading = true;
  int _totalEvents = 0;
  int _securityAlerts = 0;
  Timer? _autoRefreshTimer;

  // User profile
  String? _displayName;
  String? _avatarUrl;
  String? _email;

  // Format time in IST (India Standard Time)
  String _formatTime(DateTime dt) {
    final ist = _toIST(dt);
    return DateFormat('dd/MM/yyyy hh:mm:ss a').format(ist) + ' IST';
  }

  String _formatTimeShort(DateTime dt) {
    final ist = _toIST(dt);
    final now = _toIST(DateTime.now());
    final diff = now.difference(ist);

    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _loadData();
    _startAutoRefresh();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _autoRefreshTimer?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      // Refresh device status when app comes to foreground
      _refreshDeviceStatus();
      _startAutoRefresh();
    } else if (state == AppLifecycleState.paused) {
      _autoRefreshTimer?.cancel();
    }
  }

  void _startAutoRefresh() {
    _autoRefreshTimer?.cancel();
    // Refresh device status every 30 seconds
    _autoRefreshTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted) {
        _refreshDeviceStatus();
      }
    });
  }

  Future<void> _refreshDeviceStatus() async {
    if (_selectedDevice == null) return;
    try {
      final devices = await SupabaseService.getDevices();
      if (mounted && devices.isNotEmpty) {
        final updated = devices.firstWhere(
          (d) => d.id == _selectedDevice!.id,
          orElse: () => _selectedDevice!,
        );
        setState(() {
          _devices = devices;
          _selectedDevice = updated;
        });
      }
    } catch (e) {
      debugPrint('Error refreshing device status: $e');
    }
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);

    try {
      // Load devices
      final devices = await SupabaseService.getDevices();

      // Load user profile
      final user = SupabaseService.client.auth.currentUser;
      _email = user?.email;

      if (user != null) {
        try {
          final profile = await SupabaseService.client
              .from('profiles')
              .select()
              .eq('id', user.id)
              .maybeSingle();

          if (profile != null) {
            _displayName = profile['display_name'];
            _avatarUrl = profile['avatar_url'];
          }
        } catch (e) {
          debugPrint('Error loading profile: $e');
        }
      }

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
        _loadStats();
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        CustomToast.show(
          context,
          message: 'Error loading devices',
          type: ToastType.error,
        );
      }
    }
  }

  Future<void> _loadStats() async {
    if (_selectedDevice == null) return;
    try {
      final events = await SupabaseService.getEvents(
        deviceId: _selectedDevice!.id,
        limit: 100,
      );

      final securityTypes = ['Intruder', 'UnknownUSB', 'UnknownNetwork', 'GeofenceExit'];
      final alerts = events.where((e) => securityTypes.contains(e.eventType)).length;

      setState(() {
        _totalEvents = events.length;
        _securityAlerts = alerts;
      });
    } catch (e) {
      debugPrint('Error loading stats: $e');
    }
  }

  Future<void> _loadEvents() async {
    if (_selectedDevice == null) return;
    try {
      final events = await SupabaseService.getEvents(
        deviceId: _selectedDevice!.id,
        limit: 5,
      );
      final commands = await SupabaseService.getCommands(
        deviceId: _selectedDevice!.id,
        limit: 5,
      );
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
        CustomToast.show(
          context,
          message: '${cmd.name} command sent',
          type: ToastType.success,
          icon: cmd.icon,
        );
      }
    } catch (e) {
      if (mounted) {
        CustomToast.show(
          context,
          message: 'Error: $e',
          type: ToastType.error,
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(color: CyberColors.primaryRed),
        ),
      );
    }

    if (_devices.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text('Login Monitor PRO')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  color: CyberColors.primaryRed.withOpacity(0.1),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.devices_other,
                  size: 50,
                  color: CyberColors.primaryRed,
                ),
              ),
              const SizedBox(height: 24),
              const Text(
                'No devices paired',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: CyberColors.textPrimary,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Pair your Mac to get started',
                style: TextStyle(color: CyberColors.textSecondary),
              ),
              const SizedBox(height: 32),
              ElevatedButton.icon(
                onPressed: () => Navigator.pushNamed(context, '/pairing'),
                icon: const Icon(Icons.add),
                label: const Text('Pair Device'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: CyberColors.primaryRed,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      body: RefreshIndicator(
        onRefresh: () async {
          await _loadData();
        },
        color: CyberColors.primaryRed,
        child: CustomScrollView(
          slivers: [
            // Custom App Bar with Greeting
            SliverAppBar(
              expandedHeight: 140,
              pinned: true,
              backgroundColor: CyberColors.pureBlack,
              flexibleSpace: FlexibleSpaceBar(
                background: _buildGreetingHeader(),
              ),
              actions: [
                IconButton(
                  icon: const Icon(Icons.notifications_outlined),
                  onPressed: () => Navigator.pushNamed(context, '/events'),
                ),
                IconButton(
                  icon: const Icon(Icons.settings_outlined),
                  onPressed: () => Navigator.pushNamed(context, '/settings'),
                ),
              ],
            ),

            // Content
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Quick Stats
                    _buildQuickStats(),
                    const SizedBox(height: 24),

                    // Device Status
                    if (_selectedDevice != null) _buildDeviceStatus(),
                    const SizedBox(height: 24),

                    // PRO Features
                    _buildProFeatures(),
                    const SizedBox(height: 24),

                    // Quick Commands
                    _buildSectionHeader('Quick Commands', onSeeAll: () {
                      Navigator.pushNamed(context, '/commands');
                    }),
                    const SizedBox(height: 12),
                    _buildQuickCommands(),
                    const SizedBox(height: 24),

                    // Recent Activity
                    _buildSectionHeader('Recent Activity', onSeeAll: () {
                      Navigator.pushNamed(context, '/events');
                    }),
                    const SizedBox(height: 12),
                    _buildRecentActivity(),
                    const SizedBox(height: 100),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: _buildBottomNav(),
    );
  }

  Widget _buildGreetingHeader() {
    final hour = DateTime.now().hour;
    String greeting = 'Good morning';
    if (hour >= 12 && hour < 17) greeting = 'Good afternoon';
    if (hour >= 17) greeting = 'Good evening';

    return Container(
      padding: const EdgeInsets.fromLTRB(16, 60, 16, 16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            CyberColors.primaryRed.withOpacity(0.2),
            CyberColors.pureBlack,
          ],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        ),
      ),
      child: Row(
        children: [
          // Avatar
          GestureDetector(
            onTap: () => Navigator.pushNamed(context, '/profile'),
            child: Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: CyberColors.primaryRed, width: 2),
              ),
              child: ClipOval(
                child: _avatarUrl != null
                    ? CachedNetworkImage(
                        imageUrl: _avatarUrl!,
                        fit: BoxFit.cover,
                        placeholder: (context, url) => Container(
                          color: CyberColors.surfaceColor,
                          child: const Icon(Icons.person, color: CyberColors.textMuted),
                        ),
                        errorWidget: (context, url, error) => Container(
                          color: CyberColors.surfaceColor,
                          child: const Icon(Icons.person, color: CyberColors.textMuted),
                        ),
                      )
                    : Container(
                        color: CyberColors.surfaceColor,
                        child: const Icon(Icons.person, color: CyberColors.textMuted),
                      ),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  greeting,
                  style: const TextStyle(
                    color: CyberColors.textSecondary,
                    fontSize: 14,
                  ),
                ),
                Text(
                  _displayName ?? _email?.split('@').first ?? 'User',
                  style: const TextStyle(
                    color: CyberColors.textPrimary,
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickStats() {
    return Row(
      children: [
        Expanded(
          child: _buildStatCard(
            icon: Icons.event,
            value: '$_totalEvents',
            label: 'Events',
            color: CyberColors.primaryRed,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildStatCard(
            icon: Icons.warning,
            value: '$_securityAlerts',
            label: 'Alerts',
            color: _securityAlerts > 0 ? CyberColors.alertRed : CyberColors.successGreen,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildStatCard(
            icon: Icons.devices,
            value: '${_devices.length}',
            label: 'Devices',
            color: CyberColors.infoBlue,
          ),
        ),
      ],
    );
  }

  Widget _buildStatCard({
    required IconData icon,
    required String value,
    required String label,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: CyberColors.surfaceColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          Text(
            label,
            style: const TextStyle(
              color: CyberColors.textSecondary,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDeviceStatus() {
    final device = _selectedDevice!;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            device.isOnline
                ? CyberColors.successGreen.withOpacity(0.1)
                : CyberColors.textMuted.withOpacity(0.1),
            CyberColors.surfaceColor,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: device.isOnline
              ? CyberColors.successGreen.withOpacity(0.3)
              : CyberColors.borderColor,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: device.isOnline
                  ? CyberColors.successGreen.withOpacity(0.1)
                  : CyberColors.surfaceColor,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Icon(
              Icons.laptop_mac,
              color: device.isOnline ? CyberColors.successGreen : CyberColors.textMuted,
              size: 28,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  device.hostname ?? 'Unknown Mac',
                  style: const TextStyle(
                    color: CyberColors.textPrimary,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: device.isOnline ? CyberColors.successGreen : CyberColors.textMuted,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      device.isOnline ? 'Online' : 'Offline',
                      style: TextStyle(
                        color: device.isOnline ? CyberColors.successGreen : CyberColors.textMuted,
                        fontSize: 14,
                      ),
                    ),
                    if (device.lastSeen != null && !device.isOnline) ...[
                      const Text(' • ', style: TextStyle(color: CyberColors.textMuted)),
                      Text(
                        _formatTimeShort(device.lastSeen!),
                        style: const TextStyle(color: CyberColors.textSecondary, fontSize: 12),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
          if (_devices.length > 1)
            PopupMenuButton<Device>(
              icon: const Icon(Icons.expand_more, color: CyberColors.textMuted),
              onSelected: (device) {
                setState(() => _selectedDevice = device);
                context.read<AppState>().setSelectedDevice(device.id);
                _loadEvents();
                _loadStats();
              },
              itemBuilder: (context) => _devices.map((d) {
                return PopupMenuItem(
                  value: d,
                  child: Row(
                    children: [
                      Icon(
                        Icons.laptop_mac,
                        color: d.isOnline ? CyberColors.successGreen : CyberColors.textMuted,
                        size: 20,
                      ),
                      const SizedBox(width: 8),
                      Text(d.hostname ?? 'Unknown'),
                    ],
                  ),
                );
              }).toList(),
            ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title, {VoidCallback? onSeeAll}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          title,
          style: const TextStyle(
            color: CyberColors.textPrimary,
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
        if (onSeeAll != null)
          TextButton(
            onPressed: onSeeAll,
            child: const Text(
              'See All',
              style: TextStyle(color: CyberColors.primaryRed),
            ),
          ),
      ],
    );
  }

  Widget _buildProFeatures() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: CyberColors.primaryRed.withOpacity(0.2),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.star, color: CyberColors.primaryRed, size: 14),
                  SizedBox(width: 4),
                  Text(
                    'PRO',
                    style: TextStyle(
                      color: CyberColors.primaryRed,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            const Text(
              'Features',
              style: TextStyle(
                color: CyberColors.textPrimary,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: _buildFeatureCard(
                icon: Icons.security,
                title: 'Security',
                color: CyberColors.primaryRed,
                onTap: () => Navigator.pushNamed(context, '/security'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildFeatureCard(
                icon: Icons.volume_up,
                title: 'Find Mac',
                color: CyberColors.warningOrange,
                onTap: () => Navigator.pushNamed(context, '/findmac'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildFeatureCard(
                icon: Icons.location_on,
                title: 'Geofence',
                color: CyberColors.successGreen,
                onTap: () => Navigator.pushNamed(context, '/geofence'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildFeatureCard(
                icon: Icons.assessment,
                title: 'Reports',
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
    required Color color,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 8),
            Text(
              title,
              style: TextStyle(
                color: color,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickCommands() {
    return SizedBox(
      height: 80,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: availableCommands.length,
        itemBuilder: (context, index) {
          final cmd = availableCommands[index];
          return Padding(
            padding: EdgeInsets.only(right: index < availableCommands.length - 1 ? 12 : 0),
            child: _buildCommandChip(cmd),
          );
        },
      ),
    );
  }

  Widget _buildCommandChip(CommandDefinition cmd) {
    return GestureDetector(
      onTap: () => _sendCommand(cmd),
      child: Container(
        width: 80,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: CyberColors.surfaceColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: CyberColors.borderColor),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(cmd.icon, color: CyberColors.primaryRed, size: 24),
            const SizedBox(height: 6),
            Text(
              cmd.name,
              style: const TextStyle(
                color: CyberColors.textPrimary,
                fontSize: 10,
                fontWeight: FontWeight.w500,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecentActivity() {
    if (_recentEvents.isEmpty && _recentCommands.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(32),
        decoration: BoxDecoration(
          color: CyberColors.surfaceColor,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          children: [
            Icon(
              Icons.history,
              size: 48,
              color: CyberColors.textMuted,
            ),
            const SizedBox(height: 12),
            const Text(
              'No activity yet',
              style: TextStyle(
                color: CyberColors.textPrimary,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'Events and commands will appear here',
              style: TextStyle(color: CyberColors.textSecondary, fontSize: 12),
            ),
          ],
        ),
      );
    }

    return Column(
      children: [
        ..._recentEvents.take(3).map((event) => _buildActivityItem(
              icon: _getEventIcon(event.eventType),
              color: _getEventColor(event.eventType),
              title: event.eventType,
              subtitle: event.username ?? 'Unknown user',
              time: _formatTimeShort(event.timestamp),
              onTap: () => Navigator.pushNamed(context, '/event-detail', arguments: event.id),
            )),
        ..._recentCommands.take(2).map((cmd) => _buildActivityItem(
              icon: Icons.terminal,
              color: cmd.status == CommandStatus.completed
                  ? CyberColors.successGreen
                  : CyberColors.warningOrange,
              title: cmd.command.toUpperCase(),
              subtitle: cmd.status.name,
              time: _formatTimeShort(cmd.createdAt),
              onTap: () => Navigator.pushNamed(context, '/commands'),
            )),
      ],
    );
  }

  Widget _buildActivityItem({
    required IconData icon,
    required Color color,
    required String title,
    required String subtitle,
    required String time,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
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
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: color, size: 20),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      color: CyberColors.textPrimary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Text(
                    subtitle,
                    style: const TextStyle(
                      color: CyberColors.textSecondary,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            Text(
              time,
              style: const TextStyle(
                color: CyberColors.textMuted,
                fontSize: 11,
              ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _getEventIcon(String eventType) {
    switch (eventType) {
      case 'Login': return Icons.login;
      case 'Unlock': return Icons.lock_open;
      case 'Intruder': return Icons.person_off;
      case 'UnknownUSB': return Icons.usb;
      case 'UnknownNetwork': return Icons.wifi_off;
      case 'GeofenceExit': return Icons.location_off;
      default: return Icons.event;
    }
  }

  Color _getEventColor(String eventType) {
    switch (eventType) {
      case 'Login': return CyberColors.primaryRed;
      case 'Unlock': return CyberColors.successGreen;
      case 'Intruder': return CyberColors.alertRed;
      case 'UnknownUSB': return CyberColors.warningOrange;
      case 'UnknownNetwork': return CyberColors.warningOrange;
      case 'GeofenceExit': return CyberColors.alertRed;
      default: return CyberColors.textMuted;
    }
  }

  Widget _buildBottomNav() {
    return Container(
      decoration: BoxDecoration(
        color: CyberColors.darkBackground,
        border: Border(
          top: BorderSide(color: CyberColors.borderColor),
        ),
      ),
      child: NavigationBar(
        backgroundColor: Colors.transparent,
        indicatorColor: CyberColors.primaryRed.withOpacity(0.2),
        selectedIndex: 0,
        onDestinationSelected: (index) {
          switch (index) {
            case 0: break;
            case 1: Navigator.pushNamed(context, '/events'); break;
            case 2: Navigator.pushNamed(context, '/commands'); break;
            case 3: Navigator.pushNamed(context, '/settings'); break;
          }
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined, color: CyberColors.textMuted),
            selectedIcon: Icon(Icons.home, color: CyberColors.primaryRed),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.notifications_outlined, color: CyberColors.textMuted),
            selectedIcon: Icon(Icons.notifications, color: CyberColors.primaryRed),
            label: 'Events',
          ),
          NavigationDestination(
            icon: Icon(Icons.terminal_outlined, color: CyberColors.textMuted),
            selectedIcon: Icon(Icons.terminal, color: CyberColors.primaryRed),
            label: 'Commands',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined, color: CyberColors.textMuted),
            selectedIcon: Icon(Icons.settings, color: CyberColors.primaryRed),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}
