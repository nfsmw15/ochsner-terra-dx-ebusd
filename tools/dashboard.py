#!/usr/bin/env python3
"""Build the Lovelace config for the "Heizung" dashboard (built-in cards only).

Usage: dashboard.py STATES.json OUT.json
STATES.json: {entity_id: state} of the HA instance, used to drop missing entities.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema  # noqa: E402

P = "sensor.heating_ochsner_"
N = "number.heating_ochsner_"
E = {
    "at": P + "anlage_aussentemperatur_00_000",
    "wp_status": P + "waermepumpe_status_warmeerzeuger_02_053",
    "leistung": "sensor.ochsner_wp_heizleistung_berechnet",  # 23-003 needs the Fachpartner level
    "twv": P + "waermepumpe_ist_temp_twv_00_007",
    "twr": P + "waermepumpe_ist_temp_twr_00_008",
    "flow": P + "waermepumpe_volumenstrom_warmepumpe_21_002",
    "verdichter": P + "waermepumpe_soll_verdichter_01_076",
    "tpo": P + "waermemanager_tpo_puffertemperatur_oben_00_015",
    "tpm": P + "waermemanager_tpm_puffertemperatur_mitte_00_017",
    "tb": P + "waermepumpe_ist_temp_tb_warmwasser_00_004",
    "ww_soll": P + "warmwasserkreis_warmwassertemperatur_sollwert_01_004",
    "ww_status": P + "warmwasserkreis_status_warmwasserregelung_02_052",
    "hk_vl": P + "heizkreis_heizkreis_vorlauftemperatur_00_002",
    "hk_soll": P + "heizkreis_heizkreis_vorlauftemperatur_sollwert_01_002",
    "hk_status": P + "heizkreis_status_heizkreis_02_051",
    "hk_pumpe": "binary_sensor.heating_ochsner_heizkreis_heizkreispumpe_01_020",
    "mischer": P + "heizkreis_mischer_01_021",
    "ventil": "binary_sensor.heating_ochsner_warmwasserkreis_umlenkventil_ladepumpe_01_066",
    "ventil_pct": P + "warmwasserkreis_stellgrosse_umlenkventil_22_066",
    "anlage_soll": P + "waermemanager_sollwert_anlage_01_096",
    "wm_status": P + "waermemanager_status_warmemanager_02_054",
    "sammel": "binary_sensor.heating_ochsner_anlage_sammelstorung_01_099",
    "zustand": "sensor.ochsner_betriebszustand",
    "ventile": "sensor.ochsner_umschaltventile",
    "wp_pumpe": P + "waermepumpe_warmeerzeugerpumpe_01_022",
    # SDM630 electricity meter (generated/sdm630.yaml)
    "p_el": "sensor.ochsner_wp_elektrische_leistung",
    "zaehler": "sensor.ochsner_wp_stromverbrauch",
    "cop": "sensor.ochsner_wp_cop_aktuell",
    "az_heute": "sensor.ochsner_wp_arbeitszahl_heute",
    "az_monat": "sensor.ochsner_wp_arbeitszahl_monat",
    "az_gesamt": "sensor.ochsner_wp_arbeitszahl_seit_zahler",
    "strom_heute": "sensor.ochsner_wp_strom_heute",
    "warme_heute": "sensor.ochsner_wp_warme_heute",
    "strom_monat": "sensor.ochsner_wp_strom_monat",
    "warme_monat": "sensor.ochsner_wp_warme_monat",
    "warme_inkl": "sensor.ochsner_wp_warme_inkl_heizstab",
    "strom_hz": "sensor.ochsner_wp_strom_heizen",
    "strom_ww": "sensor.ochsner_wp_strom_warmwasser",
    "az_hz_heute": "sensor.ochsner_wp_arbeitszahl_heizen_heute",
    "az_hz_monat": "sensor.ochsner_wp_arbeitszahl_heizen_monat",
    "az_hz_gesamt": "sensor.ochsner_wp_arbeitszahl_heizen_seit_zahler",
    "az_ww_heute": "sensor.ochsner_wp_arbeitszahl_warmwasser_heute",
    "az_ww_monat": "sensor.ochsner_wp_arbeitszahl_warmwasser_monat",
    "az_ww_gesamt": "sensor.ochsner_wp_arbeitszahl_warmwasser_seit_zahler",
    "strom_hz_heute": "sensor.ochsner_wp_strom_heizen_heute",
    "strom_ww_heute": "sensor.ochsner_wp_strom_warmwasser_heute",
    "spreizung": "sensor.ochsner_wp_spreizung",
    "laufzeit": "sensor.ochsner_wp_laufzeit_pro_start",
    "stunden": "sensor.ochsner_wp_betriebsstunden",
    "starts": P + "waermepumpe_schaltzyklen_02_080",
    "e_heiz": "sensor.ochsner_wp_heizenergie_gesamt",
    "e_ww": "sensor.ochsner_wp_warmwasserenergie_gesamt",
    "e_ges": "sensor.ochsner_wp_warme_gesamt",
    "e_zh": "sensor.ochsner_zusatzheizung_heizenergie_gesamt",
    # settings
    "fusspunkt": N + "heizkreis_fusspunkt_vorlauftemperatur_heizkurve_03_001",
    "norm_at": N + "heizkreis_norm_aussentemperatur_heizkurve_03_012",
    "norm_vl": N + "heizkreis_vlt_bei_norm_aussentemperatur_heizkurve_03_013",
    "hg_normal": N + "heizkreis_heizgrenze_normalbetrieb_03_021",
    "hg_spar": N + "heizkreis_heizgrenze_sparbetrieb_03_002",
    "raum_normal": N + "heizkreis_normal_raumtemperatur_heizbetrieb_03_051",
    "raum_spar": N + "heizkreis_spar_raumtemperatur_heizbetrieb_03_053",
    "bw_heizung": "select.heating_ochsner_heizkreis_betriebswahl_heizung_03_050",
    "ww_normal": N + "warmwasserkreis_normal_warmwassertemperatur_05_051",
    "ww_spar": N + "warmwasserkreis_spar_warmwassertemperatur_05_086",
    "ww_diff": N + "warmwasserkreis_einschaltdifferenz_warmwasserbereitung_05_000",
    "bw_ww": "select.heating_ochsner_warmwasserkreis_betriebswahl_warmwasser_05_050",
    "sg_puffer": N + "waermemanager_puffer_solltemperatur_bei_sonderfreigabe_06_027",
}


def label(eid, left, top, size="15px", color="var(--primary-text-color)", prefix="", bold=False, anchor="middle"):
    return {"type": "state-label", "entity": eid, "prefix": prefix,
            "style": {"left": left, "top": top, "font-size": size, "color": color,
                      "font-weight": "600" if bold else "400", "white-space": "nowrap",
                      "transform": "translate(%s,-50%%)" % ("-50%" if anchor == "middle" else "0"),
                      "text-shadow": "0 0 3px var(--card-background-color)"}}


# style name from tools/schema.py -> (font size, color, bold)
LABEL_STYLE = {
    "head": ("clamp(8px, 0.94vw, 15px)", None, True),
    "big": ("clamp(8px, 0.88vw, 14px)", None, True),
    "tank": ("clamp(8px, 0.78vw, 12px)", None, True),
    "red": ("clamp(8px, 0.88vw, 14px)", schema.RED, True),
    "blue": ("clamp(8px, 0.88vw, 14px)", schema.BLUE, True),
    "orange": ("clamp(8px, 0.88vw, 14px)", schema.ORANGE, True),
    "soll": ("clamp(8px, 0.74vw, 12px)", None, False),
    "small": ("clamp(8px, 0.74vw, 12px)", None, False),
    "text": ("clamp(8px, 0.74vw, 12px)", None, False),
}


def pct(v, total):
    return "%.2f%%" % (100.0 * v / total)


def schema_version(name="anlage.svg"):
    """Content hash of a generated schematic file, so browsers fetch a changed SVG instead of a cached one."""
    import hashlib
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generated", "www", name)
    return hashlib.md5(open(path, "rb").read()).hexdigest()[:8]


def schema_elements():
    """Live values and icons on the schematic, positioned with the coordinates of tools/schema.py."""
    def layer(name):
        return {"type": "image", "image": "/local/ochsner/%s?v=%s" % (name, schema_version(name)), "tap_action": {"action": "none"},
                "hold_action": {"action": "none"},
                "style": {"left": "50%", "top": "50%", "width": "100%", "transform": "translate(-50%,-50%)", "pointer-events": "none"}}

    pump_on = {"condition": "numeric_state", "entity": E["wp_pumpe"], "above": 0}
    # valve position follows the WW charge status; water only moves while the heat generator pump runs
    els = [{"type": "conditional", "conditions": [{"condition": "state", "entity": E["ventile"], "state": pos}],
            "elements": [layer("valves_%s.svg" % k)]} for k, pos in (("ww", "Warmwasser"), ("hz", "Heizung"))]
    els += [{"type": "conditional", "conditions": [{"condition": "state", "entity": E["ventile"], "state": pos}, pump_on],
             "elements": [layer("flow_%s.svg" % k)]} for k, pos in (("ww", "Warmwasser"), ("hz", "Heizung"))]
    els.append({"type": "conditional", "conditions": [{"condition": "state", "entity": E["hk_pumpe"], "state": "on"}],
                "elements": [layer("flow_hk.svg")]})
    for x, y, key, prefix, style, anchor in schema.placements():
        size, color, bold = LABEL_STYLE[style]
        kw = {"color": color} if color else {}
        els.append(label(E[key], pct(x, schema.W), pct(y, schema.H), size, prefix=prefix, bold=bold, anchor=anchor, **kw))
    for x, y, key, icon in schema.ICONS:
        els.append({"type": "state-icon", "entity": E[key], "icon": icon,
                    "style": {"left": pct(x, schema.W), "top": pct(y, schema.H), "transform": "translate(-50%,-50%)"}})
    return els


NAMES = {
    "at": "Außen", "leistung": "Heizleistung", "twv": "Vorlauf WP", "twr": "Rücklauf WP",
    "spreizung": "Spreizung", "flow": "Volumenstrom", "tpo": "Puffer oben", "tpm": "Puffer Mitte",
    "tb": "Warmwasser Ist", "hk_vl": "Vorlauf Heizkreis", "hk_soll": "Vorlauf Soll", "laufzeit": "Laufzeit pro Start",
    "wm_status": "Wärmemanager", "hk_status": "Heizkreis", "tpm": "Puffer Mitte", "zustand": "Betriebszustand", "wp_status": "Wärmepumpe", "ww_status": "Warmwasser",
    "bw_heizung": "Betriebswahl Heizung", "bw_ww": "Betriebswahl Warmwasser",
    "e_ges": "Wärme gesamt", "e_heiz": "Heizen gesamt", "e_ww": "Warmwasser gesamt", "e_zh": "Heizstab gesamt",
    "stunden": "Betriebsstunden", "starts": "Starts",
    "p_el": "Strom aktuell", "zaehler": "Zählerstand", "cop": "COP aktuell", "az_heute": "Arbeitszahl heute",
    "az_monat": "Arbeitszahl Monat", "az_gesamt": "Arbeitszahl seit Zähler", "strom_heute": "Strom heute",
    "warme_heute": "Wärme heute", "strom_monat": "Strom Monat", "warme_monat": "Wärme Monat",
    "az_hz_heute": "AZ Heizen heute", "az_hz_monat": "AZ Heizen Monat", "az_hz_gesamt": "AZ Heizen seit Zähler",
    "az_ww_heute": "AZ Warmwasser heute", "az_ww_monat": "AZ Warmwasser Monat", "az_ww_gesamt": "AZ Warmwasser seit Zähler",
    "strom_hz_heute": "Strom Heizen heute", "strom_ww_heute": "Strom Warmwasser heute",
}


def tile(key, features=None, name=None, **kw):
    c = {"type": "tile", "entity": E[key]}
    name = name or NAMES.get(key)
    if name:
        c["name"] = name
    if features:
        c["features"] = features
    c.update(kw)
    return c


def num(key, name):
    return tile(key, [{"type": "numeric-input", "style": "buttons"}], name)


def apex_heizkurve():
    # apexcharts-card only has a time axis: map outside temp t (-20..20 °C) to today 00:00 + (t + 20) h
    base = "const b = new Date(); b.setHours(0, 0, 0, 0); const x = t => b.getTime() + (t + 20) * 3600000;"
    gen = (base + "const fp = parseFloat(entity.state);"
           "const nat = parseFloat(hass.states['%s'].state);"
           "const nvl = parseFloat(hass.states['%s'].state);"
           "const m = (nvl - fp) / (20 - nat);"
           "const pts = []; for (let t = -20; t <= 20; t += 1) pts.push([x(t), +(fp + m * (20 - t)).toFixed(1)]);"
           "return pts;") % (E["norm_at"], E["norm_vl"])
    now = base + "return [[x(parseFloat(hass.states['%s'].state)), parseFloat(entity.state)]];" % E["at"]
    to_t = "EVAL:v => { const b = new Date(); b.setHours(0, 0, 0, 0); return Math.round((v - b.getTime()) / 3600000 - 20) + ' °C'; }"
    return {
        "type": "custom:apexcharts-card", "header": {"show": True, "title": "Heizkurve", "show_states": False},
        "graph_span": "40h", "span": {"start": "day"}, "chart_type": "line", "update_interval": "5min", "now": {"show": False},
        "apex_config": {
            "chart": {"height": 280},
            "xaxis": {"tickAmount": 8, "labels": {"formatter": to_t, "rotate": 0},
                      "title": {"text": "Außentemperatur"}, "tooltip": {"enabled": False}},
            "yaxis": {"min": 15, "max": 45, "tickAmount": 6, "decimalsInFloat": 0, "title": {"text": "Vorlauf °C"}},
            "tooltip": {"x": {"formatter": to_t}},
            "markers": {"size": [0, 8]},
            "legend": {"show": True},
        },
        "series": [
            {"entity": E["fusspunkt"], "name": "Heizkurve", "data_generator": gen, "stroke_width": 3, "color": "#f5a524",
             "extend_to": False},
            {"entity": E["hk_soll"], "name": "jetzt (Soll)", "data_generator": now, "stroke_width": 0, "color": "#e5484d",
             "extend_to": False},
        ],
    }


def apex_hist(title, series, hours=24, chart="line", height=240):
    return {"type": "custom:apexcharts-card", "header": {"show": True, "title": title, "show_states": True, "colorize_states": True},
            "cache": False, "graph_span": "%dh" % hours, "chart_type": chart if chart != "area" else "line",
            "apex_config": {"chart": {"height": height}, "legend": {"show": False}},
            "series": [dict({"entity": E[k], "name": n, "color": c, "group_by": {"func": "avg", "duration": "5min"}},
                            **({"type": "area", "opacity": 0.25} if chart == "area" else {})) for k, n, c in series]}


def apex_energy():
    return {"type": "custom:apexcharts-card", "header": {"show": True, "title": "Wärme pro Tag (kWh)", "show_states": False},
            "graph_span": "30d", "span": {"end": "day"}, "chart_type": "line", "stacked": True,
            "apex_config": {"chart": {"height": 260}, "legend": {"show": True}},
            "series": [{"entity": E["e_heiz"], "name": "Heizen", "type": "column", "color": "#f5a524",
                        "statistics": {"type": "change", "period": "day", "align": "start"}},
                       {"entity": E["e_ww"], "name": "Warmwasser", "type": "column", "color": "#3e9bdc",
                        "statistics": {"type": "change", "period": "day", "align": "start"}}]}


def apex_leistung():
    """Heat output vs electrical input (both in kW) and the resulting COP, last 24 h."""
    return {"type": "custom:apexcharts-card", "header": {"show": True, "title": "Wärme, Strom & COP (24 h)", "show_states": True,
                                                         "colorize_states": True},
            "cache": False, "graph_span": "24h", "chart_type": "line",
            "apex_config": {"chart": {"height": 260}, "legend": {"show": True}},
            "yaxis": [{"id": "kw", "min": 0, "decimals": 1, "apex_config": {"title": {"text": "kW"}}},
                      {"id": "cop", "opposite": True, "min": 0, "max": 8, "decimals": 1, "apex_config": {"title": {"text": "COP"}}}],
            "series": [{"entity": E["leistung"], "name": "Wärme", "type": "area", "opacity": 0.25, "color": "#f5a524", "yaxis_id": "kw",
                        "group_by": {"func": "avg", "duration": "5min"}},
                       {"entity": E["p_el"], "name": "Strom", "type": "area", "opacity": 0.25, "color": "#3e9bdc", "yaxis_id": "kw",
                        "unit": "kW", "transform": "return x / 1000;", "group_by": {"func": "avg", "duration": "5min"}},
                       # COP is unavailable outside steady operation: leave those gaps empty instead of the
                       # default "fill: last", which would draw the last value across the whole standstill
                       {"entity": E["cop"], "name": "COP", "color": "#22c55e", "yaxis_id": "cop", "stroke_width": 2,
                        "extend_to": False, "group_by": {"func": "avg", "duration": "5min", "fill": "null"}}]}


def apex_tagesbilanz():
    """Heat (incl. heater) and electricity per day, from the long-term statistics."""
    stat = {"type": "change", "period": "day", "align": "start"}
    return {"type": "custom:apexcharts-card", "header": {"show": True, "title": "Wärme & Strom pro Tag (kWh)", "show_states": False},
            "graph_span": "30d", "span": {"end": "day"}, "chart_type": "line",
            "apex_config": {"chart": {"height": 260}, "legend": {"show": True}},
            "series": [{"entity": E["warme_inkl"], "name": "Wärme", "type": "column", "color": "#f5a524", "statistics": stat},
                       {"entity": E["zaehler"], "name": "Strom", "type": "column", "color": "#3e9bdc", "statistics": stat}]}


def apex_strom_split():
    """Electricity per day, split by operating mode (heating / hot water) from the 0501 mode byte."""
    stat = {"type": "change", "period": "day", "align": "start"}
    return {"type": "custom:apexcharts-card", "header": {"show": True, "title": "Strom pro Tag nach Betriebsart (kWh)", "show_states": False},
            "graph_span": "30d", "span": {"end": "day"}, "chart_type": "line", "stacked": True,
            "apex_config": {"chart": {"height": 240}, "legend": {"show": True}},
            "series": [{"entity": E["strom_hz"], "name": "Heizen", "type": "column", "color": "#f5a524", "statistics": stat},
                       {"entity": E["strom_ww"], "name": "Warmwasser", "type": "column", "color": "#3e9bdc", "statistics": stat}]}


def apex_laufzeit():
    stat = {"type": "change", "period": "day", "align": "start"}
    return {"type": "custom:apexcharts-card", "header": {"show": True, "title": "Laufzeit & Starts pro Tag", "show_states": False},
            "graph_span": "30d", "span": {"end": "day"}, "chart_type": "line",
            "apex_config": {"chart": {"height": 260}, "legend": {"show": True}},
            "yaxis": [{"id": "h", "min": 0, "decimals": 1, "apex_config": {"title": {"text": "Stunden"}}},
                      {"id": "n", "opposite": True, "min": 0, "decimals": 0, "apex_config": {"title": {"text": "Starts"}}}],
            "series": [{"entity": E["stunden"], "name": "Laufzeit", "type": "column", "color": "#f5a524",
                        "yaxis_id": "h", "statistics": stat},
                       {"entity": E["starts"], "name": "Starts", "type": "line", "color": "#3e9bdc", "stroke_width": 3,
                        "yaxis_id": "n", "statistics": stat}]}


def build():
    anlage = {
        "type": "picture-elements",
        "image": "/local/ochsner/anlage.svg?v=" + schema_version(),
        "elements": schema_elements(),
    }
    heizkurve = {
        "type": "markdown",
        "content": (
            "{% set fp = states('" + E["fusspunkt"] + "') | float(20) %}"
            "{% set nat = states('" + E["norm_at"] + "') | float(-12) %}"
            "{% set nvl = states('" + E["norm_vl"] + "') | float(35) %}"
            "{% set at = states('" + E["at"] + "') | float(0) %}"
            "{% set m = (nvl - fp) / (20 - nat) %}"
            "| Außen | Vorlauf-Soll |\n|---:|---:|\n"
            "{% for t in [20, 15, 10, 5, 0, -5, -10, -15] %}"
            "| {{ t }} °C | {{ '%.1f' | format(fp + m * (20 - t)) }} °C |\n"
            "{% endfor %}\n"
            "**Jetzt:** {{ at }} °C außen → Kurve {{ '%.1f' | format(fp + m * (20 - at)) }} °C, "
            "Regler-Soll {{ states('" + E["hk_soll"] + "') }} °C\n\n"
            "Steigung {{ '%.2f' | format(m) }} K pro K"
        ),
    }
    stoerungen = {
        "type": "entities",
        "title": "Störungsspeicher",
        "entities": [E["sammel"]] + ["sensor.ochsner_storung_%d" % i for i in range(1, 7)],
    }

    def hist(title, keys, hours=24):
        return {"type": "history-graph", "title": title, "hours_to_show": hours,
                "entities": [{"entity": E[k]} for k in keys]}

    def stat(title, keys, days=30):
        return {"type": "statistics-graph", "title": title, "chart_type": "bar", "period": "day",
                "days_to_show": days, "stat_types": ["change"],
                "entities": [E[k] for k in keys]}

    full, half = {"columns": "full"}, {"columns": 6}
    stoerungen = {"type": "entities", "title": "Störungsspeicher", "grid_options": full,
                  "entities": [{"entity": E["sammel"], "name": "Sammelstörung"}] +
                              [{"entity": "sensor.ochsner_storung_%d" % i, "name": "Störung %d" % i} for i in range(1, 7)]}
    info = {"type": "entities", "title": "Anlage", "grid_options": full, "entities": [
        {"entity": "sensor.ochsner_seriennummer", "name": "Seriennummer"},
        {"entity": "sensor.ochsner_installateur", "name": "Installateur"},
        {"entity": "sensor.ochsner_letzter_zugriff_fachpartner", "name": "Letzter Zugriff Fachpartner"},
        {"entity": "sensor.ochsner_letzter_zugriff_oem", "name": "Letzter Zugriff OEM"},
        {"entity": P + "anlage_sw_version_04_092", "name": "Software"},
        {"entity": P + "anlage_hw_version_04_093", "name": "Hardware"},
        {"entity": P + "waermepumpe_applikationstyp_warmepumpe_15_006", "name": "Applikationstyp"},
        {"entity": P + "anlage_ebene_einsteller_04_043", "name": "Bedienebene"}]}
    sections = [
        {"type": "grid", "column_span": 2, "cards": [
            {"type": "heading", "heading": "Anlage", "icon": "mdi:heat-pump-outline"},
            dict(anlage, grid_options=full),
            dict(hist("Status", ["wp_status", "ww_status", "hk_status"]), grid_options=full),
        ]},
        {"type": "grid", "cards": [
            {"type": "heading", "heading": "Jetzt", "icon": "mdi:gauge"},
            tile("zustand", grid_options=full),
            tile("at"), tile("leistung"), tile("twv"), tile("twr"),
            tile("spreizung"), tile("flow"), tile("tb"), tile("tpo"),
            tile("tpm"), tile("hk_vl"), tile("hk_soll"), tile("laufzeit"),
            tile("wm_status"), tile("hk_status"),
        ]},
        {"type": "grid", "cards": [
            {"type": "heading", "heading": "Heizung einstellen", "icon": "mdi:radiator"},
            tile("bw_heizung", [{"type": "select-options"}], grid_options=full),
            num("fusspunkt", "Fußpunkt (bei 20 °C außen)"),
            num("norm_vl", "Vorlauf bei Norm-AT"),
            num("norm_at", "Norm-Außentemperatur"),
            num("hg_normal", "Heizgrenze normal"),
            num("hg_spar", "Heizgrenze spar"),
            num("raum_normal", "Raum normal"),
            num("raum_spar", "Raum spar"),
        ]},
        {"type": "grid", "column_span": 4, "cards": [
            {"type": "heading", "heading": "Verläufe (24 h)", "icon": "mdi:chart-line"},
            dict(apex_hist("Temperaturen", [("twv", "Vorlauf WP", "#e5484d"), ("twr", "Rücklauf WP", "#3e9bdc"),
                                            ("hk_vl", "Vorlauf HK", "#f5a524"), ("hk_soll", "Soll HK", "#a1a1aa"),
                                            ("at", "Außen", "#22c55e")], height=320), grid_options={"columns": 24}),
            dict(apex_hist("Speicher UNI800", [("tb", "Warmwasser", "#e5484d"), ("tpo", "Puffer oben", "#f5a524"),
                                               ("tpm", "Puffer Mitte", "#3e9bdc")], chart="area", height=320), grid_options={"columns": 24}),
            dict(apex_hist("Heizleistung", [("leistung", "Heizleistung", "#f5a524")], chart="area", height=200),
                 grid_options=full),
        ]},
        {"type": "grid", "cards": [
            {"type": "heading", "heading": "Effizienz", "icon": "mdi:leaf"},
            tile("cop"), tile("az_heute"), tile("az_monat"), tile("az_gesamt"),
            tile("p_el"), tile("leistung"), tile("strom_heute"), tile("warme_heute"),
            tile("strom_monat"), tile("warme_monat"),
            {"type": "heading", "heading": "Heizen / Warmwasser getrennt", "heading_style": "subtitle"},
            tile("az_hz_heute"), tile("az_ww_heute"), tile("az_hz_monat"), tile("az_ww_monat"),
            tile("az_hz_gesamt"), tile("az_ww_gesamt"), tile("strom_hz_heute"), tile("strom_ww_heute"),
            dict(apex_leistung(), grid_options=full),
            dict(apex_tagesbilanz(), grid_options=full),
            dict(apex_strom_split(), grid_options=full),
        ]},
        {"type": "grid", "cards": [
            {"type": "heading", "heading": "Warmwasser", "icon": "mdi:water-boiler"},
            tile("bw_ww", [{"type": "select-options"}], grid_options=full),
            tile("tb"), tile("ww_status"),
            num("ww_normal", "Normal"),
            num("ww_spar", "Spar"),
            num("ww_diff", "Einschaltdifferenz"),
            num("sg_puffer", "Puffer bei SG-Freigabe"),
        ]},
        {"type": "grid", "cards": [
            {"type": "heading", "heading": "Heizkurve", "icon": "mdi:chart-bell-curve-cumulative"},
            dict(apex_heizkurve(), grid_options=full),
            dict(heizkurve, grid_options=full),
        ]},
        {"type": "grid", "cards": [
            {"type": "heading", "heading": "Energie & Zähler", "icon": "mdi:lightning-bolt"},
            dict(apex_energy(), grid_options=full),
            tile("e_ges"), tile("e_heiz"), tile("e_ww"), tile("e_zh"),
            tile("stunden"), tile("starts"),
            dict(apex_laufzeit(), grid_options=full),
        ]},
        {"type": "grid", "cards": [
            {"type": "heading", "heading": "Störungen & Info", "icon": "mdi:information-outline"},
            stoerungen, info,
        ]},
    ]
    return {"title": "Heizung", "views": [{"title": "Heizung", "path": "heizung", "type": "sections",
                                            "max_columns": 4, "icon": "mdi:heat-pump-outline",
                                            "sections": sections}]}


def prune(obj, known, missing):
    """Drop card/element/entity references to entities HA does not know."""
    if isinstance(obj, list):
        out = []
        for x in obj:
            if isinstance(x, str) and "." in x and x.split(".")[0] in ("sensor", "number", "select", "binary_sensor"):
                (out.append(x) if x in known else missing.add(x))
                continue
            if isinstance(x, dict) and "entity" in x and x["entity"] not in known:
                missing.add(x["entity"])
                continue
            out.append(prune(x, known, missing))
        return out
    if isinstance(obj, dict):
        return {k: prune(v, known, missing) for k, v in obj.items()}
    return obj


def main():
    known = set(json.load(open(sys.argv[1])))
    missing = set()
    cfg = prune(build(), known, missing)
    json.dump(cfg, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    print("fehlend:", *sorted(missing), sep="\n  ") if missing else print("alle Entitäten vorhanden")


if __name__ == "__main__":
    main()
