# guitarTuner_ESP32

## Instrucciones de ejecución

Después de clonar el repo se ha de ingresar al entorno virtual de espressif y correr el siguiente comando:

``` idf.py reconfigure ```

Lo que añadirá las dependencias del projecto y generará un archivo local sdkconfig que permitirá generar el proyecto con el siguiente comando:

``` idf.py build ```

Posterior, será necesario detectar el puerto al cual está conectado el microcontrolador (Solo se asegura compatibilidad con ESP32-S3) y flashear el proyecto.

Se asume para este caso que el microcontrolador existe en el puerto "/dev/ttyACM0"

``` idf.py -p /dev/ttyACM0 flash ```

Después de que termine el proceso se puede revisar el funcionamiento del proyecto con 

``` idf.py -p /dev/ttyACM0 monitor ```


## Avance del proyecto

Hasta ahora solo se tiene una ejecución de FFT que demuestra posible la integración de procesamiento de señales a nivel de sistemas embebidos.

