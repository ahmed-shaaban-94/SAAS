# Implementation Plan: DataPulse Android App

> **Note (2026-04)**: Keycloak references below are historical. Auth is now handled by Auth0.

## 1. Requirements Restatement

### What We Are Building

A native Android application for the DataPulse sales analytics SaaS platform. The app will consume the existing FastAPI backend (13+ REST endpoints), authenticate via Keycloak OIDC, and present the same analytics dashboards currently available in the Next.js web frontend -- optimized for mobile form factors.

### Why

- Mobile access for sales managers and field staff who need KPI visibility on the go
- Push-to-refresh data access when away from desktop
- Offline-first design so analytics remain accessible in poor connectivity zones
- Parity with the web dashboard's "midnight-pharma" visual identity

### Success Criteria

- All 8 screens functional with real API data
- Keycloak OIDC login/logout/token-refresh working
- Offline cache serves stale data when network is unavailable
- Dark/Light theme matching the web dashboard
- RTL layout support for Arabic localization
- Pull-to-refresh on every data screen
- Loading skeletons, error states, empty states on every screen
- All financial values formatted as EGP currency
- Min SDK 26, Target SDK 35
- 80%+ unit test coverage on domain + data layers

---

## 2. Architecture Overview

### Clean Architecture Layers

```
┌─────────────────────────────────────────────┐
│              Presentation Layer              │
│  Compose Screens + ViewModels + UI State     │
├─────────────────────────────────────────────┤
│               Domain Layer                   │
│  Use Cases + Repository Interfaces + Models  │
├─────────────────────────────────────────────┤
│                Data Layer                    │
│  Repository Impls + Remote (Ktor) + Local    │
│  (Room) + DataStore + Auth (AppAuth)         │
└─────────────────────────────────────────────┘
```

### Data Flow

```
User Action
    │
    ▼
ViewModel (StateFlow<UiState>)
    │
    ▼
UseCase (suspend fun)
    │
    ▼
Repository (interface in domain, impl in data)
    │
    ├──▶ Remote: KtorApiService ──▶ FastAPI Backend
    │
    └──▶ Local: Room DAO ──▶ SQLite Cache
         │
         ▼
    DataStore (Preferences: theme, auth tokens, last-sync timestamps)
```

### Dependency Injection Graph (Hilt)

```
@Singleton
├── KtorHttpClient (engine + auth interceptor + JSON config)
├── RoomDatabase (datapulse.db)
├── DataStorePreferences
├── AuthManager (AppAuth + token storage)
│
├── RemoteDataSource (uses KtorHttpClient)
├── LocalDataSource (uses Room DAOs)
│
├── AnalyticsRepository (Remote + Local, offline-first)
├── PipelineRepository (Remote + Local)
├── AuthRepository (AuthManager + DataStore)
│
├── GetDashboardUseCase
├── GetTopProductsUseCase
├── GetTopCustomersUseCase
├── GetTopStaffUseCase
├── GetSitesUseCase
├── GetReturnsUseCase
├── GetPipelineRunsUseCase
├── TriggerPipelineUseCase
├── LoginUseCase
└── LogoutUseCase
```

---

## 3. Project Structure

```
android/
├── build.gradle.kts                          # Root build file
├── settings.gradle.kts                       # Module settings
├── gradle.properties                         # Gradle config
├── gradle/
│   └── libs.versions.toml                    # Version catalog
├── app/
│   ├── build.gradle.kts                      # App module build
│   ├── proguard-rules.pro                    # ProGuard rules
│   └── src/
│       ├── main/
│       │   ├── AndroidManifest.xml
│       │   ├── res/
│       │   │   ├── values/
│       │   │   │   ├── strings.xml           # English strings
│       │   │   │   ├── colors.xml            # Brand colors
│       │   │   │   └── themes.xml            # XML theme (for splash)
│       │   │   ├── values-ar/
│       │   │   │   └── strings.xml           # Arabic strings
│       │   │   ├── values-night/
│       │   │   │   └── themes.xml            # Dark theme XML
│       │   │   ├── drawable/
│       │   │   │   └── ic_launcher_foreground.xml
│       │   │   ├── mipmap-*/ (launcher icons)
│       │   │   └── xml/
│       │   │       └── network_security_config.xml
│       │   └── kotlin/
│       │       └── com/datapulse/android/
│       │           ├── DataPulseApp.kt                    # Application class (@HiltAndroidApp)
│       │           ├── MainActivity.kt                    # Single Activity host
│       │           │
│       │           ├── domain/                            # --- DOMAIN LAYER ---
│       │           │   ├── model/
│       │           │   │   ├── KpiSummary.kt              # Domain KPI model
│       │           │   │   ├── TrendResult.kt             # Time series + stats
│       │           │   │   ├── TimeSeriesPoint.kt         # Single data point
│       │           │   │   ├── RankingResult.kt           # Ranked list
│       │           │   │   ├── RankingItem.kt             # Single ranked item
│       │           │   │   ├── ProductPerformance.kt      # Product detail
│       │           │   │   ├── CustomerAnalytics.kt       # Customer detail
│       │           │   │   ├── StaffPerformance.kt        # Staff detail
│       │           │   │   ├── ReturnAnalysis.kt          # Return row
│       │           │   │   ├── PipelineRun.kt             # Pipeline run
│       │           │   │   ├── QualityCheck.kt            # Quality check
│       │           │   │   ├── HealthStatus.kt            # Health check
│       │           │   │   ├── DashboardData.kt           # Composite dashboard
│       │           │   │   ├── FilterOptions.kt           # Filter options
│       │           │   │   └── UserSession.kt             # Auth user info
│       │           │   ├── repository/
│       │           │   │   ├── AnalyticsRepository.kt     # Interface
│       │           │   │   ├── PipelineRepository.kt      # Interface
│       │           │   │   └── AuthRepository.kt          # Interface
│       │           │   └── usecase/
│       │           │       ├── GetDashboardUseCase.kt
│       │           │       ├── GetDailyTrendUseCase.kt
│       │           │       ├── GetMonthlyTrendUseCase.kt
│       │           │       ├── GetTopProductsUseCase.kt
│       │           │       ├── GetTopCustomersUseCase.kt
│       │           │       ├── GetTopStaffUseCase.kt
│       │           │       ├── GetSitesUseCase.kt
│       │           │       ├── GetReturnsUseCase.kt
│       │           │       ├── GetPipelineRunsUseCase.kt
│       │           │       ├── TriggerPipelineUseCase.kt
│       │           │       ├── LoginUseCase.kt
│       │           │       ├── LogoutUseCase.kt
│       │           │       └── GetHealthUseCase.kt
│       │           │
│       │           ├── data/                              # --- DATA LAYER ---
│       │           │   ├── remote/
│       │           │   │   ├── dto/
│       │           │   │   │   ├── KpiSummaryDto.kt
│       │           │   │   │   ├── TrendResultDto.kt
│       │           │   │   │   ├── TimeSeriesPointDto.kt
│       │           │   │   │   ├── RankingResultDto.kt
│       │           │   │   │   ├── RankingItemDto.kt
│       │           │   │   │   ├── ProductPerformanceDto.kt
│       │           │   │   │   ├── CustomerAnalyticsDto.kt
│       │           │   │   │   ├── StaffPerformanceDto.kt
│       │           │   │   │   ├── ReturnAnalysisDto.kt
│       │           │   │   │   ├── PipelineRunDto.kt
│       │           │   │   │   ├── PipelineRunListDto.kt
│       │           │   │   │   ├── QualityCheckDto.kt
│       │           │   │   │   ├── QualityCheckListDto.kt
│       │           │   │   │   ├── TriggerResponseDto.kt
│       │           │   │   │   ├── HealthStatusDto.kt
│       │           │   │   │   ├── DashboardDataDto.kt
│       │           │   │   │   └── FilterOptionsDto.kt
│       │           │   │   ├── ApiService.kt              # Ktor HTTP client wrapper
│       │           │   │   └── AuthInterceptor.kt         # Bearer token injection
│       │           │   ├── local/
│       │           │   │   ├── DataPulseDatabase.kt       # Room database
│       │           │   │   ├── dao/
│       │           │   │   │   ├── KpiDao.kt
│       │           │   │   │   ├── TrendDao.kt
│       │           │   │   │   ├── RankingDao.kt
│       │           │   │   │   ├── PipelineDao.kt
│       │           │   │   │   └── ReturnDao.kt
│       │           │   │   ├── entity/
│       │           │   │   │   ├── KpiEntity.kt
│       │           │   │   │   ├── DailyTrendEntity.kt
│       │           │   │   │   ├── MonthlyTrendEntity.kt
│       │           │   │   │   ├── ProductRankingEntity.kt
│       │           │   │   │   ├── CustomerRankingEntity.kt
│       │           │   │   │   ├── StaffRankingEntity.kt
│       │           │   │   │   ├── SiteRankingEntity.kt
│       │           │   │   │   ├── ReturnEntity.kt
│       │           │   │   │   ├── PipelineRunEntity.kt
│       │           │   │   │   └── CacheMetadata.kt
│       │           │   │   └── converter/
│       │           │   │       └── Converters.kt          # Type converters (Date, BigDecimal, JSON)
│       │           │   ├── mapper/
│       │           │   │   ├── AnalyticsMapper.kt         # DTO <-> Domain <-> Entity
│       │           │   │   └── PipelineMapper.kt          # DTO <-> Domain <-> Entity
│       │           │   ├── repository/
│       │           │   │   ├── AnalyticsRepositoryImpl.kt # Offline-first impl
│       │           │   │   ├── PipelineRepositoryImpl.kt
│       │           │   │   └── AuthRepositoryImpl.kt
│       │           │   ├── auth/
│       │           │   │   ├── AuthManager.kt             # AppAuth wrapper
│       │           │   │   └── TokenStore.kt              # DataStore for tokens
│       │           │   └── preferences/
│       │           │       └── UserPreferences.kt         # DataStore: theme, locale
│       │           │
│       │           ├── presentation/                      # --- PRESENTATION LAYER ---
│       │           │   ├── navigation/
│       │           │   │   ├── NavGraph.kt                # Type-safe Compose Navigation
│       │           │   │   ├── NavRoutes.kt               # Route sealed class
│       │           │   │   └── BottomNavBar.kt            # Bottom navigation bar
│       │           │   ├── theme/
│       │           │   │   ├── Theme.kt                   # Material 3 theme (dark + light)
│       │           │   │   ├── Color.kt                   # Color palette
│       │           │   │   ├── Type.kt                    # Typography
│       │           │   │   └── Shape.kt                   # Shape system
│       │           │   ├── common/
│       │           │   │   ├── UiState.kt                 # Sealed class: Loading/Success/Error/Empty
│       │           │   │   ├── LoadingSkeleton.kt         # Shimmer loading composables
│       │           │   │   ├── ErrorState.kt              # Error with retry button
│       │           │   │   ├── EmptyState.kt              # Empty data illustration
│       │           │   │   ├── PullRefreshWrapper.kt      # Pull-to-refresh container
│       │           │   │   ├── KpiCard.kt                 # Reusable KPI card
│       │           │   │   ├── RankingList.kt             # Reusable ranking list
│       │           │   │   ├── TrendChart.kt              # Vico line/bar chart wrapper
│       │           │   │   ├── StatusBadge.kt             # Pipeline status badge
│       │           │   │   └── HealthIndicator.kt         # Green/amber/red dot
│       │           │   ├── screen/
│       │           │   │   ├── login/
│       │           │   │   │   ├── LoginScreen.kt
│       │           │   │   │   └── LoginViewModel.kt
│       │           │   │   ├── dashboard/
│       │           │   │   │   ├── DashboardScreen.kt
│       │           │   │   │   └── DashboardViewModel.kt
│       │           │   │   ├── products/
│       │           │   │   │   ├── ProductsScreen.kt
│       │           │   │   │   └── ProductsViewModel.kt
│       │           │   │   ├── customers/
│       │           │   │   │   ├── CustomersScreen.kt
│       │           │   │   │   └── CustomersViewModel.kt
│       │           │   │   ├── staff/
│       │           │   │   │   ├── StaffScreen.kt
│       │           │   │   │   └── StaffViewModel.kt
│       │           │   │   ├── sites/
│       │           │   │   │   ├── SitesScreen.kt
│       │           │   │   │   └── SitesViewModel.kt
│       │           │   │   ├── returns/
│       │           │   │   │   ├── ReturnsScreen.kt
│       │           │   │   │   └── ReturnsViewModel.kt
│       │           │   │   └── pipeline/
│       │           │   │       ├── PipelineScreen.kt
│       │           │   │       └── PipelineViewModel.kt
│       │           │   └── util/
│       │           │       ├── Formatters.kt              # EGP currency, percent, compact
│       │           │       └── DateUtils.kt               # Date parsing, presets
│       │           │
│       │           └── di/                                # --- HILT MODULES ---
│       │               ├── NetworkModule.kt               # Ktor client, JSON config
│       │               ├── DatabaseModule.kt              # Room database + DAOs
│       │               ├── RepositoryModule.kt            # Binds interfaces to impls
│       │               ├── AuthModule.kt                  # AppAuth + token storage
│       │               └── PreferencesModule.kt           # DataStore
│       │
│       ├── test/                                          # --- UNIT TESTS ---
│       │   └── kotlin/com/datapulse/android/
│       │       ├── data/
│       │       │   ├── mapper/AnalyticsMapperTest.kt
│       │       │   ├── mapper/PipelineMapperTest.kt
│       │       │   ├── repository/AnalyticsRepositoryImplTest.kt
│       │       │   └── repository/PipelineRepositoryImplTest.kt
│       │       ├── domain/usecase/
│       │       │   ├── GetDashboardUseCaseTest.kt
│       │       │   ├── GetTopProductsUseCaseTest.kt
│       │       │   └── TriggerPipelineUseCaseTest.kt
│       │       └── presentation/
│       │           ├── DashboardViewModelTest.kt
│       │           ├── ProductsViewModelTest.kt
│       │           └── PipelineViewModelTest.kt
│       │
│       └── androidTest/                                   # --- INSTRUMENTED TESTS ---
│           └── kotlin/com/datapulse/android/
│               ├── data/local/
│               │   ├── KpiDaoTest.kt
│               │   └── PipelineDaoTest.kt
│               └── presentation/
│                   ├── LoginScreenTest.kt
│                   ├── DashboardScreenTest.kt
│                   └── NavigationTest.kt
```

