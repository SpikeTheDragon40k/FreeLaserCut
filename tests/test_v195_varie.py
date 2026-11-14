# FreeLaserCut — © 2026 fringuello79 — GPL-3.0-or-later
"""Versione 0.19.5: finestra del nesting manuale che si nota, elenco delle scorciatoie rifatto, Sculpfun E1
riconosciuta dalla scritta della scheda, «Riconosci la macchina → Applica» che non perde più angolo e assi.
Uso: python tests/test_v195_varie.py [banco]
"""
import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp()
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp()
os.environ["FLC_SETTINGS_INI"] = os.path.join(tempfile.mkdtemp(), "prova.ini")
UI = sys.argv[1] if len(sys.argv) > 1 else "classica"
os.environ["FLC_UI"] = UI
os.environ["FLC_NO_DIALOGS"] = "1"
os.environ["FLC_NO_FIRST_RUN"] = "1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics, QKeySequence, QTransform
from PySide6.QtWidgets import QApplication, QMessageBox

app = QApplication([])
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Ok)

from freelasercut import machines
from freelasercut.core.document import RectShape
from freelasercut.grbl import SIM_PORT
from freelasercut.profile import MachineProfile
from freelasercut.ui import shortcuts
from freelasercut.ui.main_window import MainWindow

results = []


def check(name, cond, info=""):
    results.append(bool(cond))
    print(("OK  " if cond else "NO  ") + name + (f"  [{info}]" if info and not cond else ""))


def spin(t=0.05):
    end = time.time() + t
    while time.time() < end:
        app.processEvents()
        time.sleep(0.005)


w = MainWindow()
w.resize(1500, 950)
w.show()
spin(0.6)
ed = w.editor

# ================================================================== 1. nesting manuale: la finestra sporge a sinistra
parts = []
for i in range(4):
    s = RectShape(20, 12)
    s.apply(QTransform.fromTranslate(300 + i * 30, 250))
    parts.append(s)
ed.add(parts, select=False)
ed.select(parts)
scr = w.screen().availableGeometry()
# la finestra tutta dentro lo schermo (senza schermo vero può stare in parte fuori); w.move è il pannello Movimento
w.setGeometry(scr.x(), scr.y() + 30, min(1500, scr.width()), min(950, scr.height() - 30))
spin(0.4)
panel = w.nest_dialog(mode="manual")
spin(0.3)
left = panel.right_panels_left()
g = panel.frameGeometry()
adv = QFontMetrics(panel.font()).horizontalAdvance("Nesting")
check("ci sono pannelli sul lato destro (dock o pannello del Banco)", left is not None, left)
if left is not None:
    want = max(scr.left(), min(left - adv - 8, scr.right() - panel.width()))
    check("la finestra sporge a sinistra dei pannelli quanto la parola «Nesting» (+ qualche pixel), dentro lo schermo",
          abs(panel.x() - want) <= 2 and (want != left - adv - 8 or panel.x() < left), (left, panel.x(), adv, want))
    if want == left - adv - 8:  # senza schermo vero la finestra può essere più larga dello schermo: lì si ferma al bordo
        check("…e per il resto copre i pannelli (il suo bordo destro è oltre il loro bordo sinistro)",
              g.right() > left + 100, (g.right(), left))
    check("…ed è dentro lo schermo", panel.screen().availableGeometry().contains(panel.geometry().topLeft()))
check("resta stretta e in alto, come prima", panel.width() <= 400 and panel.y() >= w.geometry().top() + 100)
PX = type(panel).place_x
check("calcolo: pannelli da x=1500, «Nesting» 50 px, finestra 380, schermo 1920: x = 1442 (sporge di 58 px)",
      PX(1500, 50, 380, 1900, (0, 1919)) == 1442, PX(1500, 50, 380, 1900, (0, 1919)))
check("calcolo: pannelli stretti al bordo dello schermo: la finestra resta dentro (x = 1920 − 380)",
      PX(1800, 50, 380, 1900, (0, 1919)) == 1539, PX(1800, 50, 380, 1900, (0, 1919)))
check("calcolo: senza pannelli come prima (40 px dal bordo destro della finestra)", PX(None, 50, 380, 1900, (0, 1919)) == 1480)
check("calcolo: su un secondo schermo a destra (da 1920 a 3839) le misure valgono lì",
      PX(3400, 50, 380, 3800, (1920, 3839)) == 3342)
panel.cancel()
spin(0.2)
# senza pannelli a destra: come prima
if UI == "classica":
    vis = {k: d.isVisible() for k, d in w.docks.items()}
    for d in w.docks.values():
        d.hide()
    spin(0.2)
    ed.select(parts)
    panel = w.nest_dialog(mode="manual")
    spin(0.3)
    check("pannelli nascosti: niente da cui sporgere, la finestra va dove andava prima (a destra della finestra)",
          panel.right_panels_left() is None and abs(panel.x() - (w.geometry().right() - panel.width() - 40)) <= 2
          or panel.screen().availableGeometry().right() - panel.width() == panel.x(), (panel.x(), w.geometry()))
    panel.cancel()
    for k, d in w.docks.items():
        d.setVisible(vis[k])
    spin(0.2)

