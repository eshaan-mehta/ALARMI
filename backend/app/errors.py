class ApiError(Exception):
    """Raised by routers to return a JSON ``{"message": ...}`` body with a given
    HTTP status, matching the error shape the frontend expects."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