---

## 4. Implementation Phases

### Phase 1: Project Scaffold + Build System (Est: 1 day)

**Goal**: Empty Android project that compiles, with all dependencies declared.

| Step | File | Action | Depends On |
|------|------|--------|------------|
| 1.1 | `android/settings.gradle.kts` | Create root settings with `app` module | None |
| 1.2 | `android/build.gradle.kts` | Root build file with plugin declarations (AGP, Kotlin, Hilt, KSP) | None |
| 1.3 | `android/gradle/libs.versions.toml` | Version catalog: all 20+ dependencies | None |
| 1.4 | `android/gradle.properties` | `android.useAndroidX=true`, `kotlin.code.style=official` | None |
| 1.5 | `android/app/build.gradle.kts` | App module: minSdk=26, targetSdk=35, all dependencies, KSP for Room/Hilt | 1.1-1.3 |
| 1.6 | `android/app/src/main/AndroidManifest.xml` | Manifest: internet permission, AppAuth redirect, single activity | 1.5 |
| 1.7 | `android/app/src/main/res/xml/network_security_config.xml` | Allow cleartext for local dev (10.0.2.2) | 1.6 |
| 1.8 | `DataPulseApp.kt` | `@HiltAndroidApp` Application class | 1.5 |
| 1.9 | `MainActivity.kt` | `@AndroidEntryPoint`, `setContent { DataPulseTheme {} }` | 1.8 |
| 1.10 | `.gitignore` | Android-specific ignores (build/, .gradle/, local.properties) | None |

**Version Catalog** (`libs.versions.toml`):

| Library | Version | Key |
|---------|---------|-----|
| AGP | 8.7.3 | agp |
| Kotlin | 2.1.0 | kotlin |
| Compose BOM | 2024.12.01 | compose-bom |
| Material 3 | (from BOM) | material3 |
| Hilt | 2.53.1 | hilt |
| Hilt Navigation Compose | 1.2.0 | hilt-navigation-compose |
| Ktor | 3.0.3 | ktor |
| Kotlinx Serialization | 1.7.3 | kotlinx-serialization |
| Room | 2.6.1 | room |
| DataStore | 1.1.1 | datastore |
| Navigation Compose | 2.8.5 | navigation |
| AppAuth | 0.11.2 | appauth |
| Vico | 2.0.0-beta.2 | vico |
| Coil Compose | 2.7.0 | coil |
| Lifecycle ViewModel Compose | 2.8.7 | lifecycle |
| Coroutines | 1.9.0 | coroutines |
| JUnit 5 | 5.10.3 | junit5 |
| Turbine | 1.2.0 | turbine |
| MockK | 1.13.13 | mockk |

**Risk**: Low. Standard project setup.

---

### Phase 2: Theme + Navigation Shell (Est: 1 day)

**Goal**: App launches with bottom navigation, all 8 screens as placeholder stubs, dark/light theme toggle working.

