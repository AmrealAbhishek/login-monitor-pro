import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:supabase_flutter/supabase_flutter.dart' show FileOptions;
import '../theme/cyber_theme.dart';
import '../widgets/cyber_button.dart';
import '../services/supabase_service.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  bool _isLoading = true;
  bool _isSaving = false;
  bool _isUploadingAvatar = false;

  final _displayNameController = TextEditingController();
  final _phoneController = TextEditingController();

  String? _email;
  String? _avatarUrl;
  DateTime? _createdAt;
  int _deviceCount = 0;
  File? _selectedImage;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  @override
  void dispose() {
    _displayNameController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _loadProfile() async {
    setState(() => _isLoading = true);

    try {
      final user = SupabaseService.client.auth.currentUser;
      if (user == null) {
        if (mounted) Navigator.pop(context);
        return;
      }

      _email = user.email;
      _createdAt = DateTime.tryParse(user.createdAt);

      // Load profile data from profiles table
      try {
        final profile = await SupabaseService.client
            .from('profiles')
            .select()
            .eq('id', user.id)
            .maybeSingle();

        if (profile != null) {
          _displayNameController.text = profile['display_name'] ?? '';
          _phoneController.text = profile['phone_number'] ?? '';
          _avatarUrl = profile['avatar_url'];
        }
      } catch (e) {
        debugPrint('Error loading profile: $e');
      }

      // Count devices
      try {
        final devices = await SupabaseService.client
            .from('devices')
            .select('id')
            .eq('user_id', user.id);
        _deviceCount = devices.length;
      } catch (e) {
        debugPrint('Error counting devices: $e');
      }

      setState(() => _isLoading = false);
    } catch (e) {
      debugPrint('Error: $e');
      setState(() => _isLoading = false);
    }
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final picker = ImagePicker();
      final pickedFile = await picker.pickImage(
        source: source,
        maxWidth: 512,
        maxHeight: 512,
        imageQuality: 80,
      );

      if (pickedFile != null) {
        setState(() {
          _selectedImage = File(pickedFile.path);
        });
        await _uploadAvatar();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error picking image: $e'),
            backgroundColor: CyberColors.alertRed,
          ),
        );
      }
    }
  }

  void _showImageSourceDialog() {
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
          children: [
            const Text(
              'Choose Photo Source',
              style: TextStyle(
                color: CyberColors.textPrimary,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildSourceOption(
                  icon: Icons.camera_alt,
                  label: 'Camera',
                  onTap: () {
                    Navigator.pop(context);
                    _pickImage(ImageSource.camera);
                  },
                ),
                _buildSourceOption(
                  icon: Icons.photo_library,
                  label: 'Gallery',
                  onTap: () {
                    Navigator.pop(context);
                    _pickImage(ImageSource.gallery);
                  },
                ),
              ],
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _buildSourceOption({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 70,
            height: 70,
            decoration: BoxDecoration(
              color: CyberColors.surfaceColor,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: CyberColors.primaryRed.withOpacity(0.5)),
            ),
            child: Icon(icon, color: CyberColors.primaryRed, size: 32),
          ),
          const SizedBox(height: 8),
          Text(
            label,
            style: const TextStyle(color: CyberColors.textSecondary),
          ),
        ],
      ),
    );
  }

  Future<void> _uploadAvatar() async {
    if (_selectedImage == null) return;

    setState(() => _isUploadingAvatar = true);

    try {
      final user = SupabaseService.client.auth.currentUser;
      if (user == null) return;

      final fileName = 'avatar_${user.id}_${DateTime.now().millisecondsSinceEpoch}.jpg';
      final bytes = await _selectedImage!.readAsBytes();

      // Upload to Supabase Storage
      await SupabaseService.client.storage
          .from('avatars')
          .uploadBinary(fileName, bytes, fileOptions: FileOptions(upsert: true));

      // Get public URL
      final publicUrl = SupabaseService.client.storage
          .from('avatars')
          .getPublicUrl(fileName);

      // Update profile
      await SupabaseService.client.from('profiles').upsert({
        'id': user.id,
        'avatar_url': publicUrl,
        'updated_at': DateTime.now().toIso8601String(),
      });

      setState(() {
        _avatarUrl = publicUrl;
        _selectedImage = null;
        _isUploadingAvatar = false;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Profile photo updated!'),
            backgroundColor: CyberColors.successGreen,
          ),
        );
      }
    } catch (e) {
      setState(() => _isUploadingAvatar = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error uploading: $e'),
            backgroundColor: CyberColors.alertRed,
          ),
        );
      }
    }
  }

  Future<void> _saveProfile() async {
    setState(() => _isSaving = true);

    try {
      final user = SupabaseService.client.auth.currentUser;
      if (user == null) return;

      await SupabaseService.client.from('profiles').upsert({
        'id': user.id,
        'display_name': _displayNameController.text.trim(),
        'phone_number': _phoneController.text.trim(),
        'updated_at': DateTime.now().toIso8601String(),
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Profile saved!'),
            backgroundColor: CyberColors.successGreen,
          ),
        );
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

    setState(() => _isSaving = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('PROFILE'),
        actions: [
          if (!_isLoading)
            TextButton(
              onPressed: _isSaving ? null : _saveProfile,
              child: _isSaving
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: CyberColors.primaryRed,
                      ),
                    )
                  : const Text(
                      'SAVE',
                      style: TextStyle(
                        color: CyberColors.primaryRed,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
            ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: CyberColors.primaryRed),
            )
          : SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  // Avatar
                  _buildAvatarSection(),
                  const SizedBox(height: 32),

                  // Profile Fields
                  _buildProfileFields(),
                  const SizedBox(height: 32),

                  // Account Info
                  _buildAccountInfo(),
                ],
              ),
            ),
    );
  }

  Widget _buildAvatarSection() {
    return Column(
      children: [
        Stack(
          children: [
            Container(
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: CyberColors.primaryRed,
                  width: 3,
                ),
                boxShadow: [
                  BoxShadow(
                    color: CyberColors.primaryRed.withOpacity(0.3),
                    blurRadius: 20,
                    spreadRadius: 5,
                  ),
                ],
              ),
              child: ClipOval(
                child: _isUploadingAvatar
                    ? Container(
                        color: CyberColors.surfaceColor,
                        child: const Center(
                          child: CircularProgressIndicator(
                            color: CyberColors.primaryRed,
                          ),
                        ),
                      )
                    : _selectedImage != null
                        ? Image.file(_selectedImage!, fit: BoxFit.cover)
                        : _avatarUrl != null
                            ? CachedNetworkImage(
                                imageUrl: _avatarUrl!,
                                fit: BoxFit.cover,
                                placeholder: (context, url) => Container(
                                  color: CyberColors.surfaceColor,
                                  child: const Center(
                                    child: CircularProgressIndicator(
                                      color: CyberColors.primaryRed,
                                    ),
                                  ),
                                ),
                                errorWidget: (context, url, error) => Container(
                                  color: CyberColors.surfaceColor,
                                  child: const Icon(
                                    Icons.person,
                                    size: 60,
                                    color: CyberColors.textMuted,
                                  ),
                                ),
                              )
                            : Container(
                                color: CyberColors.surfaceColor,
                                child: const Icon(
                                  Icons.person,
                                  size: 60,
                                  color: CyberColors.textMuted,
                                ),
                              ),
              ),
            ),
            Positioned(
              right: 0,
              bottom: 0,
              child: GestureDetector(
                onTap: _showImageSourceDialog,
                child: Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: CyberColors.primaryRed,
                    shape: BoxShape.circle,
                    border: Border.all(color: CyberColors.pureBlack, width: 3),
                  ),
                  child: const Icon(
                    Icons.camera_alt,
                    color: CyberColors.pureWhite,
                    size: 18,
                  ),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Text(
          _displayNameController.text.isNotEmpty
              ? _displayNameController.text
              : _email?.split('@').first ?? 'User',
          style: const TextStyle(
            color: CyberColors.textPrimary,
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          _email ?? '',
          style: const TextStyle(
            color: CyberColors.textSecondary,
            fontSize: 14,
          ),
        ),
      ],
    );
  }

  Widget _buildProfileFields() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: CyberColors.surfaceColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: CyberColors.borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Profile Information',
            style: TextStyle(
              color: CyberColors.primaryRed,
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 20),

          // Display Name
          TextField(
            controller: _displayNameController,
            decoration: const InputDecoration(
              labelText: 'Display Name',
              hintText: 'Enter your name',
              prefixIcon: Icon(Icons.person_outline, color: CyberColors.primaryRed),
            ),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 16),

          // Phone Number
          TextField(
            controller: _phoneController,
            keyboardType: TextInputType.phone,
            decoration: const InputDecoration(
              labelText: 'Phone Number',
              hintText: '+91 XXXXX XXXXX',
              prefixIcon: Icon(Icons.phone_outlined, color: CyberColors.primaryRed),
            ),
          ),
          const SizedBox(height: 16),

          // Email (Read-only)
          TextField(
            controller: TextEditingController(text: _email),
            readOnly: true,
            decoration: InputDecoration(
              labelText: 'Email',
              prefixIcon: const Icon(Icons.email_outlined, color: CyberColors.textMuted),
              suffixIcon: const Icon(Icons.lock_outline, color: CyberColors.textMuted, size: 18),
              filled: true,
              fillColor: CyberColors.darkBackground,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAccountInfo() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: CyberColors.surfaceColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: CyberColors.borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Account',
            style: TextStyle(
              color: CyberColors.primaryRed,
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          _buildInfoTile(
            icon: Icons.devices,
            label: 'Linked Devices',
            value: '$_deviceCount',
            color: CyberColors.successGreen,
          ),
          const Divider(color: CyberColors.borderColor, height: 24),
          _buildInfoTile(
            icon: Icons.calendar_today,
            label: 'Member Since',
            value: _createdAt != null
                ? '${_createdAt!.day}/${_createdAt!.month}/${_createdAt!.year}'
                : 'Unknown',
            color: CyberColors.textMuted,
          ),
          const SizedBox(height: 24),
          CyberButton(
            label: 'SIGN OUT',
            icon: Icons.logout,
            color: CyberColors.alertRed,
            onPressed: () async {
              final confirm = await showDialog<bool>(
                context: context,
                builder: (context) => AlertDialog(
                  title: const Text('Sign Out'),
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

              if (confirm == true && mounted) {
                await SupabaseService.client.auth.signOut();
                if (mounted) {
                  Navigator.of(context).pushNamedAndRemoveUntil('/login', (route) => false);
                }
              }
            },
            width: double.infinity,
          ),
        ],
      ),
    );
  }

  Widget _buildInfoTile({
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Row(
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
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: const TextStyle(
                  color: CyberColors.textSecondary,
                  fontSize: 12,
                ),
              ),
              Text(
                value,
                style: const TextStyle(
                  color: CyberColors.textPrimary,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
