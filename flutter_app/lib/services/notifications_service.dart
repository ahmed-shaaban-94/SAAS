import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/network/api_client.dart';
import '../models/notification_model.dart';

final notificationsServiceProvider = Provider<NotificationsService>((ref) {
  return NotificationsService(ref.watch(apiClientProvider));
});

class NotificationsService {
  final ApiClient _api;

  NotificationsService(this._api);

  Future<List<AppNotification>> getNotifications({
    bool unreadOnly = false,
  }) async {
    return _api.get(
      '/notifications',
      queryParameters: {
        if (unreadOnly) 'unread_only': true,
      },
      fromJson: (data) => (data as List)
          .map((e) => AppNotification.fromJson(e))
          .toList(),
    );
  }

  Future<NotificationCount> getCount() async {
    return _api.get(
      '/notifications/count',
      fromJson: (data) => NotificationCount.fromJson(data),
    );
  }

  Future<void> markAsRead(String notificationId) async {
    await _api.post('/notifications/$notificationId/read');
  }

  Future<void> markAllAsRead() async {
    await _api.post('/notifications/read-all');
  }
}
