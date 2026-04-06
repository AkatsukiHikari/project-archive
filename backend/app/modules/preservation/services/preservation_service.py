import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.preservation.schemas.detection import DetectionRequest, DetectionResult


class PreservationService:
    @staticmethod
    async def check_integrity(file_content: bytes, expected_hash: str, algorithm: str = "sha256") -> Dict[str, Any]:
        """Check file integrity using MD5/SHA256"""
        if algorithm.lower() == "sha256":
            actual_hash = hashlib.sha256(file_content).hexdigest()
        else:
            actual_hash = hashlib.md5(file_content).hexdigest()

        is_valid = actual_hash == expected_hash
        return {
            "is_valid": is_valid,
            "actual_hash": actual_hash,
            "expected_hash": expected_hash,
        }

    @staticmethod
    async def check_usability(filename: str, file_content: bytes) -> Dict[str, Any]:
        """Check file format and virus scan stub"""
        allowed_extensions = {".pdf", ".ofd", ".jpg", ".png", ".tiff"}
        extension = filename.lower()[filename.rfind("."):] if "." in filename else ""

        format_valid = extension in allowed_extensions
        # Virus scan stub
        virus_free = True

        return {
            "format_valid": format_valid,
            "extension": extension,
            "virus_free": virus_free,
            "is_valid": format_valid and virus_free,
        }

    @staticmethod
    async def check_authenticity(metadata: Dict[str, Any], signature_valid: bool = True) -> Dict[str, Any]:
        """Check metadata completeness and signature"""
        required_fields = ["fonds_id", "year", "title", "retention_period"]
        missing_fields = [field for field in required_fields if field not in metadata or not metadata[field]]

        is_valid = len(missing_fields) == 0 and signature_valid
        return {
            "is_valid": is_valid,
            "missing_fields": missing_fields,
            "signature_verified": signature_valid,
        }

    @staticmethod
    async def check_safety(content_text: str) -> Dict[str, Any]:
        """Sensitive word filtering stub"""
        sensitive_words = ["confidential", "secret"]  # Placeholder
        found_words = [word for word in sensitive_words if word in content_text.lower()]

        is_valid = len(found_words) == 0
        return {
            "is_valid": is_valid,
            "found_sensitive_words": found_words,
        }

    async def run_four_natures_check(
        self,
        filename: str,
        file_content: bytes,
        expected_hash: str,
        metadata: Dict[str, Any],
        content_text: str = "",
    ) -> DetectionResult:
        """Run all 4-Natures checks"""
        integrity = await self.check_integrity(file_content, expected_hash)
        usability = await self.check_usability(filename, file_content)
        authenticity = await self.check_authenticity(metadata)
        safety = await self.check_safety(content_text)

        is_valid = all([
            integrity["is_valid"],
            usability["is_valid"],
            authenticity["is_valid"],
            safety["is_valid"],
        ])

        details = {
            "authenticity": authenticity,
            "integrity": integrity,
            "usability": usability,
            "safety": safety,
        }

        # Simple score calculation
        score = sum([1 for v in details.values() if v["is_valid"]]) / 4.0 * 100

        return DetectionResult(is_valid=is_valid, details=details, score=score)

    async def store_detection(
        self,
        db: AsyncSession,
        request: DetectionRequest,
        current_user_id: uuid.UUID,
    ):
        """Run four-natures check and persist the result as a DetectionRecord."""
        from app.modules.preservation.models.detection import DetectionRecord
        from app.modules.preservation.repositories.detection_repository import SQLAlchemyDetectionRepository

        # Use empty bytes — hash is pre-computed and supplied in request
        file_content = b""
        result = await self.run_four_natures_check(
            filename=request.filename,
            file_content=file_content,
            expected_hash=request.expected_hash,
            metadata=request.metadata,
            content_text=request.content_text,
        )

        record = DetectionRecord(
            archive_id=request.archive_id,
            filename=request.filename,
            original_hash=request.expected_hash,
            algorithm=request.algorithm,
            metadata_json=request.metadata,
            content_text=request.content_text or None,
            status="pass" if result.is_valid else "fail",
            score=result.score,
            details_json=result.details,
            checked_by=current_user_id,
            checked_at=datetime.now(timezone.utc),
            create_by=current_user_id,
        )

        repo = SQLAlchemyDetectionRepository(db)
        return await repo.create(record)


preservation_service = PreservationService()
