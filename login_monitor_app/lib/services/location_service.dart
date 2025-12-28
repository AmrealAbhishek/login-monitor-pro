import 'package:geocoding/geocoding.dart';

/// Service to handle location-related functionality including reverse geocoding
class LocationService {
  static final LocationService _instance = LocationService._internal();
  factory LocationService() => _instance;
  LocationService._internal();

  // Cache for geocoded addresses to avoid repeated API calls
  final Map<String, String> _addressCache = {};

  /// Get address from coordinates using reverse geocoding
  /// Returns formatted address string or null if failed
  Future<String?> getAddressFromCoordinates(double latitude, double longitude) async {
    final cacheKey = '${latitude.toStringAsFixed(4)},${longitude.toStringAsFixed(4)}';

    // Check cache first
    if (_addressCache.containsKey(cacheKey)) {
      return _addressCache[cacheKey];
    }

    try {
      final placemarks = await placemarkFromCoordinates(latitude, longitude);

      if (placemarks.isNotEmpty) {
        final place = placemarks.first;
        final address = _formatAddress(place);

        // Cache the result
        _addressCache[cacheKey] = address;
        return address;
      }
    } catch (e) {
      print('[LocationService] Reverse geocoding failed: $e');
    }

    return null;
  }

  /// Format placemark into readable address
  String _formatAddress(Placemark place) {
    final parts = <String>[];

    // Add street/sublocality
    if (place.subLocality != null && place.subLocality!.isNotEmpty) {
      parts.add(place.subLocality!);
    } else if (place.street != null && place.street!.isNotEmpty) {
      parts.add(place.street!);
    }

    // Add locality (city)
    if (place.locality != null && place.locality!.isNotEmpty) {
      parts.add(place.locality!);
    }

    // Add administrative area (state/region)
    if (place.administrativeArea != null && place.administrativeArea!.isNotEmpty) {
      parts.add(place.administrativeArea!);
    }

    // Add country
    if (place.country != null && place.country!.isNotEmpty) {
      parts.add(place.country!);
    }

    return parts.isNotEmpty ? parts.join(', ') : 'Unknown location';
  }

  /// Get Google Maps URL for coordinates
  String getGoogleMapsUrl(double latitude, double longitude) {
    return 'https://www.google.com/maps?q=$latitude,$longitude';
  }

  /// Get Apple Maps URL for coordinates
  String getAppleMapsUrl(double latitude, double longitude) {
    return 'https://maps.apple.com/?q=$latitude,$longitude';
  }

  /// Clear the address cache
  void clearCache() {
    _addressCache.clear();
  }
}
