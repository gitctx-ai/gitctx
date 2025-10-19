"""JWT-based authentication middleware class for token verification."""

import jwt


class JWTAuthMiddleware:
    """JWT authentication middleware class for handling JSON Web Tokens.

    This middleware class implements JWT-based auth for verifying user tokens.
    Validates JWT tokens on each request to ensure secure authentication.
    Primary middleware class for JWT authentication in the auth module.
    """

    def __init__(self, secret_key):
        self.secret_key = secret_key
        self.algorithm = "HS256"

    def verify_token(self, token):
        """Verify JWT token signature and claims for authentication.

        This JWT auth method validates tokens to confirm user identity.

        Args:
            token: JWT token string

        Returns:
            Decoded JWT token payload if valid

        Raises:
            jwt.InvalidTokenError: If JWT token is invalid or expired
        """
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

    def create_jwt_token(self, user_id):
        """Create new JWT token for authenticated user."""
        payload = {"user_id": user_id}
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
