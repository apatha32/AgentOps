"""OpenTelemetry tracing setup."""
import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from config import settings

logger = logging.getLogger(__name__)
_tracer: trace.Tracer | None = None


def init_tracing(service_name: str = "agentops-api") -> None:
    global _tracer
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if settings.otel_exporter_otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            exporter = OTLPSpanExporter(
                endpoint=settings.otel_exporter_otlp_endpoint, insecure=True
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception as exc:
            logger.warning("OTel exporter init failed (skipping): %s", exc)

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)


def get_tracer() -> trace.Tracer:
    if _tracer is None:
        init_tracing()
    return _tracer  # type: ignore[return-value]
