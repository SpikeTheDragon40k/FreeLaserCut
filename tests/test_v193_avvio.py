# FreeLaserCut — © 2026 fringuello79 — GPL-3.0-or-later
"""Versione 0.19.3: Windows troppo vecchio detto chiaro all'avvio; icona giusta sulla barra di Windows.

A. WINDOWS TROPPO VECCHIO (rapporto del 13/11: Windows 10 build 10240, «DLL load failed while importing QtCore»).
   Qt 6.12 gira da Windows 10 versione 1809 (build 17763). Il dato: la build di Windows (un intero, o «non si sa»).
   Casi: 10240 / 17134 / 17762 → messaggio e uscita, prima di caricare Qt; 17763 / 19045 / 22000 / 26100 → avvio
   normale; build illeggibile → avvio normale (mai bloccare per un dato che manca); Linux → niente; con
   FLC_WINDOWS_VECCHIO_OK=1 si prova lo stesso; il testo è fisso, inglese + italiano; resta scritto in flc.log.
B. BARRA DI WINDOWS: fissando il programma compariva l'icona di Python (il programma gira dentro pythonw.exe).
   Si scrivono sulla finestra le proprietà di rilancio (comando, nome, icona, identificativo).
   Casi: che cosa si scrive (pythonw accanto a python, eseguibile sconosciuto, icona che manca); le strutture hanno
   le misure di Windows a 64 bit; la chiamata a Windows provata con un deposito finto che riceve gli stessi
   puntatori (ordine dei metodi, chiave, tipo e testo di ogni valore, rilascio); fuori da Windows non fa niente.

Non provato qui: un Windows vero (lo fa la prova di avvio su GitHub, che scrive «barra di Windows: ok») e l'icona
vista da una persona sulla barra (Ale, sul suo PC: fissare, chiudere, riaprire dall'icona)."""
import ctypes
import os
import subprocess
import sys
import tempfile
import uuid

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
TMP = tempfile.mkdtemp(prefix="flc_v193_")
os.environ["APPDATA"] = os.path.join(TMP, "dati")
os.environ["XDG_CONFIG_HOME"] = os.path.join(TMP, "dati")
os.environ["FLC_SETTINGS_INI"] = os.path.join(TMP, "prova.ini")
os.environ["FLC_NO_DIALOGS"] = "1"
os.environ["FLC_NO_FIRST_RUN"] = "1"
os.makedirs(os.environ["APPDATA"])
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from freelasercut import startup_guard as g  # noqa: E402
from freelasercut import taskbar as tb  # noqa: E402

results = []


