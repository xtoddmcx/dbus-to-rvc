# ######################################
# ######## Hardware settings ###########
# ######################################

# Nr. of physical batteries to be aggregated. Smart shunt for battery current is not needed and not supported.
BATTERY_INSTANCE = 0
CANBUS_NAME = 'vecan0'
CANBUS_BIT_RATE = 250000
CANBUS_SOCKET_TYPE = 'socketcan'

SOURCE_BMS_PATH = "com.victronenergy.battery.aggregate"

BATTERY_PRIORITY = 0x78
BATTERY_ID = 0x01
PRODUCT_ID = 'LI3*8**'

SOURCE_ID = 0x46

LOGGING = 2
