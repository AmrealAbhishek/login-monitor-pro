import 'package:flutter/material.dart';
import '../theme/cyber_theme.dart';

/// A card with neon glow effect
class NeonCard extends StatefulWidget {
  final Widget child;
  final Color? glowColor;
  final double glowIntensity;
  final double borderRadius;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final VoidCallback? onTap;
  final bool animate;
  final bool isAlert;

  const NeonCard({
    super.key,
    required this.child,
    this.glowColor,
    this.glowIntensity = 0.5,
    this.borderRadius = 16,
    this.padding,
    this.margin,
    this.onTap,
    this.animate = false,
    this.isAlert = false,
  });

  @override
  State<NeonCard> createState() => _NeonCardState();
}

class _NeonCardState extends State<NeonCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );

    _glowAnimation = Tween<double>(
      begin: widget.isAlert ? 0.3 : 0.2,
      end: widget.isAlert ? 0.8 : 0.5,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: Curves.easeInOut,
    ));

    if (widget.animate || widget.isAlert) {
      _controller.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = widget.glowColor ??
        (widget.isAlert ? CyberColors.alertRed : CyberColors.neonCyan);

    return AnimatedBuilder(
      animation: _glowAnimation,
      builder: (context, child) {
        final glowOpacity = widget.animate || widget.isAlert
            ? _glowAnimation.value
            : widget.glowIntensity;

        return Container(
          margin: widget.margin ?? const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(widget.borderRadius),
            boxShadow: [
              BoxShadow(
                color: color.withOpacity(glowOpacity * 0.6),
                blurRadius: 20,
                spreadRadius: 1,
              ),
              BoxShadow(
                color: color.withOpacity(glowOpacity * 0.3),
                blurRadius: 40,
                spreadRadius: 2,
              ),
            ],
          ),
          child: Material(
            color: CyberColors.cardBackground,
            borderRadius: BorderRadius.circular(widget.borderRadius),
            child: InkWell(
              onTap: widget.onTap,
              borderRadius: BorderRadius.circular(widget.borderRadius),
              splashColor: color.withOpacity(0.2),
              highlightColor: color.withOpacity(0.1),
              child: Container(
                padding: widget.padding ?? const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(widget.borderRadius),
                  border: Border.all(
                    color: color.withOpacity(0.8),
                    width: 1.5,
                  ),
                ),
                child: widget.child,
              ),
            ),
          ),
        );
      },
    );
  }
}

/// A small neon badge/chip
class NeonBadge extends StatelessWidget {
  final String label;
  final Color? color;
  final IconData? icon;

  const NeonBadge({
    super.key,
    required this.label,
    this.color,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final badgeColor = color ?? CyberColors.neonCyan;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: badgeColor.withOpacity(0.15),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: badgeColor, width: 1),
        boxShadow: [
          BoxShadow(
            color: badgeColor.withOpacity(0.3),
            blurRadius: 8,
            spreadRadius: 0,
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 14, color: badgeColor),
            const SizedBox(width: 4),
          ],
          Text(
            label,
            style: TextStyle(
              color: badgeColor,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}

/// Status indicator with neon glow
class NeonStatusIndicator extends StatefulWidget {
  final bool isOnline;
  final double size;

  const NeonStatusIndicator({
    super.key,
    required this.isOnline,
    this.size = 12,
  });

  @override
  State<NeonStatusIndicator> createState() => _NeonStatusIndicatorState();
}

class _NeonStatusIndicatorState extends State<NeonStatusIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.5).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );

    if (widget.isOnline) {
      _controller.repeat(reverse: true);
    }
  }

  @override
  void didUpdateWidget(NeonStatusIndicator oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isOnline && !_controller.isAnimating) {
      _controller.repeat(reverse: true);
    } else if (!widget.isOnline && _controller.isAnimating) {
      _controller.stop();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = widget.isOnline
        ? CyberColors.successGreen
        : CyberColors.textMuted;

    return AnimatedBuilder(
      animation: _pulseAnimation,
      builder: (context, child) {
        return Container(
          width: widget.size,
          height: widget.size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: color,
            boxShadow: widget.isOnline
                ? [
                    BoxShadow(
                      color: color.withOpacity(0.6),
                      blurRadius: 8 * _pulseAnimation.value,
                      spreadRadius: 2 * _pulseAnimation.value,
                    ),
                  ]
                : null,
          ),
        );
      },
    );
  }
}
