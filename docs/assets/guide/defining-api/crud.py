from stoma import APIRoute, APIRouter

router = APIRouter(prefix="/api/v1")


@router.get("/users")
class GetUsers(APIRoute):
    limit: int = 20


@router.post("/users")
class CreateUser(APIRoute):
    name: str
    email: str
