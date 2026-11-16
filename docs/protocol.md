# TEM / Ochsner OTE eBUS protocol

How the TEM controller in the Ochsner TERRA DX (SE 6024 WPC platform) exposes its
parameters on the eBUS, as derived by reverse engineering and cross-checked
against the controller display and the official TEM SE 6024 WPC parameter list.

The controller is eBUS slave `15` (master `10`), scan ID `24849`. The attached
heat-generator modules are WE_1 at `03`/`08` and WE_2 at `13`/`18`.

## Parameter addressing

Every display parameter has a number `GG-PPP` (group `GG`, parameter `PPP`) and
belongs to a functional **block**:

| Block | Circuit |
|-------|---------|
| `0x00` | Anlage (plant / globals) |
| `0x02` | Wärmepumpe (heat pump) |
| `0x04` | Zusatzheizung (aux heater) |
| `0x08` / `0x0a` / `0x0c` | heating circuits (HC) |
| `0x0e` | Warmwasser (DHW) |
| `0x10` | Wärmemanager / buffer |
| `0x12` | Kaskadenmanager |

### Direct read (`0621`)

Read a single parameter with a 4-byte id:

```
15 0621 04 <id>              id = GG, 0x80+PPP, 00, 0x40+block
```

Example: parameter `09-007` in block `0x02` → id `09 87 00 42`.

An invalid / not-available parameter answers `0a ff9f 00...`.

### Response layout

After the length byte `0x0a` the 10-byte payload is:

```
pn(LE16)  type(1)  unit(1)  max(SIN,2)  min(SIN,2)  value(2)
```

- `pn`: bits 14–15 are flags (`0x4000` = settable); `group = (pn>>7)&0x7f`,
  `param = pn&0x7f`.
- `type`: TEM data type (`0x02` on/off, `0x09` selection, `0x0d` temperature,
  `0x40` duration, …).
- `unit`: `0x02` °C, `0x12` kWh, `0x34` l/min, `0x3c` MWh, …
- Temperatures are value/10. Counters use type `0x1d` with an HCD value.
- Some parameters use **1-byte fields** (`max,pad,min,pad,val,pad`) with
  per-parameter scaling that is *not* derivable from the type byte (e.g.
  whole-°C or 0.5-°C steps). These are listed in
  [`display-notes.csv`](display-notes.csv).

### Multi-part read (`0622`)

`0622` reads use the 3rd id byte as a part index for values that span several
frames: text fields (serial, installer …) and the error history.

## Access levels

Parameter `04-043` reports the level: `0` user, `1` Fachpartner, `2` OEM.
Many settings answer only at Fachpartner level or above; at user level they
return `ff9f`. The Fachpartner code is entered at `04-042`. OEM uses a dynamic
challenge code shown on the display (not a static password).

The menu-list ids (`6x`/`7x` mirroring the display pages) stop answering after a
Fachpartner login on this unit, so this configuration relies on **direct ids
only**.

## Writing (`0623`)

```
10 0623 06 <direct id> <value LE16>       sent to master 10
```

Values are always written as 2 bytes little-endian, including for 1-byte-field
parameters. Writing was verified (e.g. setting the clock, `02-072`). Changing
installer/OEM settings can affect operation and safety — proceed with caution.

## Error history (Service Report)

```
0622 02da<entry*16+part>40    entry 0..5 (0 = newest), parts 0..3 concatenated
```

The 37 concatenated bytes are: source, OTE error code, date (UIN, days since
1899-12-31), time (UIN, minutes since Monday 00:00), status, then 15 × SIN/10
sensor snapshots: `TA TMK TPO TB TWV TWR TQE TQA TPV TSGv TSGk THG SW PND PHD`
(`0x8000` = no sensor). `02-090` holds the entry count. These refrigerant-circuit
values (TSG, THG, PND, PHD) appear **only** in the error history — they are not
exposed as live registers.

## Passive module telegrams

The controller and the heat-generator modules exchange cyclic master-master
telegrams that can be read passively (no polling):

### `0501` – request to the module (`10` → `03`/`13`)

10 data bytes: flow setpoint (D2B), power request %, release, and an operating
mode byte (`0` heating, `1` hot water) that drives the internal diverter valve.

### `0503` – module status (`03`/`13` → `10`), block `01`

12 bytes, every ~8 s:

| Byte | Meaning |
|------|---------|
| 1 | state: `0` off, `1` compressor on, `2` start-up (~30 s, pumps only) |
| 2 | output bits: `0x40` pump (incl. overrun), `0x08` compressor |
| 3 | compressor power % |
| 4 | flow temperature (D1C, = TWV, updates faster than the register) |
| 5 | return temperature (whole °C, `0xff` = none) |
| 10 | heat-generator type (= parameter `09-007`) |

ebusd logs these unknown master-master frames at notice level, so
`docker logs` / the bus log is a convenient timestamped passive capture.

## See also

- [`display-notes.csv`](display-notes.csv) – confirmed names, value lists and 1-byte scalings.
- [`status-lists.csv`](status-lists.csv) – status enumerations.
- [`errcodes.txt`](errcodes.txt) – OTE error codes.
- The official **TEM SE 6024 WPC** parameter list (TEM download center) documents
  the generic register set; firmware builds differ in the OEM-specific entries.
