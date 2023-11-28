from apiclient_pydantic_generator.parser import OpenAPIParser


def test_parser(resources_folder):
    with (resources_folder / "openapi.json").open('r') as f:
        input_text = "".join(f.readlines())
        parser = OpenAPIParser(input_text)
        parser.parse()

    operations = parser.operations
    op = operations.get("#/paths/v1/query/post")
    assert op.response == 'QueryRequestOut'

