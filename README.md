# guitarTuner_ESP32


This creates  sdkconfig.defaults , which should be committed. Each developer can then run:

idf.py reconfigure

or build the project, and ESP-IDF will generate their local  sdkconfig .

Commit  sdkconfig  only if you intentionally require every developer to use the exact same complete configuration and are prepared to resolve configuration conflicts.
