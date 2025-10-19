"""Authentication middleware for request processing."""


class AuthMiddleware:
    """Middleware for user authentication and authorization logic.

    This middleware intercepts incoming requests to verify user credentials
    before allowing access to protected resources. Implements core authentication
    logic for validating user identity.
    """

    def __init__(self, app):
        self.app = app
        self.users = {}

    def process_request(self, request):
        """Process incoming request for user authentication.

        Validates user credentials and applies authentication logic to determine
        if the user should be granted access.

        Args:
            request: HTTP request object containing user credentials

        Returns:
            Authenticated request or error response
        """
        user = request.get_user()
        return self.authenticate_user(user)

    def authenticate_user(self, user):
        """Apply authentication logic to validate user credentials."""
        return user in self.users
