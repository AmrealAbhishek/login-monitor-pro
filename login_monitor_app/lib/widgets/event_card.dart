import 'package:flutter/material.dart';
import 'package:timeago/timeago.dart' as timeago;
import 'package:cached_network_image/cached_network_image.dart';
import '../models/event.dart';

class EventCard extends StatelessWidget {
  final MonitorEvent event;
  final VoidCallback? onTap;

  const EventCard({
    super.key,
    required this.event,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  // Event icon
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: _getEventColor(context).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Center(
                      child: Text(
                        event.eventIcon,
                        style: const TextStyle(fontSize: 22),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  // Event info
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              event.eventType,
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                            if (!event.isRead) ...[
                              const SizedBox(width: 8),
                              Container(
                                width: 8,
                                height: 8,
                                decoration: BoxDecoration(
                                  color: Theme.of(context).colorScheme.primary,
                                  shape: BoxShape.circle,
                                ),
                              ),
                            ],
                          ],
                        ),
                        const SizedBox(height: 2),
                        Text(
                          timeago.format(event.timestamp),
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  ),
                  // Indicators
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (event.hasPhotos)
                        _buildIndicator(context, Icons.photo_camera),
                      if (event.hasAudio)
                        _buildIndicator(context, Icons.mic),
                      if (event.hasLocation)
                        _buildIndicator(context, Icons.location_on),
                      if (event.faceRecognition.hasUnknownFaces)
                        _buildIndicator(context, Icons.warning, isWarning: true),
                    ],
                  ),
                ],
              ),
              // Photo preview if available
              if (event.hasPhotos && event.photos.isNotEmpty) ...[
                const SizedBox(height: 12),
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: SizedBox(
                    height: 120,
                    child: Row(
                      children: event.photos.take(3).map((photo) {
                        return Expanded(
                          child: Padding(
                            padding: const EdgeInsets.only(right: 4),
                            child: CachedNetworkImage(
                              imageUrl: photo,
                              fit: BoxFit.cover,
                              height: 120,
                              placeholder: (context, url) => Container(
                                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                              ),
                              errorWidget: (context, url, error) => Container(
                                color: Theme.of(context).colorScheme.errorContainer,
                                child: const Icon(Icons.error),
                              ),
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ),
              ],
              // Location info
              if (event.location.city != null) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(
                      Icons.location_on,
                      size: 16,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        event.location.displayLocation,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                          fontSize: 13,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Color _getEventColor(BuildContext context) {
    switch (event.eventType.toLowerCase()) {
      case 'login':
        return Colors.blue;
      case 'unlock':
        return Colors.green;
      case 'wake':
        return Colors.orange;
      default:
        return Theme.of(context).colorScheme.primary;
    }
  }

  Widget _buildIndicator(BuildContext context, IconData icon,
      {bool isWarning = false}) {
    return Padding(
      padding: const EdgeInsets.only(left: 4),
      child: Icon(
        icon,
        size: 18,
        color: isWarning
            ? Theme.of(context).colorScheme.error
            : Theme.of(context).colorScheme.onSurfaceVariant,
      ),
    );
  }
}
