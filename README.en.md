# Carbon Storage Assessment Module for Restoration Sites

A PyQt5 port of the original MATLAB App Designer application
(`Carbon_251002_5.mlapp` / `Carbon2_251013_1.mlapp`). The project builds two
executables: the **carbon storage assessment module** (the core software) and the
**species data updater**, which applies a new species dataset and rebuilds the
core executable.

The interface, figures and Excel output are available in **Korean and English**.
In English mode every species is labelled with its scientific name
(e.g. *Pinus densiflora*), so tables and figures can be used directly in a
manuscript.

## Repository layout

```
├── main.py                  ← entry point (Carbon1 · Carbon2 in one tabbed window)
├── build_exe.py             ← builds the core software (main.py → module executable)
├── build_updater.py         ← builds the updater (updater_app.py → updater executable)
├── updater_app.py           ← updater application (runs build_exe.py logic internally)
├── updater_빌드.bat         ← Windows batch wrapper for build_updater.py
├── 실행_rudckd.bat          ← Windows batch launcher (conda env, dependency check, run)
├── installer.iss            ← Inno Setup script for a Windows installer
├── requirements.txt         ← runtime dependencies
├── species_data.json        ← combined species dataset (trees, shrubs, domestic, international)
├── icon.ico                 ← application icon
└── carbon_calculator/       ← core package
    ├── data.py / data2.py          — species coefficients and allometric equations
    ├── calculations.py             — carbon storage calculation
    ├── equation_eval.py            — evaluation of equations given as strings
    ├── widgets.py / plotting.py    — shared widgets / figures
    ├── theme.py / font_config.py / ui_scale.py  — theme, fonts, DPI scaling
    ├── excel_export.py             — Excel export
    ├── i18n.py / translations.py / species_names_en.py  — Korean/English display layer
    ├── language_dialog.py          — language selection at first start
    ├── main_window.py              — Carbon1 (native restoration species)
    ├── main_window2.py             — Carbon2 (domestic and international species)
    ├── combined_window.py          — integrated main window with one tab per site
    └── tree_simulation/            — 3D vegetation growth visualization (PyVista/VTK)
```

---

## 0. Prerequisites (once)

```powershell
pip install -r requirements.txt
```

Python **3.10 or later** is required, because the 3D visualization depends on
`pyvista >= 0.48`. Everything else runs on 3.9.

The build scripts (`build_exe.py`, `build_updater.py`) do **not** require a manual
PyInstaller installation: they create a dedicated build virtual environment at
`~/.carboncalc_build_venv` and install what they need there. The first build takes
several minutes; later builds reuse the environment.

> **Conda users:** activate the environment before building
> (`conda activate <env>`, then `python build_exe.py`). Running the interpreter by
> its full path without activating leaves `<env>/Library/bin` off `PATH`, so
> PyInstaller cannot find `ffi.dll` and the resulting executable fails at startup
> with `ImportError: DLL load failed while importing _ctypes`.

---

## 1. Run from source

```powershell
python main.py
python main.py --lang en     # start in English, skipping the language prompt
python main.py --lang ko     # start in Korean
```

Carbon1 (native restoration species) and Carbon2 (domestic and international
species) are managed as per-site tabs in a single window.

On first start the application asks for a display language. The choice is stored
and reused; it can be changed at any time from the **Language** menu, which
restarts the application in the selected language.

---

## 2. Build the core software

```powershell
python build_exe.py              # onefile (single executable) — default
python build_exe.py --onedir     # folder layout (faster startup)
python build_exe.py --debug      # show a console window (for diagnosing errors)
python build_exe.py --upx        # enable UPX compression (smaller output)
python build_exe.py --clean-cache        # remove build/ and dist/ first
python build_exe.py --rebuild-venv       # force re-creation of the build venv
```

- Output: `dist/탄소저장량측정모듈.exe` (onefile) or `dist/탄소저장량측정모듈/` (onedir)
- If `species_data.json` is present in the project root it is bundled into the
  executable and loaded at runtime.
- Use `--rebuild-venv` whenever `requirements.txt` changes. The build venv is
  considered reusable when PyInstaller and PyQt5 import successfully, so a venv
  built for an older dependency set is otherwise silently reused.
- If the executable exits immediately, rebuild with `--debug` and read the
  console output.

---

## 3. Build the species data updater

```powershell
python build_updater.py
```

or, on Windows:

```powershell
updater_빌드.bat
```

- Output: `dist/수종데이터업데이터.exe`
- This executable bundles the **entire source** of the core software
  (`carbon_calculator`, `main.py`, `build_exe.py`, ...), so it can be distributed
  on its own.
- On launch it opens `species_data.json` in a **table editor** (four tabs — trees, shrubs,
  domestic, international; double-click cells to edit; add/delete species; per-environment
  coefficients for trees; validation before saving; a `.bak` backup on save). After editing,
  it offers two ways to apply the data:
  1. **Rebuild executable** — takes a new `species_data.json` and rebuilds the core
     executable from the bundled source (requires Python 3.10+ on the machine).
  2. **Apply JSON** — copies `species_data.json` next to an existing executable
     (no Python required; effective from the next launch).

---

## 4. Windows installer — optional

1. Build in folder form: `python build_exe.py --onedir`
2. Install [Inno Setup 6](https://jrsoftware.org/isdl.php)
3. Compile with either
   - Inno Setup Compiler: open `installer.iss`, then `Build > Compile`, or
   - the command line: `"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss`
4. Output: `installer_output/탄소저장량측정모듈_Setup_3.0.exe`

---

## 5. Updating the species dataset

Edit species, coefficients, equations and ranges in the table editor of the updater
(`수종데이터업데이터.exe`) and save (recommended), or edit `species_data.json` by hand and
rebuild with `python build_exe.py`. Apply it to an already-distributed executable through
the updater (section 3). When adding a species, fill in the scientific-name column so that
English mode can label it.

`species_data.json` also carries the English labels:

- `SPECIES_EN` — base species name → scientific name. Qualifiers such as
  `(지상부)` or `(전체, 경남)` are translated automatically
  (`후박나무(지상부)` → *Machilus thunbergii* (aboveground)).
- `ENVIRONMENTS_EN` — restoration environment names.

When adding a species, add its scientific name to `SPECIES_EN` as well; otherwise
English mode falls back to the Korean name rather than inventing a binomial.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'PyQt5'` | `pip install -r requirements.txt` |
| `Could not find a version that satisfies pyvista>=0.48` | The environment is Python 3.9 or older; the 3D view needs 3.10+ |
| Built executable exits with `DLL load failed while importing _ctypes` | Activate the conda environment before building (see Prerequisites) |
| 3D view missing from a built executable | Rebuild with `python build_exe.py --rebuild-venv` |
| PyInstaller errors during the build | `python build_exe.py --rebuild-venv` |
| Korean text renders as boxes | Confirm the Windows font "Malgun Gothic" is installed |
| Executable closes immediately | Rebuild with `python build_exe.py --debug` and read the console |
| Text too large or too small | Adjust `FONT_SIZE_DELTA` in `carbon_calculator/font_config.py` |

---

한국어 설명은 [README.md](README.md) 를 참고하세요.