| Step | File | Action | Depends On |
|------|------|--------|------------|
| 2.1 | `presentation/theme/Color.kt` | Define color palettes matching web CSS tokens | Phase 1 |
| 2.2 | `presentation/theme/Type.kt` | Typography scale (Segoe UI fallback to system) | Phase 1 |
| 2.3 | `presentation/theme/Shape.kt` | Rounded corner shapes (8dp cards, 12dp dialogs) | Phase 1 |
| 2.4 | `presentation/theme/Theme.kt` | `DataPulseTheme` composable with `darkColorScheme` + `lightColorScheme` | 2.1-2.3 |
| 2.5 | `presentation/navigation/NavRoutes.kt` | Sealed class with 8 routes | Phase 1 |
| 2.6 | `presentation/navigation/BottomNavBar.kt` | 4 primary tabs + overflow menu | 2.5 |
| 2.7 | `presentation/navigation/NavGraph.kt` | NavHost with all 8 destinations | 2.5 |
| 2.8 | `presentation/screen/*/Screen.kt` (x8) | Placeholder `Text("Screen Name")` for each | 2.7 |
| 2.9 | `di/PreferencesModule.kt` | DataStore for theme preference | Phase 1 |
| 2.10 | `data/preferences/UserPreferences.kt` | `isDarkMode: Flow<Boolean>` | 2.9 |
| 2.11 | `res/values/strings.xml` | All English strings | None |
| 2.12 | `res/values-ar/strings.xml` | All Arabic strings (RTL) | 2.11 |

**Color Mapping (Web CSS -> Material 3)**:

| Web Token (Dark) | Hex | Material 3 Role |
|------------------|-----|-----------------|
| `--bg-page` | `#0D1117` | `background` |
| `--bg-card` | `#161B22` | `surface` / `surfaceContainer` |
| `--border-color` | `#30363D` | `outline` / `outlineVariant` |
| `--text-primary` | `#E6EDF3` | `onBackground` / `onSurface` |
| `--text-secondary` | `#A8B3BD` | `onSurfaceVariant` |
| `--accent-color` | `#00BFA5` | `primary` |
| `--chart-blue` | `#2196F3` | `tertiary` (chart use) |
| `--chart-amber` | `#FFB300` | Custom `chartAmber` |
| `--growth-green` | `#4CAF50` | Custom `growthGreen` |
| `--growth-red` | `#EF5350` | Custom `growthRed` |

| Web Token (Light) | Hex | Material 3 Role |
|--------------------|-----|-----------------|
| `--bg-page` | `#F6F8FA` | `background` |
| `--bg-card` | `#FFFFFF` | `surface` |
| `--border-color` | `#D0D7DE` | `outline` |
| `--text-primary` | `#1F2328` | `onBackground` |
| `--text-secondary` | `#57606A` | `onSurfaceVariant` |
| `--accent-color` | `#00897B` | `primary` |
| `--chart-blue` | `#1976D2` | `tertiary` |
| `--chart-amber` | `#F9A825` | Custom |
| `--growth-green` | `#2E7D32` | Custom |
| `--growth-red` | `#C62828` | Custom |

**Bottom Navigation Tabs** (4 primary, rest in "More"):

| Tab | Icon | Route |
|-----|------|-------|
| Overview | `Icons.Outlined.Dashboard` | `/dashboard` |
| Products | `Icons.Outlined.Inventory2` | `/products` |
| Customers | `Icons.Outlined.People` | `/customers` |
| More | `Icons.Outlined.MoreHoriz` | Sheet with Staff, Sites, Returns, Pipeline |

**Risk**: Low. No network calls yet.

---

### Phase 3: Networking + Auth (Est: 2 days)

**Goal**: Keycloak OIDC login working, Ktor client configured with auth interceptor, health endpoint responding.

| Step | File | Action | Depends On |
|------|------|--------|------------|
| 3.1 | `di/NetworkModule.kt` | Ktor `HttpClient` with `ContentNegotiation` (JSON), logging, timeout (30s) | Phase 1 |
| 3.2 | `data/remote/dto/*.kt` (18 files) | All DTOs with `@Serializable` annotations | Phase 1 |
| 3.3 | `data/remote/ApiService.kt` | All API call functions using Ktor client | 3.1, 3.2 |
| 3.4 | `di/AuthModule.kt` | AppAuth `AuthorizationService`, config | Phase 1 |
| 3.5 | `data/auth/TokenStore.kt` | DataStore-backed encrypted token storage | 3.4 |
| 3.6 | `data/auth/AuthManager.kt` | AppAuth wrapper: login, logout, refresh, isLoggedIn | 3.4, 3.5 |
| 3.7 | `data/remote/AuthInterceptor.kt` | Ktor plugin: inject Bearer token, handle 401 -> refresh | 3.1, 3.6 |
| 3.8 | `domain/repository/AuthRepository.kt` | Interface: login(), logout(), observeAuth() | None |
| 3.9 | `data/repository/AuthRepositoryImpl.kt` | Implements AuthRepository using AuthManager | 3.6, 3.8 |
| 3.10 | `domain/usecase/LoginUseCase.kt` | Orchestrates OIDC login flow | 3.8 |
| 3.11 | `domain/usecase/LogoutUseCase.kt` | Clears tokens, navigates to login | 3.8 |
| 3.12 | `presentation/screen/login/LoginViewModel.kt` | Login state management | 3.10 |
| 3.13 | `presentation/screen/login/LoginScreen.kt` | Login UI: logo, "Sign in with Keycloak" button | 3.12 |
| 3.14 | `domain/usecase/GetHealthUseCase.kt` | Calls GET /health | 3.3 |
| 3.15 | `presentation/common/HealthIndicator.kt` | Green/amber/red dot composable | 3.14 |
| 3.16 | Update `NavGraph.kt` | Add auth-gated navigation (login vs. main) | 3.9 |
| 3.17 | Keycloak realm update | Add Android redirect URI to `datapulse-frontend` client | None |

**Keycloak OIDC Configuration for Android**:

```
Discovery URL: http://<host>:8081/realms/datapulse/.well-known/openid-configuration
Client ID:     datapulse-frontend  (public client, same as web)
Redirect URI:  com.datapulse.android:/oauth2callback
Scopes:        openid email profile datapulse-scope
PKCE:          S256 (already enabled in realm)
```

**Keycloak Realm Update Required**: Add `com.datapulse.android:/oauth2callback` to the `redirectUris` array in `keycloak/realm-export.json` for the `datapulse-frontend` client.

**Auth Token Flow**:

```
1. User taps "Sign In"
2. AppAuth opens Chrome Custom Tab -> Keycloak login page
3. User enters credentials (demo-admin / admin)
4. Keycloak redirects to com.datapulse.android:/oauth2callback
5. AppAuth exchanges code for tokens (access + refresh + id)
6. Tokens stored in encrypted DataStore
7. Ktor AuthInterceptor reads access_token for every API call
8. On 401: AuthInterceptor uses refresh_token to get new access_token
9. On refresh failure: Navigate to login screen
```

**Risk**: Medium. AppAuth Chrome Custom Tab can be tricky on emulators. Keycloak realm needs the Android redirect URI added.

---

### Phase 4: Domain Models + Room Database + Offline Strategy (Est: 2 days)

**Goal**: Domain models defined, Room database with all entities/DAOs, offline-first repository pattern working.

| Step | File | Action | Depends On |
|------|------|--------|------------|
| 4.1 | `domain/model/*.kt` (14 files) | All domain models as Kotlin data classes | None |
| 4.2 | `data/mapper/AnalyticsMapper.kt` | DTO-to-Domain and Entity-to-Domain mappers | 4.1, 3.2 |
| 4.3 | `data/mapper/PipelineMapper.kt` | Pipeline DTO/Entity/Domain mappers | 4.1, 3.2 |
| 4.4 | `data/local/entity/*.kt` (10 files) | Room entities with `@Entity` annotations | 4.1 |
| 4.5 | `data/local/converter/Converters.kt` | TypeConverters: Date, BigDecimal, JSON maps | 4.4 |
| 4.6 | `data/local/dao/*.kt` (5 files) | Room DAOs with insert/query/delete | 4.4, 4.5 |
| 4.7 | `data/local/DataPulseDatabase.kt` | `@Database` with all entities, version=1 | 4.4-4.6 |
| 4.8 | `di/DatabaseModule.kt` | Hilt module providing Room DB + all DAOs | 4.7 |
| 4.9 | `domain/repository/AnalyticsRepository.kt` | Interface with all analytics methods | 4.1 |
| 4.10 | `domain/repository/PipelineRepository.kt` | Interface with pipeline methods | 4.1 |
| 4.11 | `data/repository/AnalyticsRepositoryImpl.kt` | Offline-first: cache -> network -> update cache | 4.2, 4.6, 3.3, 4.9 |
| 4.12 | `data/repository/PipelineRepositoryImpl.kt` | Offline-first for pipeline data | 4.3, 4.6, 3.3, 4.10 |
| 4.13 | `di/RepositoryModule.kt` | Binds repository interfaces to impls | 4.11, 4.12 |

**Offline-First Strategy**:

```
suspend fun getDashboard(forceRefresh: Boolean = false): Flow<Resource<DashboardData>>
    │
    ├── 1. Emit cached data immediately (if exists and not forceRefresh)
    │      → Query Room, map Entity -> Domain, emit Resource.Success(data, fromCache=true)
    │
    ├── 2. Fetch from network (in background)
    │      → GET /api/v1/analytics/dashboard
    │      → On success: map DTO -> Entity, insert into Room, emit Resource.Success(fresh)
    │      → On failure: emit Resource.Error(exception, cachedData)
    │
    └── 3. Cache metadata
           → Store lastFetchedAt timestamp in CacheMetadata table
           → Stale threshold: 5 minutes (configurable)
```

