import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';
import '../main.dart';
import '../theme/cyber_theme.dart';
import '../widgets/neon_card.dart';
import '../widgets/cyber_button.dart';
import '../services/supabase_service.dart';

class GeofenceScreen extends StatefulWidget {
  const GeofenceScreen({super.key});

  @override
  State<GeofenceScreen> createState() => _GeofenceScreenState();
}

class _GeofenceScreenState extends State<GeofenceScreen> {
  final MapController _mapController = MapController();
  List<Map<String, dynamic>> _geofences = [];
  bool _isLoading = true;
  bool _isAddingGeofence = false;
  LatLng? _selectedLocation;
  double _selectedRadius = 500;
  final TextEditingController _nameController = TextEditingController();

  // Default center (will be updated to device location)
  LatLng _center = const LatLng(28.6139, 77.2090); // Delhi

  @override
  void initState() {
    super.initState();
    _loadGeofences();
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _loadGeofences() async {
    final deviceId = context.read<AppState>().selectedDeviceId;
    if (deviceId == null) return;

    setState(() => _isLoading = true);

    try {
      // Send listgeofences command and wait for result
      await SupabaseService.sendCommand(
        deviceId: deviceId,
        command: 'listgeofences',
      );

      // Wait a bit for command to execute
      await Future.delayed(const Duration(seconds: 2));

      // Fetch geofences from database
      final response = await SupabaseService.client
          .from('geofences')
          .select()
          .eq('device_id', deviceId)
          .order('created_at', ascending: false);

      setState(() {
        _geofences = List<Map<String, dynamic>>.from(response);
        _isLoading = false;
      });

      // Center map on first geofence if available
      if (_geofences.isNotEmpty) {
        final first = _geofences.first;
        _center = LatLng(
          (first['latitude'] as num).toDouble(),
          (first['longitude'] as num).toDouble(),
        );
      }
    } catch (e) {
      setState(() => _isLoading = false);
      debugPrint('Error loading geofences: $e');
    }
  }

  void _onMapTap(TapPosition tapPosition, LatLng point) {
    if (_isAddingGeofence) {
      setState(() {
        _selectedLocation = point;
      });
    }
  }

  Future<void> _saveGeofence() async {
    if (_selectedLocation == null || _nameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter a name and select a location'),
          backgroundColor: CyberColors.alertRed,
        ),
      );
      return;
    }

    final deviceId = context.read<AppState>().selectedDeviceId;
    if (deviceId == null) return;

