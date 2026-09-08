# FORECAST-SW - Forest Carbon Estimation and Scenario Analysis Software for Restoration Sites

A PyQt5 port of the original MATLAB App Designer application
(`Carbon_251002_5.mlapp` / `Carbon2_251013_1.mlapp`). The project builds two
executables: the **FORECAST-SW Assessment Application** (`FORECAST-SW.exe`) and
the **FORECAST-SW Equation Library Manager**
(`FORECAST-SW-Equation-Library-Manager.exe`). The manager edits, validates,
backs up, and deploys allometric equation records used by the assessment
application.

The version 1.0 scientific library separates its user-facing and compatibility
coverage. The primary site-assessment workflow exposes **22 native records**
(seven tree and 15 shrub records). A further **55 compatibility records**
(30 domestic and 25 international records) are maintained in the Equation
Library Manager and equation evaluator but are not selectable in the primary
workflow. Together,
the 77 named records implement 79 executable equations. This distinction is
important when interpreting the software's current operational coverage.

The site category stored with each project is descriptive metadata. It does
not select or modify the allometric coefficients in this release; every site
uses the species-level default record from the validated library.

All user-facing diameter inputs and outputs use centimetres: tree diameter at
breast height (DBH) and shrub root-collar diameter (RCD) are reported in cm in
the interface, tables, plots, visualizations, and XLSX files. The 15 legacy
shrub equations retain their original millimetre-based fitted coefficients for
scientific traceability. The analytical adapter converts RCD from cm to the
equation-native predictor only at evaluation, so existing carbon estimates are
unchanged.

Before calculation, the assessment application validates the mixed inventory
against the configured site area. Version 1.0 assigns input-guard footprints
of 1.00 m² per tree and 0.25 m² per shrub and blocks the calculation when their
combined requirement exceeds the site area. These configurable values prevent
accidental over-entry; they are not species-specific planting recommendations.

The multi-site comparison reports both total carbon stock and area-normalized
carbon density. For each site, the shared analytical service calculates
`total carbon (kg C) / site area (m²)` and reports the result in `kg C/m²`.
Changing site area alone therefore changes the normalization denominator but
does not rescale the submitted inventory or its total carbon stock. The
dashboard and combined XLSX report present total stock and normalized density
as paired charts and retain the underlying numerical values in the comparison
table.

The interface, figures and Excel output are available in **Korean and English**.
In English mode every species is labelled with its scientific name
(e.g. *Pinus densiflora*), so tables and figures can be used directly in a
manuscript.

## Repository layout

