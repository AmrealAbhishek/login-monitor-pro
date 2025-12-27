import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../main.dart';
import '../theme/cyber_theme.dart';
import '../widgets/neon_card.dart';
import '../widgets/cyber_button.dart';
import '../widgets/pulse_indicator.dart';
import '../services/supabase_service.dart';

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  bool _isLoading = false;
  bool _isGenerating = false;
  List<Map<String, dynamic>> _reports = [];
  String _selectedReportType = 'daily';

  @override
  void initState() {
    super.initState();
    _loadReports();
  }

  Future<void> _loadReports() async {
    final deviceId = context.read<AppState>().selectedDeviceId;
    if (deviceId == null) return;

    setState(() => _isLoading = true);

    try {
      // Load reports from Supabase
      final response = await SupabaseService.client
          .from('reports')
          .select()
          .eq('device_id', deviceId)
          .order('created_at', ascending: false)
          .limit(20);

      setState(() {
        _reports = List<Map<String, dynamic>>.from(response);
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      debugPrint('Error loading reports: $e');
    }
  }

  Future<void> _generateReport() async {
    final deviceId = context.read<AppState>().selectedDeviceId;
    if (deviceId == null) return;

    setState(() => _isGenerating = true);

    try {
      await SupabaseService.sendCommand(
        deviceId: deviceId,
        command: 'generatereport',
        args: {'type': _selectedReportType},
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Report generation started! It will appear shortly.'),
            backgroundColor: CyberColors.successGreen,
          ),
        );
      }

      // Wait a bit then reload
      await Future.delayed(const Duration(seconds: 3));
      _loadReports();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: CyberColors.alertRed,
          ),
        );
      }
    } finally {
      setState(() => _isGenerating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SECURITY REPORTS'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadReports,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CyberLoadingIndicator(message: 'Loading reports...'))
          : RefreshIndicator(
              onRefresh: _loadReports,
              color: CyberColors.neonCyan,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // Generate Report Section
                  _buildGenerateSection(),
                  const SizedBox(height: 24),

                  // Reports List
                  _buildReportsList(),
                ],
              ),
            ),
    );
  }

  Widget _buildGenerateSection() {
    return NeonCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.auto_graph,
                color: CyberColors.neonCyan,
              ),
              const SizedBox(width: 12),
              const Text(
                'Generate New Report',
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
              _buildReportTypeOption('daily', 'Daily'),
              const SizedBox(width: 12),
              _buildReportTypeOption('weekly', 'Weekly'),
              const SizedBox(width: 12),
              _buildReportTypeOption('monthly', 'Monthly'),
            ],
          ),
          const SizedBox(height: 16),
          CyberButton(
            label: 'GENERATE REPORT',
            icon: Icons.summarize,
            isLoading: _isGenerating,
            onPressed: _generateReport,
            width: double.infinity,
          ),
        ],
      ),
    );
  }

  Widget _buildReportTypeOption(String type, String label) {
    final isSelected = _selectedReportType == type;

    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _selectedReportType = type),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: isSelected
                ? CyberColors.neonCyan.withOpacity(0.2)
                : CyberColors.surfaceColor,
            borderRadius: BorderRadius.circular(8),
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

  Widget _buildReportsList() {
    if (_reports.isEmpty) {
      return NeonCard(
        glowIntensity: 0.2,
        child: Column(
          children: [
            Icon(
              Icons.assessment_outlined,
              size: 64,
              color: CyberColors.textMuted,
            ),
            const SizedBox(height: 16),
            const Text(
              'No reports yet',
              style: TextStyle(
                color: CyberColors.textPrimary,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Generate your first security report above',
              style: TextStyle(
                color: CyberColors.textSecondary,
              ),
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Recent Reports',
          style: TextStyle(
            color: CyberColors.neonCyan,
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 12),
        ..._reports.map((report) => _buildReportCard(report)),
      ],
    );
  }

  Widget _buildReportCard(Map<String, dynamic> report) {
    final summary = report['summary'] as Map<String, dynamic>?;
    final totalEvents = summary?['total_events'] ?? 0;
    final securityAlerts = (summary?['security_alerts'] as List?)?.length ?? 0;
    final reportType = report['report_type'] ?? 'daily';
    final createdAt = DateTime.tryParse(report['created_at'] ?? '');

    Color typeColor;
    IconData typeIcon;

    switch (reportType) {
      case 'weekly':
        typeColor = CyberColors.infoBlue;
        typeIcon = Icons.calendar_view_week;
        break;
      case 'monthly':
        typeColor = CyberColors.warningOrange;
        typeIcon = Icons.calendar_month;
        break;
      default:
        typeColor = CyberColors.neonCyan;
        typeIcon = Icons.today;
    }

    return NeonCard(
      glowIntensity: 0.3,
      glowColor: typeColor,
      onTap: () => _showReportDetails(report),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: typeColor.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(typeIcon, color: typeColor),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${reportType.toUpperCase()} REPORT',
                  style: TextStyle(
                    color: typeColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  createdAt != null
                      ? _formatDate(createdAt)
                      : 'Unknown date',
                  style: const TextStyle(
                    color: CyberColors.textSecondary,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '$totalEvents',
                    style: const TextStyle(
                      color: CyberColors.neonCyan,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(width: 4),
                  const Text(
                    'events',
                    style: TextStyle(
                      color: CyberColors.textMuted,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
              if (securityAlerts > 0)
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '$securityAlerts',
                      style: const TextStyle(
                        color: CyberColors.alertRed,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(width: 4),
                    const Text(
                      'alerts',
                      style: TextStyle(
                        color: CyberColors.textMuted,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
            ],
          ),
          const SizedBox(width: 8),
          const Icon(
            Icons.chevron_right,
            color: CyberColors.textMuted,
          ),
        ],
      ),
    );
  }

  void _showReportDetails(Map<String, dynamic> report) {
    final summary = report['summary'] as Map<String, dynamic>?;

    showModalBottomSheet(
      context: context,
      backgroundColor: CyberColors.darkBackground,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => Container(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '${(report['report_type'] ?? 'daily').toString().toUpperCase()} REPORT',
                  style: const TextStyle(
                    color: CyberColors.neonCyan,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: CyberColors.textMuted),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // Summary stats
            if (summary != null) ...[
              _buildDetailRow('Total Events', '${summary['total_events'] ?? 0}'),
              _buildDetailRow(
                'Security Alerts',
                '${(summary['security_alerts'] as List?)?.length ?? 0}',
              ),
              _buildDetailRow('Photos Captured', '${summary['photos_captured'] ?? 0}'),
              const SizedBox(height: 16),

              // Highlights
              if (summary['highlights'] != null) ...[
                const Text(
                  'Highlights',
                  style: TextStyle(
                    color: CyberColors.neonCyan,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                ...(summary['highlights'] as List).map((h) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.arrow_right,
                            color: CyberColors.neonCyan,
                            size: 20,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              h.toString(),
                              style: const TextStyle(
                                color: CyberColors.textSecondary,
                              ),
                            ),
                          ),
                        ],
                      ),
                    )),
              ],
            ],

            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: CyberColors.textSecondary,
            ),
          ),
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

  String _formatDate(DateTime dt) {
    return '${dt.day}/${dt.month}/${dt.year} ${dt.hour}:${dt.minute.toString().padLeft(2, '0')}';
  }
}
