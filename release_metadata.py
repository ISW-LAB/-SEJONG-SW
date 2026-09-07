# SPDX-License-Identifier: MIT
"""Generate Windows version metadata for FOCA-SW release executables."""

from __future__ import annotations

import os
from pathlib import Path

from carbon_calculator.version import __version__


def _version_quad(version: str) -> tuple[int, int, int, int]:
    """Convert a public version such as ``1.0`` to a Windows version tuple."""
    parts = version.split(".")
    if not parts or any(not part.isdigit() for part in parts) or len(parts) > 4:
        raise ValueError(f"Unsupported release version: {version!r}")
    parsed = tuple(int(part) for part in parts)
    return parsed + (0,) * (4 - len(parsed))


def write_windows_version_info(
    output_dir: Path,
    *,
    internal_name: str,
    original_filename: str,
    file_description: str,
) -> Path | None:
    """Write a PyInstaller-compatible version resource for Windows builds."""
    if os.name != "nt":
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    version_file = output_dir / f"{internal_name}_version_info.txt"
    version_quad = _version_quad(__version__)
    version_file.write_text(
        f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_quad},
    prodvers={version_quad},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'FOCA-SW contributors'),
          StringStruct('FileDescription', {file_description!r}),
          StringStruct('FileVersion', {__version__!r}),
          StringStruct('InternalName', {internal_name!r}),
          StringStruct('LegalCopyright', 'Copyright (c) 2026 FOCA-SW contributors'),
          StringStruct('OriginalFilename', {original_filename!r}),
          StringStruct('ProductName', 'FOCA-SW'),
          StringStruct('ProductVersion', {__version__!r})
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )
    return version_file
