import 'package:intl/intl.dart';

class Formatters {
  Formatters._();

  static final _currencyFormat = NumberFormat.currency(
    symbol: '',
    decimalDigits: 2,
  );

  static final _compactFormat = NumberFormat.compact();

  static final _percentFormat = NumberFormat.percentPattern();

  static final _dateFormat = DateFormat('dd MMM yyyy');

  static final _monthFormat = DateFormat('MMM yyyy');

  static final _shortDateFormat = DateFormat('dd/MM');

  /// Format number as currency: 1,234,567.89
  static String currency(num? value) {
    if (value == null) return '—';
    return _currencyFormat.format(value);
  }

  /// Format large numbers compactly: 1.2M, 45.3K
  static String compact(num? value) {
    if (value == null) return '—';
    return _compactFormat.format(value);
  }

  /// Format as percentage: 12.5%
  static String percent(num? value) {
    if (value == null) return '—';
    return '${value.toStringAsFixed(1)}%';
  }

  /// Format growth with sign: +12.5% or -3.2%
  static String growth(num? value) {
    if (value == null) return '—';
    final sign = value >= 0 ? '+' : '';
    return '$sign${value.toStringAsFixed(1)}%';
  }

  /// Format integer with thousands separator
  static String integer(num? value) {
    if (value == null) return '—';
    return NumberFormat('#,###').format(value.toInt());
  }

  /// Format date: 15 Jan 2024
  static String date(DateTime? date) {
    if (date == null) return '—';
    return _dateFormat.format(date);
  }

  /// Format month: Jan 2024
  static String month(DateTime? date) {
    if (date == null) return '—';
    return _monthFormat.format(date);
  }

  /// Format short date: 15/01
  static String shortDate(DateTime? date) {
    if (date == null) return '—';
    return _shortDateFormat.format(date);
  }

  /// Format date for API: 2024-01-15
  static String apiDate(DateTime date) {
    return DateFormat('yyyy-MM-dd').format(date);
  }

  /// Truncate text with ellipsis
  static String truncate(String text, int maxLength) {
    if (text.length <= maxLength) return text;
    return '${text.substring(0, maxLength)}...';
  }
}
