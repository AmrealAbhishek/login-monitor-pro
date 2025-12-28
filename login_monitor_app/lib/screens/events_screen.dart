import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../main.dart';
import '../models/event.dart';
import '../services/supabase_service.dart';
import '../theme/cyber_theme.dart';

DateTime _toIST(DateTime dt) {
  return dt.toUtc().add(const Duration(hours: 5, minutes: 30));
}

class EventsScreen extends StatefulWidget {
  const EventsScreen({super.key});

  @override
  State<EventsScreen> createState() => _EventsScreenState();
}

class _EventsScreenState extends State<EventsScreen> {
  List<MonitorEvent> _events = [];
  bool _isLoading = true;
  String? _error;
  String _selectedFilter = 'All';
  String _searchQuery = '';
  final _searchController = TextEditingController();

  final List<String> _filters = ['All', 'Login', 'Unlock', 'Intruder', 'Security'];

  @override
  void initState() {
    super.initState();
    _loadEvents();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadEvents() async {
    final deviceId = context.read<AppState>().selectedDeviceId;
    if (deviceId == null) {
      setState(() {
        _isLoading = false;
        _error = 'No device selected';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final events = await SupabaseService.getEvents(
        deviceId: deviceId,
        limit: 100,
      );
      setState(() {
        _events = events;
        _isLoading = false;
      });

      // Mark all as read
      for (final event in events.where((e) => !e.isRead)) {
        await SupabaseService.markEventAsRead(event.id);
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  List<MonitorEvent> get _filteredEvents {
    var events = _events;

    // Apply type filter
    if (_selectedFilter != 'All') {
      if (_selectedFilter == 'Security') {
        events = events.where((e) =>
            ['Intruder', 'UnknownUSB', 'UnknownNetwork', 'GeofenceExit'].contains(e.eventType)).toList();
      } else {
        events = events.where((e) =>
            e.eventType.toLowerCase() == _selectedFilter.toLowerCase()).toList();
      }
    }

    // Apply search
    if (_searchQuery.isNotEmpty) {
      events = events.where((e) =>
          e.eventType.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          (e.username?.toLowerCase().contains(_searchQuery.toLowerCase()) ?? false) ||
          (e.hostname?.toLowerCase().contains(_searchQuery.toLowerCase()) ?? false)).toList();
    }

    return events;
  }

  String _formatTime(DateTime dt) {
    final ist = _toIST(dt);
    return DateFormat('dd MMM, hh:mm a').format(ist);
  }

  String _getRelativeTime(DateTime dt) {
    final now = DateTime.now();
    final diff = now.difference(dt);

    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return DateFormat('dd MMM').format(_toIST(dt));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('EVENTS'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadEvents,
          ),
        ],
      ),
      body: Column(
        children: [
          // Search and Filters
          Container(
            padding: const EdgeInsets.all(16),
            color: CyberColors.pureBlack,
            child: Column(
              children: [
                // Search bar
                Container(
                  decoration: BoxDecoration(
                    color: CyberColors.surfaceColor,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: CyberColors.borderColor),
                  ),
                  child: TextField(
                    controller: _searchController,
                    onChanged: (value) => setState(() => _searchQuery = value),
                    decoration: InputDecoration(
                      hintText: 'Search events...',
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
                ),
                const SizedBox(height: 12),

                // Filter chips
                SizedBox(
                  height: 36,
                  child: ListView.builder(
                    scrollDirection: Axis.horizontal,
                    itemCount: _filters.length,
                    itemBuilder: (context, index) {
                      final filter = _filters[index];
                      final isSelected = _selectedFilter == filter;
                      return Padding(
                        padding: EdgeInsets.only(right: index < _filters.length - 1 ? 8 : 0),
                        child: GestureDetector(
                          onTap: () => setState(() => _selectedFilter = filter),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 14),
                            decoration: BoxDecoration(
                              color: isSelected ? CyberColors.primaryRed : CyberColors.surfaceColor,
                              borderRadius: BorderRadius.circular(18),
                              border: Border.all(
                                color: isSelected ? CyberColors.primaryRed : CyberColors.borderColor,
                              ),
                            ),
                            child: Center(
                              child: Text(
                                filter,
                                style: TextStyle(
                                  color: isSelected ? CyberColors.pureWhite : CyberColors.textSecondary,
                                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),

          // Events list
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: CyberColors.primaryRed),
      );
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: CyberColors.alertRed),
            const SizedBox(height: 16),
            Text('Error: $_error', style: const TextStyle(color: CyberColors.textSecondary)),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadEvents,
              style: ElevatedButton.styleFrom(backgroundColor: CyberColors.primaryRed),
              child: const Text('Retry', style: TextStyle(color: CyberColors.pureWhite)),
            ),
          ],
        ),
      );
    }

    final events = _filteredEvents;
    if (events.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.event_busy, size: 64, color: CyberColors.textMuted),
            const SizedBox(height: 16),
            Text(
              _selectedFilter != 'All' ? 'No $_selectedFilter events' : 'No events yet',
              style: const TextStyle(
                color: CyberColors.textPrimary,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Events will appear when someone\nlogs into or unlocks your Mac',
              textAlign: TextAlign.center,
              style: TextStyle(color: CyberColors.textSecondary),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadEvents,
      color: CyberColors.primaryRed,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: events.length,
        itemBuilder: (context, index) {
          final event = events[index];
          final showDateHeader = index == 0 ||
              !_isSameDay(events[index - 1].timestamp, event.timestamp);

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (showDateHeader) ...[
                if (index > 0) const SizedBox(height: 16),
                _buildDateHeader(event.timestamp),
                const SizedBox(height: 12),
              ],
              _buildEventCard(event),
            ],
          );
        },
      ),
    );
  }

  bool _isSameDay(DateTime a, DateTime b) {
    final aIST = _toIST(a);
    final bIST = _toIST(b);
    return aIST.year == bIST.year && aIST.month == bIST.month && aIST.day == bIST.day;
  }

  Widget _buildDateHeader(DateTime date) {
    final ist = _toIST(date);
    final now = _toIST(DateTime.now());
    final yesterday = now.subtract(const Duration(days: 1));

    String label;
    if (_isSameDay(date, DateTime.now())) {
      label = 'Today';
    } else if (ist.year == yesterday.year && ist.month == yesterday.month && ist.day == yesterday.day) {
      label = 'Yesterday';
    } else {
      label = DateFormat('EEEE, dd MMM yyyy').format(ist);
    }

    return Text(
      label,
      style: const TextStyle(
        color: CyberColors.primaryRed,
        fontSize: 13,
        fontWeight: FontWeight.bold,
        letterSpacing: 1,
      ),
    );
  }

  Widget _buildEventCard(MonitorEvent event) {
    final color = _getEventColor(event.eventType);
    final icon = _getEventIcon(event.eventType);

    return GestureDetector(
      onTap: () => Navigator.pushNamed(context, '/event-detail', arguments: event.id),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: CyberColors.surfaceColor,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: !event.isRead ? color.withOpacity(0.5) : CyberColors.borderColor,
            width: !event.isRead ? 1.5 : 1,
          ),
        ),
        child: Row(
          children: [
            // Timeline indicator
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: color, size: 22),
            ),
            const SizedBox(width: 14),

            // Content
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        event.eventType,
                        style: TextStyle(
                          color: color,
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (!event.isRead)
                        Container(
                          margin: const EdgeInsets.only(left: 8),
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(
                            color: CyberColors.primaryRed,
                            shape: BoxShape.circle,
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      if (event.username != null) ...[
                        Icon(Icons.person, size: 12, color: CyberColors.textMuted),
                        const SizedBox(width: 4),
                        Text(
                          event.username!,
                          style: const TextStyle(color: CyberColors.textSecondary, fontSize: 12),
                        ),
                        const SizedBox(width: 12),
                      ],
                      Icon(Icons.access_time, size: 12, color: CyberColors.textMuted),
                      const SizedBox(width: 4),
                      Text(
                        _formatTime(event.timestamp),
                        style: const TextStyle(color: CyberColors.textSecondary, fontSize: 12),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Indicators
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  _getRelativeTime(event.timestamp),
                  style: const TextStyle(color: CyberColors.textMuted, fontSize: 11),
                ),
                const SizedBox(height: 6),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (event.hasPhotos)
                      Padding(
                        padding: const EdgeInsets.only(left: 4),
                        child: Icon(Icons.photo_camera, size: 14, color: CyberColors.textMuted),
                      ),
                    if (event.hasLocation)
                      Padding(
                        padding: const EdgeInsets.only(left: 4),
                        child: Icon(Icons.location_on, size: 14, color: CyberColors.textMuted),
                      ),
                    if (event.hasAudio)
                      Padding(
                        padding: const EdgeInsets.only(left: 4),
                        child: Icon(Icons.mic, size: 14, color: CyberColors.textMuted),
                      ),
                  ],
                ),
              ],
            ),
            const SizedBox(width: 8),
            const Icon(Icons.chevron_right, color: CyberColors.textMuted, size: 20),
          ],
        ),
      ),
    );
  }

  IconData _getEventIcon(String eventType) {
    switch (eventType) {
      case 'Login':
        return Icons.login;
      case 'Unlock':
        return Icons.lock_open;
      case 'Wake':
        return Icons.wb_sunny;
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
        return Icons.event;
    }
  }

  Color _getEventColor(String eventType) {
    switch (eventType) {
      case 'Login':
        return CyberColors.primaryRed;
      case 'Unlock':
        return CyberColors.successGreen;
      case 'Wake':
        return CyberColors.infoBlue;
      case 'Intruder':
        return CyberColors.alertRed;
      case 'UnknownUSB':
        return CyberColors.warningOrange;
      case 'UnknownNetwork':
        return CyberColors.warningOrange;
      case 'GeofenceExit':
        return CyberColors.alertRed;
      case 'Movement':
        return CyberColors.warningOrange;
      default:
        return CyberColors.textMuted;
    }
  }
}
