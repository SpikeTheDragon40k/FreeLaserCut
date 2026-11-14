# FreeLaserCut — © 2026 fringuello79 — GPL-3.0-or-later
"""Versione 0.19.4: Sculpfun E1 (12 W, Pro 21 W, modulo infrarosso da 3 W) nel catalogo, chiesto da Ale.

Dati (letti il 14/11/2026):
- pagine ufficiali Sculpfun della serie E1 e del modulo IR3: area 400 × 320 mm, 600 mm/s, diodo da 12 W con spot
  0,04 × 0,06 mm (E1) o da 21 W con spot 0,06 × 0,08 mm (E1 Pro), infrarosso da 3 W con spot 0,03 × 0,03 mm;
- guida ufficiale «E1 Series User Guide» (wiki.sculpfun.com): i moduli si montano uno alla volta, la telecamera ha
  un cavo USB suo, la luce interna si regola con «$light/duty», rete propria con password 12345678 e 192.168.4.1;
- tabella delle impostazioni di fabbrica di diode-laser-wiki.com (non è una fonte Sculpfun): $130=400, $131=320,
  $110/$111=36000, $120/$121=1000, $30=1000, $32=1, $22=1, $23 con X e Y, $21=1, $20=0, porta di rete 8080.

Casi: le tre voci (area, velocità, accelerazione, potenza, spot, porta, aria, fonte, nota); niente che non è
dichiarato; riconoscimento di una scheda con l'area dell'E1, con la marca e senza, con X e Y scambiati, con un'area
vicina ma diversa; gli altri Sculpfun e le altre famiglie com'erano; profilo costruito dalla scheda; angolo dell'homing
e ritorno a fine lavoro; rete propria «Sculpfun E1» nella procedura Wi-Fi; traduzioni.
"""
import json
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp()
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp()
os.environ["FLC_SETTINGS_INI"] = os.path.join(tempfile.mkdtemp(), "prova.ini")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from freelasercut import machines, wifi_setup
from freelasercut.grbl import optical_watts

results = []


def check(name, cond, info=""):
    results.append(bool(cond))
    print(("OK  " if cond else "NO  ") + name + (f"  [{info}]" if info and not cond else ""))


E12, EPRO, EIR = "Sculpfun E1 12W", "Sculpfun E1 Pro 21W", "Sculpfun E1 3W IR"
E1 = (E12, EPRO, EIR)
names = machines.catalog_names()
check("1 le tre voci dell'E1 sono nel catalogo, sceglibili, senza doppioni: 67 modelli più il generico",
      all(n in names for n in E1) and len(machines.CATALOG) >= 67 and len(names) == len(machines.CATALOG) + 1 == len(set(names)),
      len(machines.CATALOG))
check("1 …nell'elenco stanno insieme, dopo i C1 e prima degli iCube, e si trovano cercando «E1»",
      sorted(names.index(n) for n in E1) == list(range(names.index(E12), names.index(E12) + 3))
      and names.index("Sculpfun C1 6W") + 1 == names.index(E12)
      and names.index("Sculpfun iCube Pro Max 10W") == names.index(E12) + 3
      and sorted(n for n in names if "Sculpfun E1" in n) == sorted(E1), [n for n in names if "Sculpfun" in n])
check("1 …e la famiglia dichiarata è proprio quella, con il 12 W per primo", machines.E1 == E1 and E1 in machines.FAMILIES)
pr = {n: machines.preset_profile(n) for n in E1}
check("2 area 400 × 320 mm con X sul lato lungo ($130=400, $131=320)",
      all((p.bed_x, p.bed_y) == (400.0, 320.0) and p.travel() == (400.0, 320.0) for p in pr.values()),
      [(p.bed_x, p.bed_y) for p in pr.values()])
check("2 velocità massima 36.000 mm/min (600 mm/s dichiarati) e accelerazione 1000 mm/s²",
      all((p.max_rate_x, p.max_rate_y, p.accel_x, p.accel_y) == (36000.0, 36000.0, 1000.0, 1000.0) for p in pr.values()),
      [(p.max_rate_x, p.accel_x) for p in pr.values()])
