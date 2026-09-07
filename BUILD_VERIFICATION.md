# FORECAST-SW v1.0 build verification

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
3. `dist/FORECAST-SW/FORECAST-SW.exe --lang en`: startup smoke test passed.
4. `python build_updater.py`: completed successfully.
5. `dist/수종데이터업데이터.exe`: startup smoke test passed.
6. `installer.iss`: compiled successfully with Inno Setup.
7. Windows product-version metadata: version 1.0 confirmed for the core
   executable, data updater, and installer.

## Locally reproduced artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `dist/FORECAST-SW/FORECAST-SW.exe` | 13,185,536 | `36F5E9F9851AB16C87F4CF133AEF56ACD1F5098A876361F0D22BF9B05AE2276F` |
| `dist/수종데이터업데이터.exe` | 47,772,242 | `68D4A946F3EDDED61959A439ED920736FDF119CA9B55ADC713C8101F3581133C` |
| `installer_output/FORECAST-SW_Setup_1.0.exe` | 103,241,446 | `13EFD0C6E0D2367E2F78D859C0E6F675182DDFCBE9C5A54F44013B90E79A1F11` |

The executable and installer are reproducible local build outputs and are not
tracked in Git. The installer is not Authenticode-signed; users should verify
the release source tag and locally generated checksum when reproducing it.
