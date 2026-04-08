import 'package:flutter/material.dart';

import '../config/theme.dart';

class StatusBadge extends StatelessWidget {
  final String status;
  final double? fontSize;

  const StatusBadge({super.key, required this.status, this.fontSize});

  @override
  Widget build(BuildContext context) {
    final (color, icon) = _statusConfig(status);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 4),
          Text(
            status.toUpperCase(),
            style: TextStyle(
              fontSize: fontSize ?? 11,
              fontWeight: FontWeight.w600,
              color: color,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }

  (Color, IconData) _statusConfig(String status) {
    switch (status.toLowerCase()) {
      case 'success':
      case 'passed':
      case 'healthy':
      case 'achieved':
        return (AppColors.success, Icons.check_circle_rounded);
      case 'failed':
      case 'critical':
      case 'unhealthy':
        return (AppColors.error, Icons.cancel_rounded);
      case 'running':
      case 'pending':
      case 'in_progress':
        return (AppColors.info, Icons.hourglass_top_rounded);
      case 'warning':
      case 'degraded':
        return (AppColors.warning, Icons.warning_rounded);
      case 'cancelled':
        return (Colors.grey, Icons.block_rounded);
      default:
        return (Colors.grey, Icons.info_rounded);
    }
  }
}
