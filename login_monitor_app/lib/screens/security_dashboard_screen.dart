import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../main.dart';
import '../theme/cyber_theme.dart';
import '../widgets/neon_card.dart';
import '../widgets/pulse_indicator.dart';
import '../services/supabase_service.dart';
import '../models/event.dart';

class SecurityDashboardScreen extends StatefulWidget {
  const SecurityDashboardScreen({super.key});

  @override
  State<SecurityDashboardScreen> createState() => _SecurityDashboardScreenState();
}

class _SecurityDashboardScreenState extends State<SecurityDashboardScreen>
    with SingleTickerProviderStateMixin {
  bool _isLoading = true;
  int _totalEvents = 0;
  int _securityAlerts = 0;
  int _unreadCount = 0;
  List<MonitorEvent> _recentAlerts = [];
  Map<String, int> _eventStats = {};

  late AnimationController _scanController;

  @override
  void initState() {
    super.initState();
    _scanController = AnimationController(
      duration: const Duration(seconds: 3),
      vsync: this,
    )..repeat();
    _loadSecurityData();
  }

  @override
  void dispose() {
    _scanController.dispose();
    super.dispose();
  }

  Future<void> _loadSecurityData() async {
    final deviceId = context.read<AppState>().selectedDeviceId;
    if (deviceId == null) {
      setState(() => _isLoading = false);
      return;
    }

    try {
      final events = await SupabaseService.getEvents(deviceId: deviceId, limit: 100);
      final unread = await SupabaseService.getUnreadCount(deviceId);

      // Count by type
      final stats = <String, int>{};
      final securityTypes = ['Intruder', 'UnknownUSB', 'UnknownNetwork', 'GeofenceExit', 'Movement'];
      final alerts = <MonitorEvent>[];

      for (final event in events) {
        stats[event.eventType] = (stats[event.eventType] ?? 0) + 1;
        if (securityTypes.contains(event.eventType)) {
          alerts.add(event);
        }
      }

      setState(() {
        _totalEvents = events.length;
        _securityAlerts = alerts.length;
        _unreadCount = unread;
        _recentAlerts = alerts.take(5).toList();
        _eventStats = stats;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SECURITY DASHBOARD'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              setState(() => _isLoading = true);
              _loadSecurityData();
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CyberLoadingIndicator(message: 'Scanning...'))
          : RefreshIndicator(
              onRefresh: _loadSecurityData,
              color: CyberColors.neonCyan,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // Security Status
                  _buildSecurityStatus(),
                  const SizedBox(height: 24),

                  // Quick Stats
                  _buildQuickStats(),
                  const SizedBox(height: 24),

                  // Event Breakdown
                  _buildEventBreakdown(),
                  const SizedBox(height: 24),

                  // Recent Security Alerts
                  _buildRecentAlerts(),
                ],
              ),
            ),
    );
  }

  Widget _buildSecurityStatus() {
    final isSecure = _securityAlerts == 0;
    final statusColor = isSecure ? CyberColors.successGreen : CyberColors.alertRed;
    final statusText = isSecure ? 'SECURE' : 'ALERTS DETECTED';

    return NeonCard(
      glowColor: statusColor,
      animate: !isSecure,
      isAlert: !isSecure,
      child: Column(
        children: [
          ScanningIndicator(
            color: statusColor,
            size: 120,
            child: Icon(
              isSecure ? Icons.shield : Icons.warning,
              color: statusColor,
              size: 40,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            statusText,
            style: TextStyle(
              color: statusColor,
              fontSize: 24,
              fontWeight: FontWeight.bold,
              letterSpacing: 2,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            isSecure
                ? 'No security threats detected'
                : '$_securityAlerts security alert(s) require attention',
            style: TextStyle(
              color: CyberColors.textSecondary,
              fontSize: 14,
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
            'Total Events',
            _totalEvents.toString(),
            Icons.event,
            CyberColors.neonCyan,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildStatCard(
            'Security Alerts',
            _securityAlerts.toString(),
            Icons.security,
            _securityAlerts > 0 ? CyberColors.alertRed : CyberColors.successGreen,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildStatCard(
            'Unread',
            _unreadCount.toString(),
            Icons.notifications,
            _unreadCount > 0 ? CyberColors.warningOrange : CyberColors.textMuted,
          ),
        ),
      ],
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return NeonCard(
      glowColor: color,
      glowIntensity: 0.3,
      padding: const EdgeInsets.all(12),
      child: Column(
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 28,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: const TextStyle(
              color: CyberColors.textSecondary,
              fontSize: 11,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildEventBreakdown() {
    if (_eventStats.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Event Breakdown',
          style: TextStyle(
            color: CyberColors.neonCyan,
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 12),
        NeonCard(
          glowIntensity: 0.2,
          child: Column(
            children: _eventStats.entries.map((entry) {
              final percentage = _totalEvents > 0
                  ? (entry.value / _totalEvents * 100).round()
                  : 0;

              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Row(
                  children: [
                    SizedBox(
                      width: 100,
                      child: Text(
                        entry.key,
                        style: const TextStyle(
                          color: CyberColors.textPrimary,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                    Expanded(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: percentage / 100,
                          backgroundColor: CyberColors.surfaceColor,
                          valueColor: AlwaysStoppedAnimation(
                            _getEventColor(entry.key),
                          ),
                          minHeight: 8,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    SizedBox(
                      width: 50,
                      child: Text(
                        '${entry.value}',
                        style: const TextStyle(
                          color: CyberColors.neonCyan,
                          fontWeight: FontWeight.bold,
                        ),
                        textAlign: TextAlign.end,
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        ),
      ],
    );
  }

  Color _getEventColor(String eventType) {
    switch (eventType) {
      case 'Login':
        return CyberColors.neonCyan;
      case 'Unlock':
        return CyberColors.primaryRedLight;
      case 'Intruder':
        return CyberColors.alertRed;
      case 'UnknownUSB':
        return CyberColors.warningOrange;
      case 'UnknownNetwork':
        return CyberColors.warningOrange;
      case 'GeofenceExit':
        return CyberColors.alertRed;
      case 'Movement':
        return CyberColors.infoBlue;
      default:
        return CyberColors.textMuted;
    }
  }

  Widget _buildRecentAlerts() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Recent Security Alerts',
              style: TextStyle(
                color: CyberColors.neonCyan,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            if (_recentAlerts.isNotEmpty)
              NeonBadge(
                label: '${_recentAlerts.length}',
                color: CyberColors.alertRed,
              ),
          ],
        ),
        const SizedBox(height: 12),
        if (_recentAlerts.isEmpty)
          NeonCard(
            glowColor: CyberColors.successGreen,
            glowIntensity: 0.3,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.verified_user,
                  color: CyberColors.successGreen,
                  size: 32,
                ),
                const SizedBox(width: 12),
                const Text(
                  'No security alerts',
                  style: TextStyle(
                    color: CyberColors.successGreen,
                    fontSize: 16,
                  ),
                ),
              ],
            ),
          )
        else
          ..._recentAlerts.map((alert) => _buildAlertCard(alert)),
      ],
    );
  }

  Widget _buildAlertCard(MonitorEvent alert) {
    final color = _getEventColor(alert.eventType);

    return NeonCard(
      glowColor: color,
      glowIntensity: 0.4,
      isAlert: true,
      onTap: () {
        Navigator.pushNamed(context, '/event-detail', arguments: alert.id);
      },
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: color.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              _getAlertIcon(alert.eventType),
              color: color,
              size: 24,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  alert.eventType,
                  style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _formatTime(alert.timestamp),
                  style: const TextStyle(
                    color: CyberColors.textSecondary,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          Icon(
            Icons.chevron_right,
            color: CyberColors.textMuted,
          ),
        ],
      ),
    );
  }

  IconData _getAlertIcon(String eventType) {
    switch (eventType) {
      case 'Intruder':
        return Icons.person_off;
      case 'UnknownUSB':
        return Icons.usb;
      case 'UnknownNetwork':
        return Icons.wifi_off;
      case 'GeofenceExit':
        return Icons.location_off;
      case 'Movement':
        return Icons.directions_run;
      default:
        return Icons.warning;
    }
  }

  String _formatTime(DateTime dt) {
    final now = DateTime.now();
    final diff = now.difference(dt);

    if (diff.inMinutes < 60) {
      return '${diff.inMinutes}m ago';
    } else if (diff.inHours < 24) {
      return '${diff.inHours}h ago';
    } else {
      return '${diff.inDays}d ago';
    }
  }
}