    try {
      await SupabaseService.sendCommand(
        deviceId: deviceId,
        command: 'setgeofence',
        args: {
          'name': _nameController.text,
          'lat': _selectedLocation!.latitude,
          'lon': _selectedLocation!.longitude,
          'radius': _selectedRadius.toInt(),
        },
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Geofence "${_nameController.text}" created!'),
            backgroundColor: CyberColors.successGreen,
          ),
        );
      }

      setState(() {
        _isAddingGeofence = false;
        _selectedLocation = null;
        _nameController.clear();
      });

      // Reload geofences
      await Future.delayed(const Duration(seconds: 2));
      _loadGeofences();
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

  Future<void> _deleteGeofence(String id, String name) async {
    final deviceId = context.read<AppState>().selectedDeviceId;
    if (deviceId == null) return;

    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Geofence'),
        content: Text('Are you sure you want to delete "$name"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete', style: TextStyle(color: CyberColors.alertRed)),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    try {
      await SupabaseService.sendCommand(
        deviceId: deviceId,
        command: 'removegeofence',
        args: {'id': id},
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Geofence "$name" deleted'),
            backgroundColor: CyberColors.successGreen,
          ),
        );
      }

      await Future.delayed(const Duration(seconds: 2));
      _loadGeofences();
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('GEOFENCES'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadGeofences,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: CyberColors.primaryRed),
            )
          : Column(
              children: [
                // Map
                Expanded(
                  flex: 3,
                  child: Stack(
                    children: [
                      FlutterMap(
                        mapController: _mapController,
                        options: MapOptions(
                          initialCenter: _center,
                          initialZoom: 14,
                          onTap: _onMapTap,
                        ),
                        children: [
                          TileLayer(
                            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                            userAgentPackageName: 'com.loginmonitor.app',
                          ),
                          // Geofence circles
                          CircleLayer(
                            circles: [
                              ..._geofences.map((g) => CircleMarker(
                                    point: LatLng(
                                      (g['latitude'] as num).toDouble(),
                                      (g['longitude'] as num).toDouble(),
                                    ),
                                    radius: (g['radius_meters'] as num?)?.toDouble() ?? 500,
                                    useRadiusInMeter: true,
                                    color: CyberColors.primaryRed.withOpacity(0.2),
                                    borderColor: CyberColors.primaryRed,
                                    borderStrokeWidth: 2,
                                  )),
                              // Selected location circle
                              if (_selectedLocation != null)
                                CircleMarker(
                                  point: _selectedLocation!,
                                  radius: _selectedRadius,
                                  useRadiusInMeter: true,
                                  color: CyberColors.successGreen.withOpacity(0.3),
                                  borderColor: CyberColors.successGreen,
                                  borderStrokeWidth: 3,
                                ),
                            ],
                          ),
                          // Geofence markers
                          MarkerLayer(
                            markers: [
                              ..._geofences.map((g) => Marker(
                                    point: LatLng(
                                      (g['latitude'] as num).toDouble(),
                                      (g['longitude'] as num).toDouble(),
                                    ),
                                    width: 40,
                                    height: 40,
                                    child: GestureDetector(
                                      onTap: () => _showGeofenceInfo(g),
                                      child: Container(
                                        decoration: BoxDecoration(
                                          color: CyberColors.pureBlack,
                                          shape: BoxShape.circle,
                                          border: Border.all(
                                            color: CyberColors.primaryRed,
                                            width: 2,
                                          ),
                                        ),
                                        child: const Icon(
                                          Icons.location_on,
                                          color: CyberColors.primaryRed,
                                          size: 24,
                                        ),
                                      ),
                                    ),
                                  )),
                              // Selected location marker
                              if (_selectedLocation != null)
                                Marker(
                                  point: _selectedLocation!,
                                  width: 50,
                                  height: 50,
                                  child: Container(
                                    decoration: BoxDecoration(
                                      color: CyberColors.successGreen,
                                      shape: BoxShape.circle,
                                      border: Border.all(
                                        color: CyberColors.pureWhite,
                                        width: 3,
                                      ),
                                    ),
                                    child: const Icon(
                                      Icons.add_location,
                                      color: CyberColors.pureWhite,
                                      size: 28,
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ],
                      ),
                      // Add mode indicator
                      if (_isAddingGeofence)
                        Positioned(
                          top: 16,
                          left: 16,
                          right: 16,
                          child: Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: CyberColors.pureBlack.withOpacity(0.9),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: CyberColors.successGreen),
                            ),
                            child: const Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.touch_app, color: CyberColors.successGreen),
                                SizedBox(width: 8),
                                Text(
                                  'Tap on map to select location',
                                  style: TextStyle(
                                    color: CyberColors.successGreen,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                    ],
                  ),
                ),

                // Bottom panel
                Container(
                  color: CyberColors.pureBlack,
                  child: _isAddingGeofence
                      ? _buildAddGeofencePanel()
                      : _buildGeofenceList(),
                ),
              ],
            ),
      floatingActionButton: !_isAddingGeofence
          ? FloatingActionButton(
              onPressed: () => setState(() => _isAddingGeofence = true),
              backgroundColor: CyberColors.primaryRed,
              child: const Icon(Icons.add_location, color: CyberColors.pureWhite),
            )
          : null,
    );
  }

  Widget _buildAddGeofencePanel() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              const Icon(Icons.add_location, color: CyberColors.successGreen),
              const SizedBox(width: 8),
              const Text(
                'New Geofence',
                style: TextStyle(
                  color: CyberColors.textPrimary,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const Spacer(),
              IconButton(
                icon: const Icon(Icons.close, color: CyberColors.textMuted),
                onPressed: () => setState(() {
                  _isAddingGeofence = false;
                  _selectedLocation = null;
                  _nameController.clear();
                }),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Name input
          TextField(
            controller: _nameController,
            decoration: const InputDecoration(
              labelText: 'Geofence Name',
              hintText: 'e.g., Home, Office, School',
              prefixIcon: Icon(Icons.label, color: CyberColors.primaryRed),
            ),
          ),
          const SizedBox(height: 16),

          // Radius slider
          Row(
            children: [
              const Text('Radius:', style: TextStyle(color: CyberColors.textSecondary)),
              Expanded(
                child: Slider(
                  value: _selectedRadius,
                  min: 100,
                  max: 2000,
                  divisions: 19,
                  label: '${_selectedRadius.toInt()}m',
                  onChanged: (value) => setState(() => _selectedRadius = value),
                ),
              ),
              Text(
                '${_selectedRadius.toInt()}m',
                style: const TextStyle(
                  color: CyberColors.primaryRed,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Location info
          if (_selectedLocation != null)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: CyberColors.surfaceColor,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.location_on, color: CyberColors.successGreen, size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Lat: ${_selectedLocation!.latitude.toStringAsFixed(4)}, Lon: ${_selectedLocation!.longitude.toStringAsFixed(4)}',
                      style: const TextStyle(color: CyberColors.textSecondary, fontSize: 12),
                    ),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 16),

          // Save button
          CyberButton(
            label: 'SAVE GEOFENCE',
            icon: Icons.save,
            onPressed: _saveGeofence,
            width: double.infinity,
          ),
        ],
      ),
    );
  }

  Widget _buildGeofenceList() {
    if (_geofences.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.location_off, size: 48, color: CyberColors.textMuted),
            const SizedBox(height: 12),
            const Text(
              'No geofences yet',
              style: TextStyle(
                color: CyberColors.textPrimary,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'Tap + to add a geofence',
              style: TextStyle(color: CyberColors.textSecondary),
            ),
          ],
        ),
      );
    }

    return Container(
      constraints: const BoxConstraints(maxHeight: 200),
      child: ListView.builder(
        shrinkWrap: true,
        padding: const EdgeInsets.all(8),
        itemCount: _geofences.length,
        itemBuilder: (context, index) {
          final g = _geofences[index];
          return ListTile(
            leading: Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: CyberColors.primaryRed.withOpacity(0.2),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.location_on, color: CyberColors.primaryRed),
            ),
            title: Text(
              g['name'] ?? 'Unnamed',
              style: const TextStyle(
                color: CyberColors.textPrimary,
                fontWeight: FontWeight.bold,
              ),
            ),
            subtitle: Text(
              'Radius: ${g['radius_meters'] ?? 500}m',
              style: const TextStyle(color: CyberColors.textSecondary, fontSize: 12),
            ),
            trailing: IconButton(
              icon: const Icon(Icons.delete, color: CyberColors.alertRed),
              onPressed: () => _deleteGeofence(g['id'], g['name'] ?? 'Unnamed'),
            ),
            onTap: () {
              _mapController.move(
                LatLng(
                  (g['latitude'] as num).toDouble(),
                  (g['longitude'] as num).toDouble(),
                ),
                15,
              );
            },
          );
        },
      ),
    );
  }

  void _showGeofenceInfo(Map<String, dynamic> g) {
    showModalBottomSheet(
      context: context,
      backgroundColor: CyberColors.darkBackground,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: CyberColors.primaryRed.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.location_on, color: CyberColors.primaryRed),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        g['name'] ?? 'Unnamed',
                        style: const TextStyle(
                          color: CyberColors.primaryRed,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        g['is_active'] == true ? 'Active' : 'Inactive',
                        style: TextStyle(
                          color: g['is_active'] == true
                              ? CyberColors.successGreen
                              : CyberColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: CyberColors.textMuted),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const SizedBox(height: 24),
            _buildInfoRow('Latitude', '${g['latitude']}'),
            _buildInfoRow('Longitude', '${g['longitude']}'),
            _buildInfoRow('Radius', '${g['radius_meters'] ?? 500} meters'),
            const SizedBox(height: 24),
            CyberButton(
              label: 'DELETE GEOFENCE',
              icon: Icons.delete,
              color: CyberColors.alertRed,
              onPressed: () {
                Navigator.pop(context);
                _deleteGeofence(g['id'], g['name'] ?? 'Unnamed');
              },
              width: double.infinity,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: CyberColors.textSecondary)),
          Text(
            value,
            style: const TextStyle(
              color: CyberColors.textPrimary,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
