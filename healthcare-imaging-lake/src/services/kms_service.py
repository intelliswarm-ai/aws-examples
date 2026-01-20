"""KMS service for healthcare imaging data lake encryption."""

import base64

import boto3
from aws_lambda_powertools import Logger
from botocore.config import Config
from botocore.exceptions import ClientError

from src.common.config import settings
from src.common.exceptions import EncryptionError

logger = Logger()


class KMSService:
    """Service for KMS encryption operations."""

    def __init__(self, key_id: str | None = None) -> None:
        """Initialize KMS service.

        Args:
            key_id: KMS key ID or ARN.
        """
        self.key_id = key_id or settings.kms_key_id

        config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=5,
            read_timeout=10,
        )
        self.client = boto3.client("kms", config=config, region_name=settings.aws_region)

    def encrypt(
        self,
        plaintext: str | bytes,
        encryption_context: dict[str, str] | None = None,
    ) -> bytes:
        """Encrypt data using KMS key.

        Args:
            plaintext: Data to encrypt.
            encryption_context: Optional encryption context for additional security.

        Returns:
            Encrypted ciphertext as bytes.

        Raises:
            EncryptionError: If encryption fails.
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")

        try:
            params = {"KeyId": self.key_id, "Plaintext": plaintext}
            if encryption_context:
                params["EncryptionContext"] = encryption_context

            response = self.client.encrypt(**params)
            return response["CiphertextBlob"]

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            raise EncryptionError(
                f"KMS encryption failed: {error_code}",
                key_id=self.key_id,
                operation="encrypt",
            ) from e

    def decrypt(
        self,
        ciphertext: bytes,
        encryption_context: dict[str, str] | None = None,
    ) -> bytes:
        """Decrypt data using KMS key.

        Args:
            ciphertext: Encrypted data.
            encryption_context: Encryption context used during encryption.

        Returns:
            Decrypted plaintext as bytes.

        Raises:
            EncryptionError: If decryption fails.
        """
        try:
            params = {"CiphertextBlob": ciphertext}
            if encryption_context:
                params["EncryptionContext"] = encryption_context

            response = self.client.decrypt(**params)
            return response["Plaintext"]

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            raise EncryptionError(
                f"KMS decryption failed: {error_code}",
                key_id=self.key_id,
                operation="decrypt",
            ) from e

    def generate_data_key(
        self,
        key_spec: str = "AES_256",
        encryption_context: dict[str, str] | None = None,
    ) -> tuple[bytes, bytes]:
        """Generate a data key for client-side encryption.

        Args:
            key_spec: Key specification (AES_128 or AES_256).
            encryption_context: Optional encryption context.

        Returns:
            Tuple of (plaintext_key, encrypted_key).

        Raises:
            EncryptionError: If key generation fails.
        """
        try:
            params = {"KeyId": self.key_id, "KeySpec": key_spec}
            if encryption_context:
                params["EncryptionContext"] = encryption_context

            response = self.client.generate_data_key(**params)
            return response["Plaintext"], response["CiphertextBlob"]

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            raise EncryptionError(
                f"Failed to generate data key: {error_code}",
                key_id=self.key_id,
                operation="generate_data_key",
            ) from e

    def encrypt_patient_id(
        self,
        patient_id: str,
        facility_id: str,
    ) -> str:
        """Encrypt patient ID with facility context.

        Args:
            patient_id: Patient identifier to encrypt.
            facility_id: Facility ID for encryption context.

        Returns:
            Base64-encoded encrypted patient ID.
        """
        encryption_context = {
            "purpose": "patient_id_encryption",
            "facility_id": facility_id,
        }
        ciphertext = self.encrypt(patient_id, encryption_context)
        return base64.b64encode(ciphertext).decode("utf-8")

    def decrypt_patient_id(
        self,
        encrypted_patient_id: str,
        facility_id: str,
    ) -> str:
        """Decrypt patient ID with facility context.

        Args:
            encrypted_patient_id: Base64-encoded encrypted patient ID.
            facility_id: Facility ID for encryption context.

        Returns:
            Decrypted patient ID.
        """
        encryption_context = {
            "purpose": "patient_id_encryption",
            "facility_id": facility_id,
        }
        ciphertext = base64.b64decode(encrypted_patient_id)
        plaintext = self.decrypt(ciphertext, encryption_context)
        return plaintext.decode("utf-8")

    def get_key_policy(self) -> dict:
        """Get the key policy for the KMS key.

        Returns:
            Key policy as dictionary.

        Raises:
            EncryptionError: If policy retrieval fails.
        """
        try:
            response = self.client.get_key_policy(
                KeyId=self.key_id,
                PolicyName="default",
            )
            import json

            return json.loads(response["Policy"])

        except ClientError as e:
            raise EncryptionError(
                f"Failed to get key policy: {e}",
                key_id=self.key_id,
                operation="get_key_policy",
            ) from e

    def describe_key(self) -> dict:
        """Describe the KMS key.

        Returns:
            Key metadata dictionary.

        Raises:
            EncryptionError: If describe fails.
        """
        try:
            response = self.client.describe_key(KeyId=self.key_id)
            key_metadata = response["KeyMetadata"]
            return {
                "key_id": key_metadata["KeyId"],
                "arn": key_metadata["Arn"],
                "key_state": key_metadata["KeyState"],
                "key_usage": key_metadata["KeyUsage"],
                "key_spec": key_metadata.get("KeySpec", "SYMMETRIC_DEFAULT"),
                "creation_date": key_metadata["CreationDate"],
                "enabled": key_metadata["Enabled"],
                "key_rotation_enabled": self._is_rotation_enabled(),
            }

        except ClientError as e:
            raise EncryptionError(
                f"Failed to describe key: {e}",
                key_id=self.key_id,
                operation="describe_key",
            ) from e

    def _is_rotation_enabled(self) -> bool:
        """Check if automatic key rotation is enabled."""
        try:
            response = self.client.get_key_rotation_status(KeyId=self.key_id)
            return response.get("KeyRotationEnabled", False)
        except ClientError:
            return False

    def verify_key_access(self) -> bool:
        """Verify that the key can be used for encryption.

        Returns:
            True if key is accessible and enabled.
        """
        try:
            key_info = self.describe_key()
            return key_info["enabled"] and key_info["key_state"] == "Enabled"
        except EncryptionError:
            return False
