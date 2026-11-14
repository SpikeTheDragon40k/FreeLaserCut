# FreeLaserCut — © 2026 fringuello79 — GPL-3.0-or-later
"""Versione 0.19.5: scheda Movimento con Puntino e Lucciola al centro delle frecce e joystick virtuale.

- Al centro della croce Puntino (tieni premuto) e Lucciola (resta accesa): gli stessi comandi della scheda Laser.
- «Vai a X0 Y0» nella colonna di destra.
- Interruttore Frecce | Joystick (si ricorda). Joystick: pezzetti corti di jog, al massimo 2 in attesa, velocità
  proporzionale alla distanza dal centro, zona morta, tagliati al bordo dell'area, arresto al rilascio, fermo se la
  macchina non è pronta o se FreeLaserCut perde il primo piano.
Uso: python tests/test_v195_movimento.py [banco]
"""
import math
import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp()
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp()
os.environ["FLC_SETTINGS_INI"] = os.path.join(tempfile.mkdtemp(), "prova.ini")
os.environ["FLC_UI"] = sys.argv[1] if len(sys.argv) > 1 else "classica"
os.environ["FLC_NO_DIALOGS"] = "1"
os.environ["FLC_NO_FIRST_RUN"] = "1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QFocusEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

app = QApplication([])
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Ok)

from freelasercut.grbl import SIM_PORT
from freelasercut.ui import jogpad
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


def until(fn, t=5.0):
    end = time.time() + t
    while time.time() < end:
        if fn():
            return True
        spin(0.02)
    return bool(fn())


w = MainWindow()
w.resize(1500, 950)
w.show()
spin(0.5)
mv, lz, ctl = w.move, w.laser, w.ctl
pad = mv.pad

# ---------------------------------------------------------------- com'è fatta
check("8 frecce come prima", len(mv.jog_buttons) == 8)
check("al centro della croce Puntino e Lucciola", pad.b_dot.parent() is pad.center and pad.b_glow.parent() is pad.center
      and pad.center.size().width() == 52)
check("le due metà sono cliccabili (almeno 24 px di larghezza)", pad.b_dot.width() >= 24 and pad.b_glow.width() >= 24,
      (pad.b_dot.width(), pad.b_glow.width()))
check("«Vai a X0 Y0» nella colonna di destra", mv.b_goto0.text() == "Vai a X0 Y0", mv.b_goto0.text())
check("passi come prima (0,1 · 1 · 10 · 50 · 100) e «Continuo»", [s for s, _ in mv.steps] == [0.1, 1, 10, 50, 100]
      and mv.cont is pad.cont)
check("si parte con le frecce", pad.mode() == "arrows" and pad.b_arrows.isChecked() and pad.steps_w.isVisibleTo(mv))
check("senza macchina: frecce, Puntino, Lucciola e joystick spenti", not any(b.isEnabled() for b in mv.jog_buttons)
      and not pad.b_dot.isEnabled() and not pad.b_glow.isEnabled() and not pad.pad.isEnabled())

# ---------------------------------------------------------------- con il simulatore
ctl.connect_port(SIM_PORT)
ctl.sim.speedup = 1
until(lambda: ctl.board_settings, 8)
spin(0.6)
check("macchina collegata: si accendono", all(b.isEnabled() for b in mv.jog_buttons) and pad.b_dot.isEnabled()
      and pad.b_glow.isEnabled() and pad.pad.isEnabled())
pad.b_dot.pressed.emit()
check("Puntino tenuto premuto: laser acceso (lo stesso della scheda Laser)", until(lambda: ctl.fire_active, 3))
pad.b_dot.released.emit()
check("…rilasciato: spento", until(lambda: not ctl.fire_active, 3))
pad.b_glow.click()
spin(0.4)
check("Lucciola: accesa dal centro della croce, anche nella scheda Laser", lz._glow_on and lz.b_glow.isChecked()
      and pad.b_glow.isChecked() and ctl.fire_active)
check("…si vede che è accesa (colore) e il tempo che resta nel suggerimento", "FFD43B" in pad.b_glow.styleSheet()
      and "LASER ACCESO" in pad.b_glow.toolTip(), pad.b_glow.toolTip()[:40])
lz.b_glow.click()
spin(0.4)
check("spenta dalla scheda Laser: si spegne anche al centro della croce", not lz._glow_on and not pad.b_glow.isChecked()
      and "FFD43B" not in pad.b_glow.styleSheet())
pad.b_glow.click()
spin(0.3)
pad.b_glow.click()
spin(0.3)
check("…e spenta dal centro della croce si spegne anche nella scheda Laser", not lz._glow_on and not lz.b_glow.isChecked())