check("3 potenza per voce: 12 W, 21 W e 3 W infrarosso",
      [optical_watts(pr[n].optical_power) for n in E1] == [12.0, 21.0, 3.0] and "infrarosso" in pr[EIR].optical_power,
      [pr[n].optical_power for n in E1])
check("3 spot dichiarato: 0,04 × 0,06 mm il 12 W; 0,06 × 0,08 mm il Pro; 0,03 × 0,03 mm l'infrarosso",
      [(pr[n].spot_x_mm, pr[n].spot_y_mm) for n in E1] == [(0.04, 0.06), (0.06, 0.08), (0.03, 0.03)]
      and all(n in machines.SPOTS for n in E1), [(pr[n].spot_x_mm, pr[n].spot_y_mm) for n in E1])
check("4 porta a 115200 baud, scala S 1000, modalità laser, homing acceso, aria con M8",
      all(p.baud == 115200 and p.s_max == 1000.0 and p.laser_mode and p.homing and (p.air_on, p.air_off) == ("M8", "M9")
          for p in pr.values()) and not any(n in machines.BAUD or n in machines.AIR_ON for n in E1))
check("5 niente che non è dichiarato: area non ridotta, nessuna correzione della scansione, G55 non tolto, assi non "
      "invertiti, angolo dello 0 non indicato, piano non ruotato",
      not any(n in machines.AREA_NOTE or n in machines.SCAN or n in machines.NO_G55 for n in E1)
      and all(not p.scan_offsets and not p.no_g55 and not p.invert_x and not p.invert_y and p.origin_corner == ""
              and p.rot() == 0 and not p.z_motor for p in pr.values()))
check("6 fonti ufficiali Sculpfun dichiarate (pagina dell'E1, dell'E1 Pro e del modulo IR3)",
      all(machines.SOURCES.get(n, "").startswith("https://www.sculpfun.com/products/") for n in E1)
      and "e1-pro" in machines.SOURCES[EPRO] and "ir3" in machines.SOURCES[EIR] and "e1-pro" not in machines.SOURCES[E12]
      and all(pr[n].name == n and pr[n].model == n and bool(pr[n].source) for n in E1))
note = machines.NOTES.get(E12, "")
check("6 la nota è la stessa per le tre e dice le cose che servono per partire",
      all(machines.NOTES.get(n) == note for n in E1)
      and all(w in note for w in ("chiavetta USB", "emergenza", "coperchio chiuso", "CH340", "homing", "pannello Camera",
                                  "$light/duty", "12345678", "192.168.4.1", "8080", "asse A", "configurazione guidata",
                                  "400 × 320", "Non ancora provato")), note)
check("6 …le note degli altri Sculpfun sono rimaste le loro",
      "E1" not in machines.NOTES["Sculpfun iCube Ultra 12W"] and "E1" not in machines.NOTES["Sculpfun C1 3W"])

# ------------------------------------------------------------------ riconoscimento
# impostazioni di fabbrica dell'E1 (tabella di diode-laser-wiki.com)
BOARD = {0: "3", 1: "25", 10: "1", 11: "0.010", 20: "0", 21: "1", 22: "1", 23: "3", 24: "1000.000", 25: "20000.000",
         30: "1000", 31: "0", 32: "1", 100: "80.000", 101: "80.000", 110: "36000.000", 111: "36000.000",
         120: "1000.000", 121: "1000.000", 130: "400.000", 131: "320.000", 132: "45.000", 133: "300.000"}
plain = dict(banner=["Grbl 1.3a ['$' for help]"], info=["[VER:1.3a.20260618:]", "[OPT:PHS,15,256]"])
i = machines.identify(settings=BOARD, **plain)
texts = " | ".join(t for _k, t in i.notes)
check("7 scheda senza marca con l'area dell'E1: proposto «Sculpfun E1 12W», le altre due voci fra i candidati",
      not i.vendor and i.model == E12 and list(i.candidates) == list(E1), (i.vendor, i.model, i.candidates))
check("7 …e lo dice: il modulo non si legge dalla scheda, e il modello viene solo dall'area",
      "non si legge dalla scheda" in texts and "12 W" in texts and EPRO in texts and EIR in texts
      and "solo dall'area di lavoro" in texts, texts)
