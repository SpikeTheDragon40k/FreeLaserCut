# FreeLaserCut — © 2026 fringuello79 — GPL-3.0-or-later
"""Impostazioni → Configurazione guidata della macchina (anche al primo avvio).

Poche domande: il modello, l'angolo in cui sta lo 0 della macchina e, se il laser è collegato, la prova delle
frecce. Da lì FreeLaserCut ricava il verso degli assi, così testa e lavoro compaiono nel punto giusto del piano.
Alla fine: nomi sotto i comandi oppure modalità esperto. Si può rifare quando si vuole."""
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QRadioButton, QGridLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout,
    QWidget,
)

from .. import machines
from ..profile import MachineProfile
from ..theme import C
from . import style
from freelasercut.i18n import tr  # noqa: E402

CORNERS = {"bl": tr("dietro a sinistra"), "br": tr("dietro a destra"), "fl": tr("davanti a sinistra"),
           "fr": tr("davanti a destra")}
STEP_MM = 10.0
JOG_FEED = 1500


def corner_name(corner):
    return CORNERS.get(corner or "fl", CORNERS["fl"])


class CornerPicker(QWidget):
    """Il piano visto dall'alto, con i quattro angoli da cliccare. In alto il fondo della macchina."""

    changed = Signal(str)
    W, H = 320, 220

    def __init__(self, corner="fl", parent=None):
        super().__init__(parent)
        self.corner = corner if corner in CORNERS else "fl"
        self.touched = False  # l'utente ha scelto un angolo (non solo lasciato quello proposto, né «Non lo so»)
        self.setFixedSize(self.W, self.H)
        self.setCursor(Qt.PointingHandCursor)

    def _bed(self):
        return QRectF(40, 26, self.W - 80, self.H - 56)

    def _points(self):
        r = self._bed()
        return {"bl": r.topLeft(), "br": r.topRight(), "fl": r.bottomLeft(), "fr": r.bottomRight()}

    def set_corner(self, c):
        if c in CORNERS and c != self.corner:
            self.corner = c
            self.update()
            self.changed.emit(c)

    def choose(self, c):
        """Angolo scelto dall'utente (clic)."""
        self.touched = True
        if c == self.corner:
            self.changed.emit(c)
        self.set_corner(c)

    def mousePressEvent(self, e):
        pos = e.position()
        best = min(self._points().items(), key=lambda kv: (kv[1] - pos).manhattanLength())
        self.choose(best[0])

    def paint_corner(self, p, pt, on):
        col = QColor(C["accent"]) if on else QColor(C["muted"])
        p.setPen(QPen(col, 2))
        p.setBrush(col if on else Qt.NoBrush)
        p.drawEllipse(pt, 11 if on else 8, 11 if on else 8)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self._bed()
        pal = self.palette()
        p.setPen(QPen(QColor(C["muted"]), 1.5))
        p.setBrush(pal.color(QPalette.Base))
        p.drawRoundedRect(r, 6, 6)
        p.setFont(style.ui_font(8))
        p.setPen(pal.color(QPalette.WindowText))
        p.drawText(QRectF(0, 2, self.W, 20), Qt.AlignCenter, tr("DIETRO (fondo della macchina)"))
        p.drawText(QRectF(0, self.H - 24, self.W, 20), Qt.AlignCenter, tr("DAVANTI (verso di te)"))
        for c, pt in self._points().items():
            self.paint_corner(p, pt, c == self.corner)
        # piccola testa nell'angolo scelto
        pt = self._points()[self.corner]
        p.setPen(QPen(QColor(C["accent_hi"]), 2))
        p.setBrush(Qt.NoBrush)
        inward = QPointF(18 if "l" in self.corner[1:] else -18, 18 if self.corner[0] == "b" else -18)
        p.drawText(QRectF(pt.x() + inward.x() - 40, pt.y() + inward.y() - 8, 80, 16), Qt.AlignCenter, "0,0")
        p.end()


ROT_NAMES = {0: tr("non ruotato"), 1: tr("ruotato a sinistra"), 3: tr("ruotato a destra"), 2: tr("capovolto")}


