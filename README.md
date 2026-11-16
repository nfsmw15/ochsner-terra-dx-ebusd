# Ochsner TERRA DX 5 HCUA – eBUS / ebusd configuration

Reverse-engineered [ebusd](https://github.com/john30/ebusd) configuration and
documentation for the **Ochsner TERRA DX 5 HCUA** heat pump, which uses a
**TEM** controller (eBUS manufacturer `TEM`, scan ID `24849`, slave address
`15`). Most of this applies to other Ochsner / TEM-based units (OTE controller,
SE 6024 WPC family) as well, though the exact parameters per block differ.

The controller is the same **TEM SE 6024 WPC** platform that TEM sells to
several heat pump makers, so the register layout here is useful well beyond this
one model.

## What's in here

| Path | Contents |
|------|----------|
| [`ebusd/15.24849.csv`](ebusd/15.24849.csv) | Ready-to-use ebusd message definitions (drop into your ebusd config dir). |
| [`ebusd/15.24849.tsp`](ebusd/15.24849.tsp) | The same definitions in [TypeSpec](https://github.com/john30/ebus-typespec) form, matching the current `ebusd-configuration` repo format. |
| [`docs/protocol.md`](docs/protocol.md) | The TEM eBUS protocol: id scheme, response layout, decoding, write access, error history. |
| [`docs/display-notes.csv`](docs/display-notes.csv) | Parameter names / value lists confirmed against the controller display and the official TEM parameter list. |
| [`docs/status-lists.csv`](docs/status-lists.csv), [`docs/errcodes.txt`](docs/errcodes.txt) | Status enumerations and OTE error codes. |
| [`tools/`](tools/) | Python tools: bus scanner, decoder, CSV generator, TypeSpec generator, HA dashboard/schematic builders. |
| [`homeassistant/`](homeassistant/) | Example Home Assistant integration: MQTT package, electricity meter + COP/SPF, Fachpartner login automation, dashboard, hydraulic schematic. |

## Hardware

- **Heat pump:** Ochsner TERRA DX 5 HCUA (direct expansion / water, R407C), hydraulic variant M2‑1, controller SW 6.05 / HW 3.03.
- **eBUS adapter:** any ebusd-supported adapter. This unit was read through an Ethernet eBUS gateway in raw TCP mode.
- **ebusd:** run with this config directory; the controller answers on slave `15` with scan ID `24849`.

## Quick start

1. Copy [`ebusd/15.24849.csv`](ebusd/15.24849.csv) into your ebusd configuration
   directory (e.g. `.../ebusd-configuration/de/tem/`).
2. Start ebusd pointed at that directory. The messages appear under circuits
   `Waermepumpe`, `Zusatzheizung`, `Heizkreis`, `Warmwasserkreis`,
   `Waermemanager`, `Kaskadenmanager`, `Anlage` and `Stoerungen`.
3. Read live values, e.g. `ebusctl read -c Anlage p00_000_aussentemperatur`.

### Fachpartner level

Many settings only answer while the controller is at **Fachpartner** access
level. These messages carry a condition on parameter `04-043` and stay silent at
user level. See [`homeassistant/fachpartner-automation.yaml`](homeassistant/fachpartner-automation.yaml)
for a way to keep that level active over MQTT.

## Scope and caveats

- **Reads** cover the live values, settings, counters, energy totals, operating
  data and the two passive module telegrams (`0501` request, `0503` module
  status — the latter gives compressor state, power and flow faster than the
  controller's own registers).
- **Writes** are included in the CSV only for a small, verified whitelist.
  Changing controller settings can affect heating safety and your warranty —
  do it at your own risk and know the parameter first.
- A handful of parameters remain labelled `Unbekannt`; they read fine but are
  not documented in any public TEM source (they are OEM-build specific).
- Value meanings were cross-checked against the controller display and the
  official **TEM SE 6024 WPC** parameter list where possible.

## Credits

Protocol worked out with [ebusd](https://github.com/john30/ebusd) by John Baier.
Manufacturer documentation belongs to Ochsner and TEM and is **not** included
here — only independently derived message definitions.

## License

MIT – see [`LICENSE`](LICENSE). The message definitions may be contributed to
[`john30/ebusd-configuration`](https://github.com/john30/ebusd-configuration)
(GPL‑3.0); that contribution is made under the destination project's license.
