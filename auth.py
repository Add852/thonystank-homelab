from fastapi import Request, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import secrets
import os

class BasicAuthMiddleware(BaseHTTPMiddleware):
    """
    Global Authentication Middleware.
    Removes the need for 'Depends(verify_credentials)' on every single route.
    """
    def __init__(self, app, username: str, password: str):
        super().__init__(app)
        self.username = username
        self.password = password

    async def dispatch(self, request: Request, call_next):
        # Allow static files to be accessed without auth
        if request.url.path.startswith("/static"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            return self._unauthorized_response()

        try:
            # Decode Basic Auth header: "Basic base64(user:pass)"
            import base64
            encoded_credentials = auth_header.split(" ")[1]
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
            username, password = decoded_credentials.split(":", 1)
            
            if secrets.compare_digest(username, self.username) and \
               secrets.compare_digest(password, self.password):
                return await call_next(request)
        except Exception:
            pass

        return self._unauthorized_response()

    def _unauthorized_response(self):
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": "Basic realm='Secure Area'"},
            content="Unauthorized"
        )
