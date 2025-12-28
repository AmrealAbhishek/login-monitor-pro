import 'package:flutter/material.dart';
import '../theme/cyber_theme.dart';

enum ToastType { success, error, info, warning }

class CustomToast {
  static OverlayEntry? _currentToast;

  static void show(
    BuildContext context, {
    required String message,
    ToastType type = ToastType.success,
    IconData? icon,
    Duration duration = const Duration(seconds: 3),
    VoidCallback? onTap,
    String? actionLabel,
  }) {
    _currentToast?.remove();

    final overlay = Overlay.of(context);

    Color backgroundColor;
    Color borderColor;
    IconData defaultIcon;

    switch (type) {
      case ToastType.success:
        backgroundColor = CyberColors.successGreen.withOpacity(0.15);
        borderColor = CyberColors.successGreen;
        defaultIcon = Icons.check_circle_rounded;
        break;
      case ToastType.error:
        backgroundColor = CyberColors.alertRed.withOpacity(0.15);
        borderColor = CyberColors.alertRed;
        defaultIcon = Icons.error_rounded;
        break;
      case ToastType.warning:
        backgroundColor = CyberColors.warningOrange.withOpacity(0.15);
        borderColor = CyberColors.warningOrange;
        defaultIcon = Icons.warning_rounded;
        break;
      case ToastType.info:
        backgroundColor = CyberColors.infoBlue.withOpacity(0.15);
        borderColor = CyberColors.infoBlue;
        defaultIcon = Icons.info_rounded;
        break;
    }

    final entry = OverlayEntry(
      builder: (context) => _ToastWidget(
        message: message,
        backgroundColor: backgroundColor,
        borderColor: borderColor,
        icon: icon ?? defaultIcon,
        duration: duration,
        onTap: onTap,
        actionLabel: actionLabel,
        onDismiss: () => _currentToast?.remove(),
      ),
    );

    _currentToast = entry;
    overlay.insert(entry);

    Future.delayed(duration, () {
      if (_currentToast == entry) {
        entry.remove();
        _currentToast = null;
      }
    });
  }

  static void dismiss() {
    _currentToast?.remove();
    _currentToast = null;
  }
}

class _ToastWidget extends StatefulWidget {
  final String message;
  final Color backgroundColor;
  final Color borderColor;
  final IconData icon;
  final Duration duration;
  final VoidCallback? onTap;
  final String? actionLabel;
  final VoidCallback onDismiss;

  const _ToastWidget({
    required this.message,
    required this.backgroundColor,
    required this.borderColor,
    required this.icon,
    required this.duration,
    this.onTap,
    this.actionLabel,
    required this.onDismiss,
  });

  @override
  State<_ToastWidget> createState() => _ToastWidgetState();
}

class _ToastWidgetState extends State<_ToastWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );

    _fadeAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOut,
    );

    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, -1),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOutCubic,
    ));

    _controller.forward();

    // Auto dismiss animation
    Future.delayed(widget.duration - const Duration(milliseconds: 300), () {
      if (mounted) {
        _controller.reverse().then((_) => widget.onDismiss());
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: MediaQuery.of(context).padding.top + 16,
      left: 16,
      right: 16,
      child: SlideTransition(
        position: _slideAnimation,
        child: FadeTransition(
          opacity: _fadeAnimation,
          child: GestureDetector(
            onTap: widget.onTap,
            onHorizontalDragEnd: (_) {
              _controller.reverse().then((_) => widget.onDismiss());
            },
            child: Material(
              color: Colors.transparent,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                decoration: BoxDecoration(
                  color: widget.backgroundColor,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: widget.borderColor.withOpacity(0.5), width: 1.5),
                  boxShadow: [
                    BoxShadow(
                      color: widget.borderColor.withOpacity(0.2),
                      blurRadius: 20,
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: Row(
                  children: [
                    Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        color: widget.borderColor.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(
                        widget.icon,
                        color: widget.borderColor,
                        size: 20,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        widget.message,
                        style: const TextStyle(
                          color: CyberColors.textPrimary,
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (widget.actionLabel != null) ...[
                      const SizedBox(width: 8),
                      TextButton(
                        onPressed: widget.onTap,
                        style: TextButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          backgroundColor: widget.borderColor.withOpacity(0.2),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                        ),
                        child: Text(
                          widget.actionLabel!,
                          style: TextStyle(
                            color: widget.borderColor,
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
