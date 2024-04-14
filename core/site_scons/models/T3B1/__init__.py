from __future__ import annotations

from typing import Optional

from .emulator import configure as emul
from .trezor_t3b1_revB import configure as configure_revB


def configure_board(
    revision: Optional[int | str],
    features_wanted: list[str],
    env: dict,  # type: ignore
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
):
    if revision is None:
        revision = "B"
    if revision == "emulator":
        return emul(env, features_wanted, defines, sources, paths)
    elif revision == "B":
        return configure_revB(env, features_wanted, defines, sources, paths)
    raise Exception("Unknown model_t3b1_version")
