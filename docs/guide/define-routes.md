# Routes

Define an endpoint's route with the HTTP method decorators of an `APIRouter` instance (`get` / `post` and so on).

```python
from stoma import APIRoute, APIRouter

router = APIRouter(prefix="/api/v1")

@router.get("/users")
class GetUsers(APIRoute):
    limit: int = 20

@router.post("/users")
class CreateUser(APIRoute):
    name: str
    email: str
```

Every decorator accepts a `path` argument, and `{}` placeholders can be used to set path parameters.

If the `APIRouter` was created with a `prefix=` argument, the actual request path is `prefix + path`.

## HTTP methods

`APIRouter` provides these 8 HTTP method decorators:

| Method | Signature | Purpose |
|--------|-----------|---------|
| GET | `router.get(path)` | Retrieve a resource; does not change server state |
| POST | `router.post(path)` | Create a new resource |
| PUT | `router.put(path)` | Replace a resource entirely |
| PATCH | `router.patch(path)` | Update a resource partially |
| DELETE | `router.delete(path)` | Delete a resource |
| HEAD | `router.head(path)` | Same as GET, but returns only the response headers |
| OPTIONS | `router.options(path)` | Return the HTTP methods the server supports |
| TRACE | `router.trace(path)` | Loopback test, for diagnosing request paths |