# ================================================================== 2. scorciatoie da tastiera
dlg = w.show_shortcuts()
spin(0.2)
check("Aiuto → Scorciatoie (F1): una finestra propria, ridimensionabile, con la ricerca", dlg is not None and dlg.isVisible()
      and hasattr(dlg, "search") and not isinstance(dlg, QMessageBox))
html_all, n_all = shortcuts.to_html()
check("una scorciatoia per riga, il tasto in grassetto", "<tr><td" in html_all and "<b>Ctrl+Z</b>" in html_all
      and n_all >= 80, n_all)
secs = [t for t, _r in shortcuts.sections()]
check("sezioni con un titolo vero, anche quelle di prima (Disponi, Banco, Piani di lavoro)",
      all(t in secs for t in ("Strumenti", "Sulla tela", "Nodi", "Modifica", "Laser", "Disponi", "Interfaccia Banco",
                              "Piani di lavoro", "Guida")), secs)
rows = {k: d for _t, r in shortcuts.sections() for k, d, _a in r}
check("ci sono i tasti nuovi dei nodi: J, Maiusc+J, Ctrl+clic, Ctrl+A", "J" in rows and "Maiusc+J" in rows
      and any("Ctrl+clic" in k for k in rows) and "Ctrl+A" in rows)
check("e gli spostamenti della testa: frecce senza selezione, Continuo, Joystick",
      any("senza niente selezionato" in k for k in rows) and any("Joystick" in k for k in rows)
      and any("Continuo" in k for k in rows))
dlg.search.setText("nodi")
spin(0.1)
check("ricerca «nodi»: solo le righe che c'entrano", 0 < dlg.count < n_all and "Unisce due estremi" in dlg.view.toHtml(),
      dlg.count)
dlg.search.setText("zzzz")
spin(0.1)
check("ricerca senza risultati: lo dice", dlg.count == 0 and "Nessuna scorciatoia" in dlg.view.toPlainText())
dlg.search.setText("")
dlg.close()


def norm(k):
    return k.replace("Maiusc", "Shift").replace("Invio", "Return").replace("Spazio", "Space").replace("Pausa", "Pause") \
        .replace("PagSu", "PgUp").replace("PagGiù", "PgDown")


bad = []
for _t, r in shortcuts.sections():
    for k, d, act in r:
        if act is None:
            continue
        have = {QKeySequence(x).toString() for x in [s_.toString() for s_ in w.acts[act].shortcuts()]}
        want = [QKeySequence(norm(x.strip())).toString() for x in norm(k).replace(" / ", " o ").split(" o ")]
        if not any(x in have for x in want):
            bad.append((k, act, sorted(have)))
check("ogni scorciatoia dell'elenco legata a un comando è davvero quella del comando", not bad, bad)

# ================================================================== 3. Sculpfun E1 dalla scritta della scheda
BOARD = {22: "1", 30: "1000", 32: "1", 130: "400.000", 131: "320.000", 110: "36000", 111: "36000"}
for lab, info in (("riga [VER:] di $I", ["[VER:1.3a.20260618:Sculpfun E1]", "[OPT:PHS,15,256]"]),
                  ("messaggio d'avvio", ["[MSG:Using machine: Sculpfun E1]"])):
    i = machines.identify(banner=["Grbl 1.3a ['$' for help]"], info=info, settings=BOARD)
    texts = " | ".join(t for _k, t in i.notes)
    check(f"E1 dalla {lab}: marca Sculpfun, «Sculpfun E1 12W», le altre due fra i candidati, lo dice",
          i.vendor == "Sculpfun" and i.model == "Sculpfun E1 12W" and list(i.candidates) == list(machines.E1)
          and "riconosciuta dalla scheda" in texts and "non si legge dalla scheda" in texts, (i.vendor, i.model, texts))
i = machines.identify(banner=["Grbl 1.3a"], info=["[MSG:Using machine: Sculpfun E1]"],
                      settings={**BOARD, 130: "410.000", 131: "400.000"})
texts = " | ".join(t for _k, t in i.notes)
check("E1 dalla scritta anche con un'area diversa, e avvisa di controllare $130/$131",
      i.model == "Sculpfun E1 12W" and "$130" in texts, texts)
i = machines.identify(banner=["Grbl 1.3a"], info=["[MSG:Using machine: Sculpfun E1]"],
                      settings={**BOARD, 130: "320.000", 131: "400.000"})
check("…con X e Y scambiati nessun avviso sull'area", i.model == "Sculpfun E1 12W"
      and not any("$130" in t for _k, t in i.notes))
i = machines.identify(banner=["Grbl 1.1h"], info=["[MSG:FW:SCULPFUN V2.1]"], settings={**BOARD, 130: "410", 131: "400"})
check("«Sculpfun» senza «E1»: resta solo la marca (S10/S30 da scegliere)", i.vendor == "Sculpfun"
      and i.model != "Sculpfun E1 12W" and not set(machines.E1) & set(i.candidates), (i.model, i.candidates))
