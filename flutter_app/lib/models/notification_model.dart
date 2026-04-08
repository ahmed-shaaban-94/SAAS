class AppNotification {
  final String id;
  final String type;
  final String title;
  final String message;
  final bool read;
  final DateTime createdAt;
  final Map<String, dynamic>? metadata;

  const AppNotification({
    required this.id,
    required this.type,
    required this.title,
    required this.message,
    required this.read,
    required this.createdAt,
    this.metadata,
  });

  factory AppNotification.fromJson(Map<String, dynamic> json) =>
      AppNotification(
        id: json['id'] as String,
        type: json['type'] as String,
        title: json['title'] as String,
        message: json['message'] as String,
        read: json['read'] as bool? ?? false,
        createdAt: DateTime.parse(json['created_at'] as String),
        metadata: json['metadata'] as Map<String, dynamic>?,
      );
}

class NotificationCount {
  final int total;
  final int unread;

  const NotificationCount({required this.total, required this.unread});

  factory NotificationCount.fromJson(Map<String, dynamic> json) =>
      NotificationCount(
        total: json['total'] as int,
        unread: json['unread'] as int,
      );
}
