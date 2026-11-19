#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera los diagramas del anteproyecto del afinador automático de guitarra.
Salida: SVG + PNG en docs/images/

Uso:  python3 generar_diagramas.py
"""
import math
import os
import subprocess

FONT = "DejaVu Sans"
TXT = "#16202A"

# ---------------------------------------------------------------- paleta
SENS_F, SENS_S = "#E8F5E9", "#2E7D32"      # sensores
ANA_F, ANA_S = "#FFF8E1", "#EF6C00"        # acondicionamiento analógico
MCU_F, MCU_S = "#E3F2FD", "#1565C0"        # microcontrolador
DRV_F, DRV_S = "#F3E5F5", "#6A1B9A"        # driver
ACT_F, ACT_S = "#FCE4EC", "#AD1457"        # actuador
UI_F, UI_S = "#ECEFF1", "#455A64"          # interfaz de usuario
PWR_F, PWR_S = "#FFF3E0", "#E65100"        # potencia
ERR_F, ERR_S = "#FFEBEE", "#C62828"        # advertencia / error
IPC_F, IPC_S = "#FFF3E0", "#EF6C00"        # IPC / colas
CORE1_F, CORE1_S = "#E8F5E9", "#2E7D32"    # core 1
CORE0_F, CORE0_S = "#E3F2FD", "#1565C0"    # core 0


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class SVG:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.parts = []

    def add(self, s):
        self.parts.append(s)

    # ------------------------------------------------ primitivas
    def rect(self, x, y, w, h, fill="#fff", stroke="#888", sw=2, rx=10, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def circle(self, cx, cy, r, fill="#fff", stroke="#888", sw=2, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def text(self, x, y, s, size=15, anchor="middle", weight="normal",
             fill=TXT, italic=False):
        st = ' font-style="italic"' if italic else ""
        self.add(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
                 f'font-weight="{weight}" text-anchor="{anchor}" fill="{fill}"'
                 f'{st}>{esc(s)}</text>')

    def box(self, x, y, w, h, title=None, body=(), fill="#fff", stroke="#555",
            tsize=16, bsize=13, lh=18, rx=12, sw=2, dash=None, tcolor=None,
            bcolor="#37474F"):
        self.rect(x, y, w, h, fill, stroke, sw, rx, dash)
        body = list(body)
        total = (tsize + 6 if title else 0) + len(body) * lh
        cy = y + (h - total) / 2.0
        if title:
            self.text(x + w / 2, cy + tsize * 0.86, title, size=tsize,
                      weight="bold", fill=tcolor or stroke)
            cy += tsize + 6
        for i, l in enumerate(body):
            self.text(x + w / 2, cy + lh * 0.78 + i * lh, l, size=bsize, fill=bcolor)

    def tag(self, x, y, s, size=12, color="#37474F", bg="#FFFFFF", pad=5, bold=False):
        w = len(s) * size * 0.56 + 2 * pad
        h = size * 1.45
        self.add(f'<rect x="{x-w/2:.1f}" y="{y-h/2:.1f}" width="{w:.1f}" height="{h:.1f}" '
                 f'rx="4" fill="{bg}" stroke="none" opacity="0.95"/>')
        self.text(x, y + size * 0.35, s, size=size, fill=color,
                  weight="bold" if bold else "normal")

    def line(self, x1, y1, x2, y2, color="#455A64", sw=2.2, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                 f'stroke-width="{sw}"{d} stroke-linecap="round"/>')

    def pline(self, pts, color="#455A64", sw=2.2, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p = " ".join(f"{x},{y}" for x, y in pts)
        self.add(f'<polyline points="{p}" fill="none" stroke="{color}" '
                 f'stroke-width="{sw}"{d} stroke-linejoin="round" stroke-linecap="round"/>')

    def _head(self, x, y, ang, color, size):
        a1, a2 = ang + math.radians(155), ang - math.radians(155)
        p1 = (x + size * math.cos(a1), y + size * math.sin(a1))
        p2 = (x + size * math.cos(a2), y + size * math.sin(a2))
        self.add(f'<polygon points="{x:.1f},{y:.1f} {p1[0]:.1f},{p1[1]:.1f} '
                 f'{p2[0]:.1f},{p2[1]:.1f}" fill="{color}"/>')

    def arrow(self, x1, y1, x2, y2, color="#455A64", sw=2.2, dash=None, head=12):
        ang = math.atan2(y2 - y1, x2 - x1)
        bx, by = x2 - head * 0.8 * math.cos(ang), y2 - head * 0.8 * math.sin(ang)
        self.line(x1, y1, bx, by, color, sw, dash)
        self._head(x2, y2, ang, color, head)

    def parcel(self, x1, y1, x2, y2, color="#455A64", sw=2.2, dash=None, head=12, bulge=0.2):
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        cx, cy = mx - dy * bulge, my + dx * bulge
        ang = math.atan2(y2 - cy, x2 - cx)
        ex, ey = x2 - head * 0.8 * math.cos(ang), y2 - head * 0.8 * math.sin(ang)
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="M {x1} {y1} Q {cx:.1f} {cy:.1f} {ex:.1f} {ey:.1f}" fill="none" '
                 f'stroke="{color}" stroke-width="{sw}"{d} stroke-linecap="round"/>')
        self._head(x2, y2, ang, color, head)

    def elbow_arrow(self, pts, color="#455A64", sw=2.2, dash=None, head=12):
        self.pline(pts, color, sw, dash)
        ang = math.atan2(pts[-1][1] - pts[-2][1], pts[-1][0] - pts[-2][0])
        self._head(pts[-1][0], pts[-1][1], ang, color, head)

    def junction(self, x, y, color="#455A64", r=4.5):
        self.circle(x, y, r, color, color, 1)

    def res_h(self, x, y, w=58, h=22, stroke="#5D4037"):
        self.rect(x, y - h / 2, w, h, "#FFFFFF", stroke, 2, 3)

    def res_v(self, x, y, w=22, h=58, stroke="#5D4037"):
        self.rect(x - w / 2, y, w, h, "#FFFFFF", stroke, 2, 3)

    def diode_up(self, x, y_bot, color="#C62828", size=14):
        self.add(f'<polygon points="{x-size},{y_bot} {x+size},{y_bot} {x},{y_bot-size*1.2}" '
                 f'fill="#FFFFFF" stroke="{color}" stroke-width="2"/>')
        self.line(x - size, y_bot - size * 1.2, x + size, y_bot - size * 1.2, color, 2.6)

    def legend(self, x, y, items, size=12.5, gap=190):
        for i, (fill, stroke, label) in enumerate(items):
            cx = x + i * gap
            self.rect(cx, y, 22, 16, fill, stroke, 1.5, 4)
            self.text(cx + 30, y + 13, label, size=size, anchor="start", fill="#455A64")

    def render(self, name, outdir=None):
        outdir = outdir or os.path.dirname(os.path.abspath(__file__))
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}">\n'
               f'<rect width="{self.w}" height="{self.h}" fill="#FFFFFF"/>\n'
               + "\n".join(self.parts) + "\n</svg>\n")
        sp = os.path.join(outdir, name + ".svg")
        pp = os.path.join(outdir, name + ".png")
        with open(sp, "w", encoding="utf-8") as f:
            f.write(svg)
        subprocess.run(["rsvg-convert", "-z", "1.6", "-o", pp, sp], check=True)
        print("ok:", name)


# =====================================================================
# 1. DIAGRAMA DE COMPONENTES
# =====================================================================
def diagrama_componentes():
    s = SVG(1740, 1010)
    s.text(40, 52, "Diagrama de componentes", size=27, weight="bold",
           anchor="start", fill="#0D2E4A")
    s.text(40, 82, "Afinador automático de guitarra · ESP32-S3 FeatherS3 · dos sensores, un actuador, "
           "lazo cerrado sobre la frecuencia", size=14, anchor="start", fill="#546E7A")

    # ---------------- guitarra
    gx = 150
    s.add(f'<ellipse cx="{gx}" cy="700" rx="98" ry="118" fill="#C98B5E" stroke="#7B4B2A" stroke-width="3"/>')
    s.add(f'<ellipse cx="{gx-40}" cy="672" rx="42" ry="46" fill="#B57A4E" stroke="#7B4B2A" stroke-width="2"/>')
    s.add(f'<ellipse cx="{gx+42}" cy="742" rx="38" ry="42" fill="#B57A4E" stroke="#7B4B2A" stroke-width="2"/>')
    s.circle(gx - 12, 700, 20, "#3E2723", "#2B1A12", 2)
    s.add(f'<rect x="{gx-17}" y="300" width="34" height="290" fill="#E0BE8C" stroke="#8D6E63" stroke-width="2"/>')
    s.add(f'<polygon points="{gx-20},305 {gx+20},305 {gx+34},232 {gx-8},222" fill="#4E342E" stroke="#2B1A12" stroke-width="2"/>')
    for i in range(3):
        s.circle(gx + 30, 240 + i * 22, 6.5, "#CFD8DC", "#78909C", 1.5)
        s.circle(gx - 6, 238 + i * 22, 6.5, "#CFD8DC", "#78909C", 1.5)
    for i in range(6):
        x0 = gx - 12 + i * 5
        s.line(x0, 258, gx - 26 + i * 9, 620, "#B0BEC5", 1)
    s.text(gx, 862, "Guitarra", size=15, weight="bold", fill="#4E342E")
    s.text(gx, 882, "6 cuerdas · afinación estándar A4 = 440 Hz", size=11.5, fill="#6D4C41")

    # ---------------- sensores
    s.box(300, 250, 270, 96, "Piezo de contacto 27 mm",
          ["pinza en el clavijero", "sensor primario (inmune al ruido)"],
          SENS_F, SENS_S, bsize=12.5)
    s.box(300, 640, 270, 86, "6 pulsadores 6×6 mm",
          ["selección manual de cuerda"], UI_F, UI_S, bsize=12.5)
    s.box(620, 430, 250, 96, "INMP441 (I²S)",
          ["micrófono digital 24 bits", "canal de comparación"], SENS_F, SENS_S, bsize=12.5)

    s.arrow(252, 296, 298, 296, SENS_S, 2.4)

    # ---------------- acondicionamiento
    s.box(620, 250, 250, 96, "Acondicionamiento",
          ["MCP6002 · G = ×100 (40 dB)", "LPF 4 kHz · clamp BAT54S"],
          ANA_F, ANA_S, bsize=12.5)
    s.arrow(570, 296, 618, 296, ANA_S, 2.4)

    # ---------------- MCU
    s.rect(970, 170, 400, 560, MCU_F, MCU_S, 3, 16)
    s.text(1170, 205, "ESP32-S3 FeatherS3", size=18, weight="bold", fill=MCU_S)
    s.text(1170, 226, "240 MHz · 512 KB SRAM · 21 GPIO", size=11.5, fill="#37474F")
    s.box(995, 250, 350, 150, "Core 0",
          ["FSM / control de motor", "UI: pulsadores y LEDs", "tiempo real determinista"],
          "#FFFFFF", CORE0_S, tsize=15, bsize=12.5)
    s.box(995, 425, 350, 150, "Core 1",
          ["ADC + I²S con DMA", "FFT / YIN · estimación de tono", "ventana de 512 ms"],
          "#FFFFFF", CORE1_S, tsize=15, bsize=12.5)
    s.text(1170, 610, "FreeRTOS · 2 núcleos", size=13, weight="bold", fill=MCU_S)
    s.text(1170, 632, "solo lógica 3,3 V (40 mA por GPIO)", size=11.5, fill="#37474F")

    s.arrow(870, 296, 968, 296, MCU_S, 2.4)
    s.tag(918, 278, "ADC1 · IO1", 10, MCU_S)
    s.arrow(870, 478, 968, 478, MCU_S, 2.4)
    s.tag(918, 460, "I²S · IO5/6/7", 10, MCU_S)
    s.elbow_arrow([(570, 683), (1170, 683), (1170, 730)], UI_S, 2.4)
    s.tag(760, 683, "GPIO · 6 líneas", 10, UI_S)

    # onda acústica (opcional)
    s.add(f'<path d="M 260 640 Q 430 620 615 500" fill="none" stroke="#90A4AE" '
          f'stroke-width="1.8" stroke-dasharray="6 5" stroke-linecap="round"/>')
    s.tag(430, 588, "sonido (opcional)", 10, "#78909C")

    # ---------------- driver + actuador
    s.box(1450, 250, 220, 120, "A4988",
          ["1/16 micropaso", "1,0 A/fase · 12 V"], DRV_F, DRV_S, bsize=12.5)
    s.arrow(1372, 296, 1448, 296, DRV_S, 2.4)
    s.tag(1404, 266, "STEP/DIR/EN", 9, DRV_S)
    s.box(1450, 470, 220, 140, "NEMA-17 17HS4401",
          ["1,8° · 0,4 N·m", "bipolar 4 hilos", "1,5 A/fase"], ACT_F, ACT_S, bsize=12.5)
    s.arrow(1560, 370, 1560, 468, ACT_S, 2.4)
    s.tag(1605, 419, "A / B", 10.5, ACT_S)

    # acople mecánico al clavijero
    s.elbow_arrow([(1670, 540), (1720, 540), (1720, 120), (196, 120), (196, 222)],
                  "#2E7D32", 2.2, dash="8 6", head=13)
    s.tag(880, 108, "acople mecánico 3D con resbalamiento → giro de la clavija", 11.5, "#2E7D32")

    # ---------------- nota
    s.rect(300, 782, 1080, 74, "#F5F7FA", "#B0BEC5", 1.6, 10)
    s.text(320, 806, "La FeatherS3 NO alimenta el motor: solo entrega STEP, DIR, EN y MS1-3 (3,3 V).",
           size=13, anchor="start", weight="bold", fill="#37474F")
    s.text(320, 830, "La potencia del NEMA-17 viene de la fuente externa de 12 V a través del A4988 "
           "(ver diagrama de potencia).", size=12.5, anchor="start", fill="#546E7A")

    s.text(40, 906, "Leyenda", size=13, weight="bold", anchor="start", fill="#37474F")
    s.legend(40, 920, [(SENS_F, SENS_S, "Sensor"), (ANA_F, ANA_S, "Analógico"),
                       (MCU_F, MCU_S, "MCU"), (DRV_F, DRV_S, "Driver")], 11.5, 180)
    s.legend(800, 920, [(ACT_F, ACT_S, "Actuador"), (UI_F, UI_S, "Interfaz"),
                        (PWR_F, PWR_S, "Potencia")], 11.5, 180)
    s.render("diagrama-componentes")


# =====================================================================
# 2. CIRCUITO DE POTENCIA
# =====================================================================
def circuito_potencia():
    s = SVG(1660, 1090)
    s.text(40, 50, "Circuito de potencia y cableado del motor", size=26, weight="bold",
           anchor="start", fill="#0D2E4A")
    s.text(40, 78, "Dos fuentes separadas y tierra común. La FeatherS3 nunca ve los 12 V.",
           size=14, anchor="start", fill="#546E7A")

    GND_Y = 900
    # ---------------- entrada 12 V
    s.box(60, 100, 130, 86, "J1", ["jack 12 V / 2 A"], PWR_F, PWR_S, tsize=15, bsize=11.5)
    s.line(190, 143, 240, 143, PWR_S, 2.6)

    s.rect(240, 128, 64, 30, "#FFFDE7", PWR_S, 2, 3)
    s.line(240, 143, 304, 143, PWR_S, 2.6)
    s.text(272, 190, "F1 · 2 A", size=11.5, fill=PWR_S)

    s.add(f'<polygon points="322,128 322,158 350,143" fill="#FFFDE7" stroke="{PWR_S}" stroke-width="2"/>')
    s.line(350, 128, 350, 158, PWR_S, 2.6)
    s.line(304, 143, 322, 143, PWR_S, 2.6)
    s.line(350, 143, 400, 143, PWR_S, 2.6)
    s.text(336, 190, "D1 · SS34", size=11.5, fill=PWR_S)

    s.line(400, 143, 700, 143, PWR_S, 2.6)
    s.junction(430, 143, PWR_S)
    s.junction(600, 143, PWR_S)
    s.tag(425, 124, "+12 V", 11.5, PWR_S, bold=True)

    # capacitores
    def cap(cx, top, bot, label, sub, side="right"):
        s.line(cx, top, cx, (top + bot) / 2 - 12, PWR_S, 2.4)
        s.line(cx - 24, (top + bot) / 2 - 12, cx + 24, (top + bot) / 2 - 12, PWR_S, 4)
        s.line(cx - 24, (top + bot) / 2 + 12, cx + 24, (top + bot) / 2 + 12, PWR_S, 4)
        s.line(cx, (top + bot) / 2 + 12, cx, bot, PWR_S, 2.4)
        if side == "right":
            s.text(cx + 32, (top + bot) / 2 - 2, label, size=11.5, anchor="start", fill="#5D4037")
            s.text(cx + 32, (top + bot) / 2 + 15, sub, size=10, anchor="start", fill="#8D6E63")
        else:
            s.text(cx - 40, (top + bot) / 2 - 2, label, size=11.5, anchor="end", fill="#5D4037")
            s.text(cx - 40, (top + bot) / 2 + 15, sub, size=10, anchor="end", fill="#8D6E63")

    cap(430, 143, 560, "C1 · 470 µF", "35 V · bulk", "left")
    cap(600, 143, 560, "C2 · 100 µF", "35 V · junto al driver", "left")
    s.line(430, 560, 430, GND_Y, PWR_S, 2.4)
    s.line(600, 560, 600, GND_Y, PWR_S, 2.4)

    # ---------------- driver
    s.rect(700, 100, 380, 300, DRV_F, DRV_S, 3, 14)
    s.text(890, 132, "A4988", size=19, weight="bold", fill=DRV_S)
    s.text(890, 152, "módulo stepstick + disipador", size=11, fill="#4A148C")
    s.line(700, 143, 735, 143, "#B45309", 2.4)
    s.tag(792, 168, "VMOT", 12, PWR_S, bold=True)
    s.text(792, 188, "8 – 35 V", size=10.5, fill="#6D4C41")
    s.line(700, 240, 650, 240, DRV_S, 2.4)
    s.line(650, 240, 650, GND_Y, DRV_S, 2.4)
    s.tag(675, 226, "GND", 11, DRV_S)

    # bornes del motor
    y0 = 180
    for i, (nm, col) in enumerate([("1A", "#37474F"), ("1B", "#2E7D32"),
                                   ("2A", "#C62828"), ("2B", "#1565C0")]):
        y = y0 + i * 55
        s.line(1080, y, 1130, y, col, 3)
        s.tag(1105, y - 16, nm, 11, col, bold=True, pad=4)

    # ---------------- motor
    s.rect(1130, 90, 300, 330, "#FFFFFF", ACT_S, 2.5, 14)
    s.circle(1250, 255, 62, ACT_F, ACT_S, 3)
    s.circle(1250, 255, 26, "#FFFFFF", ACT_S, 2)
    s.line(1312, 255, 1360, 255, "#90A4AE", 6)
    s.text(1250, 348, "NEMA-17 17HS4401", size=13.5, weight="bold", fill=ACT_S)
    s.text(1250, 368, "bipolar · 1,5 A/fase", size=11.5, fill="#7B1FA2")
    s.text(1250, 388, "0,4 N·m · 1,8°", size=11.5, fill="#7B1FA2")
    s.text(1250, 408, "eje 5 mm", size=11.5, fill="#7B1FA2")

    # ---------------- pines de lógica
    logic = [("VDD", 725, "3V3"), ("EN", 770, "IO42"), ("MS1", 815, "3V3"),
             ("MS2", 855, "3V3"), ("MS3", 895, "3V3"), ("RST", 935, "3V3"),
             ("SLP", 975, "3V3"), ("STEP", 1020, "IO33"), ("DIR", 1060, "IO38")]
    for nm, x, lab in logic[:7]:
        s.line(x, 400, x, 432, MCU_S, 1.8)
        s.tag(x, 448, nm, 9.5, MCU_S, pad=3)
    # net 3V3: MS1..MS3, RST y SLP
    s.line(815, 480, 975, 480, MCU_S, 1.8)
    for x in (815, 855, 895, 935, 975):
        s.line(x, 432, x, 480, MCU_S, 1.8)
        s.junction(x, 480, MCU_S, 3.5)
    s.tag(895, 500, "3V3 → 1/16 de micropaso", 9.5, MCU_S, pad=3)

    for nm, x, lab in logic[7:]:
        s.line(x, 400, x, 655, MCU_S, 1.8)
        s.tag(x, 448, nm, 9.5, MCU_S, pad=3)
        s.tag(x, 640, lab, 10, MCU_S, pad=3)
    s.line(725, 400, 725, 655, MCU_S, 1.8)
    s.tag(725, 448, "VDD", 9.5, MCU_S, pad=3)
    s.tag(725, 640, "3V3", 10, MCU_S, pad=3)
    s.line(770, 400, 770, 655, MCU_S, 1.8)
    s.tag(770, 448, "EN", 9.5, MCU_S, pad=3)
    s.tag(770, 640, "IO42", 10, MCU_S, pad=3)
    s.text(1120, 452, "EN opcional: a GND = siempre habilitado", size=10,
           anchor="start", fill="#546E7A")
    s.text(1120, 472, "RST = SLP = 3V3", size=10, anchor="start", fill="#546E7A")

    # ---------------- Feather
    s.rect(690, 660, 400, 210, MCU_F, MCU_S, 3, 14)
    s.text(890, 692, "ESP32-S3 FeatherS3", size=16, weight="bold", fill=MCU_S)
    s.text(890, 711, "solo lógica 3,3 V", size=11, fill="#37474F")
    s.text(890, 836, "pines usados: 3V3 · IO42 · IO33 · IO38 · GND · USB (5 V)", size=10.5, fill="#546E7A")

    # 5 V USB
    s.box(60, 730, 150, 86, "USB-C", ["5 V / 1 A", "cargador o power bank"], PWR_F, PWR_S,
          tsize=15, bsize=11)
    s.elbow_arrow([(210, 800), (688, 800)], MCU_S, 2.4)
    s.tag(430, 786, "5 V → pin USB (nunca 12 V)", 11, MCU_S, pad=4)

    # ---------------- presupuesto
    s.rect(60, 420, 520, 170, "#F5F7FA", "#B0BEC5", 1.6, 10)
    s.text(80, 448, "Presupuesto de corriente (a 1,0 A/fase)", size=13, weight="bold",
           anchor="start", fill="#37474F")
    s.text(80, 474, "Motor: 2 × 1,0² × 1,8 Ω = 3,6 W  →  0,33 A de 12 V", size=11.5,
           anchor="start", fill="#546E7A")
    s.text(80, 496, "Lógica: 0,10 A a 3,3 V  →  0,08 A de 5 V", size=11.5,
           anchor="start", fill="#546E7A")
    s.text(80, 518, "Fuente 12 V / 2 A: margen > 3×", size=11.5, anchor="start",
           weight="bold", fill="#2E7D32")
    s.text(80, 548, "El pin 5 V de la Feather alimenta solo la lógica:", size=11,
           anchor="start", fill="#8D6E63")
    s.text(80, 568, "el motor jamás pasa por la placa.", size=11, anchor="start",
           fill="#8D6E63")

    # ---------------- secuencia
    s.rect(1110, 516, 490, 258, "#F5F7FA", "#B0BEC5", 1.6, 10)
    s.text(1130, 546, "Secuencia de puesta en marcha", size=13, weight="bold",
           anchor="start", fill="#37474F")
    seq = ["1. Unir GND de ambas fuentes (cable corto).",
           "2. Ajustar Vref con el motor desconectado.",
           "3. Energizar 12 V (driver en reposo).",
           "4. Conectar 5 V / USB-C a la Feather.",
           "5. Verificar STEP/DIR con un solo paso.",
           "6. Conectar el motor (nunca en caliente)."]
    for i, t in enumerate(seq):
        s.text(1130, 578 + i * 29, t, size=11, anchor="start", fill="#546E7A")

    # ---------------- tierra común
    s.line(60, GND_Y, 1100, GND_Y, "#263238", 5)
    for x in (430, 600, 650):
        s.junction(x, GND_Y, "#263238")
    s.text(60, 878, "GND común: único punto de unión (tierra en estrella)", size=12,
           anchor="start", weight="bold", fill="#263238")

    # ---------------- notas
    s.rect(60, 940, 700, 110, "#FFF8E1", "#EF6C00", 1.6, 10)
    s.text(78, 966, "Ajuste de corriente (obligatorio)", size=13, weight="bold",
           anchor="start", fill="#E65100")
    s.text(78, 990, "I = Vref / (8 × Rsense).  Con Rsense = 0,05 Ω:", size=12,
           anchor="start", fill="#4E342E")
    s.text(78, 1012, "Vref = 0,40 V  →  1,0 A/fase  (recomendado)", size=12,
           anchor="start", weight="bold", fill="#4E342E")
    s.text(78, 1034, "Medir con el motor desconectado. Nunca 1,5 A sin disipador.",
           size=11, anchor="start", fill="#6D4C41")

    s.rect(790, 940, 500, 110, ERR_F, ERR_S, 2, 10)
    s.text(808, 966, "Advertencias", size=13, weight="bold", anchor="start", fill=ERR_S)
    s.text(808, 990, "· NUNCA 12 V al pin 5 V ni a VBAT de la Feather.", size=12,
           anchor="start", fill="#B71C1C")
    s.text(808, 1012, "· No desconectar el motor con VMOT energizado.", size=12,
           anchor="start", fill="#B71C1C")
    s.text(808, 1034, "· GND común SIEMPRE: sin él, STEP/DIR flotan.", size=12,
           anchor="start", fill="#B71C1C")

    s.text(1130, 930, "cruce sin punto = sin conexión", size=10, anchor="start",
           fill="#78909C")
    s.render("circuito-potencia")


# =====================================================================
# 3. ACONDICIONAMIENTO DEL PIEZO
# =====================================================================
def circuito_piezo():
    s = SVG(1560, 900)
    s.text(40, 50, "Acondicionamiento del piezo de contacto", size=25, weight="bold",
           anchor="start", fill="#0D2E4A")
    s.text(40, 78, "Ganancia total ×100 (40 dB) · salida centrada en 1,65 V · fondo de escala 0 a 3,1 V",
           size=14, anchor="start", fill="#546E7A")

    Y = 435
    # ---------------- piezo
    s.circle(120, Y, 50, "#FFFDE7", ANA_S, 3)
    s.line(74, Y, 166, Y, ANA_S, 1.6)
    s.text(120, Y - 4, "P1", size=15, weight="bold", fill=ANA_S)
    s.text(120, Y + 18, "piezo", size=9.5, fill="#8D6E63")
    s.text(120, Y + 78, "disco 27 mm", size=11.5, fill="#5D4037")
    s.text(120, Y + 96, "≈ 25 nF", size=11, fill="#8D6E63")
    s.line(170, Y, 232, Y, "#5D4037", 2.6)

    # ---------------- C1
    s.line(232, Y - 26, 232, Y + 26, "#5D4037", 4.5)
    s.line(247, Y - 26, 247, Y + 26, "#5D4037", 4.5)
    s.line(247, Y, 318, Y, "#5D4037", 2.6)
    s.text(240, Y - 40, "C1 · 100 nF", size=11, fill="#5D4037")

    # ---------------- nodo A + R1 a VBIAS
    s.junction(318, Y, "#5D4037")
    s.line(318, Y, 448, Y, "#5D4037", 2.6)
    s.line(318, Y, 318, 398, "#5D4037", 2.4)
    s.res_v(318, 340, h=58)
    s.line(318, 340, 318, 300, "#5D4037", 2.4)
    s.text(340, 358, "R1", size=12, weight="bold", anchor="start", fill="#5D4037")
    s.text(340, 376, "1 MΩ", size=11, anchor="start", fill="#8D6E63")

    # ---------------- rail VBIAS
    s.line(318, 300, 670, 300, "#EF6C00", 2.6)
    s.tag(430, 282, "VBIAS = 1,65 V", 11.5, "#EF6C00", bold=True)

    s.rect(230, 160, 220, 70, "#FFF3E0", "#EF6C00", 1.6, 8)
    s.text(340, 186, "Generador de VBIAS", size=12, weight="bold", fill="#E65100")
    s.text(340, 206, "3V3 → divisor 10k/10k", size=10.5, fill="#6D4C41")
    s.text(340, 222, "+ 10 µF + 100 nF", size=10.5, fill="#6D4C41")
    s.arrow(340, 230, 340, 298, "#EF6C00", 2.2)

    # ---------------- etapas
    def opamp(x, y, gain, lbl, rf_x, rg_x):
        s.add(f'<polygon points="{x},{y-70} {x},{y+70} {x+150},{y}" fill="#FFFFFF" '
              f'stroke="{ANA_S}" stroke-width="2.6"/>')
        s.text(x + 16, y - 28, "−", size=20, anchor="start", fill=ANA_S)
        s.text(x + 16, y + 6, "+", size=20, anchor="start", fill=ANA_S)
        s.text(x + 80, y - 6, gain, size=15, weight="bold", fill=ANA_S)
        s.text(x + 80, y + 14, lbl, size=10, fill="#8D6E63")
        # realimentación: − (arriba) -> abajo -> Rf -> salida
        s.line(x, y - 33, x - 30, y - 33, "#5D4037", 2.2)
        s.line(x - 30, y - 33, x - 30, y + 75, "#5D4037", 2.2)
        s.line(x - 30, y + 75, rf_x, y + 75, "#5D4037", 2.2)
        s.res_h(rf_x, y + 75)
        s.line(rf_x + 58, y + 75, x + 150, y + 75, "#5D4037", 2.2)
        s.line(x + 150, y + 75, x + 150, y, "#5D4037", 2.2)
        s.text(rf_x + 29, y + 106, "Rf 91k", size=10.5, fill="#8D6E63")
        # Rg del nodo − a VBIAS
        s.line(x - 30, y - 33, x - 30, y - 87, "#5D4037", 2.2)
        s.res_v(x - 30, y - 123, h=36)
        s.line(x - 30, y - 123, x - 30, y - 135, "#5D4037", 2.2)
        s.text(x - 42, y - 100, "Rg 10k", size=10.5, anchor="end", fill="#8D6E63")

    opamp(448, Y, "×10,1", "MCP6002/A", 500, 0)
    opamp(698, Y, "×10,1", "MCP6002/B", 750, 0)
    s.line(598, Y, 698, Y, "#5D4037", 2.6)

    # Rg superiores al rail
    s.line(418, 312, 418, 300, "#EF6C00", 2.2)
    s.line(668, 312, 668, 300, "#EF6C00", 2.2)

    # ---------------- LPF
    s.line(848, Y, 910, Y, "#5D4037", 2.6)
    s.rect(910, Y - 46, 150, 92, "#FFFFFF", ANA_S, 2.2, 8)
    s.text(985, Y - 18, "LPF RC", size=13, weight="bold", fill=ANA_S)
    s.text(985, Y + 4, "1 kΩ + 39 nF", size=11, fill="#5D4037")
    s.text(985, Y + 24, "fc ≈ 4,1 kHz", size=10.5, fill="#8D6E63")
    s.line(1060, Y, 1120, Y, "#5D4037", 2.6)

    # ---------------- clamp
    s.rect(1120, Y - 95, 220, 190, "#FFFDE7", ERR_S, 1.8, 8, dash="7 5")
    s.text(1132, Y - 70, "Protección", size=12.5, weight="bold", anchor="start", fill=ERR_S)
    s.text(1132, Y - 50, "BAT54S", size=11, anchor="start", fill="#5D4037")
    s.res_h(1136, Y, w=40, h=18)
    s.text(1156, Y - 16, "1 kΩ", size=10, fill="#5D4037")
    s.line(1176, Y, 1240, Y, "#5D4037", 2.6)
    s.junction(1240, Y, "#5D4037")
    s.line(1240, Y, 1240, Y - 55, ERR_S, 2.2)
    s.diode_up(1240, Y - 55, ERR_S, 12)
    s.line(1240, Y - 55 - 14.4, 1240, Y - 78, ERR_S, 2.2)
    s.text(1260, Y - 74, "a 3V3", size=10, anchor="start", fill=ERR_S)
    s.line(1240, Y, 1240, Y + 62, ERR_S, 2.2)
    s.diode_up(1240, Y + 62, ERR_S, 12)
    s.text(1262, Y + 58, "a GND", size=10, anchor="start", fill=ERR_S)
    s.line(1240, Y, 1348, Y, "#5D4037", 2.6)

    # ---------------- ADC
    s.box(1348, Y - 48, 150, 96, "ADC1", ["GPIO1", "atenuación 12 dB"], MCU_F, MCU_S,
          tsize=15, bsize=11)

    # ---------------- tabla
    s.rect(60, 640, 1440, 150, "#F5F7FA", "#B0BEC5", 1.6, 10)
    s.text(80, 668, "Lista de valores", size=13, weight="bold", anchor="start", fill="#37474F")
    rows = [
        ("P1", "disco piezo 27 mm, ≈25 nF"),
        ("C1", "100 nF · acoplo (fc ≈6 Hz con R1)"),
        ("R1", "1 MΩ · polariza la entrada (no usar < 1 M)"),
        ("Bias", "divisor 10k/10k + 10 µF + 100 nF"),
        ("U1", "MCP6002 (rail-to-rail, 3,3 V)"),
        ("Rf/Rg", "91k / 10k por etapa (×10,1)"),
        ("LPF", "1 kΩ + 39 nF → 4,1 kHz"),
        ("D1", "BAT54S + 1 kΩ en serie al ADC"),
    ]
    for i, (a, b) in enumerate(rows):
        x = 80 + (i % 2) * 720
        y = 696 + (i // 2) * 24
        s.text(x, y, a, size=11.5, weight="bold", anchor="start", fill="#E65100")
        s.text(x + 58, y, b, size=11.5, anchor="start", fill="#37474F")

    s.rect(60, 806, 1440, 62, "#FFF8E1", "#EF6C00", 1.6, 10)
    s.text(80, 830, "¿Por qué no usar un divisor de 100 kΩ? El piezo es una fuente capacitiva de ≈25 nF;",
           size=12, anchor="start", fill="#4E342E")
    s.text(80, 850, "con menos de 1 MΩ el corte sube a ≈64 Hz y se pierde la 6ª cuerda (82,4 Hz).",
           size=12, anchor="start", fill="#4E342E")

    s.render("circuito-piezo")


# =====================================================================
# 4. ARQUITECTURA DE SOFTWARE POR NÚCLEOS
# =====================================================================
def arquitectura_software():
    s = SVG(1660, 1000)
    s.text(40, 50, "Arquitectura de software por núcleos (FreeRTOS)", size=26, weight="bold",
           anchor="start", fill="#0D2E4A")
    s.text(40, 78, "Core 1: adquisición y DSP (bloques, sin tiempo crítico).   "
           "Core 0: control determinista y máquina de estados.", size=14, anchor="start",
           fill="#546E7A")

    # ---------- Core 1
    s.rect(60, 110, 660, 700, CORE1_F, CORE1_S, 3, 16)
    s.text(390, 142, "CORE 1 · adquisición y DSP", size=18, weight="bold", fill=CORE1_S)
    s.text(390, 162, "prioridad alta, sin bloqueos; nunca espera al motor", size=11.5, fill="#37474F")

    tasks = [
        (95, 190, 590, 108, "T1  sensor_adc  (prio 10)",
         ["ADC1 continuo + DMA · 8 kHz", "bloques de 4096 muestras → ring buffer"]),
        (95, 318, 590, 108, "T2  sensor_i2s  (prio 9)",
         ["INMP441 · I²S · 16 kHz · 24 bits", "canal de comparación"]),
        (95, 446, 590, 140, "T3  pitch_est  (prio 8)",
         ["ventana Hann → FFT 4096 → interpolación parabólica",
          "o YIN para cuerdas graves → cents respecto al objetivo",
          "rechazo de armónicos y de transitorios"]),
        (95, 606, 590, 90, "T4  telemetría  (prio 3)",
         ["log por UART / USB Serial JTAG para SIL y HIL"]),
    ]
    for x, y, w, h, ti, bo in tasks:
        s.box(x, y, w, h, ti, bo, "#FFFFFF", CORE1_S, tsize=14.5, bsize=11.5)

    for y1, y2 in ((298, 316), (426, 444), (586, 604)):
        s.arrow(390, y1, 390, y2, CORE1_S, 2)
    s.text(500, 312, "ring buffer SPSC", size=9.5, fill="#6D8B74")

    s.rect(95, 720, 590, 72, "#FFFFFF", "#A5D6A7", 1.4, 8, dash="6 4")
    s.text(390, 744, "Regla de oro", size=12, weight="bold", fill=CORE1_S)
    s.text(390, 766, "el Core 1 solo publica \"cents\": jamás escribe GPIO del motor.", size=11,
           fill="#546E7A")
    s.text(390, 784, "Así una FFT lenta no puede hacer perder pasos.", size=11, fill="#546E7A")

    # ---------- IPC
    s.rect(760, 110, 170, 700, "#FFFDF5", "#EF6C00", 3, 16)
    s.text(845, 142, "IPC", size=17, weight="bold", fill="#EF6C00")
    s.text(845, 162, "FreeRTOS", size=10.5, fill="#8D6E63")
    s.box(775, 176, 140, 146, "Flags",
          ["EventGroup", "motor_moving", "sample_ready"], "#FFFFFF", IPC_S,
          tsize=14, bsize=10, lh=18)
    s.box(775, 430, 140, 120, "q_pitch",
          ["Queue", "depth 4", "xQueueSend"], IPC_F, IPC_S, tsize=14, bsize=10.5, lh=16)
    s.text(845, 340, "se pone en 1", size=9.5, fill="#8D6E63")
    s.text(845, 354, "mientras gira", size=9.5, fill="#8D6E63")
    s.text(845, 596, "bloqueante,", size=9.5, fill="#8D6E63")
    s.text(845, 610, "timeout 0", size=9.5, fill="#8D6E63")

    # ---------- Core 0
    s.rect(970, 110, 630, 700, CORE0_F, CORE0_S, 3, 16)
    s.text(1285, 142, "CORE 0 · control y UI", size=18, weight="bold", fill=CORE0_S)
    s.text(1285, 162, "determinista: los pulsos STEP nunca dependen del DSP", size=11.5, fill="#37474F")
    s.box(1000, 190, 570, 150, "T5  fsm  (prio 12)",
          ["consume q_pitch · LISTEN / PROBE / ACT / WAIT / ERROR",
           "banda muerta ±3 cents · seguridad de sobretensión"], "#FFFFFF", CORE0_S,
          tsize=14.5, bsize=11.5)
    s.box(1000, 365, 570, 150, "T6  motor_ctrl  (prio 11)",
          ["MCPWM por hardware (STEP) · rampa de aceleración",
           "DIR / EN / conteo de pasos · ráfagas acotadas"], "#FFFFFF", CORE0_S,
          tsize=14.5, bsize=11.5)
    s.box(1000, 540, 570, 120, "T7  ui  (prio 6)",
          ["6 pulsadores por ISR → cola de eventos",
           "LEDs: afinada / girando / error"], "#FFFFFF", CORE0_S,
          tsize=14.5, bsize=11.5)
    s.box(1000, 685, 570, 90, "ISR  GPIO",
          ["flanco de bajada: solo encola (sin lógica pesada)"], UI_F, UI_S,
          tsize=13.5, bsize=11.5)
    s.arrow(1285, 685, 1285, 662, UI_S, 2)

    # ---------- flechas IPC
    s.arrow(690, 500, 773, 490, "#EF6C00", 3)
    s.tag(735, 478, "cents", 9.5, "#EF6C00", pad=3)
    s.elbow_arrow([(917, 470), (945, 470), (945, 270), (998, 270)], "#EF6C00", 3)
    s.tag(945, 380, "T5 consume", 9.5, "#EF6C00", pad=3)
    s.arrow(998, 240, 918, 240, "#EF6C00", 3)
    s.arrow(773, 240, 692, 240, "#EF6C00", 3)
    s.tag(731, 220, "motor_moving", 9, "#EF6C00", pad=3)

    # ---------- presupuesto
    s.rect(60, 840, 1540, 120, "#F5F7FA", "#B0BEC5", 1.6, 10)
    s.text(80, 868, "Presupuesto de tiempo", size=13, weight="bold", anchor="start",
           fill="#37474F")
    s.text(80, 894, "4096 muestras a 8 kHz = 512 ms de ventana.  FFT real de 4096 puntos con esp-dsp: "
           "≈1,5 ms a 240 MHz.", size=12, anchor="start", fill="#546E7A")
    s.text(80, 916, "Carga de CPU del DSP < 2 %.  Pilas: 8 KB para T3, 4 KB para el resto.  "
           "WDT de 5 s en cada tarea.", size=12, anchor="start", fill="#546E7A")
    s.text(80, 940, "Asignación estática: sin malloc en tiempo de ejecución (evita fragmentación y bloqueos).",
           size=12, anchor="start", fill="#546E7A")

    s.render("arquitectura-software")


# =====================================================================
# 5. MÁQUINA DE ESTADOS
# =====================================================================
def maquina_estados():
    s = SVG(1560, 1010)
    s.text(40, 50, "Máquina de estados finitos del lazo de afinación", size=25, weight="bold",
           anchor="start", fill="#0D2E4A")
    s.text(40, 78, "La dirección de giro se mide (PROBE), no se adivina con un IMU.",
           size=14, anchor="start", fill="#546E7A")

    def st(x, y, r, name, sub, fill, stroke):
        s.circle(x, y, r, fill, stroke, 3)
        s.text(x, y + 5, name, size=15.5, weight="bold", fill=stroke)
        if sub:
            s.text(x, y + 25, sub, size=9.5, fill="#546E7A")

    st(150, 210, 66, "INIT", "auto-test", "#ECEFF1", "#455A64")
    st(430, 470, 95, "LISTEN", "mide y compara", CORE0_F, CORE0_S)
    st(870, 190, 86, "PROBE", "Δf por paso", "#FFF3E0", "#E65100")
    st(1320, 470, 86, "ACT", "gira N pasos", "#F3E5F5", "#6A1B9A")
    st(870, 770, 82, "WAIT", "asentamiento", "#ECEFF1", "#455A64")
    st(190, 800, 78, "ERROR", "estado seguro", ERR_F, ERR_S)

    # INIT -> LISTEN
    s.arrow(196, 254, 372, 402, "#455A64", 2.6)
    s.tag(250, 312, "auto-test OK", 10.5, "#455A64")

    # LISTEN -> PROBE
    s.arrow(498, 404, 800, 236, "#E65100", 2.6)
    s.tag(640, 300, "|cents| > 3 y estable 600 ms", 10.5, "#E65100")

    # PROBE -> LISTEN (ya afinada)
    s.parcel(830, 274, 486, 386, "#2E7D32", 2.2, head=11, bulge=-0.13)
    s.tag(660, 372, "ya afinada: K ≈ 0 → LED verde", 10, "#2E7D32")

    # PROBE -> ACT
    s.arrow(944, 238, 1256, 408, "#6A1B9A", 2.6)
    s.tag(1112, 306, "signo + ganancia K medidos", 10.5, "#6A1B9A")

    # ACT -> WAIT
    s.arrow(1256, 532, 944, 722, "#455A64", 2.6)
    s.tag(1112, 654, "ráfaga terminada", 10.5, "#455A64")

    # WAIT -> LISTEN
    s.arrow(794, 730, 500, 540, "#455A64", 2.6)
    s.tag(620, 654, "300 ms → vuelve a medir", 10.5, "#455A64")

    # self loop "afinada"
    s.add(f'<path d="M 337 432 C 262 440, 262 500, 337 508" fill="none" stroke="#2E7D32" '
          f'stroke-width="2.2" stroke-linecap="round"/>')
    s._head(337, 508, math.radians(6), "#2E7D32", 11)
    s.tag(288, 404, "|cents| ≤ 3", 10, "#2E7D32")

    # LISTEN -> ERROR
    s.arrow(368, 548, 232, 738, ERR_S, 2.2)
    s.tag(272, 600, "fuera de rango", 10, ERR_S)

    # ERROR -> LISTEN
    s.arrow(262, 782, 402, 566, "#455A64", 2.2)
    s.tag(392, 726, "reset manual", 10, "#455A64")

    # ACT -> ERROR (por abajo)
    s.elbow_arrow([(1259, 532), (1259, 925), (190, 925), (190, 880)], ERR_S, 2.2,
                  dash="8 5")
    s.tag(760, 912, "tope de pasos / |cents| > 200 / timeout 30 s", 10.5, ERR_S)

    # nota PROBE
    s.rect(1150, 96, 380, 200, "#F5F7FA", "#B0BEC5", 1.5, 10)
    s.text(1170, 124, "Qué hace PROBE", size=13, weight="bold", anchor="start", fill="#37474F")
    s.text(1170, 150, "1. mueve 64 micropasos y mide Δf", size=11, anchor="start", fill="#546E7A")
    s.text(1170, 172, "2. Δf > 0 tensa · Δf < 0 afloja", size=11, anchor="start", fill="#546E7A")
    s.text(1170, 194, "3. si Δf ≈ 0: prueba 128 y 256", size=11, anchor="start", fill="#546E7A")
    s.text(1170, 216, "4. 3 intentos sin respuesta: ERROR", size=11, anchor="start", fill="#546E7A")
    s.text(1170, 248, "de paso entrega K (cents/paso),", size=10.5, anchor="start", fill="#8D6E63")
    s.text(1170, 266, "que usa ACT para calcular los pasos.", size=10.5, anchor="start", fill="#8D6E63")

    s.rect(60, 952, 1000, 46, "#FFF8E1", "#EF6C00", 1.6, 8)
    s.text(78, 981, "PROBE deduce el signo de giro y la ganancia en el mismo movimiento: elimina el IMU "
           "y sirve como prueba de acople.", size=11.5, anchor="start", fill="#4E342E")

    s.render("maquina-estados")


if __name__ == "__main__":
    diagrama_componentes()
    circuito_potencia()
    circuito_piezo()
    arquitectura_software()
    maquina_estados()
    print("\nListo.")
