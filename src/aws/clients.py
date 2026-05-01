from __future__ import annotations

from typing import Any

from src.config.settings import Settings, get_settings


def create_aws_client(service_name: str, settings: Settings | None = None) -> Any:
    """Create a boto3 client using shared app settings.

    boto3 is imported lazily so local tests that do not touch AWS can run before
    production dependencies are installed.
    """

    try:
        import boto3
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "boto3 is required for AWS integrations. Install requirements.txt first."
        ) from exc

    resolved_settings = settings or get_settings()
    client_kwargs: dict[str, Any] = {"region_name": resolved_settings.aws_region}
    if resolved_settings.aws_endpoint_url:
        client_kwargs["endpoint_url"] = resolved_settings.aws_endpoint_url
    return boto3.client(service_name, **client_kwargs)

