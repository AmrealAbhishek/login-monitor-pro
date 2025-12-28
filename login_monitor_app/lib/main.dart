import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'services/supabase_service.dart';
import 'services/alert_service.dart';
import 'services/fcm_service.dart';
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
import 'screens/profile_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Firebase FIRST (required for FCM)
  await Firebase.initializeApp();
  print('[Main] Firebase initialized');

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
        title: 'CyVigil',
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
          '/profile': (context) => const ProfileScreen(),
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
  final AlertService _alertService = AlertService();
  final FCMService _fcmService = FCMService();

  String? get selectedDeviceId => _selectedDeviceId;
  bool get isLoading => _isLoading;
  AlertService get alertService => _alertService;
  FCMService get fcmService => _fcmService;

  AppState() {
    _alertService.initialize();
    // Initialize FCM for push notifications
    _fcmService.initialize();
  }

  void setSelectedDevice(String? deviceId) {
    _selectedDeviceId = deviceId;
    notifyListeners();

    // Subscribe to real-time alerts for this device
    if (deviceId != null) {
      _alertService.subscribeToDevice(deviceId);
    } else {
      _alertService.unsubscribe();
    }
  }

  void setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  @override
  void dispose() {
    _alertService.dispose();
    super.dispose();
  }
}
