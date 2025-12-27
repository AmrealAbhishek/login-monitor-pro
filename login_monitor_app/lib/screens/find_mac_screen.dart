import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:async';
import '../main.dart';
import '../theme/cyber_theme.dart';
import '../widgets/neon_card.dart';
import '../widgets/cyber_button.dart';
import '../widgets/pulse_indicator.dart';
import '../services/supabase_service.dart';

class FindMacScreen extends StatefulWidget {
  const FindMacScreen({super.key});

  @override
  State<FindMacScreen> createState() => _FindMacScreenState();
}

class _FindMacScreenState extends State<FindMacScreen>
    with TickerProviderStateMixin {
  bool _isFinding = false;
  bool _isLoading = false;
  int _duration = 60;
  Map<String, dynamic>? _lastLocation;
  String? _lastLocationTime;
  Timer? _locationTimer;

  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );
    _loadLastLocation();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _locationTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadLastLocation() async {
    final deviceId = context.read<AppState>().selectedDeviceId;
    if (deviceId == null) return;

    try {
      // Get the most recent location from events
      final events = await SupabaseService.getEvents(deviceId: deviceId, limit: 50);

      for (final event in events) {
        if (event.location != null &&
            event.location!['latitude'] != null &&
            event.location!['longitude'] != null) {
          setState(() {
            _lastLocation = event.location;
            _lastLocationTime = _formatTime(event.timestamp);
          });
          break;
        }
      }
    } catch (e) {
      debugPrint('Error loading location: $e');
    }
  }

  Future<void> _startFinding() async {
    final deviceId = context.read<AppState>().selectedDeviceId;
    if (deviceId == null) return;

    setState(() {
      _isLoading = true;
    });

    try {
      await SupabaseService.sendCommand(
        deviceId: deviceId,
        command: 'findme',
        args: {'duration': _duration},
      );

      setState(() {
        _isFinding = true;
        _isLoading = false;
      });

      _pulseController.repeat();

      // Start polling for location updates
      _locationTimer = Timer.periodic(const Duration(seconds: 5), (_) {
        _loadLastLocation();
      });

      // Auto-stop after duration
      Future.delayed(Duration(seconds: _duration), () {
        if (mounted && _isFinding) {
          _stopFinding();
        }
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Find My Mac activated! Alarm playing on Mac...'),
            backgroundColor: CyberColors.successGreen,
          ),
        );
      }
    } catch (e) {
      setState(() => _isLoading = false);
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

  Future<void> _stopFinding() async {
    final deviceId = context.read<AppState>().selectedDeviceId;
    if (deviceId == null) return;

    try {
      await SupabaseService.sendCommand(
        deviceId: deviceId,
        command: 'stopfind',
      );
    } catch (e) {
      debugPrint('Error stopping: $e');
    }

    _locationTimer?.cancel();
    _pulseController.stop();

    setState(() {
      _isFinding = false;
    });

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Find My Mac stopped'),
          backgroundColor: CyberColors.textMuted,
        ),
      );
    }
  }

  String _formatTime(DateTime dt) {
    final now = DateTime.now();
    final diff = now.difference(dt);

    if (diff.inMinutes < 1) {
      return 'Just now';
    } else if (diff.inMinutes < 60) {
      return '${diff.inMinutes}m ago';
    } else if (diff.inHours < 24) {
      return '${diff.inHours}h ago';
    } else {
      return '${diff.inDays}d ago';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('FIND MY MAC'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            // Status Card
            _buildStatusCard(),
            const SizedBox(height: 24),

            // Duration Selector
            if (!_isFinding) _buildDurationSelector(),
            const SizedBox(height: 24),

            // Action Button
            _buildActionButton(),
            const SizedBox(height: 24),

            // Last Known Location
            _buildLocationCard(),
            const SizedBox(height: 24),

            // Instructions
            _buildInstructions(),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusCard() {
    return NeonCard(
      glowColor: _isFinding ? CyberColors.alertRed : CyberColors.neonCyan,
      animate: _isFinding,
      isAlert: _isFinding,
      child: Column(
        children: [
          if (_isFinding)
            PulseIndicator(
              color: CyberColors.alertRed,
              size: 150,
              child: Icon(
                Icons.volume_up,
                color: CyberColors.alertRed,
                size: 50,
              ),
            )
          else
            Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: CyberColors.surfaceColor,
                border: Border.all(color: CyberColors.neonCyan, width: 2),
              ),
              child: const Icon(
                Icons.laptop_mac,
                color: CyberColors.neonCyan,
                size: 50,
              ),
            ),
          const SizedBox(height: 20),
          Text(
            _isFinding ? 'FINDING YOUR MAC...' : 'FIND MY MAC',
            style: TextStyle(
              color: _isFinding ? CyberColors.alertRed : CyberColors.neonCyan,
              fontSize: 24,
              fontWeight: FontWeight.bold,
              letterSpacing: 2,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _isFinding
                ? 'Alarm is playing on your Mac'
                : 'Play a loud alarm on your Mac to find it',
            style: const TextStyle(
              color: CyberColors.textSecondary,
              fontSize: 14,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildDurationSelector() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Alarm Duration',
          style: TextStyle(
            color: CyberColors.neonCyan,
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            _buildDurationOption(30, '30s'),
            const SizedBox(width: 12),
            _buildDurationOption(60, '1m'),
            const SizedBox(width: 12),
            _buildDurationOption(120, '2m'),
            const SizedBox(width: 12),
            _buildDurationOption(300, '5m'),
          ],
        ),
      ],
    );
  }

  Widget _buildDurationOption(int seconds, String label) {
    final isSelected = _duration == seconds;

    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _duration = seconds),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: isSelected
                ? CyberColors.neonCyan.withOpacity(0.2)
                : CyberColors.surfaceColor,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isSelected ? CyberColors.neonCyan : CyberColors.textMuted,
              width: isSelected ? 2 : 1,
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: isSelected ? CyberColors.neonCyan : CyberColors.textSecondary,
              fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            ),
            textAlign: TextAlign.center,
          ),
        ),
      ),
    );
  }

  Widget _buildActionButton() {
    if (_isFinding) {
      return CyberButton(
        label: 'STOP ALARM',
        icon: Icons.stop,
        color: CyberColors.alertRed,
        onPressed: _stopFinding,
        width: double.infinity,
        height: 60,
      );
    }

    return CyberButton(
      label: 'START FINDING',
      icon: Icons.volume_up,
      isLoading: _isLoading,
      onPressed: _startFinding,
      width: double.infinity,
      height: 60,
    );
  }

  Widget _buildLocationCard() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Last Known Location',
          style: TextStyle(
            color: CyberColors.neonCyan,
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 12),
        NeonCard(
          glowIntensity: 0.2,
          child: _lastLocation != null
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(
                          Icons.location_on,
                          color: CyberColors.neonCyan,
                          size: 24,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${_lastLocation!['city'] ?? 'Unknown'}, ${_lastLocation!['country'] ?? ''}',
                                style: const TextStyle(
                                  color: CyberColors.textPrimary,
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Updated $_lastLocationTime',
                                style: const TextStyle(
                                  color: CyberColors.textSecondary,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    const Divider(color: CyberColors.textMuted),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        Column(
                          children: [
                            const Text(
                              'Latitude',
                              style: TextStyle(
                                color: CyberColors.textMuted,
                                fontSize: 12,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              '${_lastLocation!['latitude']?.toStringAsFixed(4) ?? '-'}',
                              style: const TextStyle(
                                color: CyberColors.neonCyan,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                        Column(
                          children: [
                            const Text(
                              'Longitude',
                              style: TextStyle(
                                color: CyberColors.textMuted,
                                fontSize: 12,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              '${_lastLocation!['longitude']?.toStringAsFixed(4) ?? '-'}',
                              style: const TextStyle(
                                color: CyberColors.neonCyan,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ],
                )
              : const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.location_off,
                      color: CyberColors.textMuted,
                    ),
                    SizedBox(width: 8),
                    Text(
                      'No location data available',
                      style: TextStyle(color: CyberColors.textMuted),
                    ),
                  ],
                ),
        ),
      ],
    );
  }

  Widget _buildInstructions() {
    return NeonCard(
      glowIntensity: 0.2,
      glowColor: CyberColors.infoBlue,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.info_outline, color: CyberColors.infoBlue),
              const SizedBox(width: 8),
              const Text(
                'How it works',
                style: TextStyle(
                  color: CyberColors.infoBlue,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildInstruction('1', 'Your Mac will play a loud alarm'),
          _buildInstruction('2', 'Volume will be set to maximum'),
          _buildInstruction('3', 'Location updates will be sent'),
          _buildInstruction('4', 'Tap "Stop Alarm" when you find it'),
        ],
      ),
    );
  }

  Widget _buildInstruction(String number, String text) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: CyberColors.infoBlue.withOpacity(0.2),
            ),
            child: Center(
              child: Text(
                number,
                style: const TextStyle(
                  color: CyberColors.infoBlue,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Text(
            text,
            style: const TextStyle(
              color: CyberColors.textSecondary,
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }
}
