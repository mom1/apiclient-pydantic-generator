![GitHub issues](https://img.shields.io/github/issues/mom1/apiclient-pydantic-generator.svg)
![GitHub stars](https://img.shields.io/github/stars/mom1/apiclient-pydantic-generator.svg)
![GitHub Release Date](https://img.shields.io/github/release-date/mom1/apiclient-pydantic-generator.svg)
![GitHub commits since latest release](https://img.shields.io/github/commits-since/mom1/apiclient-pydantic-generator/latest.svg)
![GitHub last commit](https://img.shields.io/github/last-commit/mom1/apiclient-pydantic-generator.svg)
[![GitHub license](https://img.shields.io/github/license/mom1/apiclient-pydantic-generator)](https://github.com/mom1/apiclient-pydantic-generator/blob/master/LICENSE)

[![PyPI](https://img.shields.io/pypi/v/apiclient-pydantic-generator.svg)](https://pypi.python.org/pypi/apiclient-pydantic-generator)
[![PyPI](https://img.shields.io/pypi/pyversions/apiclient-pydantic-generator.svg)]()
![PyPI - Downloads](https://img.shields.io/pypi/dm/apiclient-pydantic-generator.svg?label=pip%20installs&logo=python)


# apiclient-pydantic-generator

This code generator creates a ApiClient app from an openapi file.

This project uses:
  - [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator) to generate pydantic models
  - [api-client](https://github.com/MikeWooster/api-client) to create class ApiClient
  - [api-client-pydantic](https://github.com/mom1/api-client-pydantic) extension for validate request data and converting json straight to pydantic class.


This project highly inspired [fastapi-code-generator](https://github.com/koxudaxi/fastapi-code-generator)

## Installation

To install `apiclient-pydantic-generator`:
```sh
$ pip install apiclient-pydantic-generator
```

## Usage

The `apiclient-pydantic-generator` command:
```
Usage: apiclient-codegen [OPTIONS]

Options:
  -i, --input FILENAME     [required]
  -o, --output PATH        [required]
  -t, --template-dir PATH
  -b, --base_url TEXT      [default: ]
  -p, --prefix TEXT        If "My" then will be MyApiClient  [default: My]
  -a, --base_api_cls TEXT  Base class for client class  [default:
                           apiclient.APIClient]

  --install-completion     Install completion for the current shell.
  --show-completion        Show completion for the current shell, to copy it
                           or customize the installation.

  --help                   Show this message and exit.
```


## Example

### OpenAPI

<details>
  <summary>petstore.yaml</summary>
  <pre>
    <code>
      openapi: '3.0.0'
      info:
        version: 1.0.0
        title: Swagger Petstore
        license:
          name: MIT
      servers:
        - url: http://petstore.swagger.io/v1
      paths:
        /pets:
          get:
            summary: List all pets
            operationId: listPets
            tags:
              - pets
            parameters:
              - name: limit
                in: query
                description: How many items to return at one time (max 100)
                required: false
                schema:
                  type: integer
                  format: int32
            responses:
              '200':
                description: A paged array of pets
                headers:
                  x-next:
                    description: A link to the next page of responses
                    schema:
                      type: string
                content:
                  application/json:
                    schema:
                      $ref: '#/components/schemas/Pets'
              default:
                description: unexpected error
                content:
                  application/json:
                    schema:
                      $ref: '#/components/schemas/Error'
                      x-amazon-apigateway-integration:
                        uri:
                          Fn::Sub: arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${PythonVersionFunction.Arn}/invocations
                        passthroughBehavior: when_no_templates
                        httpMethod: POST
                        type: aws_proxy
          post:
            summary: Create a pet
            operationId: createPets
            tags:
              - pets
            responses:
              '201':
                description: Null response
              default:
                description: unexpected error
                content:
                  application/json:
                    schema:
                      $ref: '#/components/schemas/Error'
                      x-amazon-apigateway-integration:
                        uri:
                          Fn::Sub: arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${PythonVersionFunction.Arn}/invocations
                        passthroughBehavior: when_no_templates
                        httpMethod: POST
                        type: aws_proxy
        /pets/{petId}:
          get:
            summary: Info for a specific pet
            operationId: showPetById
            tags:
              - pets
            parameters:
              - name: petId
                in: path
                required: true
                description: The id of the pet to retrieve
                schema:
                  type: string
            responses:
              '200':
                description: Expected response to a valid request
                content:
                  application/json:
                    schema:
                      $ref: '#/components/schemas/Pets'
              default:
                description: unexpected error
                content:
                  application/json:
                    schema:
                      $ref: '#/components/schemas/Error'
          x-amazon-apigateway-integration:
            uri:
              Fn::Sub: arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${PythonVersionFunction.Arn}/invocations
            passthroughBehavior: when_no_templates
            httpMethod: POST
            type: aws_proxy
      components:
        schemas:
          Pet:
            required:
              - id
              - name
            properties:
              id:
                type: integer
                format: int64
              name:
                type: string
              tag:
                type: string
          Pets:
            type: array
            description: list of pet
            items:
              $ref: '#/components/schemas/Pet'
          Error:
            required:
              - code
              - message
            properties:
              code:
                type: integer
                format: int32
              message:
                type: string
    </code>
  </pre>
</details>

```sh
$ apiclient-codegen --input petstore.yaml --output app_petstore --prefix PetStore
```

`app_petstore/__init__.py`:
```python
from .client import PetStoreAPIClient


__all__ = ('PetStoreAPIClient', )
```

`app_petstore/client.py`:
```python
from __future__ import annotations

from apiclient import APIClient
from apiclient_pydantic import serialize_all_methods

from .endpoints import Endpoints
from .models import LimitQueryParams, PetIdPathParams, Pets


@serialize_all_methods()
class PetStoreAPIClient(APIClient):
    def list_pets(self, query_params: LimitQueryParams) -> Pets:
        """List all pets"""
        return self.get(Endpoints.list_pets, query_params)

    def create_pets(self) -> None:
        """Create a pet"""
        self.post(Endpoints.create_pets)

    def show_pet_by_id(self, path_params: PetIdPathParams) -> Pets:
        """Info for a specific pet"""
        return self.get(Endpoints.show_pet_by_id.format(**path_params))
```

`app_petstore/endpoints.py`:
```python
from apiclient import endpoint


@endpoint(base_url='http://petstore.swagger.io/v1')
class Endpoints:
    list_pets: str = '/pets'
    create_pets: str = '/pets'
    show_pet_by_id: str = '/pets/{pet_id}'
```

`app_petstore/models.py`:
```python
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet] = Field(..., description='list of pet')


class Error(BaseModel):
    code: int
    message: str


class LimitQueryParams(BaseModel):
    limit: Optional[int] = None


class PetIdPathParams(BaseModel):
    petId: str
```

Using a class:
```python
from apiclient.request_formatters import JsonRequestFormatter
from apiclient.response_handlers import JsonResponseHandler

from app_petstore import PetStoreAPIClient


pet_client = PetStoreAPIClient(response_handler=JsonResponseHandler, request_formatter=JsonRequestFormatter)
pets = pet_client.list_pets()
for pet in pets:
    print(pet.name)
```

## License

apiclient-pydantic-generator is released under the MIT License. http://www.opensource.org/licenses/mit-license
