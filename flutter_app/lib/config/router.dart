import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/auth_provider.dart';
import '../screens/login/login_screen.dart';
import '../screens/dashboard/dashboard_screen.dart';
import '../screens/products/products_screen.dart';
import '../screens/products/product_detail_screen.dart';
import '../screens/customers/customers_screen.dart';
import '../screens/customers/customer_detail_screen.dart';
import '../screens/staff/staff_screen.dart';
import '../screens/staff/staff_detail_screen.dart';
import '../screens/sites/sites_screen.dart';
import '../screens/sites/site_detail_screen.dart';
import '../screens/returns/returns_screen.dart';
import '../screens/pipeline/pipeline_screen.dart';
import '../screens/alerts/alerts_screen.dart';
import '../screens/insights/insights_screen.dart';
import '../screens/goals/goals_screen.dart';
import '../screens/reports/reports_screen.dart';
import '../screens/explore/explore_screen.dart';
import '../screens/sql_lab/sql_lab_screen.dart';
import '../screens/quality/quality_screen.dart';
import '../screens/settings/settings_screen.dart';
import '../widgets/app_shell.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _shellNavigatorKey = GlobalKey<NavigatorState>();

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authStateProvider);

  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/dashboard',
    redirect: (context, state) {
      final isLoggedIn = authState.value?.isAuthenticated ?? false;
      final isLoginRoute = state.matchedLocation == '/login';

      if (!isLoggedIn && !isLoginRoute) return '/login';
      if (isLoggedIn && isLoginRoute) return '/dashboard';
      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      ShellRoute(
        navigatorKey: _shellNavigatorKey,
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(
            path: '/dashboard',
            builder: (context, state) => const DashboardScreen(),
          ),
          GoRoute(
            path: '/products',
            builder: (context, state) => const ProductsScreen(),
            routes: [
              GoRoute(
                path: ':key',
                builder: (context, state) => ProductDetailScreen(
                  productKey: state.pathParameters['key']!,
                ),
              ),
            ],
          ),
          GoRoute(
            path: '/customers',
            builder: (context, state) => const CustomersScreen(),
            routes: [
              GoRoute(
                path: ':key',
                builder: (context, state) => CustomerDetailScreen(
                  customerKey: state.pathParameters['key']!,
                ),
              ),
            ],
          ),
          GoRoute(
            path: '/staff',
            builder: (context, state) => const StaffScreen(),
            routes: [
              GoRoute(
                path: ':key',
                builder: (context, state) => StaffDetailScreen(
                  staffKey: state.pathParameters['key']!,
                ),
              ),
            ],
          ),
          GoRoute(
            path: '/sites',
            builder: (context, state) => const SitesScreen(),
            routes: [
              GoRoute(
                path: ':key',
                builder: (context, state) => SiteDetailScreen(
                  siteKey: state.pathParameters['key']!,
                ),
              ),
            ],
          ),
          GoRoute(
            path: '/returns',
            builder: (context, state) => const ReturnsScreen(),
          ),
          GoRoute(
            path: '/pipeline',
            builder: (context, state) => const PipelineScreen(),
          ),
          GoRoute(
            path: '/quality',
            builder: (context, state) => const QualityScreen(),
          ),
          GoRoute(
            path: '/alerts',
            builder: (context, state) => const AlertsScreen(),
          ),
          GoRoute(
            path: '/insights',
            builder: (context, state) => const InsightsScreen(),
          ),
          GoRoute(
            path: '/goals',
            builder: (context, state) => const GoalsScreen(),
          ),
          GoRoute(
            path: '/reports',
            builder: (context, state) => const ReportsScreen(),
          ),
          GoRoute(
            path: '/explore',
            builder: (context, state) => const ExploreScreen(),
          ),
          GoRoute(
            path: '/sql-lab',
            builder: (context, state) => const SqlLabScreen(),
          ),
          GoRoute(
            path: '/settings',
            builder: (context, state) => const SettingsScreen(),
          ),
        ],
      ),
    ],
  );
});
