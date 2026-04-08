class HealthStatus {
  final String status; // healthy, degraded, unhealthy
  final Map<String, ComponentHealth> components;

  const HealthStatus({required this.status, required this.components});

  bool get isHealthy => status == 'healthy';

  factory HealthStatus.fromJson(Map<String, dynamic> json) => HealthStatus(
        status: json['status'] as String,
        components: (json['components'] as Map<String, dynamic>?)
                ?.map((k, v) => MapEntry(k, ComponentHealth.fromJson(v))) ??
            {},
      );
}

class ComponentHealth {
  final String status;
  final String? message;
  final double? latencyMs;

  const ComponentHealth({
    required this.status,
    this.message,
    this.latencyMs,
  });

  factory ComponentHealth.fromJson(Map<String, dynamic> json) =>
      ComponentHealth(
        status: json['status'] as String,
        message: json['message'] as String?,
        latencyMs: (json['latency_ms'] as num?)?.toDouble(),
      );
}
