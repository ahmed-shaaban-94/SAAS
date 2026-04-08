import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';

import '../core/utils/extensions.dart';

class LoadingShimmer extends StatelessWidget {
  final int itemCount;
  final double height;

  const LoadingShimmer({
    super.key,
    this.itemCount = 3,
    this.height = 100,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;
    final baseColor = isDark ? const Color(0xFF1E293B) : const Color(0xFFE2E8F0);
    final highlightColor =
        isDark ? const Color(0xFF334155) : const Color(0xFFF1F5F9);

    return Shimmer.fromColors(
      baseColor: baseColor,
      highlightColor: highlightColor,
      child: Column(
        children: List.generate(
          itemCount,
          (i) => Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Container(
              height: height,
              decoration: BoxDecoration(
                color: baseColor,
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class ShimmerCard extends StatelessWidget {
  final double? height;
  final double? width;

  const ShimmerCard({super.key, this.height, this.width});

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;

    return Shimmer.fromColors(
      baseColor: isDark ? const Color(0xFF1E293B) : const Color(0xFFE2E8F0),
      highlightColor:
          isDark ? const Color(0xFF334155) : const Color(0xFFF1F5F9),
      child: Container(
        height: height,
        width: width,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
        ),
      ),
    );
  }
}