# frecce come prima
sent = []
ctl.line_sent.connect(sent.append)
pad.cont.setChecked(False)
pad.set_step(10)
mv._jog_press(1, 0)
check("freccia destra, passo 10: un jog di 10 mm come prima", until(lambda: any(l.startswith("$J=G91") and "X10.000" in l
                                                                                 for l in sent), 3), sent[-2:])
until(lambda: ctl.last_status.get("state") == "Idle", 8)
pad.set_step(50)
check("passo 50 scelto e ricordato", mv.step() == 50 and float(w.qs.value("jog_step")) == 50)

# ---------------------------------------------------------------- joystick
pad.set_mode("joystick")
check("interruttore su Joystick: si vede il joystick, la fila dei passi sparisce",
      pad.mode() == "joystick" and not pad.steps_w.isVisibleTo(mv) and pad.stack.currentWidget() is pad.page_joy)
check("…Puntino e Lucciola restano, sotto il joystick", pad.b_dot.parent() is pad.page_joy and pad.b_glow.parent() is pad.page_joy)
check("…la scelta si ricorda", w.qs.value("jog_mode") == "joystick")
joy = pad.joy
mv.feed.setValue(3000)
joy.set_vector(0.5, 0)
check("velocità proporzionale alla distanza dal centro", abs(joy.speed() - (0.5 - joy.DEAD) / (1 - joy.DEAD) * 3000) < 1e-6,
      joy.speed())
joy.set_vector(1.0, 0)
check("in fondo: la «Velocità jog»", abs(joy.speed() - 3000) < 1e-6)
joy.set_vector(0.05, 0)
check("zona morta al centro: velocità 0", joy.speed() == 0)
joy.set_vector(3, 4)
check("fuori dal cerchio: limitato a 1", abs(joy.magnitude() - 1) < 1e-9)
joy.set_vector(0, 0)
L = joy._limit
check("bordo: si ferma a mezzo millimetro, e con la testa già sul bordo l'altro asse non si muove",
      L(399.0, 5.0, 400) == 399.5 and L(0.0, 0.0, 400) == 0.0 and L(0.0, -1.0, 400) == 0.0 and L(0.2, 1.0, 400) == 1.2
      and L(399.8, 1.0, 400) == 399.8, (L(399.0, 5.0, 400), L(0.0, -1.0, 400), L(399.8, 1.0, 400)))

until(lambda: w.canvas.head_pos() is not None, 3)
h0 = w.canvas.head_pos()
mx = [0]


def watch():
    mx[0] = max(mx[0], ctl.queued(jogpad.TAG))


n_sent0 = len(sent)
ok = joy.start()
check("joystick: si avvia con la macchina pronta", ok and joy.active, joy.stop_reason)
joy.set_vector(0.05, 0)
spin(0.3)
check("nella zona morta non parte niente", joy.sent == 0)
joy.set_vector(1, 0)
t_end = time.time() + 1.5
while time.time() < t_end:
    watch()
    spin(0.01)
sent_n = joy.sent
h1 = w.canvas.head_pos()
check("tenuto a destra: tanti pezzetti mandati", sent_n >= 10, sent_n)
check("…mai più di 2 in attesa sulla scheda", mx[0] <= jogpad.JoyJog.MAX_Q, mx[0])
check("…la testa va a destra e non in Y", h1.x() > h0.x() + 10 and abs(h1.y() - h0.y()) < 0.5, (h0, h1))
check("…i pezzetti non riempiono la console", not any(l.startswith("$J") for l in sent[n_sent0:]), sent[n_sent0:][:3])
joy.set_vector(0, 1)
spin(0.6)
h2 = w.canvas.head_pos()
check("cambio di direzione senza fermarsi: ora in su", h2.y() > h1.y() + 3, (h1, h2))
rt = []
_real_rt = ctl.realtime
ctl.realtime = lambda b: (rt.append(b), _real_rt(b))[1]
joy.stop()
ctl.realtime = _real_rt
check("al rilascio parte subito l'arresto del jog (0x85)", rt == [0x85], rt)
check("rilascio: fermo e niente più in coda", not joy.active and ctl.queued(jogpad.TAG) <= jogpad.JoyJog.MAX_Q)
spin(0.6)
h3 = w.canvas.head_pos()
spin(0.6)
h4 = w.canvas.head_pos()
check("…la testa si ferma davvero", math.dist((h3.x(), h3.y()), (h4.x(), h4.y())) < 0.05, (h3, h4))
check("…coda vuota", until(lambda: ctl.queued(jogpad.TAG) == 0, 3))

# l'arresto toglie dalla coda i pezzetti non ancora mandati (e solo quelli)
from freelasercut.grbl import _Cmd  # noqa: E402

with ctl._lock:
    ctl._pending.extend([_Cmd("$J=G91 G21 X0.100 F600", jogpad.TAG), _Cmd("$J=G91 G21 X0.100 F600", jogpad.TAG),
                         _Cmd("G4 P0", "altro")])
