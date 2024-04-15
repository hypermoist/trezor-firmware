from __future__ import annotations

from .. import get_hw_model_as_number


def configure(
    env: dict,
    features_wanted: list[str],
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
) -> list[str]:

    board = "T2T1/boards/t2t1-unix.h"
    hw_model = get_hw_model_as_number("T2T1")
    hw_revision = 0
    mcu = "STM32F427xx"

    features = []
    defines += [mcu]
    defines += [f'TREZOR_BOARD=\\"{board}\\"']
    defines += [f"HW_MODEL={hw_model}"]
    defines += [f"HW_REVISION={hw_revision}"]
    defines += [f"MCU_TYPE={mcu}"]
    defines += ["FLASH_BIT_ACCESS=1"]
    defines += ["FLASH_BLOCK_WORDS=1"]

    if "dma2d" in features_wanted:
        features.append("dma2d")
        sources += ["embed/lib/dma2d_emul.c"]
        defines += ["USE_DMA2D"]

    if "sd_card" in features_wanted:
        features.append("sd_card")
        sources += [
            "embed/trezorhal/unix/sdcard.c",
            "embed/extmod/modtrezorio/ff.c",
            "embed/extmod/modtrezorio/ffunicode.c",
        ]

    if "sbu" in features_wanted:
        sources += ["embed/trezorhal/unix/sbu.c"]

    if "input" in features_wanted:
        features.append("touch")

    features.append("backlight")

    sources += ["embed/models/T2T1/model_T2T1_layout.c"]

    return features
