"""APIRouter 功能演示。

此示例展示如何使用 APIRouter 定义接口类并注入路由元数据。
"""

from __future__ import annotations

import sys
from pathlib import Path as PathLib
from typing import Annotated

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(PathLib(__file__).parent.parent))

from pydantic import BaseModel  # noqa: E402

from src.params import Path, Query  # noqa: E402
from src.routing import APIRoute, APIRouter  # noqa: E402


# 定义产品数据模型
class ProductData(BaseModel):
    """产品数据模型。"""

    id: int
    name: str
    price: float
    description: str | None = None


# 创建路由器并配置全局 servers
router = APIRouter(servers=["https://api.example.com"])


@router.get("/products")
class GetProducts(APIRoute[list[ProductData]]):
    """获取产品列表，使用全局 servers。"""

    category: Annotated[str | None, Query()] = None
    limit: Annotated[int, Query(ge=1, le=100)] = 20


@router.post("/products", servers=["https://api-staging.example.com"])
class CreateProduct(APIRoute[ProductData]):
    """创建产品，覆盖全局 servers。"""

    name: str
    price: float
    description: str | None = None


@router.put("/products/{product_id}")
class UpdateProduct(APIRoute[ProductData]):
    """更新产品。"""

    product_id: Annotated[int, Path()]
    name: str
    price: float


@router.delete("/products/{product_id}")
class DeleteProduct(APIRoute[None]):
    """删除产品。"""

    product_id: Annotated[int, Path()]


def main() -> None:
    """演示接口定义和元数据访问。"""
    print("=" * 70)
    print("APIRouter 功能演示")
    print("=" * 70)

    print(f"\n配置的全局 servers: {router.servers}\n")

    print("1. GetProducts 接口（使用全局 servers）:")
    print(f"   HTTP 方法: {GetProducts._route_meta.method}")
    print(f"   路径: {GetProducts._route_meta.path}")
    print(f"   Servers: {GetProducts._route_meta.servers}")

    print("\n2. CreateProduct 接口（覆盖全局 servers）:")
    print(f"   HTTP 方法: {CreateProduct._route_meta.method}")
    print(f"   路径: {CreateProduct._route_meta.path}")
    print(f"   Servers: {CreateProduct._route_meta.servers}")

    print("\n3. UpdateProduct 接口（PUT 方法）:")
    print(f"   HTTP 方法: {UpdateProduct._route_meta.method}")
    print(f"   路径: {UpdateProduct._route_meta.path}")
    print(f"   Servers: {UpdateProduct._route_meta.servers}")

    print("\n4. DeleteProduct 接口（DELETE 方法）:")
    print(f"   HTTP 方法: {DeleteProduct._route_meta.method}")
    print(f"   路径: {DeleteProduct._route_meta.path}")
    print(f"   Servers: {DeleteProduct._route_meta.servers}")

    # 演示实例化
    print("\n" + "=" * 70)
    print("【实例化示例】")
    print("=" * 70)

    product_endpoint = GetProducts(category="electronics", limit=50)
    print(f"\n类型: {type(product_endpoint).__name__}")
    print(f"category: {product_endpoint.category}")
    print(f"limit: {product_endpoint.limit}")

    # 演示元数据不可变性
    print("\n" + "=" * 70)
    print("【元数据不可变性验证】")
    print("=" * 70)

    try:
        GetProducts._route_meta.method = "POST"
        print("\n❌ 失败：元数据应该是不可变的")
    except Exception as e:
        print(f"\n✅ 成功：修改元数据抛出 {type(e).__name__}")

    print("\n" + "=" * 70)
    print("演示完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
