import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../config/theme.dart';
import '../providers/auth_provider.dart';

class AppDrawer extends ConsumerWidget {
  final bool isPermanent;

  const AppDrawer({super.key, this.isPermanent = false});

  static const _sections = [
    _DrawerSection('Analytics', [
      _DrawerItem('/dashboard', Icons.dashboard_rounded, 'Dashboard'),
      _DrawerItem('/products', Icons.inventory_2_rounded, 'Products'),
      _DrawerItem('/customers', Icons.people_rounded, 'Customers'),
      _DrawerItem('/staff', Icons.badge_rounded, 'Staff'),
      _DrawerItem('/sites', Icons.store_rounded, 'Sites'),
      _DrawerItem('/returns', Icons.assignment_return_rounded, 'Returns'),
    ]),
    _DrawerSection('Intelligence', [
      _DrawerItem('/insights', Icons.auto_awesome_rounded, 'AI Insights'),
      _DrawerItem('/goals', Icons.flag_rounded, 'Goals'),
      _DrawerItem('/alerts', Icons.warning_amber_rounded, 'Alerts'),
    ]),
    _DrawerSection('Data', [
      _DrawerItem('/pipeline', Icons.sync_rounded, 'Pipeline'),
      _DrawerItem('/quality', Icons.verified_rounded, 'Quality'),
      _DrawerItem('/explore', Icons.explore_rounded, 'Explore'),
      _DrawerItem('/sql-lab', Icons.code_rounded, 'SQL Lab'),
    ]),
    _DrawerSection('Reports', [
      _DrawerItem('/reports', Icons.description_rounded, 'Reports'),
    ]),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final location = GoRouterState.of(context).matchedLocation;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final content = Column(
      children: [
        if (!isPermanent) ...[
          DrawerHeader(
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(
                    Icons.analytics_rounded,
                    color: Colors.white,
                    size: 28,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'DataPulse',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Sales Analytics',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: isDark
                            ? Colors.white54
                            : Colors.black54,
                      ),
                ),
              ],
            ),
          ),
        ] else ...[
          const SizedBox(height: 16),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(
                    Icons.analytics_rounded,
                    color: Colors.white,
                    size: 20,
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  'DataPulse',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          const Divider(height: 1),
        ],
        Expanded(
          child: ListView(
            padding: const EdgeInsets.symmetric(vertical: 8),
            children: [
              for (final section in _sections) ...[
                Padding(
                  padding:
                      const EdgeInsets.fromLTRB(16, 16, 16, 4),
                  child: Text(
                    section.title,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: isDark ? Colors.white38 : Colors.black38,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 1.2,
                        ),
                  ),
                ),
                for (final item in section.items)
                  _buildNavItem(context, item, location),
              ],
            ],
          ),
        ),
        const Divider(height: 1),
        ListTile(
          leading: const Icon(Icons.settings_rounded),
          title: const Text('Settings'),
          selected: location == '/settings',
          onTap: () {
            if (!isPermanent) Navigator.pop(context);
            context.go('/settings');
          },
        ),
        ListTile(
          leading: const Icon(Icons.logout_rounded),
          title: const Text('Logout'),
          onTap: () {
            ref.read(authStateProvider.notifier).logout();
            context.go('/login');
          },
        ),
        const SizedBox(height: 8),
      ],
    );

    if (isPermanent) {
      return SizedBox(
        width: 250,
        child: Material(
          color: Theme.of(context).appBarTheme.backgroundColor,
          child: content,
        ),
      );
    }

    return Drawer(child: content);
  }

  Widget _buildNavItem(
      BuildContext context, _DrawerItem item, String location) {
    final isSelected = location == item.path ||
        (item.path != '/dashboard' && location.startsWith(item.path));

    return ListTile(
      leading: Icon(item.icon),
      title: Text(item.label),
      selected: isSelected,
      selectedTileColor: AppColors.primary.withOpacity(0.1),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16),
      dense: true,
      visualDensity: const VisualDensity(vertical: -1),
      onTap: () {
        if (!isPermanent) Navigator.pop(context);
        context.go(item.path);
      },
    );
  }
}

class _DrawerSection {
  final String title;
  final List<_DrawerItem> items;

  const _DrawerSection(this.title, this.items);
}

class _DrawerItem {
  final String path;
  final IconData icon;
  final String label;

  const _DrawerItem(this.path, this.icon, this.label);
}
