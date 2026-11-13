"""Constants for the RIKA integration."""

from datetime import timedelta

DOMAIN = "rika"

BASE_URL = "https://www.rika-firenet.com"

SCAN_INTERVAL = timedelta(seconds=30)

# The stove is reported offline when the cloud has not heard from it for longer.
OFFLINE_AFTER_MINUTES = 2

# controls.operatingMode
MODE_MANUAL = 0
MODE_AUTO = 1
MODE_COMFORT = 2

# Option: the Home Assistant schedule copied to the stove's heating times
CONF_SCHEDULE_ENTITY = "schedule_entity"
