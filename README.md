# Stoma

<p align="center">
  <a href="https://pypi.org/project/stoma/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/stoma.svg"></a>
  <a href="https://pypi.org/project/stoma/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/stoma.svg"></a>
  <a href="https://img.shields.io/pypi/dm/stoma.svg"><img alt="PyPI downloads" src="https://img.shields.io/pypi/dm/stoma.svg"></a>
  <a href="https://github.com/dengmingcong/stoma/blob/master/LICENSE"><img alt="License" src="https://img.shields.io/github/license/dengmingcong/stoma.svg"></a>
</p>

<p align="center"><b>Define with OpenAPI. Autocomplete with Stoma.</b></p>

<p align="center">
  <img width="80%" style="border-radius: 8px;" alt="IDE autocompletes API parameters" src="https://raw.githubusercontent.com/dengmingcong/stoma/master/docs/assets/readme/autocomplete.gif" />
</p>

<!-- README-I18N:START -->

<p align="center">
  <b>English</b> ·
  <a href="./README.zh.md">中文</a>
</p>

<!-- README-I18N:END -->

<p align="center">
  <a href="#installation">Installation</a> ·
  <a href="#example">Example</a> ·
  <a href="#key-features">Key features</a> ·
  <a href="#docs">Docs</a> ·
  <a href="#about">About</a>
</p>

---

## Installation

Requires Python 3.12 or higher.

```bash
pip install stoma
```

## Example

Define an endpoint:

```python
from typing import Annotated
from pydantic import BaseModel, Field
from stoma import APIRoute, APIRouter, ResponseSpec

class User(BaseModel):
    id: Annotated[int | None, Field(examples=[10])] = None
    """Example: 10"""

    username: Annotated[str | None, Field(examples=["theUser"])] = None
    """Example: 'theUser'"""

    first_name: Annotated[str | None, Field(alias="firstName", examples=["John"])] = None
    """Example: 'John'"""

router = APIRouter(prefix="/api/v3")

@router.get("/user/{username}")
class GetUserByName(APIRoute):
    """Get user by user name."""

    username: str

    @property
    def on_200(self) -> ResponseSpec[User]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=User,
        )
```

Call it:

```python
from playwright.sync_api import sync_playwright
from stoma import Client

with sync_playwright() as p:
    ctx = p.request.new_context(base_url="https://petstore3.swagger.io")
    client = Client(context=ctx)

    endpoint = GetUserByName(username="user1")
    response = client.send(endpoint)
    user = response.expect(endpoint.on_200)
    assert user.username == "user1"
```

## Key features

- **The code is the protocol**: Stoma holds everything needed to call an endpoint, so you no
  longer have to switch between your IDE and the API documentation.
- **Autocomplete**: thanks to Pydantic and generics, the IDE autocompletes both request
  parameters and response types.
- **OpenAPI CLI**: a CLI command generates the whole set of endpoint code from an OpenAPI spec.
  <img width="80%" style="border-radius: 8px;" alt="stoma CLI generating endpoint code" src="https://raw.githubusercontent.com/dengmingcong/stoma/master/docs/assets/readme/cli.gif" />


## Docs

- [Quickstart](https://github.com/dengmingcong/stoma/blob/master/docs/guide/quickstart.md) — installation and a walkthrough against a real API.
- Defining an endpoint — an endpoint in Stoma is made of a route, its parameters, and its response specs.
    * [Routes](https://github.com/dengmingcong/stoma/blob/master/docs/guide/define-routes.md)
    * [Parameters](https://github.com/dengmingcong/stoma/blob/master/docs/guide/define-parameters.md)
    * [Response specs](https://github.com/dengmingcong/stoma/blob/master/docs/guide/define-response-specs.md)
- [Calling an endpoint and asserting the response](https://github.com/dengmingcong/stoma/blob/master/docs/guide/client.md) — use `Client` to call an endpoint and assert on its response.
- [Generating endpoints](https://github.com/dengmingcong/stoma/blob/master/docs/guide/cli.md) — Stoma provides a CLI command that generates endpoints from an OpenAPI spec.

See also the demo repository [stoma-demo](https://github.com/dengmingcong/stoma-demo), which shows how Stoma is used in a real project.


## About

[About Stoma](https://github.com/dengmingcong/stoma/blob/master/docs/about.md) — where the project comes from, its inspiration, and its dependencies.