```
├── main.py                  ← entry point (Carbon1 · Carbon2 in one tabbed window)
├── build_exe.py             ← builds the core software (main.py → module executable)
├── build_updater.py         ← builds the Equation Library Manager
├── updater_app.py           ← manager application (runs build_exe.py logic internally)
├── build_library_manager.bat ← Windows batch wrapper for build_updater.py
├── 실행_rudckd.bat          ← Windows batch launcher (conda env, dependency check, run)
├── installer.iss            ← Inno Setup script for a Windows installer
├── requirements.txt         ← runtime dependencies
├── species_data.json        ← combined species dataset (trees, shrubs, domestic, international)
├── icon.ico                 ← application icon
└── carbon_calculator/       ← core package
    ├── data.py / data2.py          — species coefficients and allometric equations
    ├── calculations.py             — carbon storage calculation
    ├── input_limits.py             — combined tree/shrub planting-area safeguard
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

On first start the application presents an English-language selection dialog
with **English** selected by default. The choice is stored under the FORECAST-SW
v1.0 settings key and reused; it can be changed at any time from the
**Language** menu, which restarts the application in the selected language.
Legacy language preferences from pre-FORECAST-SW builds are not imported.

---

## 2. Build the FORECAST-SW Assessment Application

```powershell
python build_exe.py              # onefile (single executable) — default
python build_exe.py --onedir     # folder layout (faster startup)
python build_exe.py --debug      # show a console window (for diagnosing errors)
python build_exe.py --upx        # enable UPX compression (smaller output)
python build_exe.py --clean-cache        # remove build/ and dist/ first
python build_exe.py --rebuild-venv       # force re-creation of the build venv
```

- Output: `dist/FORECAST-SW.exe` (onefile) or `dist/FORECAST-SW/` (onedir)
- If `species_data.json` is present in the project root it is bundled into the
  executable and loaded at runtime.
- Use `--rebuild-venv` whenever `requirements.txt` changes. The build venv is
  considered reusable when PyInstaller and PyQt5 import successfully, so a venv
  built for an older dependency set is otherwise silently reused.
- If the executable exits immediately, rebuild with `--debug` and read the
  console output.

---

## 3. Build the FORECAST-SW Equation Library Manager

```powershell
python build_updater.py
```

or, on Windows:

```powershell
build_library_manager.bat
```

- Output: `dist/FORECAST-SW-Equation-Library-Manager.exe`
- This executable bundles the **entire source** of the core software
  (`carbon_calculator`, `main.py`, `build_exe.py`, ...), so it can be distributed
  on its own.
- On launch it opens `species_data.json` in a **table editor** (four tabs — trees, shrubs,
  domestic, international; double-click cells to edit; add/delete species; validation before
  saving; a `.bak` backup on save). The interface provides a larger default font,
  high-DPI-aware scaling, expanded table rows and controls, a four-step workflow guide,
  and visually distinct primary and destructive actions. After editing, it offers two ways
  to apply the data:
  1. **Rebuild executable** — takes a new `species_data.json` and rebuilds the core
     executable from the bundled source (requires Python 3.10+ on the machine).
  2. **Apply JSON** — copies `species_data.json` next to an existing executable
     (no Python required; effective from the next launch).

---

## 4. Windows installer — optional

1. Build the Assessment Application in folder form: `python build_exe.py --onedir`
2. Build the Equation Library Manager: `python build_updater.py`
3. Install [Inno Setup 6](https://jrsoftware.org/isdl.php)
4. Compile with either
   - Inno Setup Compiler: open `installer.iss`, then `Build > Compile`, or
   - the command line: `"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss`
5. Output: `installer_output/FORECAST-SW_Setup_1.0.exe`. The installer includes
   both executables and creates separate Start-menu shortcuts for their roles.

---

## 5. Updating the species dataset

Edit species, coefficients, equations, and ranges in the FORECAST-SW Equation
Library Manager (`FORECAST-SW-Equation-Library-Manager.exe`) and save
(recommended), or edit `species_data.json` by hand and rebuild with
`python build_exe.py`. Apply it to an already distributed Assessment Application
through the manager (Section 3). When adding a species, fill in the
scientific-name column so that English mode can label it.

`species_data.json` also carries the English labels:

- `SPECIES_EN` — base species name → scientific name. Qualifiers such as
  `(지상부)` or `(전체, 경남)` are translated automatically
  (`후박나무(지상부)` → *Machilus thunbergii* (aboveground)).
- `ENVIRONMENTS_EN` — English labels displayed by the site-category metadata
  control. These labels do not select coefficients.

When adding a species, add its scientific name to `SPECIES_EN` as well; otherwise
English mode falls back to the Korean name rather than inventing a binomial.

---

## 6. Verify the scientific core

Run the tracked regression suite before building or modifying the equation
library:

```powershell
python -m unittest discover -s tests -v
```

The suite checks release-library counts, JSON parsing and data licensing,
site-category invariance, the allometric calculation, exact stem-count
scaling, inclusive diameter boundaries, deterministic year-zero scenarios,
shrub unit conversion, every compatibility equation, and rejection of unsafe
equation syntax. It also verifies acceptance at the site-area boundary and
rejection when the combined tree and shrub footprint exceeds it. The same suite runs on Windows with Python 3.10 and 3.11
through the repository's continuous-integration workflow. The evaluated
Windows build environment and local artifact checksums are recorded in
[BUILD_VERIFICATION.md](BUILD_VERIFICATION.md).

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

## License

The source code, build scripts, documentation, and repository figures are
available under the [MIT License](LICENSE). The scientific equation library in
`species_data.json` is provided under KOGL Type 1 (Attribution); see
[DATA_LICENSE.md](DATA_LICENSE.md). Individual equations should also retain the
bibliographic attribution of their source studies.

---

한국어 설명은 [README.md](README.md) 를 참고하세요.
