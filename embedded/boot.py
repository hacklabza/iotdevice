# This file is executed on every boot (including wake-boot from deepsleep)
import gc
import machine
import uos

gc.collect()
