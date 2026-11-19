#!/usr/bin/env python3
"""Esquematico del afinador de guitarra en Schemdraw (dos hojas).

    pip install schemdraw
    python afinador_schemdraw.py

Genera:
    01_potencia_y_motor.svg / .png   fuente 12 V, protecciones, DRV8825, NEMA-17
    02_sensores_y_ui.svg   / .png    piezo + proteccion, INMP441, 6 pulsadores, LED

Mismo pinout que ../afinador_wiring.yml y ../README.md.
Los pines de cada bloque son los del modulo real (numero y nombre). Las
conexiones largas usan etiqueta de red, como en un esquematico KiCad.
Nota: los bloques solo llevan pines en los lados izquierdo y derecho; con
pines arriba/abajo esta version de Schemdraw desordena las etiquetas.
"""
import schemdraw
from schemdraw import elements as elm
from schemdraw.elements.intcircuits import IcPin

schemdraw.use('matplotlib')

GRIS = '#555555'


def hoja_potencia():
    d = schemdraw.Drawing()
    d.config(unit=1, fontsize=9)

    # ---------------------------------------------------------------- ESP32
    esp = elm.Ic(theta=0, size=(3.4, 7.0), label='ESP32-S3\nDevKitC-1', pins=[
        IcPin(name='3V3', pin='J1-1', side='L', pos=0.20),
        IcPin(name='GND', pin='J1-22', side='L', pos=0.35),
        IcPin(name='EN', pin='G11', side='R', pos=0.57),
        IcPin(name='STEP', pin='G9', side='R', pos=0.66),
        IcPin(name='DIR', pin='G10', side='R', pos=0.75),
        IcPin(name='FAULT', pin='G12', side='R', pos=0.84),
    ])
    d += esp.at((2.8, 8.6)).anchor('center')

    d += elm.Line().at(esp.absanchors['3V3']).left().length(1.0)
    d += elm.Vdd(theta=0).label('3V3')
    d += elm.Line().at(esp.absanchors['GND']).left().length(1.0)
    d += elm.Ground(theta=0).label('GND logica', loc='bottom', fontsize=8)

    # -------------------------------------------------------------- DRV8825
    drv = elm.Ic(theta=0, size=(4.2, 7.0), label='DRV8825', pins=[
        IcPin(name='VMOT', pin='9', side='L', pos=0.14),
        IcPin(name='GND', pin='10', side='L', pos=0.24),
        IcPin(name='EN', pin='1', side='L', pos=0.57),
        IcPin(name='STEP', pin='7', side='L', pos=0.66),
        IcPin(name='DIR', pin='8', side='L', pos=0.75),
        IcPin(name='FAULT', pin='15', side='L', pos=0.84),
        IcPin(name='A1', pin='13', side='R', pos=0.30),
        IcPin(name='A2', pin='14', side='R', pos=0.40),
        IcPin(name='B1', pin='12', side='R', pos=0.62),
        IcPin(name='B2', pin='11', side='R', pos=0.72),
    ])
    d += drv.at((10.2, 8.6)).anchor('center')

    # control ESP32 -> DRV8825 (misma altura, mismos pos: cables rectos)
    for net in ('EN', 'STEP', 'DIR', 'FAULT'):
        p1, p2 = esp.absanchors[net], drv.absanchors[net]
        d += elm.Line().at(p1).to(p2)
        d += elm.Label().at(((p1[0] + p2[0]) / 2, p1[1] + 0.15)).label(net, fontsize=8)

    # potencia del driver por etiqueta de red
    for pin, txt in (('VMOT', 'VMOT'), ('GND', 'GND PWR')):
        p = drv.absanchors[pin]
        d += elm.Line().at(p).left().length(1.0)
        d += elm.Label().at((p[0] - 1.0, p[1] + 0.15)).label(txt, fontsize=8)

    # ---------------------------------------------------------------- motor
    motor = elm.Ic(theta=0, size=(3.0, 7.0), label='NEMA-17\n17HS4401S', pins=[
        IcPin(name='A+', pin='negro', side='L', pos=0.30),
        IcPin(name='A-', pin='verde', side='L', pos=0.40),
        IcPin(name='B+', pin='rojo', side='L', pos=0.62),
        IcPin(name='B-', pin='azul', side='L', pos=0.72),
    ])
    d += motor.at((16.8, 8.6)).anchor('center')
    for a, b in (('A1', 'A+'), ('A2', 'A-'), ('B1', 'B+'), ('B2', 'B-')):
        d += elm.Line().at(drv.absanchors[a]).to(motor.absanchors[b])

    # ------------------------------------------- configuracion de micropaso
    cfg = elm.Ic(theta=0, size=(3.4, 2.8), label='DRV8825\npines 2-6', pins=[
        IcPin(name='M0', pin='2', side='L', pos=0.12),
        IcPin(name='M1', pin='3', side='L', pos=0.28),
        IcPin(name='M2', pin='4', side='L', pos=0.52),
        IcPin(name='RESET', pin='5', side='L', pos=0.70),
        IcPin(name='SLEEP', pin='6', side='L', pos=0.88),
    ])
    d += cfg.at((3.4, 2.5)).anchor('center')
    for pin in ('M0', 'M1'):
        d += elm.Line().at(cfg.absanchors[pin]).left().length(0.7)
        d += elm.Dot()
    d += elm.Line().at((1.6, cfg.absanchors['M0'][1])).to((1.6, cfg.absanchors['M1'][1]))
    d += elm.Line().at((1.6, cfg.absanchors['M1'][1])).down().length(0.5)
    d += elm.Ground(theta=0).label('0', loc='bottom', fontsize=8)
    for pin in ('M2', 'RESET', 'SLEEP'):
        d += elm.Line().at(cfg.absanchors[pin]).left().length(0.7)
        d += elm.Dot()
    d += elm.Line().at((1.6, cfg.absanchors['M2'][1])).to((1.6, cfg.absanchors['SLEEP'][1]))
    d += elm.Line().at((1.6, cfg.absanchors['M2'][1])).up().length(0.5)
    d += elm.Vdd(theta=0).label('3V3', fontsize=8)
    d += elm.Label().at((1.2, 0.9)).label('1/16 de micropaso', fontsize=8, color=GRIS)

    # ------------------------------------------------- cadena de potencia
    y_rail, y_gnd = 3.0, 1.1
    src = d.add(elm.SourceV().at((7.4, y_gnd)).up().length(y_rail - y_gnd)
                .label('12 V\n2 A', loc='bottom', fontsize=8))
    f1 = d.add(elm.Fuse().at(src.end).right().length(1.5).label('F1\n2 A T', loc='top', fontsize=8))
    d1 = d.add(elm.Diode().at(f1.end).right().length(1.3).label('D1 SS34', loc='top', fontsize=8))
    d += elm.Line().at(d1.end).right().length(1.2)
    nodo = d.here

    for i, (sym, txt) in enumerate(((elm.Capacitor(polar=True), 'C1 470u/35 V'),
                                    (elm.Capacitor(polar=True), 'C2 100u/35 V'),
                                    (elm.Capacitor(), 'C3 100 nF'))):
        x = nodo[0] + 0.6 + i * 0.9
        d += elm.Line().at((x, y_rail)).down().length(0.3)
        d += elm.Dot()
        d += sym.down().length(0.8).label(txt, loc='right', fontsize=7)
        d += elm.Line().down().length(0.4).to((x, y_gnd))

    d += elm.Line().at((7.4, y_gnd)).right().to((nodo[0] + 2.4, y_gnd))
    d += elm.Dot().at(nodo)
    d += elm.Vdd(theta=0).at(nodo).label('VMOT', loc='top', fontsize=8)
    d += elm.Ground(theta=0).at((nodo[0] + 2.4, y_gnd)).label('GND PWR', loc='bottom', fontsize=8)

    d += elm.Label().at((0.2, 12.6)).label('Hoja 1 - Potencia 12 V, DRV8825 y NEMA-17', fontsize=12)
    d += elm.Label().at((0.2, 12.2)).label(
        'Vref = 0.50 V (1.0 A/fase) - ajustar con el motor desconectado', fontsize=8, color=GRIS)
    d.save('01_potencia_y_motor.svg')
    d.save('01_potencia_y_motor.png', dpi=200)


