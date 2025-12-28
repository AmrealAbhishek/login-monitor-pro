import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
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

    // Pulse animation for the logo glow
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    )..repeat(reverse: true);

    // Logo animations
    _logoFadeAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _logoController, curve: Curves.easeOut),
    );

    _logoScaleAnimation = Tween<double>(begin: 0.5, end: 1).animate(
      CurvedAnimation(parent: _logoController, curve: Curves.elasticOut),
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
    _pulseAnimation = Tween<double>(begin: 0.6, end: 1.0).animate(
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
              CyberColors.primaryRed.withOpacity(0.1),
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
                              child: child,
                            ),
                          );
                        },
                        child: AnimatedBuilder(
                          animation: _pulseController,
                          builder: (context, child) {
                            return Container(
                              width: 180,
                              height: 140,
                              decoration: BoxDecoration(
                                boxShadow: [
                                  BoxShadow(
                                    color: CyberColors.primaryRed.withOpacity(0.3 * _pulseAnimation.value),
                                    blurRadius: 30 * _pulseAnimation.value,
                                    spreadRadius: 5,
                                  ),
                                ],
                              ),
                              child: Image.asset(
                                'assets/images/cyvigil.png',
                                fit: BoxFit.contain,
                              ),
                            );
                          },
                        ),
                      ),

                      const SizedBox(height: 30),

                      // CYVIGIL Text with Tektur font
                      SlideTransition(
                        position: _textSlideAnimation,
                        child: FadeTransition(
                          opacity: _textFadeAnimation,
                          child: Column(
                            children: [
                              // Main title - CYVIGIL with Tektur font
                              Text(
                                'CYVIGIL',
                                style: GoogleFonts.tektur(
                                  fontSize: 44,
                                  fontWeight: FontWeight.w700,
                                  color: CyberColors.pureWhite,
                                  letterSpacing: 6,
                                ),
                              ),
                              const SizedBox(height: 8),
                              // Tagline
                              Text(
                                'SECURING DIGITAL FUTURE',
                                style: GoogleFonts.tektur(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500,
                                  color: CyberColors.primaryRed,
                                  letterSpacing: 3,
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
                          // Mini logo
                          SizedBox(
                            width: 20,
                            height: 16,
                            child: Image.asset(
                              'assets/images/cyvigil.png',
                              fit: BoxFit.contain,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'CyVigilant',
                            style: GoogleFonts.tektur(
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
