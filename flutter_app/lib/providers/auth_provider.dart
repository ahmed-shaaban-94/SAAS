import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/auth/auth_service.dart';

final authServiceProvider = Provider<AuthService>((ref) => AuthService());

class AuthState {
  final bool isAuthenticated;
  final bool isLoading;
  final String? error;

  const AuthState({
    this.isAuthenticated = false,
    this.isLoading = false,
    this.error,
  });

  AuthState copyWith({
    bool? isAuthenticated,
    bool? isLoading,
    String? error,
  }) =>
      AuthState(
        isAuthenticated: isAuthenticated ?? this.isAuthenticated,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

final authStateProvider =
    AsyncNotifierProvider<AuthNotifier, AuthState>(AuthNotifier.new);

class AuthNotifier extends AsyncNotifier<AuthState> {
  @override
  Future<AuthState> build() async {
    final authService = ref.read(authServiceProvider);
    final isAuth = await authService.isAuthenticated();
    return AuthState(isAuthenticated: isAuth);
  }

  Future<void> login() async {
    state = const AsyncData(AuthState(isLoading: true));
    try {
      final authService = ref.read(authServiceProvider);
      final success = await authService.login();
      state = AsyncData(AuthState(isAuthenticated: success));
    } catch (e) {
      state = AsyncData(AuthState(error: e.toString()));
    }
  }

  Future<void> logout() async {
    final authService = ref.read(authServiceProvider);
    await authService.logout();
    state = const AsyncData(AuthState(isAuthenticated: false));
  }
}
