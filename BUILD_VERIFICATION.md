# FOCA-SW v4.4.1 build verification

Verification date: 2026-09-06 (Asia/Seoul)

## Environment

- Windows NT 10.0.26100, 64 bit
- Python 3.11.16
- PyInstaller 6.22.2
- Inno Setup 6.7.3
- Release dependencies from `requirements.txt`

## Checks performed

1. `python -m unittest discover -s tests -v`: 11 tests passed.
2. `python build_exe.py --onedir --clean-cache`: completed successfully.
3. `dist/FOCA-SW/FOCA-SW.exe --lang en`: startup smoke test passed.
4. `python build_updater.py`: completed successfully.
5. `dist/수종데이터업데이터.exe`: startup smoke test passed.
6. `installer.iss`: compiled successfully with Inno Setup.

## Locally reproduced artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `dist/FOCA-SW/FOCA-SW.exe` | 13,184,074 | `06319A20E21A9404C5BA68E7A7578879516D061508C1F35C4676029A8BF990D5` |
| `dist/수종데이터업데이터.exe` | 47,766,249 | `628B497F49B6F9832897EE12FF2BFA169215DBE9773F4D4743F228187B1358E7` |
| `installer_output/FOCA-SW_Setup_4.4.1.exe` | 103,241,556 | `D3473D3E5A82333E32C238534822A00F03341755BB0CD4FF9BF40681FD7A44F5` |

The executable and installer are reproducible local build outputs and are not
tracked in Git. The installer is not Authenticode-signed; users should verify
the release source tag and locally generated checksum when reproducing it.

