import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:datapulse/app.dart';

void main() {
  testWidgets('App launches and shows login screen', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: DataPulseApp()),
    );
    await tester.pumpAndSettle();

    // Should show the app title or login screen
    expect(find.text('DataPulse'), findsWidgets);
  });
}