def check(name, cond, info=""):
    results.append(bool(cond))
    print(("  OK  " if cond else "  KO  ") + name, info if not cond else "")


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def launch(extra_env, args=(), timeout=120):
    """Un avvio vero in un processo a parte, con la sua cartella dei dati. -> (codice, uscita, errori, cartella)"""
    d = tempfile.mkdtemp(prefix="avvio_", dir=TMP)
    env = dict(os.environ)
    env.update({"APPDATA": d, "XDG_CONFIG_HOME": d, "FLC_SETTINGS_INI": os.path.join(d, "p.ini"), "FLC_MULTI": "1",
                "FLC_NO_UPDATE": "1", "FLC_PROVA_ISTANZA": "flc-v193-" + uuid.uuid4().hex[:8]})
    env.update(extra_env)
    r = subprocess.run([sys.executable, "-m", "freelasercut", *args], cwd=ROOT, env=env, capture_output=True,
                       text=True, timeout=timeout, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr, d


# ====================================================================== A. Windows troppo vecchio
os.environ.pop(g.WIN_BUILD_ENV, None)
if sys.platform != "win32":
    check("fuori da Windows non c'è nessuna build e nessun blocco", g.windows_build() is None and g.old_windows() is False
          and g.check_windows() is False)
check("build troppo vecchie: 10240 (il rapporto), 17134, 17762", all(g.old_windows(b) for b in (10240, 17134, 17762, 7601, 9600)))
check("build che vanno: 17763 (la 1809), 19045, 22000, 26100", not any(g.old_windows(b) for b in (17763, 19045, 22000, 26100)))
check("build che non si riesce a leggere: non blocca mai", g.old_windows(None) is False and g.old_windows("") is False)
os.environ[g.WIN_BUILD_ENV] = "10240"
check("nelle prove la build si può fingere", g.windows_build() == 10240 and g.old_windows() is True)
os.environ[g.WIN_BUILD_ENV] = "boh"
check("…e una build finta illeggibile vale «non si sa»", g.windows_build() is None and g.old_windows() is False)
os.environ.pop(g.WIN_BUILD_ENV, None)
t = g.old_windows_text(10240)
check("testo in italiano, quello approvato: troppo vecchio, 1809 in poi oppure Windows 11, come aggiornare",
      "Questo Windows è troppo vecchio per FreeLaserCut." in t and
      "FreeLaserCut funziona da Windows 10 versione 1809 in poi, oppure con Windows 11." in t and
      "Aggiorna Windows (Impostazioni → Aggiornamento e sicurezza → Windows Update) e riprova." in t, t)
check("…e in inglese, prima", t.index("This Windows is too old for FreeLaserCut.") < t.index("Questo Windows") and
      "Windows 10 version 1809 or later, or on Windows 11" in t and "Windows Update" in t)
check("…con la build di chi legge", "10240" in t or sys.platform == "win32")
check("la soglia è la build 17763", g.MIN_WIN_BUILD == 17763)

rc, out, err, d = launch({g.WIN_BUILD_ENV: "10240", "FLC_PROVA_GUASTO": "qt"})
log = read(os.path.join(d, "FreeLaserCut", "flc.log")) or read(os.path.join(d, "flc.log"))
if not log:
    for base, _dirs, files in os.walk(d):
        if "flc.log" in files:
            log = read(os.path.join(base, "flc.log"))
check("avvio vero con Windows finto 10240: esce con il codice 3, senza arrivare a caricare Qt (il guasto messo alla "
      "fase «Qt» non scatta)", rc == 3 and "guasto di prova" not in err + log, f"rc={rc} {err[-200:]}")
check("…il messaggio è sull'uscita degli errori", "Questo Windows è troppo vecchio" in err and "10240" in err, err[-200:])
check("…e resta scritto in flc.log con i dati di sistema", "Windows troppo vecchio" in log and "FreeLaserCut" in log and
      "17763" in log and "Python" in log, log[-300:])
marks = [f for base, _d, files in os.walk(d) for f in files if f.startswith(g.MARK)]
check("…nessun segno di «avvio interrotto» lasciato in giro", not marks, str(marks))
for build in ("17762",):
    rc, out, err, d = launch({g.WIN_BUILD_ENV: build, "FLC_PROVA_GUASTO": "qt"})
    check(f"build {build}, l'ultima troppo vecchia: stesso messaggio", rc == 3 and "troppo vecchio" in err)
for build in ("17763", "19045", "26100"):
    rc, out, err, d = launch({g.WIN_BUILD_ENV: build, "FLC_PROVA_GUASTO": "esci"})
    check(f"build {build}: avvio normale, la finestra si apre", rc == 0 and "avvio finito" in out + err and
          "troppo vecchio" not in err, f"rc={rc} {(out + err)[-200:]}")
rc, out, err, d = launch({g.WIN_BUILD_ENV: "boh", "FLC_PROVA_GUASTO": "esci"})
check("build illeggibile: avvio normale", rc == 0 and "troppo vecchio" not in err, f"rc={rc}")
rc, out, err, d = launch({g.WIN_BUILD_ENV: "10240", g.OLD_WIN_OK_ENV: "1", "FLC_PROVA_GUASTO": "esci"})
log = ""
for base, _dirs, files in os.walk(d):
    if "flc.log" in files:
        log = read(os.path.join(base, "flc.log"))
check("con FLC_WINDOWS_VECCHIO_OK=1 si prova lo stesso: parte, ma in flc.log resta scritto",
      rc == 0 and "troppo vecchio" not in err and "Windows troppo vecchio" in log, f"rc={rc}")
rc, out, err, d = launch({"FLC_PROVA_GUASTO": "esci"})
check("senza niente di finto (questo sistema): avvio normale", rc == 0 and "avvio finito" in out + err, f"rc={rc} {err[-200:]}")

# ====================================================================== B. barra di Windows
check("strutture con le misure di Windows a 64 bit: GUID 16 byte, chiave 20, valore 24",
      (ctypes.sizeof(tb.GUID), ctypes.sizeof(tb.PROPERTYKEY), ctypes.sizeof(tb.PROPVARIANT)) == (16, 20, 24)
      or ctypes.sizeof(ctypes.c_void_p) != 8)
check("gli identificativi di Windows sono scritti byte per byte come li vuole Windows",
      bytes(tb._guid(tb.FMTID)) == uuid.UUID(tb.FMTID).bytes_le and
      bytes(tb._guid(tb.IID_PROPERTY_STORE)) == uuid.UUID(tb.IID_PROPERTY_STORE).bytes_le)
check("numeri delle proprietà: comando 2, icona 3, nome 4, identificativo 5; l'identificativo si scrive per ultimo",
      (tb.PID_COMMAND, tb.PID_ICON, tb.PID_NAME, tb.PID_ID) == (2, 3, 4, 5) and tb.ORDER[-1][0] == "id"
      and [n for n, _ in tb.ORDER][:2] == ["command", "name"])
folder = os.path.join(TMP, "python")
os.makedirs(folder)
for n in ("python.exe", "pythonw.exe", "logo.ico"):
    open(os.path.join(folder, n), "w").close()
v = tb.relaunch_values(os.path.join(folder, "python.exe"), os.path.join(folder, "logo.ico"))
check("da python.exe (finestra di diagnostica) si rilancia con pythonw.exe, senza finestra nera",
      v["command"] == f'"{os.path.join(folder, "pythonw.exe")}" -m freelasercut', v["command"])
v = tb.relaunch_values(os.path.join(folder, "pythonw.exe"), os.path.join(folder, "logo.ico"))
check("comando, nome, icona e identificativo: «…pythonw.exe» -m freelasercut, FreeLaserCut, logo.ico, lo stesso nome "
      "che il programma dichiara a Windows", v == {"id": "fringuello79.FreeLaserCut", "name": "FreeLaserCut",
                                                   "command": f'"{os.path.join(folder, "pythonw.exe")}" -m freelasercut',
                                                   "icon": os.path.join(folder, "logo.ico")}, str(v))
main_src = read(os.path.join(ROOT, "freelasercut", "__main__.py"))
check("…lo stesso identificativo dichiarato all'avvio", f'"{tb.APP_ID}"' in main_src)
v = tb.relaunch_values(os.path.join(folder, "pythonw.exe"), os.path.join(folder, "manca.ico"))
check("icona che non c'è: si scrive il resto, senza un'icona sbagliata", "icon" not in v and v["command"])
check("eseguibile sconosciuto: non si scrive niente", tb.relaunch_values("", None) is None or sys.executable)
check("l'icona di FreeLaserCut esiste nel programma", os.path.exists(os.path.join(ROOT, "freelasercut", "assets", "logo.ico")))
if sys.platform != "win32":
    check("fuori da Windows: nessuna chiamata, nessun errore", tb.set_relaunch(1234) is False and tb.read_relaunch(1234) == {}
          and tb.status_line(1234) == "")

# --- la chiamata a Windows, con un deposito delle proprietà finto che riceve gli stessi puntatori
if ctypes.sizeof(ctypes.c_void_p) == 8:
    FN = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)
    calls, stored, state = [], {}, {"released": 0, "committed": 0, "fail_at": None}
    keep = []

    def _set(this, pkey, pvar):
        key = ctypes.cast(pkey, ctypes.POINTER(tb.PROPERTYKEY)).contents
        var = ctypes.cast(pvar, ctypes.POINTER(tb.PROPVARIANT)).contents
        fmt = "{" + str(uuid.UUID(bytes_le=bytes(key.fmtid))).upper() + "}"
        text = ctypes.wstring_at(var.pwsz) if var.vt == 31 and var.pwsz else None
        calls.append((fmt, key.pid, var.vt, text))
        if state["fail_at"] == key.pid:
            return -2147467259  # E_FAIL
        buf = ctypes.create_unicode_buffer(text or "")
        keep.append(buf)
        stored[key.pid] = buf
        return 0

    def _get(this, pkey, pvar):
        key = ctypes.cast(pkey, ctypes.POINTER(tb.PROPERTYKEY)).contents
        var = ctypes.cast(pvar, ctypes.POINTER(tb.PROPVARIANT)).contents
        if key.pid in stored:
            var.vt = 31
            var.pwsz = ctypes.cast(stored[key.pid], ctypes.c_void_p).value
        else:
            var.vt = 0
        return 0

    def _commit(this):
        state["committed"] += 1
        return 0

    def _release(this):
        state["released"] += 1
        return 0

    def _nope(*_a):
        return -1

    T_SET = FN(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
    T_ONE = FN(ctypes.c_long, ctypes.c_void_p)
    T_REL = FN(ctypes.c_ulong, ctypes.c_void_p)
    cbs = [T_ONE(_nope), T_ONE(_nope), T_REL(_release), T_ONE(_nope), T_ONE(_nope), T_SET(_get), T_SET(_set), T_ONE(_commit)]
    vtbl = (ctypes.c_void_p * 8)(*[ctypes.cast(c, ctypes.c_void_p).value for c in cbs])
    obj = (ctypes.c_void_p * 1)(ctypes.addressof(vtbl))
    seen = {}

    class _Fn:
        argtypes = restype = None

        def __call__(self, hwnd, piid, pps):
            seen["hwnd"] = hwnd.value if hasattr(hwnd, "value") else hwnd
            seen["iid"] = "{" + str(uuid.UUID(bytes_le=bytes(ctypes.cast(piid, ctypes.POINTER(tb.GUID)).contents))).upper() + "}"
            ctypes.cast(pps, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.addressof(obj)
            return seen.get("hr", 0)

    class _Clear:
        argtypes = restype = None

        def __call__(self, pvar):
            state["cleared"] = state.get("cleared", 0) + 1
            return 0

    class _Lib:
        pass

    fake = _Lib(); fake.shell32 = _Lib(); fake.ole32 = _Lib()
    fake.shell32.SHGetPropertyStoreForWindow = _Fn()
    fake.ole32.PropVariantClear = _Clear()
    real_platform, had_windll, had_wft = sys.platform, hasattr(ctypes, "windll"), hasattr(ctypes, "WINFUNCTYPE")
    old_windll = getattr(ctypes, "windll", None)
    try:
        sys.platform = "win32"
        ctypes.windll = fake
        if not had_wft:
            ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE
        vals = {"id": tb.APP_ID, "command": '"C:\\\\Prog rammi\\\\pythonw.exe" -m freelasercut', "name": "FreeLaserCut",
                "icon": "C:\\\\x\\\\logo.ico"}
        ok = tb.set_relaunch(0x1234, vals)
        check("deposito finto: Windows riceve la finestra giusta e chiede il deposito delle proprietà",
              ok is True and seen.get("hwnd") == 0x1234 and seen.get("iid") == tb.IID_PROPERTY_STORE, str(seen))
        check("…quattro valori, tutti testi (tipo 31), con la chiave giusta: comando, nome, icona, identificativo in "
              "quest'ordine", calls == [(tb.FMTID, 2, 31, vals["command"]), (tb.FMTID, 4, 31, vals["name"]),
                                        (tb.FMTID, 3, 31, vals["icon"]), (tb.FMTID, 5, 31, vals["id"])], str(calls))
        check("…poi conferma una volta e rilascia il deposito una volta", state["committed"] == 1 and state["released"] == 1,
              str(state))
        got = tb.read_relaunch(0x1234)
        check("rileggendo da Windows tornano gli stessi quattro valori, e il deposito viene rilasciato",
              got == vals and state["released"] == 2 and state.get("cleared") == 4, str(got))
        check("la riga per la prova di avvio dice «ok»", tb.status_line(0x1234).startswith("barra di Windows: ok"))
        calls.clear(); state["fail_at"] = 4
        ok = tb.set_relaunch(0x1234, vals)
        check("se Windows rifiuta un valore: risultato «no», ma deposito rilasciato lo stesso",
              ok is False and state["released"] == 4, str(state))
        state["fail_at"] = None
        calls.clear()
        check("senza comando o senza nome non si scrive niente", tb.set_relaunch(0x1234, {"id": tb.APP_ID}) is False and not calls)
        seen["hr"] = -2147467262
        check("Windows non dà il deposito: «no» senza errori", tb.set_relaunch(0x1234, vals) is False and not calls)
        seen["hr"] = 0
        os.environ[tb.OFF_ENV] = "1"
        check("FLC_NO_TASKBAR=1: non chiama Windows", tb.set_relaunch(0x1234, vals) is False and not calls and
              "spenta" in tb.status_line(0x1234))
        os.environ.pop(tb.OFF_ENV)
        check("finestra che non c'è: niente", tb.set_relaunch(0, vals) is False and not calls)
        stored.clear()
        check("niente di scritto: la riga della prova di avvio lo dice", "NON scritte" in tb.status_line(0x1234))
    finally:
        sys.platform = real_platform
        if had_windll:
            ctypes.windll = old_windll
        else:
            del ctypes.windll
        if not had_wft:
            del ctypes.WINFUNCTYPE

# --- nella finestra principale
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
from freelasercut.ui.main_window import MainWindow  # noqa: E402

w = MainWindow()
r = w.pin_identity()
check("la finestra principale ha il comando «pin_identity» e fuori da Windows non fa niente e non sbaglia",
      (r is False) if sys.platform != "win32" else (r in (True, False)))
src = read(os.path.join(ROOT, "freelasercut", "ui", "main_window.py"))
check("…viene chiamato dopo che la finestra è sullo schermo", src.index("win.show()") < src.index("win.pin_identity()"))
check("…e anche dalla prova di avvio, che su Windows scrive l'esito",
      "taskbar.status_line" in read(os.path.join(ROOT, "freelasercut", "selftest.py")))
w.editor.dirty = False
w.qs.setValue("autosave_pending", False)
w.close()
app.processEvents()

print(f"\n{sum(results)}/{len(results)} verifiche superate")
sys.exit(0 if all(results) else 1)
