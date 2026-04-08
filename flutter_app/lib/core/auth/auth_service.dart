import 'package:flutter_appauth/flutter_appauth.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../config/constants.dart';

class AuthService {
  final FlutterAppAuth _appAuth = const FlutterAppAuth();
  static const _storage = FlutterSecureStorage();

  Future<bool> login() async {
    try {
      final result = await _appAuth.authorizeAndExchangeCode(
        AuthorizationTokenRequest(
          AppConstants.authClientId,
          AppConstants.authRedirectUri,
          issuer: AppConstants.authIssuer,
          scopes: ['openid', 'profile', 'email'],
          promptValues: ['login'],
        ),
      );

      if (result != null) {
        await _saveTokens(result);
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  Future<bool> refreshToken() async {
    try {
      final refreshToken = await _storage.read(key: 'refresh_token');
      if (refreshToken == null) return false;

      final result = await _appAuth.token(
        TokenRequest(
          AppConstants.authClientId,
          AppConstants.authRedirectUri,
          issuer: AppConstants.authIssuer,
          refreshToken: refreshToken,
        ),
      );

      if (result != null) {
        await _saveTokens(result);
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  Future<void> logout() async {
    await _storage.deleteAll();
  }

  Future<String?> getAccessToken() async {
    return await _storage.read(key: 'access_token');
  }

  Future<bool> isAuthenticated() async {
    final token = await _storage.read(key: 'access_token');
    return token != null;
  }

  Future<void> _saveTokens(TokenResponse result) async {
    if (result.accessToken != null) {
      await _storage.write(key: 'access_token', value: result.accessToken);
    }
    if (result.refreshToken != null) {
      await _storage.write(key: 'refresh_token', value: result.refreshToken);
    }
    if (result.idToken != null) {
      await _storage.write(key: 'id_token', value: result.idToken);
    }
  }
}