**Room Entities**:

```kotlin
@Entity(tableName = "kpi_cache")
data class KpiEntity(
    @PrimaryKey val id: Int = 1,  // singleton row
    val todayNet: Double,
    val mtdNet: Double,
    val ytdNet: Double,
    val momGrowthPct: Double?,
    val yoyGrowthPct: Double?,
    val dailyTransactions: Int,
    val dailyCustomers: Int,
    val cachedAt: Long  // System.currentTimeMillis()
)

@Entity(tableName = "daily_trend_cache")
data class DailyTrendEntity(
    @PrimaryKey val period: String,  // "2024-01-15"
    val value: Double,
    val cachedAt: Long
)

@Entity(tableName = "ranking_cache")
data class RankingEntity(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val category: String,  // "product", "customer", "staff", "site"
    val rank: Int,
    val itemKey: Int,
    val name: String,
    val value: Double,
    val pctOfTotal: Double,
    val cachedAt: Long
)

@Entity(tableName = "pipeline_run_cache")
data class PipelineRunEntity(
    @PrimaryKey val id: String,  // UUID
    val tenantId: Int,
    val runType: String,
    val status: String,
    val triggerSource: String?,
    val startedAt: Long,
    val finishedAt: Long?,
    val durationSeconds: Double?,
    val rowsLoaded: Int?,
    val errorMessage: String?,
    val metadataJson: String,  // JSON string
    val cachedAt: Long
)

@Entity(tableName = "cache_metadata")
data class CacheMetadata(
    @PrimaryKey val cacheKey: String,  // e.g. "dashboard", "products", "pipeline_runs"
    val lastFetchedAt: Long,
    val etag: String? = null
)
```

**Risk**: Low. Standard Room + repository pattern.

---

### Phase 5: All Use Cases + All Screens (Est: 4 days)

**Goal**: All 8 screens fully functional with real data, loading/error/empty states, pull-to-refresh.

**Sub-phase 5A: Common Components (Day 1)**

| Step | File | Action |
|------|------|--------|
| 5A.1 | `presentation/common/UiState.kt` | `sealed interface UiState<T> { Loading, Success(data, fromCache), Error(msg, cached), Empty }` |
| 5A.2 | `presentation/common/LoadingSkeleton.kt` | Shimmer effect composables (KPI skeleton, list skeleton, chart skeleton) |
| 5A.3 | `presentation/common/ErrorState.kt` | Error icon + message + "Retry" button |
| 5A.4 | `presentation/common/EmptyState.kt` | Illustration + "No data available" text |
| 5A.5 | `presentation/common/PullRefreshWrapper.kt` | `PullToRefreshBox` wrapper with state binding |
| 5A.6 | `presentation/common/KpiCard.kt` | Card: title, value (EGP), trend arrow + percent, color-coded |
| 5A.7 | `presentation/common/RankingList.kt` | LazyColumn of rank/name/value/percent rows |
| 5A.8 | `presentation/common/TrendChart.kt` | Vico `CartesianChartHost` wrapper (line + bar modes) |
| 5A.9 | `presentation/common/StatusBadge.kt` | Colored chip for pipeline status |
| 5A.10 | `presentation/util/Formatters.kt` | `formatEgp()`, `formatPercent()`, `formatCompact()`, `formatDuration()` |
| 5A.11 | `presentation/util/DateUtils.kt` | `parsePeriod()`, date presets (7d, 30d, 90d, YTD) |

**Sub-phase 5B: Dashboard Screen (Day 1-2)**

| Step | File | Action |
|------|------|--------|
| 5B.1 | `domain/usecase/GetDashboardUseCase.kt` | Calls `analyticsRepository.getDashboard()` |
| 5B.2 | `presentation/screen/dashboard/DashboardViewModel.kt` | Exposes `StateFlow<UiState<DashboardData>>`, pull-to-refresh, health poll |
| 5B.3 | `presentation/screen/dashboard/DashboardScreen.kt` | 7 KPI cards in grid + daily area chart + monthly bar chart |

**Dashboard Screen Layout**:

```
┌──────────────────────────────┐
│  DataPulse        [Health ●] │  <- TopAppBar
├──────────────────────────────┤
│  ┌──────┐ ┌──────┐ ┌──────┐ │
│  │Today │ │ MTD  │ │ YTD  │ │  <- KPI row 1 (EGP values)
│  │Net   │ │ Net  │ │ Net  │ │
│  └──────┘ └──────┘ └──────┘ │
│  ┌──────┐ ┌──────┐ ┌──────┐ │
│  │MoM % │ │YoY % │ │Trans.│ │  <- KPI row 2
│  └──────┘ └──────┘ └──────┘ │
│  ┌──────────────────────────┐│
│  │ Daily Revenue Trend      ││  <- Vico area chart
│  │ ~~~~~~~~~~~~~~~~~~~~~~~~ ││
│  └──────────────────────────┘│
│  ┌──────────────────────────┐│
│  │ Monthly Revenue          ││  <- Vico bar chart
│  │ ████ ████ ████ ████     ││
│  └──────────────────────────┘│
├──────────────────────────────┤
│ Overview│Products│Customers│…│  <- Bottom nav
└──────────────────────────────┘
```

**Sub-phase 5C: Analytics Screens (Day 2-3)**

| Step | File | Action |
|------|------|--------|
| 5C.1 | `domain/usecase/GetTopProductsUseCase.kt` | Calls repository for product rankings |
| 5C.2 | `presentation/screen/products/ProductsViewModel.kt` | Ranking state + filter params |
| 5C.3 | `presentation/screen/products/ProductsScreen.kt` | Horizontal bar chart + ranking table |
| 5C.4 | `domain/usecase/GetTopCustomersUseCase.kt` | Customer rankings |
| 5C.5 | `presentation/screen/customers/CustomersViewModel.kt` | Customer state |
| 5C.6 | `presentation/screen/customers/CustomersScreen.kt` | Chart + table |
| 5C.7 | `domain/usecase/GetTopStaffUseCase.kt` | Staff leaderboard |
| 5C.8 | `presentation/screen/staff/StaffViewModel.kt` | Staff state |
| 5C.9 | `presentation/screen/staff/StaffScreen.kt` | Chart + table |
| 5C.10 | `domain/usecase/GetSitesUseCase.kt` | Site comparison |
| 5C.11 | `presentation/screen/sites/SitesViewModel.kt` | Sites state |
| 5C.12 | `presentation/screen/sites/SitesScreen.kt` | Side-by-side site cards |
| 5C.13 | `domain/usecase/GetReturnsUseCase.kt` | Returns analysis |
| 5C.14 | `presentation/screen/returns/ReturnsViewModel.kt` | Returns state |
| 5C.15 | `presentation/screen/returns/ReturnsScreen.kt` | Returns table (drug, customer, qty, amount, count) |

**Analytics Screen Layout Pattern** (Products/Customers/Staff):

```
┌──────────────────────────────┐
│  < Products                  │  <- TopAppBar with title
├──────────────────────────────┤
│  Total: EGP 12.5M            │  <- Summary stat
│  ┌──────────────────────────┐│
│  │ ████████████████   Drug A ││  <- Horizontal bar chart (top 10)
│  │ ████████████      Drug B ││
│  │ ████████          Drug C ││
│  └──────────────────────────┘│
│  ┌──┬────────┬───────┬─────┐│
│  │# │ Name   │Revenue│  %  ││  <- Ranking table
│  ├──┼────────┼───────┼─────┤│
│  │1 │Drug A  │ 2.1M  │17.2%││
│  │2 │Drug B  │ 1.8M  │14.5%││
│  │3 │Drug C  │ 1.2M  │ 9.8%││
│  └──┴────────┴───────┴─────┘│
└──────────────────────────────┘
```

**Sub-phase 5D: Pipeline Screen (Day 3-4)**

| Step | File | Action |
|------|------|--------|
| 5D.1 | `domain/usecase/GetPipelineRunsUseCase.kt` | Paginated pipeline runs |
| 5D.2 | `domain/usecase/TriggerPipelineUseCase.kt` | POST /pipeline/trigger |
| 5D.3 | `presentation/screen/pipeline/PipelineViewModel.kt` | Runs list + trigger state + SSE for live updates |
| 5D.4 | `presentation/screen/pipeline/PipelineScreen.kt` | Latest run card + history list + trigger FAB |

**Pipeline Screen Layout**:

