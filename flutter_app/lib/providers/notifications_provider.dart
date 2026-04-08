import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/notification_model.dart';
import '../services/notifications_service.dart';

final notificationCountProvider =
    FutureProvider.autoDispose<NotificationCount>((ref) async {
  final service = ref.watch(notificationsServiceProvider);
  return service.getCount();
});

final notificationsProvider =
    FutureProvider.autoDispose<List<AppNotification>>((ref) async {
  final service = ref.watch(notificationsServiceProvider);
  return service.getNotifications();
});
