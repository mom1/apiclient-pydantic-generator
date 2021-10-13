from enum import Enum
from pathlib import Path
from typing import Optional

import isort
from yapf.yapflib.yapf_api import FormatCode


class PythonVersion(Enum):
    PY_36 = '3.6'
    PY_37 = '3.7'
    PY_38 = '3.8'
    PY_39 = '3.9'

    @property
    def has_literal_type(self) -> bool:  # pragma: no cover
        return self.value >= self.PY_38.value  # type: ignore


def is_supported_in_yapf(python_version: PythonVersion) -> bool:  # pragma: no cover
    return True


class YapfCodeFormatter:
    def __init__(self, _: PythonVersion = None, settings_path: Optional[Path] = None):
        if not settings_path:
            settings_path = Path().resolve()
        self.settings_path: str = str(settings_path)
        self.pyproject_path: str = str(settings_path / 'pyproject.toml')
        if isort.__version__.startswith('4.'):
            self.isort_config = None
        else:
            self.isort_config = isort.Config(settings_path=self.settings_path)

    def format_code(self, code: str) -> str:
        code = self.apply_yapf(code)
        code = self.apply_isort(code)
        return code

    def apply_yapf(self, code: str) -> str:
        formated_code, changed = FormatCode(code, style_config=self.pyproject_path)
        return formated_code

    if isort.__version__.startswith('4.'):

        def apply_isort(self, code: str) -> str:
            return isort.SortImports(file_contents=code, settings_path=self.settings_path).output
    else:

        def apply_isort(self, code: str) -> str:
            return isort.code(code, config=self.isort_config)