```
┌──────────────────────────────┐
│  < Pipeline                  │
├──────────────────────────────┤
│  ┌──────────────────────────┐│
│  │ Latest Run               ││
│  │ Status: ● Success        ││  <- StatusBadge
│  │ Type: full               ││
│  │ Duration: 2m 34s         ││
│  │ Rows: 1,134,073          ││
│  │ Started: 30 Mar 14:22    ││
│  └──────────────────────────┘│
│                               │
│  Run History                  │
│  ┌──────────────────────────┐│
│  │ #abc123  full  ● success ││
│  │ 30 Mar 14:22   2m 34s   ││
│  ├──────────────────────────┤│
│  │ #def456  full  ● failed  ││
│  │ 29 Mar 09:15   0m 12s   ││
│  └──────────────────────────┘│
│                          [▶] │  <- Trigger FAB (admin only)
└──────────────────────────────┘
```

**Risk**: Medium. Vico chart library has a learning curve. The pipeline trigger FAB should only be visible to users with the `admin` role (extracted from JWT claims).

---

### Phase 6: Keycloak Realm Update + Docker Integration (Est: 0.5 day)

**Goal**: Android app works end-to-end with the Docker stack.

| Step | File | Action | Depends On |
|------|------|--------|------------|
| 6.1 | `keycloak/realm-export.json` | Add `com.datapulse.android:/oauth2callback` to `redirectUris` | Phase 3 |
| 6.2 | `android/app/src/main/res/values/strings.xml` | Add configurable `api_base_url` and `keycloak_url` | Phase 2 |
| 6.3 | `android/app/build.gradle.kts` | Add `buildConfigField` for API_BASE_URL per build type | Phase 1 |
| 6.4 | `android/app/src/debug/res/xml/network_security_config.xml` | Allow cleartext for `10.0.2.2` (emulator -> host) | Phase 1 |
| 6.5 | Update `CLAUDE.md` | Document Android app in project structure | All phases |

**Build Config Fields**:

```kotlin
// debug
buildConfigField("String", "API_BASE_URL", "\"http://10.0.2.2:8000\"")
buildConfigField("String", "KEYCLOAK_URL", "\"http://10.0.2.2:8081/realms/datapulse\"")

// release
buildConfigField("String", "API_BASE_URL", "\"https://api.datapulse.example.com\"")
buildConfigField("String", "KEYCLOAK_URL", "\"https://auth.datapulse.example.com/realms/datapulse\"")
```

**Risk**: Low.

---

### Phase 7: Testing (Est: 2 days)

**Goal**: 80%+ coverage on domain + data layers, key UI tests.

| Step | File | Action |
|------|------|--------|
| 7.1 | `test/.../mapper/AnalyticsMapperTest.kt` | Test DTO -> Domain, Entity -> Domain, Domain -> Entity mappings |
| 7.2 | `test/.../mapper/PipelineMapperTest.kt` | Pipeline mapper tests |
| 7.3 | `test/.../repository/AnalyticsRepositoryImplTest.kt` | Mock ApiService + DAO, verify offline-first logic |
| 7.4 | `test/.../repository/PipelineRepositoryImplTest.kt` | Mock pipeline API + DAO |
| 7.5 | `test/.../usecase/GetDashboardUseCaseTest.kt` | Happy path + error + empty |
| 7.6 | `test/.../usecase/GetTopProductsUseCaseTest.kt` | Ranking use case test |
| 7.7 | `test/.../usecase/TriggerPipelineUseCaseTest.kt` | Trigger + error handling |
| 7.8 | `test/.../DashboardViewModelTest.kt` | ViewModel state transitions (Turbine) |
| 7.9 | `test/.../ProductsViewModelTest.kt` | Products ViewModel test |
| 7.10 | `test/.../PipelineViewModelTest.kt` | Pipeline ViewModel test |
| 7.11 | `androidTest/.../KpiDaoTest.kt` | Room DAO insert/query/delete |
| 7.12 | `androidTest/.../PipelineDaoTest.kt` | Pipeline DAO tests |
| 7.13 | `androidTest/.../LoginScreenTest.kt` | Compose UI test: login button visible |
| 7.14 | `androidTest/.../DashboardScreenTest.kt` | KPI cards render with test data |
| 7.15 | `androidTest/.../NavigationTest.kt` | Bottom nav navigates correctly |

**Testing Stack**:

| Layer | Framework | What |
|-------|-----------|------|
| Unit (domain) | JUnit 5 + MockK | Use cases, mappers |
| Unit (presentation) | JUnit 5 + MockK + Turbine | ViewModels (StateFlow testing) |
| Integration (data) | JUnit 5 + Room in-memory DB | DAOs |
| UI | Compose UI Test + Espresso | Screens, navigation |

**Risk**: Low. Well-established testing patterns.

---

### Phase 8: Polish + Release Prep (Est: 1 day)

**Goal**: Production-ready polish.

| Step | File | Action |
|------|------|--------|
| 8.1 | `app/proguard-rules.pro` | ProGuard rules for Ktor, Kotlinx Serialization, AppAuth |
| 8.2 | Launcher icons | Adaptive icon with DataPulse branding |
| 8.3 | Splash screen | `SplashScreen` API (Android 12+) with fallback |
| 8.4 | `res/values/themes.xml` | Splash theme matching brand colors |
| 8.5 | Analytics screen filters | Date range picker (Material 3 DateRangePicker) |
| 8.6 | Accessibility | ContentDescription on all icons, minimum touch targets 48dp |
| 8.7 | Edge-to-edge | `enableEdgeToEdge()` with proper insets handling |
| 8.8 | Animations | Shared element transitions between list -> detail |

**Risk**: Low.

---

## 5. Data Models

### Domain Models (Kotlin)

```kotlin
// domain/model/KpiSummary.kt
data class KpiSummary(
    val todayNet: Double,
    val mtdNet: Double,
    val ytdNet: Double,
    val momGrowthPct: Double?,
    val yoyGrowthPct: Double?,
    val dailyTransactions: Int,
    val dailyCustomers: Int,
)

// domain/model/TimeSeriesPoint.kt
data class TimeSeriesPoint(
    val period: String,    // "2024-01" or "2024-01-15"
    val value: Double,
)

// domain/model/TrendResult.kt
data class TrendResult(
    val points: List<TimeSeriesPoint>,
    val total: Double,
    val average: Double,
    val minimum: Double,
    val maximum: Double,
    val growthPct: Double?,
)

// domain/model/RankingItem.kt
data class RankingItem(
    val rank: Int,
    val key: Int,
    val name: String,
    val value: Double,
    val pctOfTotal: Double,
)

// domain/model/RankingResult.kt
data class RankingResult(
    val items: List<RankingItem>,
    val total: Double,
)

// domain/model/DashboardData.kt
data class DashboardData(
    val kpi: KpiSummary,
    val dailyTrend: TrendResult,
    val monthlyTrend: TrendResult,
    val topProducts: RankingResult,
    val topCustomers: RankingResult,
    val topStaff: RankingResult,
    val filterOptions: FilterOptions,
)

// domain/model/ReturnAnalysis.kt
data class ReturnAnalysis(
    val drugName: String,
    val customerName: String,
    val returnQuantity: Double,
    val returnAmount: Double,
    val returnCount: Int,
)

// domain/model/PipelineRun.kt
data class PipelineRun(
    val id: String,            // UUID as string
    val tenantId: Int,
    val runType: String,       // "full", "bronze", "staging", "marts"
    val status: String,        // "pending", "running", "success", "failed", etc.
    val triggerSource: String?,
    val startedAt: Long,       // epoch millis
    val finishedAt: Long?,
    val durationSeconds: Double?,
    val rowsLoaded: Int?,
    val errorMessage: String?,
    val metadata: Map<String, String>,
)

// domain/model/QualityCheck.kt
data class QualityCheck(
    val id: Int,
    val pipelineRunId: String,
    val checkName: String,
    val stage: String,
    val severity: String,
    val passed: Boolean,
    val message: String?,
    val checkedAt: Long,
)

// domain/model/HealthStatus.kt
data class HealthStatus(
    val status: String,        // "ok" or "degraded"
    val db: String,            // "connected" or "disconnected"
)

// domain/model/FilterOptions.kt
data class FilterOptions(
    val categories: List<String>,
    val brands: List<String>,
    val sites: List<FilterOption>,
    val staff: List<FilterOption>,
)

data class FilterOption(
    val key: Int,
    val label: String,
)

// domain/model/UserSession.kt
data class UserSession(
    val sub: String,
    val email: String,
    val preferredUsername: String,
    val tenantId: String,
    val roles: List<String>,
    val isAdmin: Boolean = roles.contains("admin"),
)
```

### Remote DTOs (Kotlinx Serialization)

```kotlin
// data/remote/dto/KpiSummaryDto.kt
@Serializable
data class KpiSummaryDto(
    @SerialName("today_net") val todayNet: Double,
    @SerialName("mtd_net") val mtdNet: Double,
    @SerialName("ytd_net") val ytdNet: Double,
    @SerialName("mom_growth_pct") val momGrowthPct: Double? = null,
    @SerialName("yoy_growth_pct") val yoyGrowthPct: Double? = null,
    @SerialName("daily_transactions") val dailyTransactions: Int,
    @SerialName("daily_customers") val dailyCustomers: Int,
)

// data/remote/dto/PipelineRunDto.kt
@Serializable
data class PipelineRunDto(
    val id: String,
    @SerialName("tenant_id") val tenantId: Int,
    @SerialName("run_type") val runType: String,
    val status: String,
    @SerialName("trigger_source") val triggerSource: String? = null,
    @SerialName("started_at") val startedAt: String,      // ISO datetime
    @SerialName("finished_at") val finishedAt: String? = null,
    @SerialName("duration_seconds") val durationSeconds: Double? = null,
    @SerialName("rows_loaded") val rowsLoaded: Int? = null,
    @SerialName("error_message") val errorMessage: String? = null,
    val metadata: Map<String, String> = emptyMap(),
)

// ... (all other DTOs follow the same pattern: @Serializable + @SerialName for snake_case)
```

