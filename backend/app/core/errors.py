from fastapi import HTTPException, status

class AgentGuardException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class NotFoundError(AgentGuardException):
    def __init__(self, resource: str, identifier: str | int):
        super().__init__(
            message=f"{resource} '{identifier}' not found",
            status_code=status.HTTP_404_NOT_FOUND
        )

class ValidationError(AgentGuardException):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

class ExecutionError(AgentGuardException):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )
