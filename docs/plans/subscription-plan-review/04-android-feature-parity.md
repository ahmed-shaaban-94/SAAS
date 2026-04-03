# Track 4 — Android Feature Parity

> **Status**: PLANNED
> **Priority**: MEDIUM
> **Current State**: 9 screens (Dashboard, Pipeline, Products, Customers, Staff, Sites, Returns, Settings, Login) — missing 6 features from web

---

## Objective

Bring the Android app to **feature parity** with the web dashboard by adding the missing screens (Goals, Alerts, AI Insights, SQL Lab, Reports, Explore), implementing **offline-first caching**, and adding **push notifications** — demonstrating full-stack mobile engineering.

---

## Why This Matters

- Full-stack = web + mobile + backend — this is the trifecta employers want
- Offline-first is a critical mobile pattern that most developers skip
- Push notifications demonstrate end-to-end system design (backend → FCM → device)
- Kotlin + Jetpack Compose is the modern Android standard

---

## Scope

- 6 new screens with ViewModels
- Offline-first architecture with Room sync
- Push notifications via Firebase Cloud Messaging (FCM)
- Biometric authentication option
- Widget for KPI quick view
- 30+ tests (unit + integration)

---

## Deliverables

| Deliverable | Description |
|-------------|-------------|
| Goals screen | Revenue target tracking with monthly breakdown + progress bars |
| Alerts screen | Alert configuration, history, acknowledgment |
| AI Insights screen | AI summaries + anomaly list (from Phase 2.8) |
| SQL Lab screen | Simple query editor with results table (read-only) |
| Reports screen | Parameterized report templates with PDF sharing |
| Explore screen | Self-serve dbt model browser with filtering |
| Offline sync | Room-based cache with background sync worker |
| Push notifications | FCM integration for alerts + pipeline status |
| Biometric auth | Fingerprint/face unlock for app access |
| KPI widget | Home screen widget showing key metrics |
| Tests | 30+ unit/integration tests |

---

## Technical Details

### New Screens Architecture

```
android/app/src/main/kotlin/com/datapulse/android/
├── presentation/
│   ├── goals/
│   │   ├── GoalsScreen.kt          # Monthly targets with progress visualization
│   │   └── GoalsViewModel.kt       # Fetches targets API, computes progress
│   ├── alerts/
│   │   ├── AlertsScreen.kt         # Alert list with swipe-to-acknowledge
│   │   └── AlertsViewModel.kt      # CRUD operations for alerts
│   ├── insights/
│   │   ├── InsightsScreen.kt       # AI summary cards + anomaly list
│   │   └── InsightsViewModel.kt    # Polls AI endpoints
│   ├── sqllab/
│   │   ├── SqlLabScreen.kt         # Query editor with syntax highlighting
│   │   └── SqlLabViewModel.kt      # Execute query, display results
│   ├── reports/
│   │   ├── ReportsScreen.kt        # Report template list + parameter form
│   │   └── ReportsViewModel.kt     # Generate + share report
│   └── explore/
│       ├── ExploreScreen.kt        # dbt model browser with filter chips
│       └── ExploreViewModel.kt     # Fetch explore models + apply filters
├── data/
│   ├── local/
│   │   ├── dao/
│   │   │   ├── GoalsDao.kt         # Room DAO for targets cache
│   │   │   ├── AlertsDao.kt        # Room DAO for alerts cache
│   │   │   └── InsightsDao.kt      # Room DAO for AI insights cache
│   │   └── entity/
│   │       ├── GoalEntity.kt
│   │       ├── AlertEntity.kt
│   │       └── InsightEntity.kt
│   ├── remote/
│   │   ├── GoalsApi.kt             # Retrofit endpoints for targets
│   │   ├── AlertsApi.kt            # Retrofit endpoints for alerts
│   │   └── InsightsApi.kt          # Retrofit endpoints for AI insights
│   └── sync/
│       ├── SyncWorker.kt           # WorkManager periodic sync (every 15 min)
│       └── SyncManager.kt          # Orchestrates Room ↔ API sync
├── notification/
│   ├── FCMService.kt               # Firebase messaging service
│   ├── NotificationChannels.kt     # Android notification channels
│   └── NotificationBuilder.kt      # Rich notification creation
└── widget/
    ├── KpiWidgetProvider.kt        # AppWidget for home screen
    ├── KpiWidgetReceiver.kt        # Widget update receiver
    └── KpiRemoteViewsFactory.kt    # Widget layout builder
```

### Offline-First Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Compose UI  │ ←── │  ViewModel   │ ←── │ Repository  │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                 │
                                    ┌────────────┴────────────┐
                                    │                         │
                              ┌─────▼─────┐           ┌──────▼──────┐
                              │ Room (Local)│           │ Retrofit    │
                              │ Source of   │           │ (Remote)    │
                              │ Truth       │           │             │
                              └────────────┘           └─────────────┘
                                    ▲
                                    │
                              ┌─────┴──────┐
                              │ SyncWorker  │  ← WorkManager (every 15 min)
                              └────────────┘

Strategy:
1. UI always reads from Room (instant, works offline)
2. Repository fetches from API → writes to Room → UI auto-updates via Flow
3. SyncWorker runs in background to keep cache fresh
4. Stale data indicator shown when offline > 15 min
```

### Push Notification Flow

```
Pipeline completes/fails
        │
        ▼
n8n workflow → POST /api/v1/notifications/push
        │
        ▼
Backend → Firebase Admin SDK → FCM
        │
        ▼
Android device receives FCM message
        │
        ▼
FCMService.kt → NotificationBuilder → System notification
        │
        ▼
User taps → Deep link to relevant screen (pipeline/alerts)
```

### KPI Widget

```kotlin
// Displays on home screen:
// ┌──────────────────────┐
// │ DataPulse             │
// │                       │
// │ Revenue    EGP 1.5M   │
// │ Orders     45,230     │
// │ Customers  12,001     │
// │                       │
// │ Updated: 5 min ago    │
// └──────────────────────┘

// Refreshes via WorkManager every 30 min
// Taps opens app to Dashboard
```

---

## Navigation Updates

```kotlin
// NavRoutes.kt — add new routes:
sealed class NavRoute(val route: String) {
    // ... existing routes
    object Goals : NavRoute("goals")
    object Alerts : NavRoute("alerts")
    object Insights : NavRoute("insights")
    object SqlLab : NavRoute("sql_lab")
    object Reports : NavRoute("reports")
    object Explore : NavRoute("explore")
}
```

---

## New Dependencies

| Library | Purpose |
|---------|---------|
| `firebase-messaging` | Push notifications via FCM |
| `firebase-analytics` | (Optional) usage analytics |
| `androidx.work:work-runtime-ktx` | Background sync worker |
| `androidx.glance:glance-appwidget` | Compose-based home screen widget |
| `androidx.biometric:biometric` | Fingerprint/face authentication |

---

## Dependencies (Project)

- Track 6 (API Improvements) — new endpoints needed for Explore/SQL Lab
- Phase 2.8 (AI-Light) — AI insights data source
- Existing Android architecture (screens, Hilt DI, Room, Retrofit)
