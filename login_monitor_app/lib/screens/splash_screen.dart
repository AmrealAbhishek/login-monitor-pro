import 'package:flutter/material.dart';
import 'dart:math' as math;
import '../services/supabase_service.dart';
import '../theme/cyber_theme.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  late AnimationController _logoController;
  late AnimationController _textController;
  late AnimationController _pulseController;

  late Animation<double> _logoFadeAnimation;
  late Animation<double> _logoScaleAnimation;
  late Animation<double> _textFadeAnimation;
  late Animation<Offset> _textSlideAnimation;
  late Animation<double> _pulseAnimation;
  late Animation<double> _rotationAnimation;

  @override
  void initState() {
    super.initState();

    // Logo animation controller
    _logoController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );

    // Text animation controller (starts after logo)
    _textController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );

    // Pulse animation for the eye glow
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    )..repeat(reverse: true);

    // Logo animations
    _logoFadeAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _logoController, curve: Curves.easeOut),
    );

    _logoScaleAnimation = Tween<double>(begin: 0.3, end: 1).animate(
      CurvedAnimation(parent: _logoController, curve: Curves.elasticOut),
    );

    _rotationAnimation = Tween<double>(begin: -0.5, end: 0).animate(
      CurvedAnimation(parent: _logoController, curve: Curves.easeOutBack),
    );

    // Text animations
    _textFadeAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _textController, curve: Curves.easeIn),
    );

    _textSlideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.3),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _textController, curve: Curves.easeOut));

    // Pulse animation
    _pulseAnimation = Tween<double>(begin: 0.8, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    // Start animations
    _logoController.forward().then((_) {
      _textController.forward();
    });

    _checkAuth();
  }

  Future<void> _checkAuth() async {
    await Future.delayed(const Duration(seconds: 3));

    if (!mounted) return;

    if (SupabaseService.isLoggedIn) {
      final devices = await SupabaseService.getDevices();
      if (devices.isEmpty) {
        Navigator.of(context).pushReplacementNamed('/pairing');
      } else {
        Navigator.of(context).pushReplacementNamed('/home');
      }
    } else {
      Navigator.of(context).pushReplacementNamed('/login');
    }
  }

  @override
  void dispose() {
    _logoController.dispose();
    _textController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: CyberColors.pureBlack,
      body: Container(
        decoration: BoxDecoration(
          gradient: RadialGradient(
            center: Alignment.center,
            radius: 1.5,
            colors: [
              CyberColors.primaryRed.withOpacity(0.15),
              CyberColors.pureBlack,
            ],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              // Main content - centered
              Expanded(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // Animated Logo
                      AnimatedBuilder(
                        animation: Listenable.merge([_logoController, _pulseController]),
                        builder: (context, child) {
                          return Opacity(
                            opacity: _logoFadeAnimation.value,
                            child: Transform.scale(
                              scale: _logoScaleAnimation.value,
                              child: Transform.rotate(
                                angle: _rotationAnimation.value,
                                child: child,
                              ),
                            ),
                          );
                        },
                        child: AnimatedBuilder(
                          animation: _pulseController,
                          builder: (context, child) {
                            return Container(
                              width: 160,
                              height: 160,
                              decoration: BoxDecoration(
                                boxShadow: [
                                  BoxShadow(
                                    color: CyberColors.primaryRed.withOpacity(0.4 * _pulseAnimation.value),
                                    blurRadius: 40 * _pulseAnimation.value,
                                    spreadRadius: 5,
                                  ),
                                ],
                              ),
                              child: CustomPaint(
                                painter: CyVigilLogoPainter(
                                  glowIntensity: _pulseAnimation.value,
                                ),
                              ),
                            );
                          },
                        ),
                      ),

                      const SizedBox(height: 40),

                      // CYVIGIL Text
                      SlideTransition(
                        position: _textSlideAnimation,
                        child: FadeTransition(
                          opacity: _textFadeAnimation,
                          child: Column(
                            children: [
                              // Main title
                              const Text(
                                'CYVIGIL',
                                style: TextStyle(
                                  fontSize: 42,
                                  fontWeight: FontWeight.w900,
                                  color: CyberColors.pureWhite,
                                  letterSpacing: 8,
                                ),
                              ),
                              const SizedBox(height: 12),
                              // Tagline
                              Text(
                                'SECURING DIGITAL FUTURE',
                                style: TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                  color: CyberColors.primaryRed,
                                  letterSpacing: 4,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),

                      const SizedBox(height: 60),

                      // Loading indicator
                      FadeTransition(
                        opacity: _textFadeAnimation,
                        child: SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(
                              CyberColors.primaryRed.withOpacity(0.8),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              // Bottom - Powered by CyVigilant
              FadeTransition(
                opacity: _textFadeAnimation,
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 40),
                  child: Column(
                    children: [
                      Text(
                        'powered by',
                        style: TextStyle(
                          fontSize: 11,
                          color: CyberColors.textMuted,
                          letterSpacing: 1,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            width: 16,
                            height: 16,
                            child: CustomPaint(
                              painter: CyVigilLogoPainter(glowIntensity: 0.5, mini: true),
                            ),
                          ),
                          const SizedBox(width: 6),
                          const Text(
                            'CyVigilant',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: CyberColors.pureWhite,
                              letterSpacing: 1,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Custom painter for the CyVigil eye logo
class CyVigilLogoPainter extends CustomPainter {
  final double glowIntensity;
  final bool mini;

  CyVigilLogoPainter({this.glowIntensity = 1.0, this.mini = false});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;

    // Colors
    const darkRed = Color(0xFF8B0000);
    const brightRed = Color(0xFFCC0000);
    const eyeRed = Color(0xFFAA0000);

    // Draw outer eye shape (rounded diamond)
    final eyePath = Path();
    final eyeWidth = radius * 0.95;
    final eyeHeight = radius * 0.7;

    // Create eye shape using bezier curves
    eyePath.moveTo(center.dx - eyeWidth, center.dy);
    eyePath.quadraticBezierTo(
      center.dx - eyeWidth * 0.5, center.dy - eyeHeight,
      center.dx, center.dy - eyeHeight * 0.8,
    );
    eyePath.quadraticBezierTo(
      center.dx + eyeWidth * 0.5, center.dy - eyeHeight,
      center.dx + eyeWidth, center.dy,
    );
    eyePath.quadraticBezierTo(
      center.dx + eyeWidth * 0.5, center.dy + eyeHeight,
      center.dx, center.dy + eyeHeight * 0.8,
    );
    eyePath.quadraticBezierTo(
      center.dx - eyeWidth * 0.5, center.dy + eyeHeight,
      center.dx - eyeWidth, center.dy,
    );
    eyePath.close();

    // Draw eye background with gradient
    final eyeGradient = RadialGradient(
      center: Alignment.center,
      radius: 1.0,
      colors: [
        darkRed.withOpacity(0.9),
        eyeRed,
        darkRed,
      ],
    );

    final eyePaint = Paint()
      ..shader = eyeGradient.createShader(
        Rect.fromCircle(center: center, radius: radius),
      );

    canvas.drawPath(eyePath, eyePaint);

    // Draw eye border
    final borderPaint = Paint()
      ..color = Colors.grey.shade600
      ..style = PaintingStyle.stroke
      ..strokeWidth = mini ? 1 : 3;
    canvas.drawPath(eyePath, borderPaint);

    // Draw iris (main red circle)
    final irisRadius = radius * 0.55;
    final irisGradient = RadialGradient(
      center: const Alignment(-0.3, -0.3),
      radius: 1.2,
      colors: [
        brightRed,
        darkRed,
        const Color(0xFF500000),
      ],
    );

    final irisPaint = Paint()
      ..shader = irisGradient.createShader(
        Rect.fromCircle(center: center, radius: irisRadius),
      );
    canvas.drawCircle(center, irisRadius, irisPaint);

    // Draw spiral/swirl pattern
    if (!mini) {
      _drawSpiral(canvas, center, irisRadius * 0.9, darkRed);
    }

    // Draw pupil (center white dot)
    final pupilPaint = Paint()..color = Colors.white;
    canvas.drawCircle(center, radius * 0.12, pupilPaint);

    // Draw small accent circles (like in the logo)
    if (!mini) {
      final accentPaint = Paint()..color = Colors.grey.shade400;
      canvas.drawCircle(
        Offset(center.dx + irisRadius * 0.5, center.dy - irisRadius * 0.3),
        radius * 0.06,
        accentPaint,
      );
      canvas.drawCircle(
        Offset(center.dx - irisRadius * 0.3, center.dy + irisRadius * 0.5),
        radius * 0.04,
        accentPaint,
      );
    }

    // Draw glow effect
    if (glowIntensity > 0) {
      final glowPaint = Paint()
        ..color = CyberColors.primaryRed.withOpacity(0.1 * glowIntensity)
        ..maskFilter = const MaskFilter.blur(BlurStyle.outer, 20);
      canvas.drawCircle(center, radius * 0.7, glowPaint);
    }
  }

  void _drawSpiral(Canvas canvas, Offset center, double radius, Color color) {
    final spiralPaint = Paint()
      ..color = color.withOpacity(0.6)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;

    final path = Path();
    const turns = 2.5;
    const startRadius = 0.2;

    for (double t = 0; t < turns * 2 * math.pi; t += 0.1) {
      final r = radius * (startRadius + (1 - startRadius) * t / (turns * 2 * math.pi));
      final x = center.dx + r * math.cos(t - math.pi / 2);
      final y = center.dy + r * math.sin(t - math.pi / 2);

      if (t == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }

    canvas.drawPath(path, spiralPaint);

    // Draw second spiral (offset)
    final path2 = Path();
    for (double t = 0; t < turns * 2 * math.pi; t += 0.1) {
      final r = radius * (startRadius + (1 - startRadius) * t / (turns * 2 * math.pi));
      final x = center.dx + r * math.cos(t + math.pi / 2);
      final y = center.dy + r * math.sin(t + math.pi / 2);

      if (t == 0) {
        path2.moveTo(x, y);
      } else {
        path2.lineTo(x, y);
      }
    }

    canvas.drawPath(path2, spiralPaint);
  }

  @override
  bool shouldRepaint(covariant CyVigilLogoPainter oldDelegate) {
    return oldDelegate.glowIntensity != glowIntensity;
  }
}
