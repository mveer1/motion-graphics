"""Provider registry. Add a provider by writing a module with a base.Provider subclass and listing it here."""
from __future__ import annotations

from typing import Dict

from .. import base
from .import_local import ImportProvider
from .kie import KieProvider
from .procedural import ProceduralProvider


def default_providers() -> Dict[str, base.Provider]:
    """Providers that need no setup are always present; remote ones report availability themselves."""
    return {"procedural": ProceduralProvider(), "import": ImportProvider(), "kie": KieProvider()}
