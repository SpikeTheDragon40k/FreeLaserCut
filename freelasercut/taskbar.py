# FreeLaserCut — © 2026 fringuello79 — GPL-3.0-or-later
"""Barra delle applicazioni di Windows: l'icona giusta quando si fissa il programma (0.19.3).

FreeLaserCut gira dentro pythonw.exe. Dice già a Windows come si chiama (SetCurrentProcessExplicitAppUserModelID), ma
fino alla 0.19.2 non diceva come rilanciarlo né con quale icona: fissando la finestra sulla barra, Windows fissava
«pythonw.exe» nudo, con l'icona di Python, e quell'icona a programma chiuso non riapriva FreeLaserCut.

Qui si scrivono sulla finestra principale le «proprietà di rilancio» di Windows (nome, comando, icona): è il modo
previsto per i programmi ospitati da un altro eseguibile. Niente librerie nuove: solo ctypes. Su Linux non fa niente.
FLC_NO_TASKBAR=1 lo spegne (assistenza e prove).
"""
import os
import sys

APP_ID = "fringuello79.FreeLaserCut"
NAME = "FreeLaserCut"
OFF_ENV = "FLC_NO_TASKBAR"
# proprietà System.AppUserModel.* (formato {9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}, numero)
FMTID = "{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"
PID_COMMAND, PID_ICON, PID_NAME, PID_ID = 2, 3, 4, 5
IID_PROPERTY_STORE = "{886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}"
VT_LPWSTR = 31
# l'ordine conta: comando e nome vanno scritti prima dell'identificativo, che li rende validi
ORDER = (("command", PID_COMMAND), ("name", PID_NAME), ("icon", PID_ICON), ("id", PID_ID))


def gui_python(executable=None):
    """L'eseguibile con cui rilanciare: pythonw.exe (senza finestra nera) se sta accanto a python.exe."""
    exe = executable or sys.executable or ""
    folder, name = os.path.split(exe)
    if name.lower() == "python.exe":
        cand = os.path.join(folder, "pythonw.exe")
        if os.path.exists(cand):
            return cand
    return exe


def relaunch_values(executable=None, icon=None):
    """Che cosa dire a Windows: {"id", "command", "name", "icon"}. Senza eseguibile noto: None (non si scrive niente,
    meglio l'icona di Python che un comando sbagliato)."""
    exe = gui_python(executable)
    if not exe:
        return None
    if icon is None:
        icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.ico")
    values = {"id": APP_ID, "command": f'"{exe}" -m freelasercut', "name": NAME}
    if icon and os.path.exists(icon):
        values["icon"] = icon
    return values


import ctypes  # noqa: E402 — solo i tipi: nessuna chiamata a Windows finché non serve
from ctypes import wintypes  # noqa: E402


class GUID(ctypes.Structure):  # misure fisse (non «DWORD», che fuori da Windows è più larga): 16 byte
    _fields_ = [("d1", ctypes.c_uint32), ("d2", ctypes.c_uint16), ("d3", ctypes.c_uint16), ("d4", ctypes.c_ubyte * 8)]


class PROPERTYKEY(ctypes.Structure):  # 20 byte
    _fields_ = [("fmtid", GUID), ("pid", ctypes.c_uint32)]


class PROPVARIANT(ctypes.Structure):  # 16 byte a 32 bit, 24 a 64 bit: tipo, tre riservati, poi il valore
    _fields_ = [("vt", ctypes.c_ushort), ("r1", ctypes.c_ushort), ("r2", ctypes.c_ushort), ("r3", ctypes.c_ushort),
                ("pwsz", ctypes.c_void_p), ("pad", ctypes.c_void_p)]


def _guid(text):
    g = GUID()
    h = text.strip("{}").replace("-", "")
    g.d1, g.d2, g.d3 = int(h[0:8], 16), int(h[8:12], 16), int(h[12:16], 16)
    for i in range(8):
        g.d4[i] = int(h[16 + 2 * i:18 + 2 * i], 16)
    return g


