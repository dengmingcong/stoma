# 关于 Stoma

关于 Stoma 项目的由来。

## 启发

Stoma 受 fastapi 启发，作用和 fastapi “相反”，fastapi 是通过 Pydantic 模型生成 OpenAPI 描述的接口协议，Stoma 则是从 OpenAPI 生成 Pydantic 模型。

设计 Stoma 时，我期望能像 Postman 一样，可以方便地实现接口请求。

## 依赖

Stoma 最核心的依赖：

* [Pydantic](https://pydantic.dev/docs/)
* [Playwright](https://playwright.dev/python/docs/api/class-playwright)

## 名字由来

Stoma 是植物学名称，意为“气孔” -- 植物表皮的小孔，是气体交换和水分蒸腾的通道，是生命活动的“接口”。