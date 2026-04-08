import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/network/api_client.dart';
import '../models/explore_model.dart';

final exploreServiceProvider = Provider<ExploreService>((ref) {
  return ExploreService(ref.watch(apiClientProvider));
});

class ExploreService {
  final ApiClient _api;

  ExploreService(this._api);

  Future<List<ExploreModel>> getModels() async {
    return _api.get(
      '/explore/models',
      fromJson: (data) => (data['models'] as List)
          .map((e) => ExploreModel.fromJson(e))
          .toList(),
    );
  }

  Future<ExploreModel> getModel(String modelName) async {
    return _api.get(
      '/explore/models/$modelName',
      fromJson: (data) => ExploreModel.fromJson(data),
    );
  }

  Future<ExploreResult> executeQuery({
    required String model,
    required List<String> dimensions,
    required List<String> metrics,
    Map<String, dynamic>? filters,
    int limit = 100,
  }) async {
    return _api.post(
      '/explore/query',
      data: {
        'model': model,
        'dimensions': dimensions,
        'metrics': metrics,
        if (filters != null) 'filters': filters,
        'limit': limit,
      },
      fromJson: (data) => ExploreResult.fromJson(data),
    );
  }
}
