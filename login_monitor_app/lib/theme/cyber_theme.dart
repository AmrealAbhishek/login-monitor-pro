import 'package:flutter/material.dart';

/// Cyber Neon Theme Colors for Login Monitor PRO v3.0
class CyberColors {
  // Primary Neon Colors
  static const Color neonCyan = Color(0xFF06E6DA);
  static const Color neonCyanLight = Color(0xFF1EDAD0);
  static const Color neonCyanDark = Color(0xFF05B8AE);

  // Background Colors
  static const Color darkBackground = Color(0xFF0C1F1F);
  static const Color pureBlack = Color(0xFF000000);
  static const Color cardBackground = Color(0xFF0F2828);
  static const Color surfaceColor = Color(0xFF1A3333);

  // Text Colors
  static const Color textPrimary = Color(0xFFFDFEFE);
  static const Color textSecondary = Color(0xFFB0C4C4);
  static const Color textMuted = Color(0xFF6B8A8A);

  // Alert Colors
  static const Color alertRed = Color(0xFFFF3B3B);
  static const Color successGreen = Color(0xFF00FF88);
  static const Color warningOrange = Color(0xFFFFB347);
  static const Color infoBlue = Color(0xFF4DA6FF);

  // Gradient
  static const LinearGradient neonGradient = LinearGradient(
    colors: [neonCyan, neonCyanLight],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient darkGradient = LinearGradient(
    colors: [pureBlack, darkBackground],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );
}

/// Cyber Theme for Login Monitor PRO
class CyberTheme {
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: CyberColors.pureBlack,
      primaryColor: CyberColors.neonCyan,

      // Color Scheme
      colorScheme: const ColorScheme.dark(
        primary: CyberColors.neonCyan,
        secondary: CyberColors.neonCyanLight,
        surface: CyberColors.cardBackground,
        error: CyberColors.alertRed,
        onPrimary: CyberColors.pureBlack,
        onSecondary: CyberColors.pureBlack,
        onSurface: CyberColors.textPrimary,
        onError: CyberColors.textPrimary,
      ),

      // AppBar Theme
      appBarTheme: const AppBarTheme(
        backgroundColor: CyberColors.pureBlack,
        foregroundColor: CyberColors.textPrimary,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: TextStyle(
          color: CyberColors.neonCyan,
          fontSize: 20,
          fontWeight: FontWeight.bold,
          letterSpacing: 1.2,
        ),
        iconTheme: IconThemeData(color: CyberColors.neonCyan),
      ),

