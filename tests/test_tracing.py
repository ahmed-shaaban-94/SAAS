"""Unit tests for the OpenTelemetry tracing initializer (#607)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from datapulse import tracing


@pytest.fixture(autouse=True)
def _clean_otel_env(monkeypatch):
    """Clear all OTel env vars so tests start from a known state."""
    for key in (
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_TRACES_SAMPLER_ARG",
        "OTEL_SERVICE_NAME",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.mark.unit
class TestIsTracingEnabled:
    def test_false_when_endpoint_unset(self):
        assert tracing.is_tracing_enabled() is False

    def test_false_when_endpoint_empty_string(self, monkeypatch):
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        assert tracing.is_tracing_enabled() is False

    def test_false_when_endpoint_only_whitespace(self, monkeypatch):
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "   ")
        assert tracing.is_tracing_enabled() is False

    def test_true_when_endpoint_set(self, monkeypatch):
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4318")
        assert tracing.is_tracing_enabled() is True


@pytest.mark.unit
class TestEnvSampleRate:
    def test_default_is_ten_percent(self):
        assert tracing._env_sample_rate() == 0.1

    def test_reads_valid_float(self, monkeypatch):
        monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "0.5")
        assert tracing._env_sample_rate() == 0.5

    def test_accepts_zero(self, monkeypatch):
        monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "0.0")
        assert tracing._env_sample_rate() == 0.0

    def test_accepts_one(self, monkeypatch):
        monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "1.0")
        assert tracing._env_sample_rate() == 1.0

    def test_falls_back_on_negative(self, monkeypatch):
        monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "-0.1")
        assert tracing._env_sample_rate() == 0.1

    def test_falls_back_on_above_one(self, monkeypatch):
        monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "2.5")
        assert tracing._env_sample_rate() == 0.1

    def test_falls_back_on_non_numeric(self, monkeypatch):
        monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "half")
        assert tracing._env_sample_rate() == 0.1


@pytest.mark.unit
class TestInitTracing:
    def test_noop_when_endpoint_unset(self):
        """Most common path — OTel must be disabled by default."""
        assert tracing.init_tracing(app=MagicMock()) is False

    def test_noop_when_packages_missing(self, monkeypatch):
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4318")

        # Simulate the otel packages being unavailable by making the
        # conditional import inside init_tracing raise ImportError.
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("opentelemetry"):
                raise ImportError(f"mocked: {name} not available")
            return real_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=fake_import):
            result = tracing.init_tracing(app=MagicMock())

        assert result is False

    def test_initializes_when_endpoint_set_and_packages_available(self, monkeypatch):
        """Full init path — mock the otel modules so we never touch real I/O."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4318")
        monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "0.25")
        monkeypatch.setenv("OTEL_SERVICE_NAME", "test-svc")

        import sys
        import types

        # Build a minimal fake otel package tree in sys.modules so the
        # conditional imports inside init_tracing resolve without the
        # real opentelemetry install.
        fake_modules: dict[str, types.ModuleType] = {}

        def _mod(name, attrs=None):
            m = types.ModuleType(name)
            for k, v in (attrs or {}).items():
                setattr(m, k, v)
            fake_modules[name] = m
            return m

        trace_mod = _mod("opentelemetry.trace")
        trace_mod.get_tracer_provider = MagicMock(return_value=object())
        trace_mod.set_tracer_provider = MagicMock()

        _mod("opentelemetry", {"trace": trace_mod})

        fake_exporter = MagicMock()
        fake_exporter_cls = MagicMock(return_value=fake_exporter)
        _mod(
            "opentelemetry.exporter.otlp.proto.http.trace_exporter",
            {"OTLPSpanExporter": fake_exporter_cls},
        )
        _mod("opentelemetry.exporter")
        _mod("opentelemetry.exporter.otlp")
        _mod("opentelemetry.exporter.otlp.proto")
        _mod("opentelemetry.exporter.otlp.proto.http")

        fastapi_inst = MagicMock()
        _mod("opentelemetry.instrumentation")
        _mod(
            "opentelemetry.instrumentation.fastapi",
            {"FastAPIInstrumentor": fastapi_inst},
        )
        _mod(
            "opentelemetry.instrumentation.httpx",
            {"HTTPXClientInstrumentor": MagicMock()},
        )
        _mod(
            "opentelemetry.instrumentation.redis",
            {"RedisInstrumentor": MagicMock()},
        )
        sa_inst = MagicMock()
        _mod(
            "opentelemetry.instrumentation.sqlalchemy",
            {"SQLAlchemyInstrumentor": sa_inst},
        )
        _mod("opentelemetry.sdk")
        _mod(
            "opentelemetry.sdk.resources",
            {"Resource": MagicMock(create=MagicMock(return_value="RES"))},
        )

        class _FakeProvider:  # distinct real class so isinstance works
            def __init__(self, *, resource=None, sampler=None):
                self.resource = resource
                self.sampler = sampler
                self.processors = []

            def add_span_processor(self, p):
                self.processors.append(p)

        _mod("opentelemetry.sdk.trace", {"TracerProvider": _FakeProvider})
        _mod(
            "opentelemetry.sdk.trace.export",
            {"BatchSpanProcessor": MagicMock()},
        )
        _mod(
            "opentelemetry.sdk.trace.sampling",
            {"ParentBased": MagicMock(), "TraceIdRatioBased": MagicMock()},
        )

        # Patch get_tracer_provider so the idempotency guard fires "not
        # yet initialized" (returning a plain object that isn't a
        # TracerProvider instance). Guard get_engine too — real DB call
        # would fail in a unit test.
        with (
            patch.dict(sys.modules, fake_modules),
            patch("datapulse.core.db.get_engine", return_value=MagicMock()),
        ):
            result = tracing.init_tracing(app=MagicMock())

        assert result is True
        trace_mod.set_tracer_provider.assert_called_once()
        fastapi_inst.instrument_app.assert_called_once()

    def test_noop_when_already_initialized(self, monkeypatch):
        """Re-entry must be idempotent — return False without re-installing."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4318")

        import sys
        import types

        fake_modules: dict[str, types.ModuleType] = {}

        def _mod(name, attrs=None):
            m = types.ModuleType(name)
            for k, v in (attrs or {}).items():
                setattr(m, k, v)
            fake_modules[name] = m
            return m

        # The existing TracerProvider — isinstance(current, TracerProvider) must be True.
        class _AlreadyInstalled:
            pass

        existing = _AlreadyInstalled()
        trace_mod = _mod("opentelemetry.trace")
        trace_mod.get_tracer_provider = MagicMock(return_value=existing)
        trace_mod.set_tracer_provider = MagicMock()
        _mod("opentelemetry", {"trace": trace_mod})

        _mod("opentelemetry.exporter")
        _mod("opentelemetry.exporter.otlp")
        _mod("opentelemetry.exporter.otlp.proto")
        _mod("opentelemetry.exporter.otlp.proto.http")
        _mod(
            "opentelemetry.exporter.otlp.proto.http.trace_exporter",
            {"OTLPSpanExporter": MagicMock()},
        )
        _mod("opentelemetry.instrumentation")
        _mod("opentelemetry.instrumentation.fastapi", {"FastAPIInstrumentor": MagicMock()})
        _mod("opentelemetry.instrumentation.httpx", {"HTTPXClientInstrumentor": MagicMock()})
        _mod("opentelemetry.instrumentation.redis", {"RedisInstrumentor": MagicMock()})
        _mod(
            "opentelemetry.instrumentation.sqlalchemy",
            {"SQLAlchemyInstrumentor": MagicMock()},
        )
        _mod("opentelemetry.sdk")
        _mod("opentelemetry.sdk.resources", {"Resource": MagicMock()})
        # The TracerProvider class must be what `existing` is an instance of.
        _mod("opentelemetry.sdk.trace", {"TracerProvider": _AlreadyInstalled})
        _mod("opentelemetry.sdk.trace.export", {"BatchSpanProcessor": MagicMock()})
        _mod(
            "opentelemetry.sdk.trace.sampling",
            {"ParentBased": MagicMock(), "TraceIdRatioBased": MagicMock()},
        )

        with patch.dict(sys.modules, fake_modules):
            result = tracing.init_tracing(app=MagicMock())

        assert result is False
        trace_mod.set_tracer_provider.assert_not_called()
