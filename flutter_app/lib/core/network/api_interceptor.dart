import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AuthInterceptor extends Interceptor {
  final Ref _ref;
  static const _storage = FlutterSecureStorage();

  AuthInterceptor(this._ref);

  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await _storage.read(key: 'access_token');
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      // Token expired — attempt refresh
      final refreshed = await _tryRefreshToken();
      if (refreshed) {
        // Retry the failed request
        final token = await _storage.read(key: 'access_token');
        err.requestOptions.headers['Authorization'] = 'Bearer $token';
        try {
          final response = await Dio().fetch(err.requestOptions);
          return handler.resolve(response);
        } catch (e) {
          return handler.next(err);
        }
      }
    }
    handler.next(err);
  }

  Future<bool> _tryRefreshToken() async {
    try {
      final refreshToken = await _storage.read(key: 'refresh_token');
      if (refreshToken == null) return false;

      // TODO: Implement token refresh via auth service
      return false;
    } catch (_) {
      return false;
    }
  }
}
