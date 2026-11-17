# Anyforce Runtime

## JWT

`anyforce.api.security.jwt.gen()` keeps its existing authentication and issuance
interface. The issuance function also accepts optional `jti` and `expires_at`
keyword arguments for registered tokens:

```python
from anyforce.api.security import jwt

get_current_user, authorize = jwt.gen("/token", secret)
encoded = authorize(
    str(user.id), jti=str(token.id), expires_at=int(expires_at.timestamp())
)
```

For request authentication that needs `jti`, use `gen_claims()` instead of the
legacy `gen()` user-ID dependency. It extracts the bearer token and returns the
complete verified `Claims`:

```python
from fastapi import Depends

get_current_claims = jwt.gen_claims("/token", secret)


async def protected(claims: jwt.Claims = Depends(get_current_claims)):
    return {"user_id": claims.sub, "token_id": claims.jti}
```

Both authentication dependencies verify the signature, expiration and required
claims, raising `HTTPUnAuthorizedError` for invalid tokens. `jti` is optional for
existing tokens. Record ownership, revocation and usage tracking remain the
application's responsibility.

## Lint

- Lint [flask8](https://flake8.pycqa.org/en/latest/)
- Type Check [pyright](https://github.com/microsoft/pyright)
