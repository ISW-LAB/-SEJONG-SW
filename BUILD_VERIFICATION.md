# FOCA-SW v4.4.2 build verification

Verification date: 2026-09-06 (Asia/Seoul)

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

## Locally reproduced artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `dist/FOCA-SW/FOCA-SW.exe` | 13,184,477 | `FE5D4081A9190D1782A9A69262C3A5F8ECBB0F9DA45AF7E6D7EDC7A2360AFFE8` |
| `dist/수종데이터업데이터.exe` | 47,766,574 | `4690BA947596602412C77D8EA103B784868FBB9F5F1CD69BDA717C46410E08DA` |
| `installer_output/FOCA-SW_Setup_4.4.2.exe` | 103,245,254 | `50F6650FA3AFD21E3DF2EB5D2CBC327788E1CDFC5AC8B6AC6AD69FF7270390A9` |

The executable and installer are reproducible local build outputs and are not
tracked in Git. The installer is not Authenticode-signed; users should verify
the release source tag and locally generated checksum when reproducing it.
