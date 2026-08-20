import logging

from azure.storage.blob import BlobServiceClient
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings


logger = logging.getLogger(__name__)


class BlobStorageService:

    def __init__(self) -> None:

        settings = get_settings()

        self.client = BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string
        )

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def upload_file(
        self,
        container_name: str,
        blob_name: str,
        file_path: str,
    ) -> str:

        container = self.client.get_container_client(
            container_name
        )

        if not container.exists():
            container.create_container()

        blob = container.get_blob_client(blob_name)

        with open(file_path, "rb") as data:

            blob.upload_blob(
                data,
                overwrite=True,
            )

        logger.info(
            "Uploaded blob container=%s blob=%s",
            container_name,
            blob_name,
        )

        return blob.url

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def upload_text(
        self,
        container_name: str,
        blob_name: str,
        content: str,
    ) -> str:

        container = self.client.get_container_client(
            container_name
        )

        if not container.exists():
            container.create_container()

        blob = container.get_blob_client(blob_name)

        blob.upload_blob(
            content,
            overwrite=True,
        )

        return blob.url
