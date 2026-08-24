# 接口路由

通过 `APIRouter` 实例的 HTTP 方法装饰器（`get` / `post` 等）定义接口路由。

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

每个装饰器接受 `path` 参数，可使用 `{}` 占位符设置路径参数。

如果 `APIRouter` 使用了 `prefix=` 参数，实际请求的路径是 `prefix + path`。

## HTTP 方法清单

`APIRouter` 提供了以下 8 个 HTTP 方法装饰器：

| 方法 | 签名 | 用途 |
|------|------|------|
| GET | `router.get(path)` | 获取资源，不改变服务器状态 |
| POST | `router.post(path)` | 创建新资源 |
| PUT | `router.put(path)` | 完整替换资源 |
| PATCH | `router.patch(path)` | 部分更新资源 |
| DELETE | `router.delete(path)` | 删除资源 |
| HEAD | `router.head(path)` | 与 GET 相同，但只返回响应头 |
| OPTIONS | `router.options(path)` | 返回服务器支持的 HTTP 方法 |
| TRACE | `router.trace(path)` | 回环测试，诊断请求路径 |