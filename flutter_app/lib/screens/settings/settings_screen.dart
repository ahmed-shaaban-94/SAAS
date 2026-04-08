import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../../config/constants.dart';
import '../../config/theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/theme_provider.dart';
import '../../services/health_service.dart';
import '../../models/health_status.dart';

final healthProvider = FutureProvider.autoDispose<HealthStatus>((ref) async {
  final service = ref.watch(healthServiceProvider);
  return service.getHealth();
});

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeMode = ref.watch(themeModeProvider);
    final health = ref.watch(healthProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Settings',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 20),

          // Appearance
          _SectionTitle('Appearance'),
          Card(
            child: SwitchListTile(
              title: const Text('Dark Mode'),
              subtitle: const Text('Toggle dark/light theme'),
              secondary: Icon(
                themeMode == ThemeMode.dark
                    ? Icons.dark_mode_rounded
                    : Icons.light_mode_rounded,
              ),
              value: themeMode == ThemeMode.dark,
              onChanged: (_) => ref.read(themeModeProvider.notifier).toggle(),
            ),
          ),
          const SizedBox(height: 16),

          // API Configuration
          _SectionTitle('API Configuration'),
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.dns_rounded),
                  title: const Text('API URL'),
                  subtitle: const Text(AppConstants.baseUrl),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.security_rounded),
                  title: const Text('Auth Provider'),
                  subtitle: const Text('Auth0 OIDC'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // System Health
          _SectionTitle('System Health'),
          health.when(
            loading: () => const Card(
              child: Padding(
                padding: EdgeInsets.all(20),
                child: Center(child: CircularProgressIndicator()),
              ),
            ),
            error: (e, _) => Card(
              child: ListTile(
                leading: const Icon(Icons.error_rounded,
                    color: AppColors.error),
                title: const Text('Unable to connect'),
                subtitle: Text(e.toString()),
              ),
            ),
            data: (status) => Card(
              child: Column(
                children: [
                  ListTile(
                    leading: Icon(
                      status.isHealthy
                          ? Icons.check_circle_rounded
                          : Icons.warning_rounded,
                      color: status.isHealthy
                          ? AppColors.success
                          : AppColors.warning,
                    ),
                    title: Text(
                        'Status: ${status.status.toUpperCase()}'),
                  ),
                  ...status.components.entries.map((entry) => ListTile(
                        dense: true,
                        leading: Icon(
                          entry.value.status == 'healthy'
                              ? Icons.circle
                              : Icons.circle,
                          size: 12,
                          color: entry.value.status == 'healthy'
                              ? AppColors.success
                              : AppColors.error,
                        ),
                        title: Text(entry.key),
                        subtitle: entry.value.latencyMs != null
                            ? Text(
                                '${entry.value.latencyMs!.toStringAsFixed(0)}ms')
                            : null,
                        trailing: Text(
                          entry.value.status,
                          style: TextStyle(
                            fontSize: 12,
                            color: entry.value.status == 'healthy'
                                ? AppColors.success
                                : AppColors.error,
                          ),
                        ),
                      )),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // About
          _SectionTitle('About'),
          Card(
            child: Column(
              children: [
                const ListTile(
                  leading: Icon(Icons.info_rounded),
                  title: Text('DataPulse'),
                  subtitle: Text('Business & Sales Analytics'),
                ),
                const Divider(height: 1),
                const ListTile(
                  leading: Icon(Icons.code_rounded),
                  title: Text('Version'),
                  subtitle: Text('1.0.0'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Logout
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () {
                ref.read(authStateProvider.notifier).logout();
                context.go('/login');
              },
              icon: const Icon(Icons.logout_rounded, color: AppColors.error),
              label: const Text(
                'Sign Out',
                style: TextStyle(color: AppColors.error),
              ),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.error),
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String title;

  const _SectionTitle(this.title);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        title,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: Colors.grey,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.8,
            ),
      ),
    );
  }
}