---

## 6. Screen Designs

### Screen 1: Login

| Element | Component | Details |
|---------|-----------|---------|
| Logo | `Image` | DataPulse logo centered |
| App name | `Text` | "DataPulse" in accent color |
| Subtitle | `Text` | "Business Analytics" |
| Sign in button | `Button` | "Sign in with Keycloak", launches Chrome Custom Tab |
| Error banner | `Snackbar` | Shows on auth failure |
| Loading | `CircularProgressIndicator` | During token exchange |

### Screen 2: Dashboard

| Element | Component | Details |
|---------|-----------|---------|
| Health dot | `HealthIndicator` | TopAppBar trailing icon |
| KPI grid | `LazyVerticalGrid(2 cols)` | 7 KpiCards (todayNet, mtdNet, ytdNet, MoM%, YoY%, transactions, customers) |
| Daily chart | `TrendChart(mode=Line)` | Vico area chart with accent color fill |
| Monthly chart | `TrendChart(mode=Bar)` | Vico grouped bar chart |
| Pull-to-refresh | `PullRefreshWrapper` | Triggers `viewModel.refresh()` |

### Screen 3: Products

| Element | Component | Details |
|---------|-----------|---------|
| Summary card | `Card` | "Total Revenue: EGP X.XM" |
| Bar chart | Vico `HorizontalBarChart` | Top 10 products, accent gradient |
| Ranking table | `RankingList` | # / Name / Revenue / % of total |

### Screen 4: Customers

Same layout as Products, but with customer data (customer_name, net_amount, transaction_count).

### Screen 5: Staff

Same layout as Products, but with staff data. Additional column: position.

### Screen 6: Sites

| Element | Component | Details |
|---------|-----------|---------|
| Site cards | `Row` of 2 `Card`s | Side-by-side comparison (matching web layout) |
| Each card | `Column` | Site name, revenue, orders, customers |

### Screen 7: Returns

| Element | Component | Details |
|---------|-----------|---------|
| Table header | `Row` | Drug / Customer / Qty / Amount / Count |
| Table rows | `LazyColumn` | Scrollable return rows |
| Sort | Tap column header | Sort by amount (default), qty, count |

### Screen 8: Pipeline

| Element | Component | Details |
|---------|-----------|---------|
| Latest run card | `ElevatedCard` | Status badge, type, duration, rows, started time |
| Run history | `LazyColumn` | List of past runs with status badges |
| Trigger FAB | `ExtendedFloatingActionButton` | "Run Pipeline" (admin only, hidden for viewer role) |
| Confirmation | `AlertDialog` | "Trigger full pipeline?" with confirm/cancel |

---

## 7. Keycloak Integration

### Configuration

```kotlin
// data/auth/AuthManager.kt

private val serviceConfig = AuthorizationServiceConfiguration(
    Uri.parse("${BuildConfig.KEYCLOAK_URL}/protocol/openid-connect/auth"),   // authEndpoint
    Uri.parse("${BuildConfig.KEYCLOAK_URL}/protocol/openid-connect/token"),  // tokenEndpoint
    null,  // registrationEndpoint
    Uri.parse("${BuildConfig.KEYCLOAK_URL}/protocol/openid-connect/logout"), // endSessionEndpoint
)

private val authRequest = AuthorizationRequest.Builder(
    serviceConfig,
    "datapulse-frontend",                              // clientId (public)
    ResponseTypeValues.CODE,                           // authorization code flow
    Uri.parse("com.datapulse.android:/oauth2callback") // redirectUri
)
    .setScope("openid email profile")
    .setCodeVerifier(CodeVerifierUtil.generateRandomCodeVerifier())  // PKCE S256
    .build()
```

### AndroidManifest.xml (redirect handler)

```xml
<activity android:name="net.openid.appauth.RedirectUriReceiverActivity"
    android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data android:scheme="com.datapulse.android" android:host="oauth2callback" />
    </intent-filter>
</activity>
```

### Token Refresh

```kotlin
// data/remote/AuthInterceptor.kt (Ktor HttpClient plugin)
install(Auth) {
    bearer {
        loadTokens {
            val access = tokenStore.getAccessToken()
            val refresh = tokenStore.getRefreshToken()
            if (access != null) BearerTokens(access, refresh ?: "") else null
        }
        refreshTokens {
            val newTokens = authManager.refreshToken()
            if (newTokens != null) {
                tokenStore.saveTokens(newTokens.accessToken, newTokens.refreshToken)
                BearerTokens(newTokens.accessToken, newTokens.refreshToken ?: "")
            } else {
                // Refresh failed — signal logout
                authManager.signOut()
                null
            }
        }
    }
}
```

### Role Extraction

```kotlin
// After successful auth, decode the access token JWT payload:
fun extractUserSession(accessToken: String): UserSession {
    val payload = decodeJwtPayload(accessToken)  // base64 decode, no verification
    val realmAccess = payload["realm_access"] as? Map<*, *>
    val roles = (realmAccess?.get("roles") as? List<*>)?.map { it.toString() } ?: emptyList()
    return UserSession(
        sub = payload["sub"] as? String ?: "",
        email = payload["email"] as? String ?: "",
        preferredUsername = payload["preferred_username"] as? String ?: "",
        tenantId = payload["tenant_id"] as? String ?: "1",
        roles = roles,
    )
}
```

---

## 8. Offline Strategy

### Cache Invalidation Rules

| Data Type | Stale After | Evict After | Reason |
|-----------|-------------|-------------|--------|
| KPI Summary | 5 min | 24 hours | Changes with each transaction |
| Daily Trend | 15 min | 7 days | Relatively stable within day |
| Monthly Trend | 1 hour | 30 days | Changes once per day |
| Rankings (all) | 15 min | 7 days | Moderate volatility |
| Returns | 15 min | 7 days | Similar to rankings |
| Pipeline Runs | 30 sec | 7 days | Needs near-real-time during execution |
| Quality Checks | 5 min | 7 days | Static once written |
| Health Status | Never cached | N/A | Always fresh |

### Offline-First Flow (Resource pattern)

```kotlin
sealed class Resource<T> {
    data class Loading<T>(val cached: T? = null) : Resource<T>()
    data class Success<T>(val data: T, val fromCache: Boolean = false) : Resource<T>()
    data class Error<T>(val message: String, val cached: T? = null) : Resource<T>()
}

// In AnalyticsRepositoryImpl:
override fun getDashboard(forceRefresh: Boolean): Flow<Resource<DashboardData>> = flow {
    // 1. Emit cache immediately
    val cached = loadFromCache()
    if (cached != null && !forceRefresh) {
        emit(Resource.Success(cached, fromCache = true))
    } else {
        emit(Resource.Loading(cached))
    }

    // 2. Try network
    try {
        val fresh = apiService.getDashboard()
        val domain = mapper.toDomain(fresh)
        saveToCache(domain)
        emit(Resource.Success(domain, fromCache = false))
    } catch (e: Exception) {
        if (cached != null) {
            emit(Resource.Error(e.message ?: "Network error", cached))
        } else {
            emit(Resource.Error(e.message ?: "Network error"))
        }
    }
}
```

### Cache Eviction

```kotlin
// In DataPulseDatabase companion:
suspend fun evictStaleCache(db: DataPulseDatabase) {
    val now = System.currentTimeMillis()
    val oneDayAgo = now - 24 * 60 * 60 * 1000
    val sevenDaysAgo = now - 7 * 24 * 60 * 60 * 1000

    db.kpiDao().deleteOlderThan(oneDayAgo)
    db.trendDao().deleteOlderThan(sevenDaysAgo)
    db.rankingDao().deleteOlderThan(sevenDaysAgo)
    db.pipelineDao().deleteOlderThan(sevenDaysAgo)
    db.returnDao().deleteOlderThan(sevenDaysAgo)
}
```

---

## 9. Theme System

### Color.kt