check("7 …la scheda ha l'homing: nessun avviso «Homing disattivato», nessun avviso sulla modalità laser",
      i.homing is True and i.laser_mode is True and "Homing disattivato" not in texts and "$32=0" not in texts, texts)
brand = dict(banner=["Grbl 1.3a ['$' for help]"], info=["[VER:1.3a.20260618:]", "[MSG:FW:SCULPFUN E1 V1.0.6]"])
i = machines.identify(settings=BOARD, **brand)
texts = " | ".join(t for _k, t in i.notes)
check("8 scheda che si dichiara Sculpfun con l'area dell'E1: «Sculpfun E1 12W», affidabilità alta, una sola nota",
      i.vendor == "Sculpfun" and i.model == E12 and list(i.candidates) == list(E1) and i.confidence == "alta"
      and "non si legge dalla scheda" in texts and "solo dall'area" not in texts and "Scegli il modello giusto" not in texts,
      (i.vendor, i.model, i.confidence, texts))
i = machines.identify(settings={**BOARD, **{130: "320.000", 131: "400.000"}}, **brand)
check("8 …anche con X e Y scambiati (320 × 400)", i.model == E12 and list(i.candidates) == list(E1), (i.model, i.candidates))
# 0.19.5: una scheda che scrive «Sculpfun E1» è una E1 (test_v195_varie); qui una Sculpfun che dice solo la marca
brand_s = dict(banner=["Grbl 1.1h ['$' for help]"], info=["[VER:1.1h.20230801:]", "[MSG:FW:SCULPFUN V2.1]"])
i = machines.identify(settings={**BOARD, **{130: "410.000", 131: "400.000"}}, **brand_s)
check("9 Sculpfun con 410 × 400: ancora S10 o S30, nessun E1",
      not i.model and set(i.candidates) == {"Sculpfun S10", "Sculpfun S30 / S30 Pro / S30 Pro Max"}, (i.model, i.candidates))
i = machines.identify(settings={**BOARD, **{130: "150", 131: "130"}}, **brand_s)
check("9 Sculpfun con 150 × 130: ancora i due C1 da scegliere, nessun modello proposto da solo",
      not i.model and set(i.candidates) == {"Sculpfun C1 3W", "Sculpfun C1 6W"}, (i.model, i.candidates))
i = machines.identify(settings={**BOARD, **{130: "400", 131: "300"}}, **plain)
check("9 scheda senza marca con 400 × 300: non è un E1 (fuori dai 2 mm)", i.model != E12 and not set(E1) & set(i.candidates),
      (i.model, i.candidates))
i = machines.identify(banner=["Grbl 1.1h"], info=["[VER:1.1h.2024:]"], settings={130: "420", 131: "400"})
check("10 le altre famiglie restano com'erano: Acmer P2 senza marca fra i candidati, nessun modello scelto da solo",
      not i.model and {"Acmer P2 10W", "Acmer P2 20W", "Acmer P2 33W"} <= set(i.candidates), (i.model, i.candidates))
i = machines.identify(banner=["Grbl 1.1h"], info=["[MSG:FW:ACMER]"], settings={130: "400", 131: "390"})
check("10 …e Acmer P3 con 400 × 390 ancora da scegliere", not i.model and len(i.candidates) == 2, (i.model, i.candidates))

j = machines.Identification()
check("10 …la famiglia vale solo se i modelli con quell'area sono proprio i suoi tre: con un estraneo in mezzo, o con "
      "due su tre, non si propone niente da soli",
      not machines._family(j, [E12, EPRO, EIR, "Longer Ray5 10W"]) and not machines._family(j, [E12, EPRO])
      and not j.model and not j.candidates and not j.notes and machines._family(j, [EIR, E12, EPRO]) and j.model == E12,
      (j.model, j.candidates))

# ------------------------------------------------------------------ profilo costruito dalla scheda
i = machines.identify(settings=BOARD, **plain)
q = machines.build_profile(i, BOARD, plain["info"])
check("11 «Riconosci → Applica»: profilo «Sculpfun E1 12W» con i valori letti (area, velocità, accelerazione, buffer)",
      (q.name, q.model, q.bed_x, q.bed_y, q.max_rate_x, q.max_rate_y, q.accel_x, q.rx_buffer)
      == (E12, E12, 400.0, 320.0, 36000.0, 36000.0, 1000.0, 256), (q.name, q.bed_x, q.bed_y, q.max_rate_x, q.accel_x, q.rx_buffer))
