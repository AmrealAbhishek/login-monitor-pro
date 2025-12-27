import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'services/supabase_service.dart';
import 'theme/cyber_theme.dart';
import 'screens/splash_screen.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';
import 'screens/pairing_screen.dart';
import 'screens/events_screen.dart';
import 'screens/event_detail_screen.dart';
import 'screens/commands_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/security_dashboard_screen.dart';
import 'screens/find_mac_screen.dart';
import 'screens/reports_screen.dart';
import 'screens/geofence_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Set system UI overlay style for immersive cyber theme
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      systemNavigationBarColor: CyberColors.pureBlack,
      systemNavigationBarIconBrightness: Brightness.light,
    ),
  );

  await SupabaseService.initialize();
  runApp(const LoginMonitorApp());
}

class LoginMonitorApp extends StatelessWidget {
  const LoginMonitorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AppState(),
      child: MaterialApp(
        title: 'Login Monitor PRO',
        debugShowCheckedModeBanner: false,
        // Use Cyber Neon Theme (dark only)
        theme: CyberTheme.darkTheme,
        darkTheme: CyberTheme.darkTheme,
        themeMode: ThemeMode.dark,
        initialRoute: '/',
        routes: {
          '/': (context) => const SplashScreen(),
          '/login': (context) => const LoginScreen(),
          '/home': (context) => const HomeScreen(),
          '/pairing': (context) => const PairingScreen(),
          '/events': (context) => const EventsScreen(),
          '/commands': (context) => const CommandsScreen(),
          '/settings': (context) => const SettingsScreen(),
          '/security': (context) => const SecurityDashboardScreen(),
          '/findmac': (context) => const FindMacScreen(),
          '/reports': (context) => const ReportsScreen(),
          '/geofence': (context) => const GeofenceScreen(),
        },
        onGenerateRoute: (settings) {
          if (settings.name == '/event-detail') {
            final eventId = settings.arguments as String;
            return MaterialPageRoute(
              builder: (context) => EventDetailScreen(eventId: eventId),
            );
          }
          return null;
        },
      ),
    );
  }
}

class AppState extends ChangeNotifier {
  String? _selectedDeviceId;
  bool _isLoading = false;

  String? get selectedDeviceId => _selectedDeviceId;
  bool get isLoading => _isLoading;

  void setSelectedDevice(String? deviceId) {
    _selectedDeviceId = deviceId;
    notifyListeners();
  }

  void setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }
}
