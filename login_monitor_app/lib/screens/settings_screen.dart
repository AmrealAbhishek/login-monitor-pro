import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/cyber_theme.dart';
import '../models/device.dart';
import '../services/supabase_service.dart';
import '../widgets/cyber_button.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  List<Device> _devices = [];
  bool _isLoading = true;

  // User profile data
  String? _displayName;
  String? _avatarUrl;
  String? _email;

  // Notification toggles
  bool _pushNotifications = true;
  bool _loginAlerts = true;
  bool _securityAlerts = true;
  bool _geofenceAlerts = true;

  // Preference toggles
  bool _soundEffects = true;
  bool _vibration = true;

  @override
  void initState() {
    super.initState();
    _loadData();
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

      // Load preferences
      final prefs = await SharedPreferences.getInstance();
      _pushNotifications = prefs.getBool('push_notifications') ?? true;
      _loginAlerts = prefs.getBool('login_alerts') ?? true;
      _securityAlerts = prefs.getBool('security_alerts') ?? true;
      _geofenceAlerts = prefs.getBool('geofence_alerts') ?? true;
      _soundEffects = prefs.getBool('sound_effects') ?? true;
      _vibration = prefs.getBool('vibration') ?? true;

      setState(() {
        _devices = devices;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _savePreference(String key, bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(key, value);
  }

  Future<void> _unpairDevice(Device device) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: CyberColors.darkBackground,
        title: const Text('Unpair Device?'),
        content: Text(
          'Are you sure you want to unpair "${device.hostname}"?\n\n'
          'You will stop receiving notifications from this device.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Unpair', style: TextStyle(color: CyberColors.alertRed)),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    try {
      await SupabaseService.unpairDevice(device.id);
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Device unpaired'),
          backgroundColor: CyberColors.successGreen,
        ),
      );
      _loadData();

      // If no devices left, go to pairing
      if (_devices.length <= 1) {
        Navigator.pushReplacementNamed(context, '/pairing');
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error: $e'),
          backgroundColor: CyberColors.alertRed,
        ),
      );
    }
  }

  Future<void> _signOut() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: CyberColors.darkBackground,
        title: const Text('Sign Out?'),
        content: const Text('Are you sure you want to sign out?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Sign Out', style: TextStyle(color: CyberColors.alertRed)),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    await SupabaseService.signOut();
    if (!mounted) return;
    Navigator.pushReplacementNamed(context, '/login');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SETTINGS'),
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: CyberColors.primaryRed),
            )
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Profile Section
                _buildProfileCard(),
                const SizedBox(height: 24),

                // Devices Section
                _buildSectionTitle('DEVICES'),
                _buildDevicesCard(),
                const SizedBox(height: 24),

                // Notifications Section
                _buildSectionTitle('NOTIFICATIONS'),
                _buildNotificationsCard(),
                const SizedBox(height: 24),

                // Preferences Section
                _buildSectionTitle('PREFERENCES'),
                _buildPreferencesCard(),
                const SizedBox(height: 24),

                // App Section
                _buildSectionTitle('APP'),
                _buildAppCard(),
                const SizedBox(height: 24),

                // Sign Out Button
                CyberButton(
                  label: 'SIGN OUT',
                  icon: Icons.logout,
                  color: CyberColors.alertRed,
                  onPressed: _signOut,
                  width: double.infinity,
                ),
                const SizedBox(height: 32),
              ],
            ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 12),
      child: Text(
        title,
        style: const TextStyle(
          color: CyberColors.primaryRed,
          fontSize: 12,
          fontWeight: FontWeight.bold,
          letterSpacing: 1.5,
        ),
      ),
    );
  }

  Widget _buildProfileCard() {
    return GestureDetector(
      onTap: () => Navigator.pushNamed(context, '/profile').then((_) => _loadData()),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              CyberColors.primaryRed.withOpacity(0.15),
              CyberColors.surfaceColor,
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: CyberColors.primaryRed.withOpacity(0.3)),
        ),
        child: Row(
          children: [
            // Avatar
            Container(
              width: 60,
              height: 60,
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
                        child: const Icon(Icons.person, color: CyberColors.textMuted, size: 30),
                      ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _displayName ?? _email?.split('@').first ?? 'User',
                    style: const TextStyle(
                      color: CyberColors.textPrimary,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _email ?? '',
                    style: const TextStyle(
                      color: CyberColors.textSecondary,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: CyberColors.primaryRed.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(
                Icons.chevron_right,
                color: CyberColors.primaryRed,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDevicesCard() {
    return Container(
      decoration: BoxDecoration(
        color: CyberColors.surfaceColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: CyberColors.borderColor),
      ),
      child: Column(
        children: [
          ..._devices.asMap().entries.map((entry) {
            final index = entry.key;
            final device = entry.value;
            return Column(
              children: [
                if (index > 0) const Divider(height: 1, color: CyberColors.borderColor),
                ListTile(
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                  leading: Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: device.isOnline
                          ? CyberColors.successGreen.withOpacity(0.1)
                          : CyberColors.textMuted.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(
                      Icons.laptop_mac,
                      color: device.isOnline ? CyberColors.successGreen : CyberColors.textMuted,
                    ),
                  ),
                  title: Text(
                    device.hostname ?? 'Unknown Mac',
                    style: const TextStyle(
                      color: CyberColors.textPrimary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  subtitle: Row(
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
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                  trailing: IconButton(
                    icon: const Icon(Icons.link_off, color: CyberColors.alertRed, size: 20),
                    onPressed: () => _unpairDevice(device),
                  ),
                ),
              ],
            );
          }),
          const Divider(height: 1, color: CyberColors.borderColor),
          ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            leading: Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: CyberColors.primaryRed.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.add, color: CyberColors.primaryRed),
            ),
            title: const Text(
              'Add New Device',
              style: TextStyle(
                color: CyberColors.primaryRed,
                fontWeight: FontWeight.w600,
              ),
            ),
            onTap: () => Navigator.pushNamed(context, '/pairing'),
          ),
        ],
      ),
    );
  }

  Widget _buildNotificationsCard() {
    return Container(
      decoration: BoxDecoration(
        color: CyberColors.surfaceColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: CyberColors.borderColor),
      ),
      child: Column(
        children: [
          _buildSwitchTile(
            icon: Icons.notifications,
            title: 'Push Notifications',
            subtitle: 'Receive alerts on your phone',
            value: _pushNotifications,
            onChanged: (value) {
              setState(() => _pushNotifications = value);
              _savePreference('push_notifications', value);
            },
          ),
          const Divider(height: 1, color: CyberColors.borderColor),
          _buildSwitchTile(
            icon: Icons.login,
            title: 'Login Alerts',
            subtitle: 'When someone logs in to your Mac',
            value: _loginAlerts,
            onChanged: (value) {
              setState(() => _loginAlerts = value);
              _savePreference('login_alerts', value);
            },
          ),
          const Divider(height: 1, color: CyberColors.borderColor),
          _buildSwitchTile(
            icon: Icons.security,
            title: 'Security Alerts',
            subtitle: 'Intruder detection, unknown devices',
            value: _securityAlerts,
            onChanged: (value) {
              setState(() => _securityAlerts = value);
              _savePreference('security_alerts', value);
            },
          ),
          const Divider(height: 1, color: CyberColors.borderColor),
          _buildSwitchTile(
            icon: Icons.location_on,
            title: 'Geofence Alerts',
            subtitle: 'When your Mac leaves safe zones',
            value: _geofenceAlerts,
            onChanged: (value) {
              setState(() => _geofenceAlerts = value);
              _savePreference('geofence_alerts', value);
            },
          ),
        ],
      ),
    );
  }

  Widget _buildPreferencesCard() {
    return Container(
      decoration: BoxDecoration(
        color: CyberColors.surfaceColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: CyberColors.borderColor),
      ),
      child: Column(
        children: [
          _buildSwitchTile(
            icon: Icons.volume_up,
            title: 'Sound Effects',
            subtitle: 'Play sounds for alerts',
            value: _soundEffects,
            onChanged: (value) {
              setState(() => _soundEffects = value);
              _savePreference('sound_effects', value);
            },
          ),
          const Divider(height: 1, color: CyberColors.borderColor),
          _buildSwitchTile(
            icon: Icons.vibration,
            title: 'Vibration',
            subtitle: 'Vibrate on notifications',
            value: _vibration,
            onChanged: (value) {
              setState(() => _vibration = value);
              _savePreference('vibration', value);
            },
          ),
        ],
      ),
    );
  }

  Widget _buildAppCard() {
    return Container(
      decoration: BoxDecoration(
        color: CyberColors.surfaceColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: CyberColors.borderColor),
      ),
      child: Column(
        children: [
          _buildNavigationTile(
            icon: Icons.info_outline,
            title: 'About',
            subtitle: 'Version 3.1.0',
            onTap: () => _showAboutDialog(),
          ),
          const Divider(height: 1, color: CyberColors.borderColor),
          _buildNavigationTile(
            icon: Icons.privacy_tip_outlined,
            title: 'Privacy Policy',
            onTap: () {},
          ),
          const Divider(height: 1, color: CyberColors.borderColor),
          _buildNavigationTile(
            icon: Icons.help_outline,
            title: 'Help & Support',
            onTap: () {},
          ),
        ],
      ),
    );
  }

  Widget _buildSwitchTile({
    required IconData icon,
    required String title,
    String? subtitle,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      leading: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: CyberColors.primaryRed.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(icon, color: CyberColors.primaryRed, size: 22),
      ),
      title: Text(
        title,
        style: const TextStyle(
          color: CyberColors.textPrimary,
          fontWeight: FontWeight.w500,
        ),
      ),
      subtitle: subtitle != null
          ? Text(
              subtitle,
              style: const TextStyle(
                color: CyberColors.textSecondary,
                fontSize: 12,
              ),
            )
          : null,
      trailing: Switch(
        value: value,
        onChanged: onChanged,
        activeColor: CyberColors.primaryRed,
        activeTrackColor: CyberColors.primaryRed.withOpacity(0.3),
      ),
    );
  }

  Widget _buildNavigationTile({
    required IconData icon,
    required String title,
    String? subtitle,
    required VoidCallback onTap,
  }) {
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      leading: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: CyberColors.primaryRed.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(icon, color: CyberColors.primaryRed, size: 22),
      ),
      title: Text(
        title,
        style: const TextStyle(
          color: CyberColors.textPrimary,
          fontWeight: FontWeight.w500,
        ),
      ),
      subtitle: subtitle != null
          ? Text(
              subtitle,
              style: const TextStyle(
                color: CyberColors.textSecondary,
                fontSize: 12,
              ),
            )
          : null,
      trailing: const Icon(Icons.chevron_right, color: CyberColors.textMuted),
      onTap: onTap,
    );
  }

  void _showAboutDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: CyberColors.darkBackground,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: CyberColors.primaryRed.withOpacity(0.1),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.security,
                color: CyberColors.primaryRed,
                size: 40,
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'Login Monitor PRO',
              style: TextStyle(
                color: CyberColors.textPrimary,
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'Version 3.1.0',
              style: TextStyle(
                color: CyberColors.textSecondary,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'Professional Mac security monitoring with real-time alerts, remote commands, and advanced protection features.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: CyberColors.textSecondary,
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 24),
            CyberButton(
              label: 'CLOSE',
              onPressed: () => Navigator.pop(context),
              width: double.infinity,
            ),
          ],
        ),
      ),
    );
  }
}