check("11 …finecorsa veri accesi, limiti software spenti, homing acceso, e dal modello potenza e spot",
      q.hard_limits and not q.soft_limits and q.homing and (q.optical_power, q.spot_x_mm, q.spot_y_mm) == ("12 W", 0.04, 0.06),
      (q.hard_limits, q.soft_limits, q.homing, q.optical_power, q.spot_x_mm))
i.model = EPRO  # la persona ha il Pro e lo sceglie
q2 = machines.build_profile(i, BOARD, plain["info"])
check("11 …scelto il Pro: 21 W e spot 0,06 × 0,08, stessa area", (q2.optical_power, q2.spot_x_mm, q2.spot_y_mm, q2.bed_x, q2.bed_y)
      == ("21 W", 0.06, 0.08, 400.0, 320.0), (q2.optical_power, q2.spot_x_mm, q2.bed_x))
check("12 homing verso X− e Y− letto dalla scheda ($23=3); senza altre indicazioni lo 0 resta davanti a sinistra e a "
      "fine lavoro la testa torna a 10 mm da lì", q.homing_mask() == 3 and q.home_corner() == (0.0, 0.0)
      and q.home_point(10.0) == (10.0, 10.0), (q.homing_mask(), q.home_corner(), q.home_point(10.0)))
q.origin_corner = "bl"  # la persona indica «dietro a sinistra» nella configurazione guidata
q.invert_x, q.invert_y = q.corner_inversion("bl", False)
check("12 …e se nella configurazione guidata si indica «dietro a sinistra», casa e ritorno seguono quell'angolo",
      q.home_corner() == (0.0, 320.0) and q.home_point(10.0) == (10.0, 310.0), (q.home_corner(), q.home_point(10.0)))

# ------------------------------------------------------------------ Wi-Fi
check("13 la rete propria «Sculpfun E1» è riconosciuta dalla procedura Wi-Fi; le reti di casa no",
      wifi_setup.is_own_net("Sculpfun E1") and wifi_setup.is_own_net("SCULPFUN E1 Pro") and not wifi_setup.is_own_net("CasaMia")
      and not wifi_setup.is_own_net("Casa Sculpfun") and wifi_setup.is_own_net("MKS_DLC32") and wifi_setup.is_own_net("FluidNC"))
check("13 …password e indirizzo della rete propria sono quelli della guida ufficiale, e la porta 8080 è fra quelle provate",
      wifi_setup.OWN_NET_PASSWORD == "12345678" and wifi_setup.OWN_NET_IP == "192.168.4.1" and 8080 in wifi_setup.PORTS)

# ------------------------------------------------------------------ traduzioni
fam_note = next(t for _k, t in machines.identify(settings=BOARD, **brand_s).notes if "non si legge dalla scheda" in t)
for lang in ("en", "es", "fr", "pt"):
    with open(os.path.join(ROOT, "freelasercut", "locale", f"{lang}.json"), encoding="utf-8") as fh:
        loc = json.load(fh)
    t = loc.get(note, "")
    check(f"traduzione {lang} della nota: c'è, con area, CH340, comando della luce e dati della rete",
          bool(t) and t != note and all(w in t for w in ("400 × 320", "CH340", "$light/duty=200", "12345678", "192.168.4.1",
                                                         "8080", "Sculpfun E1")), t[:80])
    k = next((k for k in loc if k.startswith("{0} riconosciuto dall'area di lavoro. Il modulo laser")), "")
    check(f"traduzione {lang} dell'avviso sul modulo: c'è, con i tre segnaposto",
          bool(k) and all(p in loc[k] for p in ("{0}", "{1}", "{2}")) and loc[k] != k, loc.get(k, "")[:80])
check("l'avviso sul modulo in italiano nomina la famiglia e le altre due voci",
      fam_note.startswith("Sculpfun E1 riconosciuto") and EPRO in fam_note and EIR in fam_note, fam_note)

code_ = 0 if all(results) else 1
print(f"\n{sum(results)}/{len(results)} superati")
sys.exit(code_)
