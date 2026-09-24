"""Exceptions raised by the queue adapters."""


class ConnectorConnectionError(Exception):
    """Raised when an adapter cannot reach its monitored Redis instance."""


class JobNotFoundError(Exception):
    """Raised when a job id does not exist in the monitored stack."""


class ReplayFailedError(Exception):
    """Raised when a failed job could not be requeued."""
