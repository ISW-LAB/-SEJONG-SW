# FOCA-SW v1.0 build verification

Verification date: 2026-09-07 (Asia/Seoul)

## Environment

- Windows NT 10.0.26100, 64 bit
- Python 3.11.16
- PyInstaller 6.22.2
- Inno Setup 6.7.3
- Release dependencies from `requirements.txt`

## Checks performed

1. `python -m unittest discover -s tests -v`: 12 tests passed.
2. `python build_exe.py --onedir --clean-cache`: completed successfully.
3. `dist/FOCA-SW/FOCA-SW.exe --lang en`: startup smoke test passed.
4. `python build_updater.py`: completed successfully.
5. `dist/수종데이터업데이터.exe`: startup smoke test passed.
6. `installer.iss`: compiled successfully with Inno Setup.
7. Windows product-version metadata: version 1.0 confirmed for the core
   executable, data updater, and installer.

## Locally reproduced artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `dist/FOCA-SW/FOCA-SW.exe` | 13,185,499 | `6C40E0B97958B6BB827FBAAD8D9D8802EB9705957041F54B835C083276FE9B94` |
| `dist/수종데이터업데이터.exe` | 47,770,068 | `11463FBD28668FDAC2578C0533EE73FACAE928A25CA5ACEFE22FC4D4AED68977` |
| `installer_output/FOCA-SW_Setup_1.0.exe` | 103,238,418 | `8FDE374BDDF39101A93BB64CE92940D70988372D03DEC696FCAF869FD1F77092` |

The executable and installer are reproducible local build outputs and are not
tracked in Git. The installer is not Authenticode-signed; users should verify
the release source tag and locally generated checksum when reproducing it.