      // Card Theme
      cardTheme: CardThemeData(
        color: CyberColors.cardBackground,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: CyberColors.neonCyan, width: 1),
        ),
        margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 0),
      ),

      // Elevated Button Theme
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: CyberColors.neonCyan,
          foregroundColor: CyberColors.pureBlack,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontWeight: FontWeight.bold,
            letterSpacing: 1.0,
          ),
        ),
      ),

      // Outlined Button Theme
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: CyberColors.neonCyan,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          side: const BorderSide(color: CyberColors.neonCyan, width: 1.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),

      // Filled Button Theme
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: CyberColors.neonCyan,
          foregroundColor: CyberColors.pureBlack,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),

      // Text Button Theme
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: CyberColors.neonCyan,
        ),
      ),

      // Icon Theme
      iconTheme: const IconThemeData(
        color: CyberColors.neonCyan,
        size: 24,
      ),

      // Input Decoration Theme
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: CyberColors.surfaceColor,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: CyberColors.textMuted),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: CyberColors.textMuted),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: CyberColors.neonCyan, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: CyberColors.alertRed),
        ),
        labelStyle: const TextStyle(color: CyberColors.textSecondary),
        hintStyle: const TextStyle(color: CyberColors.textMuted),
      ),

      // Navigation Bar Theme
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: CyberColors.pureBlack,
        indicatorColor: CyberColors.neonCyan.withOpacity(0.2),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return const TextStyle(
              color: CyberColors.neonCyan,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            );
          }
          return const TextStyle(
            color: CyberColors.textMuted,
            fontSize: 12,
          );
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return const IconThemeData(color: CyberColors.neonCyan);
          }
          return const IconThemeData(color: CyberColors.textMuted);
        }),
      ),

      // Bottom Navigation Bar Theme
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: CyberColors.pureBlack,
        selectedItemColor: CyberColors.neonCyan,
        unselectedItemColor: CyberColors.textMuted,
      ),

      // Floating Action Button Theme
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: CyberColors.neonCyan,
        foregroundColor: CyberColors.pureBlack,
      ),

      // Snackbar Theme
      snackBarTheme: SnackBarThemeData(
        backgroundColor: CyberColors.cardBackground,
        contentTextStyle: const TextStyle(color: CyberColors.textPrimary),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: CyberColors.neonCyan),
        ),
        behavior: SnackBarBehavior.floating,
      ),

      // Dialog Theme
      dialogTheme: DialogThemeData(
        backgroundColor: CyberColors.darkBackground,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: CyberColors.neonCyan),
        ),
        titleTextStyle: const TextStyle(
          color: CyberColors.neonCyan,
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
        contentTextStyle: const TextStyle(
          color: CyberColors.textPrimary,
          fontSize: 16,
        ),
      ),

      // Divider Theme
      dividerTheme: const DividerThemeData(
        color: CyberColors.textMuted,
        thickness: 0.5,
      ),

      // List Tile Theme
      listTileTheme: const ListTileThemeData(
        textColor: CyberColors.textPrimary,
        iconColor: CyberColors.neonCyan,
      ),

      // Switch Theme
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return CyberColors.neonCyan;
          }
          return CyberColors.textMuted;
        }),
        trackColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return CyberColors.neonCyan.withOpacity(0.5);
          }
          return CyberColors.surfaceColor;
        }),
      ),

      // Chip Theme
      chipTheme: ChipThemeData(
        backgroundColor: CyberColors.surfaceColor,
        selectedColor: CyberColors.neonCyan,
        labelStyle: const TextStyle(color: CyberColors.textPrimary),
        side: const BorderSide(color: CyberColors.neonCyan),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
      ),

      // Progress Indicator Theme
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: CyberColors.neonCyan,
        circularTrackColor: CyberColors.surfaceColor,
        linearTrackColor: CyberColors.surfaceColor,
      ),

      // Slider Theme
      sliderTheme: SliderThemeData(
        activeTrackColor: CyberColors.neonCyan,
        inactiveTrackColor: CyberColors.surfaceColor,
        thumbColor: CyberColors.neonCyan,
        overlayColor: CyberColors.neonCyan.withOpacity(0.2),
      ),

      // Text Theme
      textTheme: const TextTheme(
        displayLarge: TextStyle(
          color: CyberColors.textPrimary,
          fontSize: 32,
          fontWeight: FontWeight.bold,
          letterSpacing: 1.5,
        ),
        displayMedium: TextStyle(
          color: CyberColors.textPrimary,
          fontSize: 28,
          fontWeight: FontWeight.bold,
        ),
        displaySmall: TextStyle(
          color: CyberColors.textPrimary,
          fontSize: 24,
          fontWeight: FontWeight.bold,
        ),
        headlineLarge: TextStyle(
          color: CyberColors.neonCyan,
          fontSize: 22,
          fontWeight: FontWeight.bold,
        ),
        headlineMedium: TextStyle(
          color: CyberColors.textPrimary,
          fontSize: 20,
          fontWeight: FontWeight.w600,
        ),
        headlineSmall: TextStyle(
          color: CyberColors.textPrimary,
          fontSize: 18,
          fontWeight: FontWeight.w600,
        ),
        titleLarge: TextStyle(
          color: CyberColors.textPrimary,
          fontSize: 18,
          fontWeight: FontWeight.bold,
        ),
        titleMedium: TextStyle(
          color: CyberColors.textPrimary,
          fontSize: 16,
          fontWeight: FontWeight.w600,
        ),
        titleSmall: TextStyle(
          color: CyberColors.textSecondary,
          fontSize: 14,
          fontWeight: FontWeight.w500,
        ),
        bodyLarge: TextStyle(
          color: CyberColors.textPrimary,
          fontSize: 16,
        ),
        bodyMedium: TextStyle(
          color: CyberColors.textPrimary,
          fontSize: 14,
        ),
        bodySmall: TextStyle(
          color: CyberColors.textSecondary,
          fontSize: 12,
        ),
        labelLarge: TextStyle(
          color: CyberColors.textPrimary,
          fontSize: 14,
          fontWeight: FontWeight.w600,
        ),
        labelMedium: TextStyle(
          color: CyberColors.textSecondary,
          fontSize: 12,
        ),
        labelSmall: TextStyle(
          color: CyberColors.textMuted,
          fontSize: 11,
        ),
      ),
    );
  }
}

/// Extension for easy access to cyber colors
extension CyberColorExtension on BuildContext {
  CyberColors get cyberColors => CyberColors();

  Color get neonCyan => CyberColors.neonCyan;
  Color get alertRed => CyberColors.alertRed;
  Color get successGreen => CyberColors.successGreen;
  Color get warningOrange => CyberColors.warningOrange;
}
