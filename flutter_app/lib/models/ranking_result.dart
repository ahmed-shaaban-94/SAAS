class RankingItem {
  final int rank;
  final String key;
  final String name;
  final double value;
  final double pctOfTotal;

  const RankingItem({
    required this.rank,
    required this.key,
    required this.name,
    required this.value,
    required this.pctOfTotal,
  });

  factory RankingItem.fromJson(Map<String, dynamic> json) => RankingItem(
        rank: json['rank'] as int,
        key: json['key'] as String,
        name: json['name'] as String,
        value: (json['value'] as num).toDouble(),
        pctOfTotal: (json['pct_of_total'] as num).toDouble(),
      );
}

class RankingResult {
  final List<RankingItem> items;
  final double total;

  const RankingResult({required this.items, required this.total});

  factory RankingResult.fromJson(Map<String, dynamic> json) => RankingResult(
        items: (json['items'] as List)
            .map((e) => RankingItem.fromJson(e))
            .toList(),
        total: (json['total'] as num).toDouble(),
      );
}
