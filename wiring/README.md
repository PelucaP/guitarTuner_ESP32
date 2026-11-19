# Cableado — Afinador de guitarra (Grupo 6)

Wiring diagram definitivo para **ESP32-S3-DevKitC-1 + DRV8825 + NEMA-17 17HS4401S**,
con 6 pulsadores, **INMP441 para detección de frecuencia** y **piezo solo para detectar
vibración** (con protección de sobrevoltaje, sin acondicionamiento de señal).

```bash
wireviz afinador_wiring.yml     # genera .svg / .png / .html / .bom.tsv
```

Archivos: `afinador_wiring.yml` (fuente), `.svg` / `.png` (diagrama), `.bom.tsv` (lista de cables).

---

## 1. Mapa de pines

Todos los pines salen de la tabla de headers de la [User Guide del DevKitC-1 v1.1](https://docs.espressif.com/projects/esp-idf/en/v5.3/esp32s3/hw-reference/esp32s3/user-guide-devkitc-1.html)
(J1 = header izquierdo, J3 = header derecho, numerados como en el esquemático oficial).

| Función | GPIO | Header | Por qué |
|---|---|---|---|
| Piezo → ADC | **GPIO1** | J3-4 | ADC1_CH0. ADC1 es GPIO1–10; ADC2 (GPIO11–20) tiene restricciones con el radio |
| BTN1…BTN6 | **GPIO4, 5, 6, 7, 15, 16** | J1-4…J1-9 | 6 pines consecutivos: un solo header 1×8 con la botonera |
| I²S BCLK | **GPIO17** | J1-10 | Libres y contiguos con WS y SD |
| I²S WS | **GPIO18** | J1-11 | |
| I²S SD | **GPIO8** | J1-12 | |
| STEP | **GPIO9** | J1-15 | 4 pines contiguos → un solo cable de 4 hilos al driver |
| DIR | **GPIO10** | J1-16 | |
| ENABLE | **GPIO11** | J1-17 | Activo bajo: alto = bobinas apagadas. Ojo: el módulo arranca **habilitado** (pull-down interno de 100 kΩ), así que el firmware debe subir GPIO11 antes del primer movimiento |
| nFAULT | **GPIO12** | J1-18 | Entrada; el módulo ya trae pull-up |
| LED_OK | **GPIO21** | J3-18 | |
| 3V3 | — | J1-1 / J1-2 | |
| GND lógica | — | J1-22 | Retorno de señales |
| GND analógica | — | J3-1 | Retorno del piezo, separado del de los botones |

**Pines que NO se usan y por qué** (documentados por Espressif):

- **GPIO35, 36, 37**: no disponibles en módulos con PSRAM octal (N8R8 / WROOM-2), aunque
  estén sacados al header. Esto descarta el `IO33` que proponía la v2 del anteproyecto.
- **GPIO38** (RGB LED en v1.1; GPIO48 en la v1.0) y **GPIO48**.
- **GPIO19/20**: USB D−/D+. **GPIO43/44**: UART0.
- **GPIO0, 3, 45, 46**: strapping. **GPIO39–42**: JTAG.

---

## 2. Alimentación y protecciones

Dos fuentes, **tierra común en un solo punto**.

```
12 V/2 A ──[F1 2A T]──[D1 SS34]──┬── VMOT (DRV8825)
                                 └── C1 470µF + C2 100µF + C3 100nF ── GND
GND 12 V ──────────────────────── GND potencia (pin 10 del módulo)
GND ESP32 ─────────────────────── mismo punto de GND potencia
```

| Ref | Valor | Función | Fuente |
|---|---|---|---|
| F1 | Fusible **2 A temporizado** | Cortocircuito en bobina/cable; el primario de 2 A de la fuente queda protegido | — |
| D1 | **SS34** (Schottky 3 A/40 V) | Polaridad inversa. Caída ≈0,35 V → VMOT = 11,7 V, muy por encima del mínimo de 8,2 V | — |
| C1 | 470 µF / 35 V | *Bulk*: absorbe la inductancia del cable de la fuente (mismo nodo que C2) | — |
| C2 | **100 µF / 35 V**, a <1 cm de VMOT | **Obligatorio**: Pololu advierte que los capacitores cerámicos de baja ESR del módulo lo hacen vulnerable a picos LC que superan los 45 V con cables de más de unos centímetros, incluso con 12 V de entrada. Pide "al menos 47 µF electrolítico" | [Pololu #2133](https://www.pololu.com/product/2133) |
| C3 | 100 nF / 50 V cerámico | Desacoplo de alta frecuencia, junto a C2 | — |

**Punto de tierra.** El retorno de 12 V va directo al pin **GND potencia (10)** del módulo y
desde ese mismo nodo (no a través de la protoboard) sale el GND de la lógica hacia J1-22.
Así los ~0,3 A conmutados del motor no circulan por los cables del piezo ni del INMP441.

**Presupuesto.** Con 1,0 A/fase y 1,5 Ω de bobina: `2 × 1,0² × 1,5 = 3,0 W` → **0,26 A** a 11,7 V.
Lógica (ESP32-S3 + INMP441 2,2 mA + LED): ~60 mA por USB. Margen > 7× sobre la fuente de 2 A.

> El motor **nunca** se alimenta a través de la placa ni de la protoboard: 1 A no pasa por
> un contacto de protoboard (~1 A nominal) ni por el regulador del DevKit.

---

## 3. DRV8825: configuración y ajuste de corriente

### Micropaso

`M0`, `M1` y `M2` tienen **pull-down interno de 100 kΩ** (flotando = paso completo). La tabla
real del DRV8825 no es la del A4988:

| M0 | M1 | M2 | Resolución | Conexión |
|---|---|---|---|---|
| 0 | 0 | 0 | Paso completo | — |
| 1 | 0 | 0 | 1/2 | |
| 0 | 1 | 0 | 1/4 | |
| 1 | 1 | 0 | 1/8 | |
| 0 | 0 | 1 | **1/16** | **M2 → 3V3, M0 y M1 → GND** |
| 1 | 0 | 1 | 1/32 | |

Se usa **1/16** (3200 micropasos/vuelta, 0,1125°/paso) porque es el valor con el que están
calculadas las sensibilidades del anteproyecto (§3.1): ≈1,0 cents/micropaso en Mi grave y
≈0,07 en Mi agudo. A 1/32 se duplicaría la resolución pero habría que reescalar toda la tabla y
las amplitudes de `PROBE`; no aporta porque el límite real es el juego mecánico del clavijero.

### Señales de control

- **RESET y SLEEP deben estar altos** para que el driver funcione (pull-down interno de 100 kΩ
  en RESET, 1 MΩ en SLEEP). Ambos van a 3V3 fijo.
- **ENABLE es activo bajo** y su estado por defecto es *habilitado*. Con GPIO11 se puede apagar
  el driver entre movimientos (mitigación del riesgo 1 del anteproyecto).
- **nFAULT** es drenador abierto, pero el carrier ya trae **10 kΩ a SLEEP y 1,5 kΩ en serie**:
  no hace falta pull-up externo.
- **STEP**: pulsos de ≥ **1,9 µs** en alto y en bajo (1 µs en el A4988). El MCPWM del ESP32-S3
  los genera por hardware.

### Ajuste de corriente (antes de energizar el motor)

Rsense = **0,100 Ω** en el carrier ⇒ `I_fase = VREF × 2` ⇒ **`VREF = I_fase / 2`**.
VREF se mide en el potenciómetro del módulo (vía marcada en el silkscreen inferior).

| I fase | VREF | Uso |
|---|---|---|
| 0,8 A | 0,40 V | mínimo útil |
| **1,0 A** | **0,50 V** | **recomendado** (≈25 N·cm, sin disipador) |
| 1,2 A | 0,60 V | requiere disipador |
| 1,5 A | 0,75 V | máximo sin disipador |
| 1,7 A | 0,85 V | **no usar**: corriente nominal del motor 17HS4401S |

Con 12 V sobre una bobina de 1,5 Ω la corriente llegaría a 8 A sin limitación, así que el
*chopping* sí entra en acción a 1,0 A (condición que Pololu exige para que el micropaso sea
correcto). A 1,0 A el torque disponible es ≈0,25 N·m y afinar una clavija necesita < 0,2 N·m.

---

## 4. Motor NEMA-17

| 17HS4401S | Valor |
|---|---|
| Corriente | 1,7 A/fase |
| Resistencia | 1,5 Ω/fase |
| Inductancia | 2,8 mH |
| Torque de retención | 43 N·cm |
| Paso | 1,8° · eje Ø5 mm |

**Pares de bobinas** (medir con óhmetro si el cable no tiene colores estándar: un par mide
~1,5 Ω entre sí, y circuito abierto contra el otro par):

| Bobina | Hilos | DRV8825 |
|---|---|---|
| A | Negro (A+), Verde (A−) | A1 (13), A2 (14) |
| B | Rojo (B+), Azul (B−) | B1 (12), B2 (11) |

Invertir un par solo cambia el sentido de giro (lo absorbe `DIR`); dejar un par partido entre
A y B hace que el motor vibre sin girar.

**No se agregan diodos de rueda libre**: el DRV8825 integra los FETs con sus diodos de cuerpo
y tiene protección de sobrecorriente, sobretemperatura y UVLO. Un diodo externo solo degrada
la forma de onda.

---

## 5. INMP441 (detección de frecuencia)

| Pin del módulo | Conexión | Nota |
|---|---|---|
| VDD | 3V3 (J1-1) | Rango 1,62–3,63 V. **No es tolerante a 5 V** (abs. máx. 3,63 V) |
| GND | GND | Consumo 2,2 mA típ. a 3,3 V |
| L/R | GND (J3-1) | **Debe atarse, no dejarse flotando**. Bajo = canal izquierdo |
| SCK | GPIO17 | 64 × 16 kHz = **1,024 MHz** (rango válido 0,5–3,2 MHz) |
| WS | GPIO18 | **16 kHz** (rango válido 7,8–50 kHz) |
| SD | GPIO8 | Salida I²S de 24 bits; **100 kΩ a GND** junto al módulo (la línea queda en alta impedancia fuera del canal) |

Decoupling: **0,1 µF entre VDD y GND** pegado al módulo. En el breakout de 6 pines `CHIPEN`
ya viene atado alto; si el módulo expone los 9 pads, `CHIPEN` → VDD.

---

## 6. Piezo (solo vibración, no frecuencia)

La detección de tono la hace el INMP441, así que el piezo solo necesita **decir si la cuerda
vibra y con qué amplitud**. Eso elimina el MCP6002, las dos etapas de ×10 y el filtro
anti-alias del anteproyecto: queda una red pasiva de alta impedancia + recorte.

```
PZ+ ──┬─── R1 1 MΩ ─── VBIAS (1,65 V)          VBIAS = 3V3 / 2
      │                                        (divisor 2 × 1 MΩ + 100 nF)
      └─── R2 4,7 kΩ ──┬─── ADC_OUT ── GPIO1 (ADC1_CH0)
                       ├─── C4 100 nF ── GND
                       └─── BAT54S: pin3 al nodo, pin1 a GND, pin2 a 3V3
PZ- ─────────────────────── GND
```

| Elemento | Valor | Por qué |
|---|---|---|
| R1 | 1 MΩ a 1,65 V | El disco es una fuente capacitiva (~25 nF); con 1 MΩ el pasa-altos queda en ≈6 Hz y no se pierde el Mi grave. Además centra la señal en 1,65 V, la mitad de fondo de escala del ADC |
| R2 | 4,7 kΩ | Limita la corriente del clamp: un golpe directo sobre el disco genera decenas de volts |
| BAT54S | doble Schottky serie | Recorta a 3V3 + Vf y a −Vf. Es el encapsulado correcto (dos diodos en serie, un solo SOT-23). **Un 1N5819 no sirve**: es un rectificador de 1 A, un solo diodo, no puede recortar ambas ramas |
| C4 | 100 nF | Retiene la muestra para el S&H del ADC y forma un LPF de ≈340 Hz con R2. Adecuado porque solo interesa la envolvente de la pulsación, no el tono |

ADC: atenuación de **12 dB → fondo de escala 0–3,1 V**, con la señal centrada en 1,65 V.
En firmware conviene leer RMS por bloque; si la vibración es baja, subir R1 no ayuda (es bias,
no ganancia): en ese caso recién ahí se justifica el amplificador.

---

## 7. Pulsadores y LED

- 6 pulsadores 6×6 mm entre GPIO y GND, **pull-up interno** activado; `100 nF` en paralelo
  con cada uno para debounce por hardware, más `gpio_install_isr_service` por flanco de bajada.
- Un solo header 1×8: 6 señales + 2 GND (dos pines para que el conector no haga palanca).
- LED de estado: GPIO21 → 330 Ω → LED → GND (≈4 mA).

---

## 8. Puesta en marcha (en este orden)

1. **Sin motor y sin 12 V**: conectar el DevKit por USB, medir 3,3 V en J1-1 y continuidad de GND.
2. **Driver solo, sin motor**: 12 V por el fusible y el diodo, medir **VMOT = 11,7 V** y ajustar
   **VREF = 0,50 V** midiendo en el potenciómetro del módulo. Hacerlo *antes* de conectar el motor.
3. Apagar todo, conectar el motor a las borneras (par A / par B según la tabla §4).
4. Energizar y probar STEP/DIR con el motor en el aire, sin carga.
5. Conectar INMP441, verificar que el I²S entrega 16 kHz y datos distintos de cero.
6. Conectar el piezo y verificar la línea de base: debe leerse ≈1,65 V (±0,1 V) en reposo.
7. Recién entonces montar el acople en la clavija.

**Nunca**: conectar 12 V a 5V/3V3/VBAT del DevKit · desconectar el motor con VMOT energizado
(el pico inductivo destruye el driver, advertencia explícita de Pololu) · invertir la polaridad
de la fuente · alimentar el motor desde la protoboard.

---

## 9. Diferencias con el anteproyecto

| Ítem | Anteproyecto | Aquí | Motivo |
|---|---|---|---|
| Placa | FeatherS3 (v2) / "Devkit V1 30 pines" (v1) | **ESP32-S3-DevKitC-1** | Decisión del grupo; el pinout se rehizo sobre la tabla oficial de headers |
| Driver | A4988 | **DRV8825** | Ya disponible; se compensa la diferencia de fórmula (I = Vref×2 en vez de Vref/0,4) y se mantiene 1/16 |
| STEP/DIR/EN | IO33 / IO38 / IO42 | **GPIO9 / GPIO10 / GPIO11** | GPIO33–37 no son utilizables en módulos con PSRAM octal |
| I²S | IO5 / IO6 / IO7 | **GPIO17 / GPIO18 / GPIO8** | Pines contiguos; IO6 e IO12 quedan libres para los 6 botones |
| Botones | 6 sueltos "IO4, IO10, IO11, IO12, IO14, IO17" | **GPIO4, 5, 6, 7, 15, 16** | Un solo header, sin tocar pines de I²S ni de motor |
| Piezo | MCP6002 ×100 + LPF + clamp | **clamp + bias, sin amplificador** | El tono lo mide el INMP441; el piezo solo detecta vibración |
| Protección 12 V | F1, D1, C1, C2 en el texto | **igual, dibujado en el diagrama** | Que el cableado y el documento digan lo mismo |
| Motor | 1,5 A / 1,8 Ω / 3,2 mH | **1,7 A / 1,5 Ω / 2,8 mH** | Valores reales del datasheet del 17HS4401**S** |

---

## 10. Fuentes

1. Espressif — *ESP32-S3-DevKitC-1 v1.1 User Guide* (tablas J1/J3, GPIO35–37, RGB LED, strapping).
2. Pololu — *DRV8825 Stepper Motor Driver Carrier #2133* (VMOT 8,2–45 V, `I = VREF × 2`,
   1,5 A/fase sin disipador, picos LC y ≥47 µF, STEP ≥1,9 µs, tabla de micropaso, FAULT).
3. TI — *DRV8825 Datasheet* (estados de RESET/SLEEP/ENBL, UVLO, OCP, OTP).
4. InvenSense/TDK — *INMP441 Datasheet* DS-INMP441-00 (VDD 1,62–3,63 V, SCK 0,5–3,2 MHz,
   WS 7,8–50 kHz, L/R, decoupling, pulldown de SD).
5. Handson Technology — *17HS4401S Data Specs* (1,7 A, 1,5 Ω, 2,8 mH, 43 N·cm, Ø5 mm).
6. Murata — *Piezoelectric Sound Components Application Manual* (impedancia capacitiva del disco).
