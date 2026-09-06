# FOCA-SW v4.4

FOCA-SW v4.4 is the source release evaluated in the accompanying SoftwareX
manuscript. It standardises the FOCA-SW product name across the application,
build system, updater, installer, and bilingual documentation.

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

## Licensing

The code, build scripts, documentation, and repository figures use the MIT
License. The scientific equation library in `species_data.json` uses KOGL Type
1 (Attribution), as described in `DATA_LICENSE.md`.

## Reproduction

Install the dependencies listed in `requirements.txt`, run the source entry
point as documented in `README.en.md`, or reproduce the Windows executable and
installer with the documented build scripts. The release tag and its commit
identify the exact source state evaluated in the manuscript.
