# FORECAST-SW v1.0

FORECAST-SW v1.0 is the first public, citable release evaluated in the accompanying
SoftwareX manuscript. This release establishes a synchronized baseline for the
scientific library, graphical interface, packaging metadata, citation file,
documentation, regression tests, and Windows distribution artifacts.

## Evaluated scope

- Primary workflow: 22 native records (seven trees and 15 shrubs)
- Compatibility library: 55 records (30 domestic and 25 international)
- Complete library: 77 equation records covering 67 distinct scientific names
- Supported release environment: Windows 10 and 11 with Python 3.10 or newer
- User outputs: current stock summaries, deterministic 0-50-year scenarios,
  cross-site comparisons, 2-D and 3-D views, and XLSX reports

The 22 native records are the operational coverage evaluated in the article.
The 55 compatibility records remain available to the Equation Library Manager
and equation evaluator but are not selectable in the primary site-assessment
interface.

## Verification and hardening

- New installations now open with an English-only language-selection dialog
  and English selected by default. Legacy Korean preferences from earlier
  package identifiers are not imported, while Korean remains available from
  the Language menu.
- English-mode coverage now includes domestic/international species prefixes,
  scientific species names, warnings, charts, legends, and workbook labels.
- The interface and XLSX reports now label the legacy site-category field as
  descriptive metadata; it does not select or modify allometric coefficients.
- Tree DBH and shrub RCD now share a centimetre-based public contract across
  inputs, validity ranges, tables, plots, visualizations, and XLSX exports.
  Legacy shrub coefficients fitted with RCD in millimetres remain unchanged;
  an explicit analytical adapter converts centimetre inputs immediately before
  equation evaluation and preserves the previous numerical results.
- The former absolute 1,000-individual warning has been replaced by a
  calculation-blocking site-area safeguard. The software now sums the default
  footprints of all accepted tree and shrub entries (1.00 and 0.25 m² per
  individual, respectively) and reports the component areas and excess when
  the combined requirement exceeds the configured site area. These values are
  input safeguards rather than species-specific planting recommendations.
- The multi-profile comparison dashboard now presents accepted tree and shrub
  counts, their configured planting areas, the combined site-area requirement,
  component carbon stocks, total stock, and area-normalized carbon density in
  one auditable view. Total stock and normalized density are also displayed as
  paired charts in both the dashboard and the combined XLSX report. A shared
  tested calculation service now defines the normalization as total carbon
  stock divided by positive site area.
- The interface version is imported from one package module, while a regression
  test checks the same value against the citation file, installer, and release
  notes.
- Windows executable resources identify the Assessment Application and Equation
  Library Manager as FORECAST-SW version 1.0 components.
- The Equation Library Manager provides a larger minimum font, high-DPI-aware
  scaling, expanded table rows and controls, a four-step workflow guide, and
  visually distinct primary and destructive actions for improved readability.
- Equation strings are evaluated through an abstract-syntax-tree allowlist;
  Python `eval` is not used.
- A tracked regression suite verifies the scientific core, data-library
  counts, every compatibility equation, boundary guards, deterministic
  scenarios, and rejection of unsafe expression syntax.
- A Windows continuous-integration workflow runs the suite with Python 3.10
  and 3.11.

## Licensing

The code, build scripts, documentation, and repository figures use the MIT
License. The scientific equation library in `species_data.json` uses KOGL Type
1 (Attribution), as described in `DATA_LICENSE.md` and the JSON schema metadata.

## Reproduction

Install the dependencies listed in `requirements.txt`, run the source entry
point as documented in `README.en.md`, or reproduce the Windows executable and
installer with the documented build scripts. The `v1.0` release tag and its
commit identify the exact source state evaluated in the manuscript.