class PlanePreview(QWidget):
    """Il piano come si vedrà sullo schermo con un certo orientamento: il rettangolo con le sue proporzioni, il
    pallino dello 0 della macchina e le frecce degli assi X e Y (0.19.3)."""

    clicked = Signal()
    W, H = 150, 118

    def __init__(self, k, parent=None):
        super().__init__(parent)
        self.k = int(k)
        self.prof = None
        self.on = False
        self.setFixedSize(self.W, self.H)
        self.setCursor(Qt.PointingHandCursor)

    def set_machine(self, travel, invert, negative):
        q = MachineProfile(bed_x=float(travel[0]), bed_y=float(travel[1]), invert_x=bool(invert[0]),
                           invert_y=bool(invert[1]), negative_space=negative)
        q.set_view_rot(self.k)
        self.prof = q
        self.update()

    def set_on(self, on):
        self.on = bool(on)
        self.update()

    def mousePressEvent(self, _e):
        self.clicked.emit()

    def geometry_now(self):
        """(rettangolo del piano nel riquadro, punto dello 0, punta della freccia X, punta della freccia Y), in
        pixel del riquadro; le frecce partono dallo 0 e vanno verso l'interno del piano."""
        q = self.prof
        if q is None:
            return None
        bw, bh = max(q.bed_x, 1.0), max(q.bed_y, 1.0)
        k = min((self.W - 36) / bw, (self.H - 36) / bh)
        r = QRectF((self.W - bw * k) / 2, (self.H - bh * k) / 2, bw * k, bh * k)

        def px(u, v):  # piano (v verso l'alto) → pixel (y verso il basso)
            return QPointF(r.left() + u * k, r.bottom() - v * k)

        zu, zv = q.home_corner()
        tips = []
        for d in ((1.0, 0.0), (0.0, 1.0)):
            du, dv = q.from_machine_delta(*d)
            # verso l'interno del piano (con le coordinate negative il verso positivo esce dal piano)
            if not (-1e-6 <= zu + du * 1e-3 <= bw + 1e-6 and -1e-6 <= zv + dv * 1e-3 <= bh + 1e-6):
                du, dv = -du, -dv
            length = min(0.55 * (bw if du else bh), 46 / k)
            tips.append(px(zu + du * length, zv + dv * length))
        return r, px(zu, zv), tips[0], tips[1]

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = self.geometry_now()
        if g is None:
            p.end()
            return
        r, zero, tip_x, tip_y = g
        pal = self.palette()
        p.setPen(QPen(QColor(C["accent"] if self.on else C["muted"]), 2.5 if self.on else 1.2))
        p.setBrush(pal.color(QPalette.Base))
        p.drawRoundedRect(r, 4, 4)
        p.setFont(style.ui_font(8))
        for tip, name, col in ((tip_x, "X", "#D9480F"), (tip_y, "Y", "#1971C2")):
            p.setPen(QPen(QColor(col), 2))
            p.drawLine(zero, tip)
            d = tip - zero
            n = max(abs(d.x()) + abs(d.y()), 1.0)
            ux, uy = d.x() / n, d.y() / n
            for sgn in (1, -1):  # punta della freccia
                p.drawLine(tip, QPointF(tip.x() - 6 * ux + sgn * 4 * uy, tip.y() - 6 * uy - sgn * 4 * ux))
            p.drawText(QRectF(tip.x() + 8 * ux - 8 + 6 * abs(uy), tip.y() + 8 * uy - 8 + 0 * abs(ux), 16, 16),
                       Qt.AlignCenter, name)
        p.setPen(QPen(QColor(C["accent_hi"]), 2))
        p.setBrush(QColor(C["accent_hi"]))
        p.drawEllipse(zero, 4, 4)
        p.end()


def _title(text):
    lab = QLabel(f"<b>{text}</b>")
    lab.setStyleSheet("font-size: 13pt;")
    return lab


def _text(html):
    lab = QLabel(html)
    lab.setWordWrap(True)
    lab.setTextFormat(Qt.RichText)
    return lab


