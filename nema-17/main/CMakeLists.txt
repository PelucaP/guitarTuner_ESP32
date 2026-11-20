idf_component_register(SRCS "main.c"
                            "drv8825.c"
                            "stepper_motor_encoder.c"
                       INCLUDE_DIRS "."
                       REQUIRES esp_driver_rmt
                                esp_driver_gpio)
