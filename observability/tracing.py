"""OpenTelemetry tracing setup."""
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from config import settings

_tracer: trace.Tracer | None = None


def init_tracing(service_name: str = "agentops-api") -> None:
    global _tracer
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)


def get_tracer() -> trace.Tracer:
    if _tracer is None:
        init_tracing()
    return _tracer  # type: ignore[return-value]
