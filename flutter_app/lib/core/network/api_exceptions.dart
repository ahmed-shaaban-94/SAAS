import 'package:dio/dio.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final dynamic data;

  ApiException({
    required this.message,
    this.statusCode,
    this.data,
  });

  factory ApiException.fromDioException(DioException e) {
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return ApiException(
          message: 'Connection timed out. Please check your network.',
          statusCode: null,
        );
      case DioExceptionType.badResponse:
        final statusCode = e.response?.statusCode;
        final data = e.response?.data;
        String message;
        if (data is Map && data.containsKey('detail')) {
          message = data['detail'].toString();
        } else {
          message = _messageForStatus(statusCode);
        }
        return ApiException(
          message: message,
          statusCode: statusCode,
          data: data,
        );
      case DioExceptionType.connectionError:
        return ApiException(
          message: 'Unable to connect to server. Please check your network.',
        );
      case DioExceptionType.cancel:
        return ApiException(message: 'Request was cancelled.');
      default:
        return ApiException(
          message: 'An unexpected error occurred.',
        );
    }
  }

  static String _messageForStatus(int? statusCode) {
    switch (statusCode) {
      case 400:
        return 'Invalid request.';
      case 401:
        return 'Session expired. Please login again.';
      case 403:
        return 'Access denied.';
      case 404:
        return 'Resource not found.';
      case 422:
        return 'Invalid data provided.';
      case 429:
        return 'Too many requests. Please slow down.';
      case 500:
        return 'Server error. Please try again later.';
      case 503:
        return 'Service unavailable. Please try again later.';
      default:
        return 'Something went wrong (status: $statusCode).';
    }
  }

  @override
  String toString() => 'ApiException: $message (status: $statusCode)';
}
