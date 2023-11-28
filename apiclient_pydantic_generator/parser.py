from __future__ import annotations

import builtins
import pathlib
import re
from typing import (
    Any, Callable, DefaultDict, Dict, Iterable, List,
    Mapping, Optional, Pattern, Sequence, Set, Type, Union,
)
from urllib.parse import ParseResult

import stringcase
from datamodel_code_generator import (
    DefaultPutDict, LiteralType, OpenAPIScope, PythonVersion, cached_property, snooper_to_methods,
)
from datamodel_code_generator.imports import Import, Imports
from datamodel_code_generator.model import (
    DataModel, DataModelFieldBase, pydantic as pydantic_model,
)
from datamodel_code_generator.model.pydantic import DataModelField
from datamodel_code_generator.parser.jsonschema import JsonSchemaObject
from datamodel_code_generator.parser.openapi import (
    OpenAPIParser as OpenAPIModelParser, ParameterLocation,
    ParameterObject, ReferenceObject, RequestBodyObject, ResponseObject,
)
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType, DataTypeManager, StrictTypes
from pydantic import BaseModel, validator

RE_APPLICATION_JSON_PATTERN: Pattern[str] = re.compile(r'^application/.*json$')


class CachedPropertyModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        keep_untouched = (cached_property,)


class Response(BaseModel):
    status_code: str
    description: Optional[str]
    contents: Dict[str, JsonSchemaObject]


class Request(BaseModel):
    description: Optional[str]
    contents: Dict[str, JsonSchemaObject]
    required: bool


class UsefulStr(str):
    @classmethod
    def __get_validators__(cls) -> Any:
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> Any:
        return cls(v)

    @property
    def snakecase(self) -> str:
        return stringcase.snakecase(self)

    @property
    def pascalcase(self) -> str:
        return stringcase.pascalcase(self)

    @property
    def camelcase(self) -> str:
        return stringcase.camelcase(self)


class Argument(CachedPropertyModel):
    name: UsefulStr
    type_hint: UsefulStr
    default: Optional[UsefulStr]
    default_value: Optional[UsefulStr]
    required: bool

    def __str__(self) -> str:
        return self.argument

    @cached_property
    def argument(self) -> str:
        name = self.name if self.name not in vars(builtins) else f'{self.name}_'
        if self.default is None and self.required:
            return f'{name}: {self.type_hint}'
        return f'{name}: {self.type_hint} = {self.default}'


class Operation(CachedPropertyModel):
    method: UsefulStr
    path: UsefulStr
    operationId: Optional[UsefulStr]  # noqa: N815
    description: Optional[str]
    summary: Optional[str]
    parameters: List[Dict[str, Any]] = []
    path_argument: Optional[Argument] = None
    query_argument: Optional[Argument] = None
    responses: Dict[UsefulStr, Any] = {}
    deprecated: bool = False
    imports: List[Import] = []
    security: Optional[List[Dict[str, List[str]]]] = None
    tags: Optional[List[str]]
    arguments: str = ''
    snake_case_arguments: str = ''
    request: Optional[Argument] = None
    response: str = ''

    @cached_property
    def type(self) -> UsefulStr:  # noqa: A003
        """backwards compatibility."""
        return self.method

    @cached_property
    def root_path(self) -> UsefulStr:
        paths = self.path.split('/')
        return UsefulStr(paths[1] if len(paths) > 1 else '')

    @cached_property
    def snake_case_path(self) -> str:
        return re.sub(r'{([^\}]+)}', lambda m: stringcase.snakecase(m.group()), self.path)

    @cached_property
    def function_name(self) -> str:
        if self.operationId:
            name: str = self.operationId
        else:
            path = re.sub(r'/{|/', '_', self.snake_case_path).replace('}', '')
            name = f'{self.type}{path}'
        return stringcase.snakecase(name)

    @validator('parameters')
    def safe_name_parameters(cls, parameters):  # noqa: N805
        built = vars(builtins)
        for items in parameters:
            name = safe_name = items.get('name')
            if name and name in built:
                safe_name = f'{name}_'
            items['safe_name'] = safe_name
        return parameters


