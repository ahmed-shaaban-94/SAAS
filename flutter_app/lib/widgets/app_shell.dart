import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/theme_provider.dart';
import '../providers/notifications_provider.dart';
import 'app_drawer.dart';

class AppShell extends ConsumerStatefulWidget {
  final Widget child;

  const AppShell({super.key, required this.child});

  @override
  ConsumerState<AppShell> createState() => _AppShellState();
}

class _AppShellState extends ConsumerState<AppShell> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  int _selectedIndex = 0;

  static const _navItems = [
    _NavItem('/dashboard', Icons.dashboard_rounded, 'Dashboard'),
    _NavItem('/products', Icons.inventory_2_rounded, 'Products'),
    _NavItem('/customers', Icons.people_rounded, 'Customers'),
    _NavItem('/staff', Icons.badge_rounded, 'Staff'),
    _NavItem('/pipeline', Icons.sync_rounded, 'Pipeline'),
  ];

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    _selectedIndex = _navItems.indexWhere(
      (item) => location.startsWith(item.path),
    );
    if (_selectedIndex < 0) _selectedIndex = 0;

    final isWide = MediaQuery.sizeOf(context).width >= 768;

    return Scaffold(
      key: _scaffoldKey,
      appBar: _buildAppBar(context),
      drawer: isWide ? null : const AppDrawer(),
      body: Row(
        children: [
          if (isWide) const AppDrawer(isPermanent: true),
          Expanded(child: widget.child),
        ],
      ),
      bottomNavigationBar: isWide
          ? null
          : NavigationBar(
              selectedIndex: _selectedIndex.clamp(0, _navItems.length - 1),
              onDestinationSelected: (index) {
                context.go(_navItems[index].path);
              },
              destinations: _navItems
                  .map((item) => NavigationDestination(
                        icon: Icon(item.icon),
                        label: item.label,
                      ))
                  .toList(),
            ),
    );
  }

  PreferredSizeWidget _buildAppBar(BuildContext context) {
    final notifCount = ref.watch(notificationCountProvider);

    return AppBar(
      title: const Text(
        'DataPulse',
        style: TextStyle(fontWeight: FontWeight.w700, fontSize: 20),
      ),
      actions: [
        // Theme toggle
        IconButton(
          icon: Icon(
            ref.watch(themeModeProvider) == ThemeMode.dark
                ? Icons.light_mode_rounded
                : Icons.dark_mode_rounded,
          ),
          onPressed: () => ref.read(themeModeProvider.notifier).toggle(),
          tooltip: 'Toggle theme',
        ),
        // Notifications
        IconButton(
          icon: Badge(
            isLabelVisible: notifCount.valueOrNull?.unread != null &&
                notifCount.valueOrNull!.unread > 0,
            label: Text('${notifCount.valueOrNull?.unread ?? 0}'),
            child: const Icon(Icons.notifications_outlined),
          ),
          onPressed: () => context.go('/alerts'),
          tooltip: 'Notifications',
        ),
        const SizedBox(width: 8),
      ],
    );
  }
}

class _NavItem {
  final String path;
  final IconData icon;
  final String label;

  const _NavItem(this.path, this.icon, this.label);
}