class SetupWizard(QDialog):
    """main: MainWindow. first=True al primo avvio (il pulsante per uscire diventa «Più tardi»)."""

    def __init__(self, main, first=False):
        super().__init__(main)
        self.main, self.first = main, first
        self.setWindowTitle(tr("Configurazione guidata della macchina"))
        self.setMinimumWidth(560)
        p = main.profile
        self.tested = [bool(p.tested_x or p.axes_tested), bool(p.tested_y or p.axes_tested)]
        self.inv = [p.invert_x, p.invert_y]
        self._sign_before = tuple(getattr(main.ctl, "axis_sign", (1.0, 1.0)))
        self._rot_before = int(getattr(main.ctl, "axis_rot", 0) or 0)
        v = QVBoxLayout(self)
        self.step_lab = QLabel()
        self.step_lab.setObjectName("muted")
        v.addWidget(self.step_lab)
        self.stack = QStackedWidget()
        v.addWidget(self.stack, 1)
        self._page_model(p)
        self._page_corner(p)
        self._page_arrows()
        self._page_rotation(p)
        self._page_end()
        row = QHBoxLayout()
        self.b_skip = QPushButton(tr("Più tardi") if first else tr("Annulla"))
        self.b_skip.clicked.connect(self.reject)
        row.addWidget(self.b_skip)
        row.addStretch(1)
        self.b_back = QPushButton(tr("Indietro"))
        self.b_back.clicked.connect(lambda: self.go(self.stack.currentIndex() - 1))
        row.addWidget(self.b_back)
        self.b_next = QPushButton(tr("Avanti"))
        self.b_next.setObjectName("primary")
        self.b_next.setDefault(True)
        self.b_next.clicked.connect(self._next)
        row.addWidget(self.b_next)
        v.addLayout(row)
        self.go(0)

    # ------------------------------------------------------------------ pagine
    def _page_model(self, p):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(_title(tr("Quale laser hai?")))
        v.addWidget(_text(tr("Scegli il modello: FreeLaserCut prende area di lavoro e velocità di targa. Se il tuo non c'è, "
                             "scegli l'ultima voce: i valori veri si leggono dalla scheda quando la colleghi.")))
        self.model = QComboBox()
        names = machines.catalog_names()
        self.model.addItems(names)
        cur = p.model if p.model in names else (p.name if p.name in names else None)
        # profilo che non viene dal catalogo (riconosciuto dalla scheda, rinominato…): resta il primo della lista e
        # resta quello scelto, così Avanti non lo sostituisce con il primo modello del catalogo
        self.keep_label = None if cur else tr("Il profilo attuale: {0}", p.name)
        if self.keep_label:
            self.model.insertItem(0, self.keep_label)
            self.model.setCurrentIndex(0)
        else:
            self.model.setCurrentText(cur)
        self.model.currentTextChanged.connect(self._model_changed)
        v.addWidget(self.model)
        self.model_note = _text("")
        self.model_note.setObjectName("muted")
        v.addWidget(self.model_note)
        v.addStretch(1)
        self.stack.addWidget(w)
        self._model_changed(self.model.currentText())

    def _model_changed(self, name):
        self.model_note.setText(machines.NOTES.get(name, ""))
        if not hasattr(self, "tested"):
            return
        p = self.main.profile
        if self._same_model():  # la macchina di adesso: quello che si sa già dei suoi assi
            self.tested = [bool(p.tested_x or p.axes_tested), bool(p.tested_y or p.axes_tested)]
            self.inv = [p.invert_x, p.invert_y]
        else:  # un'altra macchina: niente di quella attuale vale per lei
            self.tested = [False, False]
            self.inv = [False, False]

    def _page_corner(self, p):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(_title(tr("Dov'è lo 0 della tua macchina?")))
        v.addWidget(_text(tr("Clicca l'angolo del piano in cui va la testa con l'<b>homing</b>. Se la macchina non ha "
                             "l'homing, è l'angolo da cui parte: lì va messa la testa prima di accenderla.<br>"
                             "Quasi tutti i laser a diodo hanno lo 0 <b>davanti a sinistra</b>; molte schede MKS DLC32 "
                             "<b>dietro a sinistra</b>.")))
        h = QHBoxLayout()
        h.addStretch(1)
        self.picker = CornerPicker(p.corner_now())
        self._unknown = False
        self.picker.changed.connect(self._corner_changed)
        h.addWidget(self.picker)
        h.addStretch(1)
        v.addLayout(h)
        r = QHBoxLayout()
        self.corner_lab = QLabel(tr("Lo 0 è {0}.", corner_name(self.picker.corner)))
        r.addWidget(self.corner_lab, 1)
        b = QPushButton(tr("Non lo so"))
        b.setToolTip(tr("Lascia davanti a sinistra, come la maggior parte dei laser: lo confermi con la prova delle frecce"))
        b.clicked.connect(self._dont_know)
        r.addWidget(b)
        v.addLayout(r)
        self.stack.addWidget(w)

    def _corner_changed(self, c):
        note = ""
        if self.picker.touched:
            self._unknown = False
            # 0.19.3 (rapporti del 14/11, Falcon A1): l'angolo indicato adesso vale più di una prova delle frecce
            # fatta prima. Fino alla 0.19.2 gli assi «provati» restavano com'erano e l'angolo scelto veniva ignorato
            # in silenzio: lo 0 tornava sempre dov'era. L'asse che cambia torna «da provare»: le frecce lo confermano.
            neg = self.main.profile.negative_space if self._same_model() else None
            want = MachineProfile.corner_inversion(c, neg)
            changed = [a for a in (0, 1) if self.tested[a] and bool(self.inv[a]) != bool(want[a])]
            for a in changed:
                self.inv[a] = bool(want[a])
                self.tested[a] = False
            if changed:
                note = " " + tr("Gli assi seguono questo angolo: al passo dopo confermali con la prova delle frecce.")
        self.corner_lab.setText(tr("Lo 0 è {0}.", corner_name(c)) + note)

    def _dont_know(self):
        """«Non lo so»: propongo davanti a sinistra ma non lo do per vero (il verso degli assi resta com'è finché non
        lo provi con le frecce)."""
        self.picker.touched = False
        self.picker.set_corner("fl")
        self._unknown = True
        self.corner_lab.setText(tr("Lo 0 non è indicato: lo scoprirai con la prova delle frecce."))

    def _page_arrows(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(_title(tr("Prova delle frecce")))
        self.arrows_intro = _text("")
        v.addWidget(self.arrows_intro)
        self.arrows_box = QWidget()
        g = QGridLayout(self.arrows_box)
        self.b_arrow = {}
        for key, text, row, col in (("up", tr("↑ verso il fondo"), 0, 1), ("left", tr("← sinistra"), 1, 0),
                                    ("right", tr("destra →"), 1, 2), ("down", tr("↓ verso di te"), 2, 1)):
            b = QPushButton(text)
            b.setMinimumHeight(34)
            b.clicked.connect(lambda _=False, k=key: self.jog(k))
            g.addWidget(b, row, col)
            self.b_arrow[key] = b
        self.fix_x = QPushButton(tr("Sinistra–destra al contrario: correggi"))
        self.fix_x.clicked.connect(lambda: self.fix(0))
        self.fix_y = QPushButton(tr("Fondo–davanti al contrario: correggi"))
        self.fix_y.clicked.connect(lambda: self.fix(1))
        g.addWidget(self.fix_x, 3, 0, 1, 3)
        g.addWidget(self.fix_y, 4, 0, 1, 3)
        v.addWidget(self.arrows_box)
        self.b_home = QPushButton(tr("Homing"))
        self.b_home.setToolTip(tr("La macchina è bloccata (allarme): con l'homing si sblocca e trova lo 0"))
        self.b_home.clicked.connect(lambda: self.main.ctl.home())
        self.b_home.setVisible(False)
        v.addWidget(self.b_home)
        self.arrows_lab = _text("")
        v.addWidget(self.arrows_lab)
        self._last_axis = None
        # spostamento rifiutato dalla scheda (fuori area, macchina bloccata): non vale come prova, e lo dico
        self.main.ctl.error_raised.connect(self._jog_refused)
        v.addStretch(1)
        self.stack.addWidget(w)

    def _page_rotation(self, p):
        """0.19.3 — da dove guardi il piatto. Dopo assi e punto zero: cambia solo come si vede il piano."""
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(_title(tr("Come vuoi vedere il piano?")))
        v.addWidget(_text(tr("<b>Di norma non serve ruotare il piano.</b> Usalo solo se la tua macchina ha un lato molto "
                             "più lungo dell'altro e vuoi disegnare con il lato lungo in orizzontale. Cambia solo come "
                             "vedi il piano: assi, punto zero e file restano quelli della macchina.")))
        row = QHBoxLayout()
        self.rot_group = QButtonGroup(self)
        self.rot_radio, self.rot_prev = {}, {}
        for k, text in ((0, tr("Non ruotato (consigliato)")), (1, tr("Ruotato a sinistra")), (3, tr("Ruotato a destra"))):
            col = QVBoxLayout()
            prev = PlanePreview(k)
            b = QRadioButton(text)
            prev.clicked.connect(lambda bb=b: bb.setChecked(True))
            b.toggled.connect(lambda _on=False: self._rotation_changed())
            self.rot_group.addButton(b)
            col.addWidget(prev, 0, Qt.AlignHCenter)
            col.addWidget(b, 0, Qt.AlignHCenter)
            row.addLayout(col)
            self.rot_radio[k], self.rot_prev[k] = b, prev
        v.addLayout(row)
        self.rot_lab = _text("")
        v.addWidget(self.rot_lab)
        note = _text(tr("Con il piano ruotato: le righe di riempimenti e immagini seguono lo schermo, quindi corrono lungo "
                        "l'asse lungo della macchina (per i riempimenti puoi rimetterle sull'altro asse con «Angolo di "
                        "scansione» a 90°); il rotativo non si può usare; cambiando orientamento la cronologia di "
                        "Annulla del disegno aperto si azzera."))
        note.setObjectName("muted")
        v.addWidget(note)
        v.addStretch(1)
        self.stack.addWidget(w)
        k0 = p.rot() if p.rot() in self.rot_radio else 0
        self.rot_radio[k0].setChecked(True)

    def rot_choice(self):
        return next((k for k, b in self.rot_radio.items() if b.isChecked()), 0)

    def _wizard_travel(self):
        """Corse della macchina scelta nel primo passo."""
        if self._same_model():
            return self.main.profile.travel()
        pre = machines.preset_profile(self.model.currentText())
        return pre.travel()

    def _enter_rotation(self):
        same = self._same_model()
        neg = self.main.profile.negative_space if same else None
        inv = self._final_axes()
        for prev in self.rot_prev.values():
            prev.set_machine(self._wizard_travel(), inv, neg)
        self._rotation_changed()

    def _rotation_changed(self):
        if not hasattr(self, "rot_lab"):
            return
        k = self.rot_choice()
        for kk, prev in self.rot_prev.items():
            prev.set_on(kk == k)
        tx, ty = self._wizard_travel()
        w, h = (ty, tx) if k % 2 else (tx, ty)
        if k:
            self.rot_lab.setText(tr("Sullo schermo il piano sarà largo {0:g} mm e alto {1:g} mm. Il pallino è lo 0 della "
                                    "macchina; le frecce sono i suoi assi X e Y.", w, h))
        else:
            self.rot_lab.setText(tr("Il piano resta com'è: largo {0:g} mm e alto {1:g} mm.", w, h))

    def _page_end(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(_title(tr("Ultima cosa: quanto aiuto vuoi sullo schermo?")))
        self.summary = _text("")
        v.addWidget(self.summary)
        self.levels = {}
        grp = QButtonGroup(self)
        for lv, text in (("principiante", tr("<b>Principiante</b>: nomi sotto i comandi e accanto ai segni del piano, "
                                             "spiegazioni e suggerimenti")),
                         ("normale", tr("<b>Normale</b>: solo icone; spiegazioni passando sui segni e suggerimenti")),
                         ("esperto", tr("<b>Esperto</b>: niente nomi, spiegazioni né suggerimenti (gli avvisi di "
                                        "sicurezza restano sempre)"))):
            b = QRadioButton()
            row = QHBoxLayout()
            row.addWidget(b)
            lab = _text(text)
            lab.mousePressEvent = lambda _e, bb=b: bb.setChecked(True)
            row.addWidget(lab, 1)
            grp.addButton(b)
            v.addLayout(row)
            self.levels[lv] = b
        self.levels[self.main.help_level()].setChecked(True)
        v.addWidget(_text(tr("Puoi cambiare tutto quando vuoi: <i>Impostazioni → Configurazione guidata della macchina</i> "
                             "e <i>Impostazioni → Livello di aiuto</i>.")))
        # 0.18.17: solo se la scheda collegata ha il Wi-Fi (ESP32)
        self.wifi_hint = _text(tr("Vuoi usarlo senza cavo? Dopo, apri <i>Impostazioni → Collegamento Wi-Fi del laser…</i>"))
        from .. import wifi_setup

        ctl = self.main.ctl
        self.wifi_hint.setVisible(bool(ctl.connected and wifi_setup.esp32_hints(ctl.board_info, ctl.board_settings)))
        v.addWidget(self.wifi_hint)
        v.addStretch(1)
        self.stack.addWidget(w)

    # ------------------------------------------------------------------ navigazione
    def _can_jog(self):
        ctl = self.main.ctl
        return bool(ctl.connected) and not (ctl.job_active or ctl.checking)

    def go(self, i):
        i = max(0, min(self.stack.count() - 1, i))
        if i == 2:
            self._enter_arrows()
        if i == 3:
            self._enter_rotation()
        if i == self.stack.count() - 1:
            self._fill_summary()
        self.stack.setCurrentIndex(i)
        self.step_lab.setText(tr("Passo {0} di {1}", i + 1, self.stack.count()))
        self.b_back.setEnabled(i > 0)
        self.b_next.setText(tr("Fine") if i == self.stack.count() - 1 else tr("Avanti"))

    def _next(self):
        if self.stack.currentIndex() == self.stack.count() - 1:
            self.accept()
        else:
            self.go(self.stack.currentIndex() + 1)

    def _enter_arrows(self):
        for axis in (0, 1):
            if not self.tested[axis]:
                self.inv[axis] = self._base_axes()[axis]
        ok = self._can_jog()
        self.arrows_box.setVisible(ok)
        self.b_home.setVisible(ok and self._alarm())
        if ok:
            self._apply_sign()
            self.arrows_intro.setText(tr(
                "Premi le frecce: la testa si sposta di {0:g} mm a laser spento. Deve andare dove indica la freccia "
                "(↑ = verso il fondo della macchina). Se va al contrario, premi «correggi» per quell'asse e riprova.<br>"
                "Se la testa è vicina a un bordo, usa la freccia che la allontana.", STEP_MM))
            self.arrows_lab.setText("")
        else:
            self.arrows_intro.setText(tr(
                "Il laser non è collegato: la prova la fai dopo. Quando lo colleghi, apri <i>Impostazioni → "
                "Configurazione guidata della macchina</i> e premi le frecce: se una va al contrario, la correggi lì. "
                "Intanto FreeLaserCut usa l'angolo che hai scelto."))
            self.arrows_lab.setText("")

    def _apply_sign(self):
        self.main.ctl.axis_sign = (-1.0 if self.inv[0] else 1.0, -1.0 if self.inv[1] else 1.0)
        self.main.ctl.axis_rot = 0  # le frecce di questa prova sono quelle della macchina: sinistra, destra, fondo

    def _alarm(self):
        return self.main.ctl.last_status.get("state") == "Alarm"

    def jog(self, key):
        if not self._can_jog():
            self.arrows_lab.setText(tr("Il laser non è pronto: collegalo e riprova."))
            return
        if self._alarm():
            self.b_home.setVisible(True)
            self.arrows_lab.setText(tr("La macchina è bloccata (allarme) e non si muove: premi <b>Homing</b> (o "
                                       "sbloccala dal pannello Laser), poi riprova le frecce."))
            return
        dx, dy = {"up": (0, STEP_MM), "down": (0, -STEP_MM), "left": (-STEP_MM, 0), "right": (STEP_MM, 0)}[key]
        base = self._base_axes()  # gli assi non ancora provati seguono il profilo (anche dopo un homing fatto da qui)
        for a in (0, 1):
            if not self.tested[a]:
                self.inv[a] = base[a]
        self._apply_sign()
        self._last_axis = 0 if dx else 1
        self._tested_before = self.tested[self._last_axis]
        self.main.ctl.jog(dx, dy, JOG_FEED)
        self.tested[self._last_axis] = True
        self.arrows_lab.setText(tr("È andata dove indica la freccia? Se sì, prova anche l'altro asse; se no, premi "
                                   "«correggi»."))

    def _jog_refused(self, code, _text, line):
        if self.stack.currentIndex() != 2 or not str(line).startswith("$J=") or self._last_axis is None:
            return
        self.tested[self._last_axis] = getattr(self, "_tested_before", False)  # non si è mosso: non è una prova
        if code == 15:
            self.arrows_lab.setText(tr("La macchina ha rifiutato lo spostamento: la testa uscirebbe dall'area di lavoro. "
                                       "Non è un verso sbagliato: usa la freccia opposta, che la allontana dal bordo."))
        else:
            self.arrows_lab.setText(tr("La macchina ha rifiutato lo spostamento (errore {0}): la testa non si è mossa. "
                                       "Controlla che sia pronta e riprova.", code))

    def fix(self, axis):
        self.inv[axis] = not self.inv[axis]
        self.tested[axis] = True
        self._apply_sign()
        self.arrows_lab.setText(tr("Corretto: ora {0} va nel verso giusto. Riprova la freccia per controllare.",
                                   tr("sinistra–destra") if axis == 0 else tr("fondo–davanti")))

    def _same_model(self):
        p = self.main.profile
        return self.model.currentText() in (p.model, p.name, self.keep_label)

    def _base_axes(self):
        """Verso degli assi non provati: dall'angolo, se l'hai scelto; altrimenti resta com'era."""
        same = self._same_model()
        if self.picker.touched:
            neg = self.main.profile.negative_space if same else None
            return list(MachineProfile.corner_inversion(self.picker.corner, neg))
        if not same:
            return [False, False]
        # il profilo di adesso, letto ora: se nel frattempo l'homing ha ricalcolato gli assi, vale quello
        return [self.main.profile.invert_x, self.main.profile.invert_y]

    def _final_axes(self):
        base = self._base_axes()
        return [self.inv[a] if self.tested[a] else base[a] for a in (0, 1)]

    def _fill_summary(self):
        ix, iy = self._final_axes()
        q = MachineProfile(invert_x=ix, invert_y=iy,
                           negative_space=self.main.profile.negative_space if self._same_model() else None)
        corner = q.corner_now()  # dagli assi come saranno (provati o dall'angolo scelto)
        tested = tr("provati con le frecce") if all(self.tested) else tr("da provare con le frecce quando colleghi il laser")
        self.summary.setText(tr("<b>Macchina:</b> {0}<br><b>Lo 0 è</b> {1}.<br><b>Assi:</b> X {2}, Y {3} ({4}).",
                                self.main.profile.name if self._same_model() else self.model.currentText(), corner_name(corner),
                                tr("invertito") if ix else tr("normale"), tr("invertito") if iy else tr("normale"),
                                tested)
                             + "<br>" + tr("<b>Piano:</b> {0}.", ROT_NAMES.get(self.rot_choice(), ROT_NAMES[0])))

    def help_level_choice(self):
        return next((lv for lv, b in self.levels.items() if b.isChecked()), "normale")

    # ------------------------------------------------------------------ fine
    def _disconnect(self):
        try:
            self.main.ctl.error_raised.disconnect(self._jog_refused)
        except (RuntimeError, TypeError):
            pass

    def reject(self):
        self._disconnect()
        self.main.ctl.axis_sign = self._sign_before
        self.main.ctl.axis_rot = self._rot_before
        super().reject()

    def accept(self):
        self._disconnect()
        self.apply()
        super().accept()

    def apply(self):
        from .dialogs_machine import use_preset

        main = self.main
        ix, iy = self._final_axes()
        if not self._same_model():
            p = use_preset(main.qs, self.model.currentText())
            if p is not None:
                main.set_active_profile(p)
        p = main.profile
        p.invert_x, p.invert_y = bool(ix), bool(iy)
        p.tested_x, p.tested_y = bool(self.tested[0]), bool(self.tested[1])
        p.axes_tested = all(self.tested)
        if self.picker.touched:
            p.origin_corner = self.picker.corner  # serve per gli assi non provati, quando l'homing dirà di più
        elif self._unknown:
            p.origin_corner = ""
        busy = bool(main.ctl.job_active or main.ctl.checking)
        if not busy:  # 0.19.3: mai cambiare orientamento del piano con un lavoro in corso
            p.set_view_rot(self.rot_choice())
        try:
            p.save()
        except OSError:
            pass
        main._sync_axes()
        main.plane_changed()  # il disegno aperto resta dov'è sulla macchina
        main.machine.refresh_profile()
        main.qs.setValue("setup_wizard_done", True)
        main.set_help_level(self.help_level_choice(), quiet=True)
        main.statusBar().showMessage(tr("Configurazione salvata: {0}, lo 0 è {1}", p.name, corner_name(p.corner_now())),
                                     8000)
        if main.job is not None and not getattr(main, "_job_is_external", False):
            main.build_job()
