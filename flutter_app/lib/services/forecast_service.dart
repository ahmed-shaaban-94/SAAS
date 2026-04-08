import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/network/api_client.dart';
import '../models/forecast_result.dart';

final forecastServiceProvider = Provider<ForecastService>((ref) {
  return ForecastService(ref.watch(apiClientProvider));
});

class ForecastService {
  final ApiClient _api;

  ForecastService(this._api);

  Future<ForecastResult> getRevenueForecast({
    String granularity = 'monthly',
  }) async {
    return _api.get(
      '/forecasting/revenue',
      queryParameters: {'granularity': granularity},
      fromJson: (data) => ForecastResult.fromJson(data),
    );
  }

  Future<ForecastResult> getProductForecast(String productKey) async {
    return _api.get(
      '/forecasting/products/$productKey',
      fromJson: (data) => ForecastResult.fromJson(data),
    );
  }

  Future<ForecastSummary> getForecastSummary() async {
    return _api.get(
      '/forecasting/summary',
      fromJson: (data) => ForecastSummary.fromJson(data),
    );
  }
}
