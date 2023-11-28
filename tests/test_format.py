from apiclient_pydantic_generator.format import YapfCodeFormatter

def test_reformat():
    expect_code = """\
from enum import Enum
from pathlib import Path
from typing import Optional

import isort
from yapf.yapflib.yapf_api import FormatCode


a = {
    1: 2,
    3: 4,
}
"""
    code = """\
import isort
from yapf.yapflib.yapf_api import FormatCode
from pathlib import Path
from enum import Enum
from typing import Optional



a = {1: 2, 3: 4,}
"""
    assert YapfCodeFormatter().format_code(code) == expect_code
