# Tools

Reference scripts used to build and maintain this configuration. They expect the
original working tree (scan captures, docs, an `ebusd-configuration` checkout)
and are provided for transparency, not as turnkey utilities.

- `temscan.py` – scan the controller over ebusd and dump raw responses.
- `temdecode.py` – decode a raw TEM response (`0a …`).
- `temgen.py` – generate `15.24849.csv` from scan results + `docs/`.
- `tspgen.py` – convert the generated CSV to TypeSpec (`15.24849.tsp`).
- `schema.py` / `dashboard.py` – build the Home Assistant hydraulic schematic and dashboard.