def _key(pid):
    k = PROPERTYKEY()
    k.fmtid = _guid(FMTID)
    k.pid = pid
    return k


def _store(hwnd):
    """(puntatore al deposito delle proprietà della finestra, tabella dei suoi metodi) o None.
    Metodi di IPropertyStore, nell'ordine: QueryInterface, AddRef, Release, GetCount, GetAt, GetValue, SetValue,
    Commit."""
    fn = ctypes.windll.shell32.SHGetPropertyStoreForWindow
    fn.argtypes = [wintypes.HWND, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
    fn.restype = ctypes.c_long
    iid = _guid(IID_PROPERTY_STORE)
    ps = ctypes.c_void_p()
    if fn(wintypes.HWND(int(hwnd)), ctypes.byref(iid), ctypes.byref(ps)) != 0 or not ps.value:
        return None
    vtbl = ctypes.cast(ctypes.cast(ps, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
    return ps, vtbl


def set_relaunch(hwnd, values=None):
    """Scrive sulla finestra le proprietà di rilancio. -> True se Windows le ha accettate tutte.
    Su un altro sistema, senza finestra o con FLC_NO_TASKBAR=1: False, senza fare niente."""
    if sys.platform != "win32" or os.environ.get(OFF_ENV) == "1" or not hwnd:
        return False
    values = values if values is not None else relaunch_values()
    if not values or not values.get("command") or not values.get("name"):
        return False
    try:
        got = _store(hwnd)
        if got is None:
            return False
        ps, vtbl = got
        set_value = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(PROPERTYKEY),
                                       ctypes.POINTER(PROPVARIANT))(vtbl[6])
        commit = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)(vtbl[7])
        release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])
        ok = True
        keep = []  # i testi devono restare vivi finché Windows non li ha copiati
        try:
            for name, pid in ORDER:
                text = values.get(name)
                if not text:
                    continue
                buf = ctypes.create_unicode_buffer(str(text))
                keep.append(buf)
                key = _key(pid)
                var = PROPVARIANT()
                var.vt = VT_LPWSTR
                var.pwsz = ctypes.cast(buf, ctypes.c_void_p).value
                if set_value(ps, ctypes.byref(key), ctypes.byref(var)) != 0:
                    ok = False
            if commit(ps) != 0:
                ok = False
        finally:
            release(ps)
        return ok
    except Exception:  # noqa: BLE001 — è solo l'icona sulla barra: il programma parte comunque
        return False


def read_relaunch(hwnd):
    """Rilegge da Windows le proprietà scritte (per la prova di avvio e il rapporto): {"id", "command", …}."""
    out = {}
    if sys.platform != "win32" or not hwnd:
        return out
    try:
        got = _store(hwnd)
        if got is None:
            return out
        ps, vtbl = got
        get_value = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(PROPERTYKEY),
                                       ctypes.POINTER(PROPVARIANT))(vtbl[5])
        release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])
        clear = ctypes.windll.ole32.PropVariantClear
        clear.argtypes = [ctypes.POINTER(PROPVARIANT)]
        clear.restype = ctypes.c_long
        try:
            for name, pid in ORDER:
                key = _key(pid)
                var = PROPVARIANT()
                if get_value(ps, ctypes.byref(key), ctypes.byref(var)) == 0 and var.vt == VT_LPWSTR and var.pwsz:
                    out[name] = ctypes.wstring_at(var.pwsz)
                clear(ctypes.byref(var))
        finally:
            release(ps)
    except Exception:  # noqa: BLE001
        return out
    return out


def status_line(hwnd):
    """Una riga per la prova di avvio e il rapporto per l'assistenza."""
    if sys.platform != "win32":
        return ""
    if os.environ.get(OFF_ENV) == "1":
        return "barra di Windows: spenta (FLC_NO_TASKBAR)"
    got = read_relaunch(hwnd)
    if got.get("command") and got.get("id") == APP_ID:
        return "barra di Windows: ok (rilancio con " + ("icona" if got.get("icon") else "icona di Python") + ")"
    return "barra di Windows: proprietà di rilancio NON scritte"
