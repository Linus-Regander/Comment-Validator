"""Azure AI Language PII detection before comment writes."""

import os
from typing import Protocol

from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential

from app.errors import PiiDetectedError, PiiScreeningUnavailableError


class PiiDetector(Protocol):
    """Contract for comment content screening."""

    def assert_clean(self, content: str) -> None:
        """Raise when PII is detected or screening cannot complete."""


class AzurePiiDetector:
    """Screen text with Azure AI Language using Entra-backed credentials."""

    def __init__(self) -> None:
        endpoint = os.getenv("AZURE_LANGUAGE_ENDPOINT")
        self._client = None
        self._credential = None
        if endpoint:
            try:
                self._credential = DefaultAzureCredential()
                self._client = TextAnalyticsClient(
                    endpoint=endpoint,
                    credential=self._credential,
                )
            except (AzureError, ValueError) as error:
                raise PiiScreeningUnavailableError(
                    "Azure PII screening is unavailable"
                ) from error

    def assert_clean(self, content: str) -> None:
        if self._client is None:
            raise PiiScreeningUnavailableError(
                "Azure PII screening is not configured"
            )

        try:
            result = next(
                iter(
                    self._client.recognize_pii_entities(
                        [content],
                    )
                )
            )
        except (AzureError, StopIteration) as error:
            raise PiiScreeningUnavailableError(
                "Azure PII screening is unavailable"
            ) from error
        except Exception as error:
            raise PiiScreeningUnavailableError(
                "Azure PII screening is unavailable"
            ) from error

        if result.is_error:
            raise PiiScreeningUnavailableError(
                "Azure PII screening is unavailable"
            )
        if result.entities:
            raise PiiDetectedError()

    def close(self) -> None:
        """Release the SDK transport and managed credential resources."""
        if self._client is not None:
            self._client.close()
        if self._credential is not None:
            self._credential.close()