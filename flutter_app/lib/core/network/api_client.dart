import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pretty_dio_logger/pretty_dio_logger.dart';

import '../../config/constants.dart';
import 'api_interceptor.dart';

final dioProvider = Provider<Dio>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: AppConstants.baseUrl,
      connectTimeout: AppConstants.connectTimeout,
      receiveTimeout: AppConstants.receiveTimeout,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ),
  );

  dio.interceptors.addAll([
    AuthInterceptor(ref),
    PrettyDioLogger(
      requestHeader: true,
      requestBody: true,
      responseHeader: false,
      responseBody: true,
      compact: true,
    ),
  ]);

  return dio;
});

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(ref.watch(dioProvider));
});

class ApiClient {
  final Dio _dio;

  ApiClient(this._dio);

  Future<T> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    T Function(dynamic)? fromJson,
  }) async {
    final response = await _dio.get(path, queryParameters: queryParameters);
    if (fromJson != null) return fromJson(response.data);
    return response.data as T;
  }

  Future<T> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    T Function(dynamic)? fromJson,
  }) async {
    final response = await _dio.post(
      path,
      data: data,
      queryParameters: queryParameters,
    );
    if (fromJson != null) return fromJson(response.data);
    return response.data as T;
  }

  Future<T> patch<T>(
    String path, {
    dynamic data,
    T Function(dynamic)? fromJson,
  }) async {
    final response = await _dio.patch(path, data: data);
    if (fromJson != null) return fromJson(response.data);
    return response.data as T;
  }

  Future<void> delete(String path) async {
    await _dio.delete(path);
  }
}