def hoja_sensores():
    d = schemdraw.Drawing()
    d.config(unit=1, fontsize=9)

    # ------------------------------------------------- piezo + proteccion
    y0 = 6.4
    pz = d.add(elm.Capacitor().at((1.6, y0)).right().length(1.4)
               .label('PZT 27 mm\n25 nF', loc='bottom', fontsize=8))
    d += elm.Line().at(pz.start).left().length(0.5)
    d += elm.Ground(theta=0)

    n1 = pz.end
    d += elm.Dot().at(n1)
    d += elm.Line().at(n1).up().length(0.5)
    d += elm.Resistor().up().length(1.3).label('R1\n1 M', loc='bottom', fontsize=8)
    d += elm.Vdd(theta=0).label('VBIAS 1.65 V', loc='top', fontsize=8)

    r2 = d.add(elm.Resistor().at(n1).right().length(1.7).label('R2\n4k7', loc='top', fontsize=8))
    nadc = r2.end
    d += elm.Dot().at(nadc)

    # C4 a masa
    d += elm.Line().at(nadc).down().length(0.4)
    d += elm.Capacitor().down().length(0.8).label('C4 100 nF', loc='right', fontsize=8)
    d += elm.Line().down().length(0.3)
    d += elm.Ground(theta=0)

    # columna del clamp BAT54S
    d += elm.Line().at(nadc).right().length(1.0)
    ncl = d.here
    d += elm.Dot()
    d += elm.Diode().at(ncl).up().length(1.1).label('BAT54S', loc='right', fontsize=8)
    d += elm.Vdd(theta=0).label('3V3', loc='top', fontsize=8)
    d += elm.Line().at(ncl).down().length(0.8)
    nlow = d.here
    d += elm.Diode().at(nlow).down().length(0.9)
    d += elm.Ground(theta=0).at(d.here)

    d += elm.Line().at(ncl).right().length(1.0)
    d += elm.Label().at((ncl[0] + 1.1, ncl[1] + 0.20)).label('ADC1_CH0', fontsize=9)
    d += elm.Label().at((ncl[0] + 1.1, ncl[1] - 0.20)).label('GPIO1 (J3-4)', fontsize=8, color=GRIS)

    # ------------------------------------------------------------ INMP441
    mic = elm.Ic(theta=0, size=(3.4, 4.8), label='INMP441', pins=[
        IcPin(name='VDD', pin='1', side='L', pos=0.13),
        IcPin(name='GND', pin='2', side='L', pos=0.28),
        IcPin(name='L/R', pin='3', side='L', pos=0.42),
        IcPin(name='SCK', pin='4', side='L', pos=0.57),
        IcPin(name='WS', pin='5', side='L', pos=0.72),
        IcPin(name='SD', pin='6', side='L', pos=0.87),
    ])
    d += mic.at((14.0, 6.4)).anchor('center')
    for pin, txt in (('VDD', '3V3 (J1-1)'), ('GND', 'GND (J3-1)'), ('L/R', 'GND (canal izq.)'),
                     ('SCK', 'I2S_BCLK GPIO17'), ('WS', 'I2S_WS GPIO18'),
                     ('SD', 'I2S_SD GPIO8')):
        p = mic.absanchors[pin]
        d += elm.Line().at(p).left().length(1.2)
        d += elm.Label().at((p[0] - 1.2, p[1] + 0.13)).label(txt, fontsize=8)

    # ------------------------------------------------------------ pulsadores
    gy, xbus = 3.6, 10.4
    d += elm.Line().at((xbus, gy)).down().to((xbus, gy - 5 * 1.1))
    d += elm.Ground(theta=0).at((xbus, gy - 5 * 1.1)).label('GND', loc='bottom', fontsize=8)
    for i, (net, gpio) in enumerate([('BTN1', 'G4'), ('BTN2', 'G5'), ('BTN3', 'G6'),
                                     ('BTN4', 'G7'), ('BTN5', 'G15'), ('BTN6', 'G16')]):
        y = gy - i * 1.1
        d += elm.Label().at((1.0, y + 0.10)).label(f'{net}/{gpio}', fontsize=8)
        d += elm.Line().at((2.6, y)).right().length(0.4)
        b = d.add(elm.Button().at((3.0, y)).right().length(1.2))
        d += elm.Line().at(b.end).to((xbus, y))
        d += elm.Dot().at((xbus, y))

    # ------------------------------------------------------------------ LED
    yl = gy - 6 * 1.1
    d += elm.Label().at((1.0, yl + 0.10)).label('LED_OK/G21', fontsize=8)
    d += elm.Line().at((2.6, yl)).right().length(0.3)
    d += elm.Resistor().right().length(1.4).label('R3 330', fontsize=8)
    led = d.add(elm.LED().right().length(1.0))
    d += elm.Line().at(led.end).right().length(0.3)
    d += elm.Ground(theta=0)

    d += elm.Label().at((0.2, 10.2)).label('Hoja 2 - Piezo (vibracion), INMP441 (frecuencia) y UI',
                                          fontsize=12)
    d += elm.Label().at((0.2, 9.8)).label(
        'Piezo: solo recorte de sobrevoltaje; el tono lo mide el INMP441', fontsize=8, color=GRIS)
    d.save('02_sensores_y_ui.svg')
    d.save('02_sensores_y_ui.png', dpi=200)


if __name__ == '__main__':
    hoja_potencia()
    hoja_sensores()
    print('Listo: 01_potencia_y_motor.svg/.png  y  02_sensores_y_ui.svg/.png')

