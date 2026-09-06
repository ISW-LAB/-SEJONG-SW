# FOCA-SW v4.4.2

FOCA-SW v4.4.2 is the source release evaluated in the accompanying SoftwareX
manuscript. It retains the scientific coverage of v4.4.1 while making the
meaning of site-category metadata explicit and preventing version drift among
the interface, packaging metadata, citation file, and release documentation.

## Evaluated scope

- Primary workflow: 22 native records (seven trees and 15 shrubs)
- Compatibility library: 55 records (30 domestic and 25 international)
- Complete library: 77 named records implementing 79 executable equations
- Supported release environment: Windows 10 and 11 with Python 3.10 or newer
- User outputs: current stock summaries, deterministic 0-50-year scenarios,
  cross-site comparisons, 2-D and 3-D views, and XLSX reports

The 22 native records are the operational coverage evaluated in the article.
The 55 compatibility records remain available to the updater and equation
evaluator but are not selectable in the primary site-assessment interface.

## Verification and hardening

- The interface and XLSX reports now label the legacy site-category field as
  descriptive metadata; it does not select or modify allometric coefficients.
- The interface version is imported from one package module, while a regression
  test checks the same value against the citation file, installer, and release
  notes.
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
installer with the documented build scripts. The release tag and its commit
identify the exact source state evaluated in the manuscript.