@snooper_to_methods(max_variable_length=None)
class OpenAPIParser(OpenAPIModelParser):
    def __init__(
        self,
        source: Union[str, pathlib.Path, List[pathlib.Path], ParseResult],
        *,
        data_model_type: Type[DataModel] = pydantic_model.BaseModel,
        data_model_root_type: Type[DataModel] = pydantic_model.CustomRootType,
        data_type_manager_type: Type[DataTypeManager] = pydantic_model.DataTypeManager,
        data_model_field_type: Type[DataModelFieldBase] = pydantic_model.DataModelField,
        base_class: Optional[str] = None,
        custom_template_dir: Optional[pathlib.Path] = None,
        extra_template_data: Optional[DefaultDict[str, Dict[str, Any]]] = None,
        target_python_version: PythonVersion = PythonVersion.PY_37,
        dump_resolve_reference_action: Optional[Callable[[Iterable[str]], str]] = None,
        validation: bool = False,
        field_constraints: bool = False,
        snake_case_field: bool = False,
        strip_default_none: bool = False,
        aliases: Optional[Mapping[str, str]] = None,
        allow_population_by_field_name: bool = False,
        apply_default_values_for_required_fields: bool = False,
        force_optional_for_required_fields: bool = False,
        class_name: Optional[str] = None,
        use_standard_collections: bool = False,
        base_path: Optional[pathlib.Path] = None,
        use_schema_description: bool = False,
        reuse_model: bool = False,
        encoding: str = 'utf-8',
        enum_field_as_literal: Optional[LiteralType] = None,
        set_default_enum_member: bool = False,
        strict_nullable: bool = False,
        use_generic_container_types: bool = False,
        enable_faux_immutability: bool = False,
        remote_text_cache: Optional[DefaultPutDict[str, str]] = None,
        disable_appending_item_suffix: bool = False,
        strict_types: Optional[Sequence[StrictTypes]] = None,
        empty_enum_field_name: Optional[str] = None,
        custom_class_name_generator: Optional[Callable[[str], str]] = None,
        field_extra_keys: Optional[Set[str]] = None,
        field_include_all_keys: bool = False,
        skip_deprecated: bool = True,
    ):
        super().__init__(
            source=source,
            data_model_type=data_model_type,
            data_model_root_type=data_model_root_type,
            data_type_manager_type=data_type_manager_type,
            data_model_field_type=data_model_field_type,
            base_class=base_class,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            target_python_version=target_python_version,
            dump_resolve_reference_action=dump_resolve_reference_action,
            validation=validation,
            field_constraints=field_constraints,
            snake_case_field=snake_case_field,
            strip_default_none=strip_default_none,
            aliases=aliases,
            allow_population_by_field_name=allow_population_by_field_name,
            apply_default_values_for_required_fields=apply_default_values_for_required_fields,
            force_optional_for_required_fields=force_optional_for_required_fields,
            class_name=class_name,
            use_standard_collections=use_standard_collections,
            base_path=base_path,
            use_schema_description=use_schema_description,
            reuse_model=reuse_model,
            encoding=encoding,
            enum_field_as_literal=enum_field_as_literal,
            set_default_enum_member=set_default_enum_member,
            strict_nullable=strict_nullable,
            use_generic_container_types=use_generic_container_types,
            enable_faux_immutability=enable_faux_immutability,
            remote_text_cache=remote_text_cache,
            disable_appending_item_suffix=disable_appending_item_suffix,
            strict_types=strict_types,
            empty_enum_field_name=empty_enum_field_name,
            custom_class_name_generator=custom_class_name_generator,
            field_extra_keys=field_extra_keys,
            field_include_all_keys=field_include_all_keys,
            openapi_scopes=[OpenAPIScope.Schemas, OpenAPIScope.Paths],
        )
        self.operations: Dict[str, Operation] = {}
        self._temporary_operation: Dict[str, Any] = {}
        self.imports_for_endpoints: Imports = Imports()
        self.imports_for_endpoints.append(Import(from_='.endpoints', import_='Endpoints'))
        self.data_types: List[DataType] = []
        self.params_classes = set()
        self.skip_deprecated = skip_deprecated

    def parse_info(self) -> Optional[List[Dict[str, List[str]]]]:
        return self.raw_obj.get('info')

    def parse_servers(self) -> Optional[List[Dict[str, List[str]]]]:
        return self.raw_obj.get('servers')

    def parse_parameters(self, parameters: ParameterObject, path: List[str]) -> None:
        super().parse_parameters(parameters, path)
        self._temporary_operation['_parameters'].append(parameters)

    def get_parameter_field(
        self,
        parameters: ParameterObject,
        snake_case: bool,
        path: List[str],
    ) -> Optional[Argument]:
        orig_name = name = parameters.name

        if snake_case:
            name = stringcase.snakecase(orig_name)
        name, alias = self.model_resolver.get_valid_field_name_and_alias(name)

        schema: Optional[JsonSchemaObject] = None
        data_type: Optional[DataType] = None
        for content in parameters.content.values():
            if isinstance(content.schema_, ReferenceObject):
                data_type = self.get_ref_data_type(content.schema_.ref)
                ref_model = self.get_ref_model(content.schema_.ref)
                schema = JsonSchemaObject.parse_obj(ref_model)
            else:
                schema = content.schema_
            break
        if not data_type:
            if not schema:
                schema = parameters.schema_
            data_type = self.parse_schema(name, schema, [*path, name])
        if not schema:
            return None

        field = DataModelField(
            name=name,
            data_type=data_type,
            required=parameters.required or parameters.in_ == ParameterLocation.path,
            alias=alias,
            default=repr(schema.default) if schema.has_default else None,
        )
        return field

    def get_arguments(self, snake_case: bool, path: List[str]) -> str:
        return ', '.join(argument.argument for argument in self.get_argument_list(snake_case, path))

    def get_argument_list(self, snake_case: bool, path: List[str]) -> List[Argument]:
        arguments: List[Argument] = []
        params_fields_path: List[DataModelField] = []
        params_fields_query: List[DataModelField] = []
        parameters = self._temporary_operation.get('_parameters')
        if parameters:
            for parameter in parameters:
                parameter_field = self.get_parameter_field(parameter, snake_case, [*path, 'parameters'])
                if parameter_field:
                    if parameter.in_ == ParameterLocation.path:
                        params_fields_path.append(parameter_field)
                    elif parameter.in_ == ParameterLocation.query:
                        params_fields_query.append(parameter_field)
            if params_fields_path:
                arguments.append(self.create_pydantic_argument(path, params_fields_path, 'PathParams'))
                self._temporary_operation['path_argument'] = arguments[-1]
            if params_fields_query:
                arguments.append(self.create_pydantic_argument(path, params_fields_query, 'QueryParams'))
                self._temporary_operation['query_argument'] = arguments[-1]

        request = self._temporary_operation.get('_request')
        if request:
            arguments.append(request)
            self._temporary_operation['request'] = request

        positional_argument: bool = False
        for argument in arguments:
            if positional_argument and argument.required and argument.default is None:
                argument.default = UsefulStr('...')
            positional_argument = argument.required

        return arguments

    def create_pydantic_argument(self, path: List[str], fields: List[DataModelField], suffix: str):
        original_name = self._get_model_name('_'.join(field.name for field in fields), '', suffix=suffix)
        name = self.model_resolver.get_class_name(
            name=original_name,
            unique=False,
            reserved_name=None,
            singular_name=None,
            singular_name_suffix=None,
        )
        reference = Reference(
            path=self.model_resolver.join_path([*path, suffix]),
            original_name=original_name,
            name=name,
        )
        data_model_type = self.data_model_type(
            reference=reference,
            fields=fields,
            custom_base_class=self.base_class,
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
        )
        data_type = self.data_type(reference=reference)
        ret = Argument(
            name=stringcase.snakecase(suffix),
            type_hint=data_type.type_hint,
            required=True,
        )
        if name not in self.params_classes:
            self.results.append(data_model_type)
            self.params_classes.add(name)
            self.data_types.append(data_type)
        return ret

    def parse_request_body(
        self,
        name: str,
        request_body: RequestBodyObject,
        path: List[str],
    ) -> None:
        super().parse_request_body(name, request_body, path)
        arguments: List[Argument] = []
        for (
            media_type,
            media_obj,
        ) in request_body.content.items():
            if isinstance(media_obj.schema_, (JsonSchemaObject, ReferenceObject)):  # pragma: no cover
                if RE_APPLICATION_JSON_PATTERN.match(media_type):
                    if isinstance(media_obj.schema_, ReferenceObject):
                        data_type = self.get_ref_data_type(media_obj.schema_.ref)
                    else:
                        data_type = self.parse_schema(name, media_obj.schema_, [*path, media_type])
                    arguments.append(
                        Argument(
                            name='body',
                            type_hint=data_type.type_hint,
                            required=request_body.required,
                        ))
                    self.data_types.append(data_type)
        self._temporary_operation['_request'] = arguments[0] if arguments else None

    def parse_responses(
        self,
        name: str,
        responses: Dict[str, Union[ResponseObject, ReferenceObject]],
        path: List[str],
    ) -> Dict[str, Dict[str, DataType]]:
        data_types = super().parse_responses(name, responses, path)
        type_hint = 'None'
        for code in [200, 201, 202]:
            response_model = self._get_response(code, data_types)
            if response_model:
                type_hint = response_model.type_hint  # TODO: change to lazy loading
                break
        self._temporary_operation['response'] = type_hint
        return data_types

    def _get_response(self, status_code: int, data_types: dict[str, dict[str, DataType]]):
        response_model = data_types.get(f"{status_code}")
        if response_model:
            data_type = list(response_model.values())[0]
            if data_type:
                self.data_types.append(data_type)
            return data_type.type_hint

    def parse_operation(
        self,
        raw_operation: Dict[str, Any],
        path: List[str],
    ) -> None:
        if self.skip_deprecated and raw_operation.get('deprecated'):
            return
        self._temporary_operation = {}
        self._temporary_operation['_parameters'] = []
        super().parse_operation(raw_operation, path)

        resolved_path = self.model_resolver.resolve_ref(path)
        path_name, method = path[-2:]

        self._temporary_operation['arguments'] = self.get_arguments(snake_case=self.snake_case_field, path=path)

        self.operations[resolved_path] = Operation(
            **raw_operation,
            **self._temporary_operation,
            path=f'/{path_name}',  # type: ignore
            method=method,  # type: ignore
        )
