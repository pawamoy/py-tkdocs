# from __future__ import annotations

from typing import Final, get_type_hints

name: Final[str] = "final"

class Class:
    value: Final = 3000

# get_type_hints(Class)
