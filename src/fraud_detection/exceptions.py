"""Domain exceptions for dataset loading and validation."""


class DatasetError(Exception):
    """Base error for transaction dataset operations."""


class DatasetLoadError(DatasetError):
    """Raised when a dataset cannot be read safely."""


class EmptyDatasetError(DatasetLoadError):
    """Raised when a dataset has no readable transaction rows."""


class SchemaValidationError(DatasetError):
    """Raised when a frame does not meet the required ULB schema."""


class InferenceInputError(ValueError):
    """Raised when transaction features violate the inference contract."""


class ArtifactError(RuntimeError):
    """Raised when a trusted local model artifact is invalid or incompatible."""