```kotlin
package com.datapulse.android.presentation.theme

import androidx.compose.ui.graphics.Color

// --- Dark palette (midnight-pharma) ---
val DarkBackground       = Color(0xFF0D1117)
val DarkSurface          = Color(0xFF161B22)
val DarkBorder           = Color(0xFF30363D)
val DarkDivider          = Color(0xFF21262D)
val DarkOnBackground     = Color(0xFFE6EDF3)
val DarkOnSurfaceVariant = Color(0xFFA8B3BD)
val DarkAccent           = Color(0xFF00BFA5)
val DarkChartBlue        = Color(0xFF2196F3)
val DarkChartAmber       = Color(0xFFFFB300)
val DarkGrowthGreen      = Color(0xFF4CAF50)
val DarkGrowthRed        = Color(0xFFEF5350)

// --- Light palette ---
val LightBackground       = Color(0xFFF6F8FA)
val LightSurface          = Color(0xFFFFFFFF)
val LightBorder           = Color(0xFFD0D7DE)
val LightDivider          = Color(0xFFD8DEE4)
val LightOnBackground     = Color(0xFF1F2328)
val LightOnSurfaceVariant = Color(0xFF57606A)
val LightAccent           = Color(0xFF00897B)
val LightChartBlue        = Color(0xFF1976D2)
val LightChartAmber       = Color(0xFFF9A825)
val LightGrowthGreen      = Color(0xFF2E7D32)
val LightGrowthRed        = Color(0xFFC62828)
```

### Theme.kt

```kotlin
@Composable
fun DataPulseTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val colorScheme = if (darkTheme) {
        darkColorScheme(
            background = DarkBackground,
            surface = DarkSurface,
            surfaceVariant = DarkSurface,
            surfaceContainer = DarkSurface,
            onBackground = DarkOnBackground,
            onSurface = DarkOnBackground,
            onSurfaceVariant = DarkOnSurfaceVariant,
            primary = DarkAccent,
            onPrimary = DarkBackground,
            tertiary = DarkChartBlue,
            outline = DarkBorder,
            outlineVariant = DarkDivider,
        )
    } else {
        lightColorScheme(
            background = LightBackground,
            surface = LightSurface,
            surfaceVariant = LightSurface,
            surfaceContainer = LightSurface,
            onBackground = LightOnBackground,
            onSurface = LightOnBackground,
            onSurfaceVariant = LightOnSurfaceVariant,
            primary = LightAccent,
            onPrimary = LightSurface,
            tertiary = LightChartBlue,
            outline = LightBorder,
            outlineVariant = LightDivider,
        )
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = DataPulseTypography,
        shapes = DataPulseShapes,
        content = content,
    )
}
```

### Custom Theme Extensions

```kotlin
// For colors not in Material 3 (chart amber, growth green/red):
data class DataPulseColors(
    val chartAmber: Color,
    val growthGreen: Color,
    val growthRed: Color,
    val chartBlue: Color,
)

val LocalDataPulseColors = staticCompositionLocalOf {
    DataPulseColors(
        chartAmber = DarkChartAmber,
        growthGreen = DarkGrowthGreen,
        growthRed = DarkGrowthRed,
        chartBlue = DarkChartBlue,
    )
}

// Access in composables:
val colors = LocalDataPulseColors.current
// colors.growthGreen, colors.growthRed, colors.chartAmber
```

---

## 10. Testing Strategy

### Unit Tests (JUnit 5 + MockK)

| Test File | What It Covers | Key Assertions |
|-----------|---------------|----------------|
| `AnalyticsMapperTest` | DTO -> Domain, Entity -> Domain | Field mapping, null handling, empty lists |
| `PipelineMapperTest` | Pipeline DTO/Entity/Domain | Date parsing, status mapping |
| `AnalyticsRepositoryImplTest` | Offline-first flow | Cache hit returns cached, network updates cache, network error returns cached |
| `PipelineRepositoryImplTest` | Pipeline repo | Same offline-first pattern |
| `GetDashboardUseCaseTest` | Use case orchestration | Calls repo, returns correct Resource |
| `TriggerPipelineUseCaseTest` | Pipeline trigger | Success -> TriggerResponse, error -> Resource.Error |
| `DashboardViewModelTest` | StateFlow transitions | Loading -> Success, Loading -> Error, refresh triggers fetch |
| `ProductsViewModelTest` | Products VM | Ranking loaded, empty state |
| `PipelineViewModelTest` | Pipeline VM | Runs list, trigger confirmation, admin check |

### Instrumented Tests (Room + Compose UI)

| Test File | What It Covers |
|-----------|---------------|
| `KpiDaoTest` | Insert, query, delete, cachedAt filter |
| `PipelineDaoTest` | Insert run, query by status, pagination |
| `LoginScreenTest` | Sign-in button visible, loading state |
| `DashboardScreenTest` | 7 KPI cards rendered with test data |
| `NavigationTest` | Bottom nav clicks navigate to correct screens |

### Coverage Target

| Layer | Target | How |
|-------|--------|-----|
| Domain (use cases) | 90%+ | Pure Kotlin, easy to test |
| Data (mappers, repos) | 85%+ | MockK for API/DAO |
| Presentation (ViewModels) | 80%+ | Turbine for Flow testing |
| Presentation (Compose UI) | 60%+ | Compose UI tests on key screens |
| **Overall** | **80%+** | `koverReport` Gradle task |

---

## 11. Risks & Mitigations

| # | Risk | Severity | Likelihood | Mitigation |
|---|------|----------|------------|------------|
| 1 | AppAuth Chrome Custom Tab fails on emulators without Google Play Services | HIGH | MEDIUM | Test on physical device; document minimum emulator image requirement (Google APIs) |
| 2 | Keycloak `datapulse-frontend` is a public client -- no client_secret -- may need a separate Android client | MEDIUM | LOW | Current public client with PKCE is the correct pattern for mobile. No separate client needed. Just add the Android redirect URI. |
| 3 | Vico charting library is in beta (2.0.0-beta) | MEDIUM | MEDIUM | Pin exact version; wrap in `TrendChart` abstraction so Vico can be swapped if needed |
| 4 | Room schema migrations when adding new entities | MEDIUM | HIGH (over time) | Use `fallbackToDestructiveMigration()` for cache DB (data is re-fetchable); document proper migration path for production |
| 5 | Large dataset in rankings (17K+ products) may cause list performance issues | MEDIUM | LOW | API already limits to top 10-100 via `limit` param. Use `LazyColumn` with keys. |
| 6 | Token refresh race condition -- multiple requests trigger simultaneous refreshes | MEDIUM | MEDIUM | Ktor's built-in `Auth` plugin handles mutual exclusion on refresh. Verify in integration tests. |
| 7 | Offline-first with stale data may confuse users | LOW | MEDIUM | Show "Last updated X min ago" banner when data is from cache. Distinguish cached vs fresh in UI. |
| 8 | Backend API running on `localhost` is not reachable from Android emulator directly | HIGH | HIGH | Use `10.0.2.2` (emulator host alias) in debug builds. Document in README. |
| 9 | EGP currency not available on all Android locales | LOW | LOW | Use explicit `Locale("en", "EG")` or manual "EGP" prefix formatting |
| 10 | Kotlinx Serialization strict mode rejects unknown JSON fields from API updates | MEDIUM | MEDIUM | Configure `Json { ignoreUnknownKeys = true }` |

---

## 12. Phase-by-Phase File List

### Phase 1 (10 files)

```
android/settings.gradle.kts
android/build.gradle.kts
android/gradle.properties
android/gradle/libs.versions.toml
android/app/build.gradle.kts
android/app/proguard-rules.pro
android/app/src/main/AndroidManifest.xml
android/app/src/main/res/xml/network_security_config.xml
android/app/src/main/kotlin/com/datapulse/android/DataPulseApp.kt
android/app/src/main/kotlin/com/datapulse/android/MainActivity.kt
android/.gitignore
```

### Phase 2 (14 files)

```
.../presentation/theme/Color.kt
.../presentation/theme/Type.kt
.../presentation/theme/Shape.kt
.../presentation/theme/Theme.kt
.../presentation/navigation/NavRoutes.kt
.../presentation/navigation/BottomNavBar.kt
.../presentation/navigation/NavGraph.kt
.../presentation/screen/login/LoginScreen.kt          (stub)
.../presentation/screen/dashboard/DashboardScreen.kt   (stub)
.../presentation/screen/products/ProductsScreen.kt     (stub)
.../presentation/screen/customers/CustomersScreen.kt   (stub)
.../presentation/screen/staff/StaffScreen.kt           (stub)
.../presentation/screen/sites/SitesScreen.kt           (stub)
.../presentation/screen/returns/ReturnsScreen.kt       (stub)
.../presentation/screen/pipeline/PipelineScreen.kt     (stub)
.../di/PreferencesModule.kt
.../data/preferences/UserPreferences.kt
.../res/values/strings.xml
.../res/values-ar/strings.xml
```

### Phase 3 (17 files)

