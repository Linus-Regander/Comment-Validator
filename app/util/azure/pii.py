from dataclasses import dataclass
from typing import Protocol

from azure.ai.textanalytics import TextAnalyticsClient
from azure.identity import DefaultAzureCredential

from app.errors import PiiDetectedError, PiiScreeningUnavailableError

MISSING_PII_CONFIGURATION = PiiScreeningUnavailableError("PII screening is not configured")
PII_SCREENING_UNAVAILABLE = PiiScreeningUnavailableError("PII screening is unavailable")

@dataclass(frozen=True)
class PiiConfig:
    enabled: bool = True
    endpoint: str = ""
    managed_identity_client_id: str | None = None

class PiiDetector(Protocol):
    def assert_clean(self, content: str) -> None:
        ...

    def close(self) -> None:
        ...

class NoopPiiDetector:
    """Lets everything through. For local development and tests only."""

    def assert_clean(self, content: str) -> None:
        return None

    def close(self) -> None:
        return None

class AzurePiiDetector:
    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint
        self._client: TextAnalyticsClient | None = None
        self._credential: DefaultAzureCredential | None = None

    def assert_clean(self, content: str) -> None:
        if not self._endpoint:
            raise MISSING_PII_CONFIGURATION

        try:
            client = self._get_client()
            result = client.recognize_pii_entities([content])[0]
        except Exception as error:
            raise PII_SCREENING_UNAVAILABLE from error

        if result.is_error:
            raise PII_SCREENING_UNAVAILABLE
        if result.entities:
            raise PiiDetectedError()

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
        
        if self._credential is not None:
            self._credential.close()

    def _get_client(self) -> TextAnalyticsClient:
        if self._client is None:
            self._credential = DefaultAzureCredential(
                managed_identity_client_id=self._config.managed_identity_client_id
            )

            self._client = TextAnalyticsClient(
                endpoint=self._config.endpoint,
                credential=self._credential,
            )

        return self._client


def pii_detector(config: PiiConfig) -> PiiDetector:
    if not config.enabled:
        return NoopPiiDetector()
    
    return AzurePiiDetector(config)