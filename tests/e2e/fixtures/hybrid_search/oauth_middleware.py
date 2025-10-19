"""OAuth authentication middleware class for third-party authentication."""


class OAuthMiddleware:
    """OAuth authentication middleware class for external auth providers.

    This middleware class implements OAuth 2.0 auth flow for authenticating users
    via third-party services. Middleware class handles OAuth authentication with
    providers like Google, GitHub, or Facebook.
    """

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.provider = "oauth"

    def handle_callback(self, code):
        """Handle OAuth callback with authorization code for authentication.

        OAuth middleware method that exchanges authorization code for access token.

        Args:
            code: Authorization code from OAuth provider

        Returns:
            Access token and user information from OAuth auth
        """
        token = self.exchange_code(code)
        return {"access_token": token, "provider": self.provider}

    def exchange_code(self, code):
        """Exchange OAuth authorization code for access token."""
        # OAuth authentication logic
        return f"oauth_token_{code}"