i = machines.identify(banner=["Grbl 1.1h"], info=["[MSG:Using machine: Sculpfun E10]"], settings={130: "410", 131: "400"})
check("«Sculpfun E10» (nome diverso) non è una E1", i.model != "Sculpfun E1 12W")
i = machines.identify(banner=["Grbl 1.3a"], info=["[VER:1.3a.20260618:]"], settings=BOARD)
check("senza la scritta: resta il riconoscimento dall'area della 0.19.4", i.model == "Sculpfun E1 12W" and not i.vendor
      and any("solo dall'area" in t for _k, t in i.notes))

# ================================================================== 3b. materiali dalla tabella ufficiale Sculpfun (E1)
from freelasercut.core import materials as mats  # noqa: E402

pro = mats.official("Sculpfun E1 Pro 21W")
cut3 = [m for m in pro if m.operation == "taglio" and m.name == "Compensato di tiglio" and m.thickness == 3]
check("E1 Pro 21 W: taglio del compensato di tiglio 3 mm a 750 mm/min, 100%, 1 passata (tabella Sculpfun)",
      len(cut3) == 1 and cut3[0].speed == 750 and cut3[0].power == 100 and cut3[0].passes == 1
      and cut3[0].source == "Tabella Sculpfun E1", cut3)
e12 = mats.official("Sculpfun E1 12W")
check("E1 12 W: 11 incisioni e 5 tagli; modulo IR: 7 incisioni e nessun taglio",
      sum(m.operation == "incisione" for m in e12) == 11 and sum(m.operation == "taglio" for m in e12) == 5
      and len(mats.official("Sculpfun E1 3W IR")) == 7
      and not any(m.operation == "taglio" for m in mats.official("Sculpfun E1 3W IR")))
lib = mats.library(2.0, "Sculpfun E1 12W")
check("con una E1 la libreria usa la tabella Sculpfun e non la stima dalla tabella Longer",
      lib and all(m.source == "Tabella Sculpfun E1" for m in lib if m.machine != "Longer B1 40W" or m.source != "Longer B1 40W")
      and not any(m.source == "Longer B1 40W" for m in lib), {m.source for m in lib})
lib2 = mats.library(None, "Longer B1 40W")
check("con le altre macchine non cambia niente (tabella Longer)", lib2 and all(m.source == "Longer B1 40W" for m in lib2)
      and len(lib2) == len(mats.builtin()))
check("le incisioni restano riempimenti (mai una foto per sbaglio) e i tagli linee",
      all((m.mode == "fill") == (m.operation == "incisione") and m.mode in ("fill", "line") for m in pro))

# ================================================================== 4. Riconosci la macchina → Applica
old = MachineProfile(name="Prova", model="Prova", bed_x=400, bed_y=300)
old.set_view_rot(1)
old.origin_corner = "bl"
old.invert_x, old.tested_x = True, True
old.negative_space = False
new = MachineProfile(name="Prova", model="Prova", bed_x=400, bed_y=300)
new.keep_user_orientation(old)
check("profilo rifatto: tiene piano ruotato, angolo dello 0, asse provato e coordinate già viste", new.rot() == 1
      and new.origin_corner == "bl" and new.invert_x and new.tested_x and new.negative_space is False, new)
check("…l'asse non provato segue l'angolo scelto (dietro = Y invertito con coordinate positive)",
      new.invert_y is True and not new.tested_y)
check("…le corse della macchina restano quelle (piano ruotato: larghezza e altezza scambiate)",
      tuple(new.travel()) == (400.0, 300.0), new.travel())
fresh_p = MachineProfile(name="Altra", model="Altra", bed_x=400, bed_y=300)
fresh_p.keep_user_orientation(MachineProfile(name="Altra"))
check("da un profilo senza scelte: niente cambia", fresh_p.rot() == 0 and not fresh_p.invert_x and not fresh_p.invert_y
      and not fresh_p.tested_x)
# con la finestra vera (simulatore)
from freelasercut.ui.dialogs_machine import MachineWizard  # noqa: E402

sim = MachineProfile(name="Simulatore", model="Simulatore", bed_x=450, bed_y=440)
sim.origin_corner = "bl"
sim.invert_y, sim.tested_y = True, True
sim.set_view_rot(3)
sim.save()
mw = MachineWizard(w)
mw._done(dict(baud=115200, banner=["Grbl 1.1h"], info=["[VER:1.1.2023080801:]", "[MSG:FW:LGT V1.2.3|MB:LS_ESP32-SIM]"],
              settings={130: "450.000", 131: "440.000", 22: "1", 30: "1000", 32: "1"}),
         machines.PortInfo(SIM_PORT, "Simulatore"))
mw.apply(connect=False)
p = MachineProfile.load(sim.path())
check("Riconosci → Applica sulla stessa macchina: angolo, asse provato e piano ruotato restano",
      p.origin_corner == "bl" and p.invert_y and p.tested_y and p.rot() == 3 and w.profile.rot() == 3,
      (p.origin_corner, p.invert_y, p.tested_y, p.rot()))
mw.close()

code_ = 0 if all(results) else 1
print(f"\n{sum(results)}/{len(results)} superati")

from _uscita import esci  # noqa: E402

esci(code_)
