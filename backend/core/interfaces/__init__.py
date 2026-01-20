"""
Core Interfaces Module
Abstract base classes for the plugin architecture
"""

from .workflow_interface import (
    IWorkflow,
    ClusterResult,
    WorkflowType,
)
from .validator_interface import (
    IValidator,
    ValidationResult,
)
from .corrector_interface import (
    ICorrector,
    CorrectionResult,
)
from .fingerprint_interface import (
    IFingerprint,
    FingerprintData,
)
from .detector_interface import (
    IDetector,
    DetectionResult,
    DetectionSource,
)
from .corrector_interface import CorrectionStatus

__all__ = [
    # Workflow
    "IWorkflow",
    "ClusterResult",
    "WorkflowType",
    # Validator
    "IValidator",
    "ValidationResult",
    # Corrector
    "ICorrector",
    "CorrectionResult",
    # Fingerprint
    "IFingerprint",
    "FingerprintData",
    # Detector
    "IDetector",
    "DetectionResult",
    "DetectionSource",
    # Corrector extras
    "CorrectionStatus",
]