```
.../di/NetworkModule.kt
.../di/AuthModule.kt
.../data/remote/dto/KpiSummaryDto.kt
.../data/remote/dto/TrendResultDto.kt
.../data/remote/dto/TimeSeriesPointDto.kt
.../data/remote/dto/RankingResultDto.kt
.../data/remote/dto/RankingItemDto.kt
.../data/remote/dto/ProductPerformanceDto.kt
.../data/remote/dto/CustomerAnalyticsDto.kt
.../data/remote/dto/StaffPerformanceDto.kt
.../data/remote/dto/ReturnAnalysisDto.kt
.../data/remote/dto/PipelineRunDto.kt
.../data/remote/dto/PipelineRunListDto.kt
.../data/remote/dto/QualityCheckDto.kt
.../data/remote/dto/QualityCheckListDto.kt
.../data/remote/dto/TriggerResponseDto.kt
.../data/remote/dto/HealthStatusDto.kt
.../data/remote/dto/DashboardDataDto.kt
.../data/remote/dto/FilterOptionsDto.kt
.../data/remote/ApiService.kt
.../data/remote/AuthInterceptor.kt
.../data/auth/AuthManager.kt
.../data/auth/TokenStore.kt
.../domain/repository/AuthRepository.kt
.../data/repository/AuthRepositoryImpl.kt
.../domain/usecase/LoginUseCase.kt
.../domain/usecase/LogoutUseCase.kt
.../presentation/screen/login/LoginViewModel.kt
.../presentation/screen/login/LoginScreen.kt           (real)
.../domain/usecase/GetHealthUseCase.kt
.../presentation/common/HealthIndicator.kt
```

### Phase 4 (28 files)

```
.../domain/model/KpiSummary.kt
.../domain/model/TimeSeriesPoint.kt
.../domain/model/TrendResult.kt
.../domain/model/RankingItem.kt
.../domain/model/RankingResult.kt
.../domain/model/DashboardData.kt
.../domain/model/ProductPerformance.kt
.../domain/model/CustomerAnalytics.kt
.../domain/model/StaffPerformance.kt
.../domain/model/ReturnAnalysis.kt
.../domain/model/PipelineRun.kt
.../domain/model/QualityCheck.kt
.../domain/model/HealthStatus.kt
.../domain/model/FilterOptions.kt
.../domain/model/UserSession.kt
.../data/local/entity/KpiEntity.kt
.../data/local/entity/DailyTrendEntity.kt
.../data/local/entity/MonthlyTrendEntity.kt
.../data/local/entity/ProductRankingEntity.kt
.../data/local/entity/CustomerRankingEntity.kt
.../data/local/entity/StaffRankingEntity.kt
.../data/local/entity/SiteRankingEntity.kt
.../data/local/entity/ReturnEntity.kt
.../data/local/entity/PipelineRunEntity.kt
.../data/local/entity/CacheMetadata.kt
.../data/local/converter/Converters.kt
.../data/local/dao/KpiDao.kt
.../data/local/dao/TrendDao.kt
.../data/local/dao/RankingDao.kt
.../data/local/dao/PipelineDao.kt
.../data/local/dao/ReturnDao.kt
.../data/local/DataPulseDatabase.kt
.../di/DatabaseModule.kt
.../data/mapper/AnalyticsMapper.kt
.../data/mapper/PipelineMapper.kt
.../domain/repository/AnalyticsRepository.kt
.../domain/repository/PipelineRepository.kt
.../data/repository/AnalyticsRepositoryImpl.kt
.../data/repository/PipelineRepositoryImpl.kt
.../di/RepositoryModule.kt
```

### Phase 5 (30 files)

```
.../presentation/common/UiState.kt
.../presentation/common/LoadingSkeleton.kt
.../presentation/common/ErrorState.kt
.../presentation/common/EmptyState.kt
.../presentation/common/PullRefreshWrapper.kt
.../presentation/common/KpiCard.kt
.../presentation/common/RankingList.kt
.../presentation/common/TrendChart.kt
.../presentation/common/StatusBadge.kt
.../presentation/util/Formatters.kt
.../presentation/util/DateUtils.kt
.../domain/usecase/GetDashboardUseCase.kt
.../domain/usecase/GetDailyTrendUseCase.kt
.../domain/usecase/GetMonthlyTrendUseCase.kt
.../domain/usecase/GetTopProductsUseCase.kt
.../domain/usecase/GetTopCustomersUseCase.kt
.../domain/usecase/GetTopStaffUseCase.kt
.../domain/usecase/GetSitesUseCase.kt
.../domain/usecase/GetReturnsUseCase.kt
.../domain/usecase/GetPipelineRunsUseCase.kt
.../domain/usecase/TriggerPipelineUseCase.kt
.../presentation/screen/dashboard/DashboardViewModel.kt
.../presentation/screen/dashboard/DashboardScreen.kt     (real)
.../presentation/screen/products/ProductsViewModel.kt
.../presentation/screen/products/ProductsScreen.kt       (real)
.../presentation/screen/customers/CustomersViewModel.kt
.../presentation/screen/customers/CustomersScreen.kt     (real)
.../presentation/screen/staff/StaffViewModel.kt
.../presentation/screen/staff/StaffScreen.kt             (real)
.../presentation/screen/sites/SitesViewModel.kt
.../presentation/screen/sites/SitesScreen.kt             (real)
.../presentation/screen/returns/ReturnsViewModel.kt
.../presentation/screen/returns/ReturnsScreen.kt         (real)
.../presentation/screen/pipeline/PipelineViewModel.kt
.../presentation/screen/pipeline/PipelineScreen.kt       (real)
```

### Phase 6 (3 files modified)

```
keycloak/realm-export.json                               (MODIFIED: add Android redirect URI)
android/app/build.gradle.kts                             (MODIFIED: buildConfigField)
CLAUDE.md                                                (MODIFIED: document Android app)
```

### Phase 7 (15 test files)

```
.../test/.../mapper/AnalyticsMapperTest.kt
.../test/.../mapper/PipelineMapperTest.kt
.../test/.../repository/AnalyticsRepositoryImplTest.kt
.../test/.../repository/PipelineRepositoryImplTest.kt
.../test/.../usecase/GetDashboardUseCaseTest.kt
.../test/.../usecase/GetTopProductsUseCaseTest.kt
.../test/.../usecase/TriggerPipelineUseCaseTest.kt
.../test/.../DashboardViewModelTest.kt
.../test/.../ProductsViewModelTest.kt
.../test/.../PipelineViewModelTest.kt
.../androidTest/.../KpiDaoTest.kt
.../androidTest/.../PipelineDaoTest.kt
.../androidTest/.../LoginScreenTest.kt
.../androidTest/.../DashboardScreenTest.kt
.../androidTest/.../NavigationTest.kt
```

### Phase 8 (6 files)

```
android/app/proguard-rules.pro                           (MODIFIED: add rules)
android/app/src/main/res/drawable/ic_launcher_foreground.xml
android/app/src/main/res/values/themes.xml
android/app/src/main/res/values-night/themes.xml
android/app/src/main/res/mipmap-*/ (generated)
.../presentation/screen/dashboard/DashboardScreen.kt     (MODIFIED: date filter)
```

---

## Summary

| Phase | Files | Duration | Dependencies |
|-------|-------|----------|-------------|
| 1: Scaffold | 11 | 1 day | None |
| 2: Theme + Nav | 19 | 1 day | Phase 1 |
| 3: Network + Auth | 31 | 2 days | Phase 1 |
| 4: Domain + Room | 40 | 2 days | Phase 3 |
| 5: Screens | 35 | 4 days | Phase 2, 4 |
| 6: Docker Integration | 3 modified | 0.5 day | Phase 3 |
| 7: Testing | 15 | 2 days | Phase 5 |
| 8: Polish | 6 | 1 day | Phase 5 |
| **Total** | **~120 files** | **~13.5 days** | |

---

The plan document is ready. The key files referenced from the existing codebase that informed this plan:

- `/src/datapulse/analytics/models.py` -- All Pydantic analytics models (KPISummary, TrendResult, RankingResult, etc.)
- `/src/datapulse/pipeline/models.py` -- Pipeline run and trigger models
- `/src/datapulse/api/routes/analytics.py` -- 10+ analytics endpoints with query params
- `/src/datapulse/api/routes/pipeline.py` -- 11 pipeline endpoints including SSE streaming
- `/src/datapulse/api/routes/health.py` -- Health check returning `{status, db}`
- `/src/datapulse/api/auth.py` -- JWT Bearer + API key fallback auth
- `/frontend/src/types/api.ts` -- TypeScript interfaces matching API responses
- `/frontend/src/app/globals.css` -- CSS theme tokens (light + dark color palettes)
- `/frontend/src/lib/auth.ts` -- NextAuth Keycloak OIDC configuration
- `/frontend/src/lib/formatters.ts` -- EGP currency formatting patterns
- `/frontend/src/lib/constants.ts` -- Chart colors, nav items
- `/keycloak/realm-export.json` -- Keycloak realm: `datapulse-frontend` public client, PKCE S256, `datapulse-scope` with tenant_id + roles
- `/docker-compose.yml` -- Service topology and Keycloak configuration

**Note**: I do not have a file-writing tool available in this session. The complete plan content above should be saved to `C:\Users\user\Documents\GitHub\SAAS\.claude\worktrees\jolly-goldstine\docs\Android App - Implementation Plan.md`. You can copy the entire markdown content starting from `# Implementation Plan: DataPulse Android App` through the end of the `Summary` table.