ctl.jog_cancel(tag=jogpad.TAG)
with ctl._lock:
    left_tags = [c.tag for c in ctl._pending]
check("arresto del joystick: i pezzetti in coda spariscono, gli altri comandi restano", jogpad.TAG not in left_tags
      and "altro" in left_tags, left_tags)
with ctl._lock:
    ctl._pending.clear()

# bordo dell'area
prof = w.profile
bx = prof.bed_x
w.goto_bed(bx - 3, 50)
until(lambda: w.canvas.head_pos() is not None and abs(w.canvas.head_pos().x() - (bx - 3)) < 0.1, 10)
until(lambda: ctl.last_status.get("state") == "Idle", 8)
joy.start()
joy.set_vector(1, 0)
spin(1.0)
joy.stop()
until(lambda: ctl.last_status.get("state") == "Idle", 5)
hx = w.canvas.head_pos().x()
check("verso il bordo: si ferma a mezzo millimetro dal bordo dell'area", hx <= bx - jogpad.JoyJog.MARGIN + 0.01
      and hx > bx - 1.0, (hx, bx))

# sicurezza
joy.start()
joy.set_vector(-1, 0)
spin(0.2)
joy._app_state(Qt.ApplicationInactive)
check("FreeLaserCut non più in primo piano: joystick fermato", not joy.active and joy.stop_reason)
until(lambda: ctl.last_status.get("state") == "Idle", 5)
joy.start()
joy.set_vector(-1, 0)
ctl.last_status["state"] = "Alarm"
joy.tick()
check("macchina in allarme: si ferma", not joy.active)
ctl.last_status["state"] = "Idle"
real_job = type(ctl).job_active
type(ctl).job_active = property(lambda self: True)
try:
    check("durante un lavoro non parte", joy.start() is False and not joy.active)
finally:
    type(ctl).job_active = real_job

# con il mouse sul joystick
jp = pad.pad
c = QPointF(jp.width() / 2, jp.height() / 2)


def send(t, p, btns):
    QApplication.sendEvent(jp, QMouseEvent(t, p, QPointF(jp.mapToGlobal(p.toPoint())), Qt.LeftButton, btns, Qt.NoModifier))


until(lambda: ctl.last_status.get("state") == "Idle", 5)
send(QEvent.MouseButtonPress, c, Qt.LeftButton)
send(QEvent.MouseMove, c + QPointF(0, -60), Qt.LeftButton)
spin(0.4)
check("mouse: premuto e trascinato in su, il joystick muove la testa in su", joy.active and joy.vec[1] > 0.9 and joy.sent > 0,
      (joy.active, joy.vec, joy.sent))
check("…la lettura dice la velocità e la direzione", "mm/min" in pad.readout.text() and "90°" in pad.readout.text(),
      pad.readout.text())
send(QEvent.MouseButtonRelease, c + QPointF(0, -60), Qt.NoButton)
spin(0.1)
check("…al rilascio la manopola torna al centro e si ferma", not joy.active and jp.knob == QPointF(0, 0)
      and pad.readout.text() == "Fermo", pad.readout.text())
send(QEvent.MouseButtonPress, c, Qt.LeftButton)
send(QEvent.MouseMove, c + QPointF(50, 0), Qt.LeftButton)
spin(0.1)
QApplication.sendEvent(jp, QFocusEvent(QEvent.FocusOut))
spin(0.05)
check("…se perde il fuoco si ferma", not joy.active)
send(QEvent.MouseButtonRelease, c, Qt.NoButton)
# assi invertiti: sul piano la testa va comunque dove punta la manopola
until(lambda: ctl.last_status.get("state") == "Idle", 5)
w.goto_bed(100, 100)
until(lambda: ctl.last_status.get("state") == "Idle", 10)
spin(0.3)
lz.inv_x.setChecked(True)
spin(0.3)
g0 = w.canvas.head_pos()
joy.start()
joy.set_vector(1, 0)
spin(0.8)
joy.stop()
until(lambda: ctl.last_status.get("state") == "Idle", 5)
g1 = w.canvas.head_pos()
check("asse X invertito: la manopola a destra porta la testa a destra sul piano", g1.x() > g0.x() + 3, (g0, g1))
lz.inv_x.setChecked(False)
ctl.disconnect_port()
spin(0.3)
check("scollegata: joystick spento e fermo", not pad.pad.isEnabled() and not joy.active)
pad.set_mode("arrows")
check("di nuovo Frecce: Puntino e Lucciola tornano al centro", pad.b_dot.parent() is pad.center and pad.steps_w.isVisibleTo(mv))

code_ = 0 if all(results) else 1
print(f"\n{sum(results)}/{len(results)} superati")

from _uscita import esci  # noqa: E402

esci(code_)
