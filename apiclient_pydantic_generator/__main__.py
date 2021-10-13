import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import toml
import typer
from datamodel_code_generator import Error, PythonVersion, chdir
from datamodel_code_generator.__main__ import Config, Exit
from datamodel_code_generator.imports import Import, Imports
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType
from jinja2 import Environment, FileSystemLoader
from pydantic.networks import AnyUrl

from .format import YapfCodeFormatter
from .parser import OpenAPIParser, Operation


app = typer.Typer()

BUILTIN_TEMPLATE_DIR = Path(__file__).parent / 'templates'

MODEL_PATH: Path = Path('models.py')


@app.command()
def main(
    input_file: typer.FileText = typer.Option(..., '--input', '-i'),  # noqa: B008
    output_dir: Path = typer.Option(..., '--output', '-o'),  # noqa: B008
    template_dir: Optional[Path] = typer.Option(None, '--template-dir', '-t'),  # noqa: B008
    base_url: Optional[str] = typer.Option('', '--base_url', '-b'),  # noqa: B008
    prefix_api_cls: Optional[str] = typer.Option(  # noqa: B008
        'My',
        '--prefix',
        '-p',
        help='If "My" then will be MyApiClient',
    ),
    base_apiclient_cls: Optional[str] = typer.Option(  # noqa: B008
        'apiclient.APIClient',
        '--base_api_cls',
        '-a',
        help='Base class for client class',
    ),
) -> None:
    input_name: str = input_file.name
    input_text: str = input_file.read()

    pyproject_toml_path = Path().resolve() / 'pyproject.toml'
    if pyproject_toml_path.is_file():
        pyproject_toml: Dict[str, Any] = {
            k.replace('-', '_'): v
            for k, v in toml.load(str(pyproject_toml_path)).get('tool', {}).get('datamodel-codegen', {}).items()
        }
    else:
        pyproject_toml = {}

    try:
        data_config = Config.parse_obj(pyproject_toml)
    except Error as e:
        print(e.message, file=sys.stderr)
        return Exit.ERROR
    return generate_code(
        input_name,
        input_text,
        output_dir,
        template_dir,
        base_url,
        data_config,
        prefix_api_cls,
        base_apiclient_cls,
    )


def _get_most_of_reference(data_type: DataType) -> Optional[Reference]:
    if data_type.reference:
        return data_type.reference
    for data_type in data_type.data_types:
        reference = _get_most_of_reference(data_type)
        if reference:
            return reference
    return None


def make_aliases(base_aliases: str) -> Optional[Dict[str, str]]:
    with base_aliases as data:
        try:
            aliases = json.load(data)
        except json.JSONDecodeError as e:
            print(f'Unable to load alias mapping: {e}', file=sys.stderr)
            raise typer.Exit(code=Exit.ERROR)
    if not isinstance(aliases, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in aliases.items()):
        print(
            'Alias mapping must be a JSON string mapping (e.g. {"from": "to", ...})',
            file=sys.stderr,
        )
        raise typer.Exit(code=Exit.ERROR)
    return aliases


def generate_code(
    input_name: str,
    input_text: str,
    output_dir: Path,
    template_dir: Optional[Path],
    base_url: Optional[AnyUrl],
    data_config: Config,
    prefix_api_cls: Optional[str],
    base_apiclient_cls: Optional[str],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    template_dir = template_dir or BUILTIN_TEMPLATE_DIR

    aliases = None
    if data_config.aliases is not None:
        aliases = make_aliases(data_config.aliases)

    parser = OpenAPIParser(
        input_text,
        target_python_version=data_config.target_python_version,
        base_class=data_config.base_class,
        custom_template_dir=data_config.custom_template_dir,
        validation=data_config.validation,
        field_constraints=data_config.field_constraints,
        snake_case_field=data_config.snake_case_field,
        strip_default_none=data_config.strip_default_none,
        # TODO: Support extra_template_data from `datamodel-codegen`
        # extra_template_data - extra_template_data
        aliases=aliases,
        allow_population_by_field_name=data_config.allow_population_by_field_name,
        apply_default_values_for_required_fields=data_config.use_default,
        force_optional_for_required_fields=data_config.force_optional,
        class_name=data_config.class_name,
        use_standard_collections=data_config.use_standard_collections,
        use_schema_description=data_config.use_schema_description,
        reuse_model=data_config.reuse_model,
        encoding=data_config.encoding,
        enum_field_as_literal=data_config.enum_field_as_literal,
        set_default_enum_member=data_config.set_default_enum_member,
        strict_nullable=data_config.strict_nullable,
        use_generic_container_types=data_config.use_generic_container_types,
        enable_faux_immutability=data_config.enable_faux_immutability,
        disable_appending_item_suffix=data_config.disable_appending_item_suffix,
        strict_types=data_config.strict_types,
        empty_enum_field_name=data_config.empty_enum_field_name,
        field_extra_keys=data_config.field_extra_keys,
        field_include_all_keys=data_config.field_include_all_keys,
    )
    with chdir(output_dir):
        models = parser.parse()
    if not models:
        return
    elif isinstance(models, str):
        output = output_dir / MODEL_PATH
        modules = {output: (models, input_name)}
    else:
        raise Exception('Modular references are not supported in this version')

    environment: Environment = Environment(loader=FileSystemLoader(
        template_dir if template_dir else f'{Path(__file__).parent}/templates',
        encoding='utf8',
    ))
    base_cls = Import.from_full_path(base_apiclient_cls)
    imports = Imports()
    imports.update(parser.imports)
    for data_type in parser.data_types:
        reference = _get_most_of_reference(data_type)
        if reference:
            imports.append(data_type.all_imports)
            imports.append(Import.from_full_path(f'.{MODEL_PATH.stem}.{reference.name}'))
    for from_, imports_ in parser.imports_for_endpoints.items():
        imports[from_].update(imports_)
    results: Dict[Path, str] = {}
    # TODO: Choose formater from cli
    code_formatter = YapfCodeFormatter(PythonVersion.PY_38, Path().resolve())
    sorted_operations: List[Operation] = sorted(parser.operations.values(), key=lambda m: m.path)
    for target in template_dir.rglob('*'):
        relative_path = target.relative_to(template_dir)
        result = environment.get_template(str(relative_path)).render(
            operations=sorted_operations,
            imports=imports,
            info=parser.parse_info(),
            servers=parser.parse_servers(),
            base_url=base_url,
            prefix_cls=prefix_api_cls,
            base_cls=base_cls,
        )
        results[relative_path] = code_formatter.format_code(result)

    for path, code in results.items():
        with output_dir.joinpath(path.with_suffix('.py')).open('wt') as file:
            print(code.rstrip(), file=file)

    for path, body_and_filename in modules.items():
        body, _ = body_and_filename
        if path is None:
            file = None
        else:
            if not path.parent.exists():
                path.parent.mkdir(parents=True)
            file = path.open('wt', encoding='utf8')

        if body:
            print(code_formatter.format_code(body).rstrip(), file=file)

        if file is not None:
            file.close()


if __name__ == '__main__':
    typer.run(main)
