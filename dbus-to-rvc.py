#!/usr/bin/env python3

# References
# https://lithionicsbattery.com/wp-content/uploads/2021/04/Lithionics-RV-C-J1939-PGN-Table-Rev3.pdf
# https://www.scribd.com/document/659063705/RV-C-Specification-Full-Layer-06-02-23-0

from signal import signal, SIGINT
import math
import sys
import dbus
import time
import can
import logging
import settings

sys.path.append("/opt/victronenergy/dbus-systemcalc-py/ext/velib_python")
from dbusmonitor import DbusMonitor  # noqa: E402
from dbus.mainloop.glib import DBusGMainLoop  # noqa: E402

from gi.repository import GLib

class DbusMon:

	def __init__(self):
		# TODO: Move these to settings
		self.battery_instance = settings.BATTERY_INSTANCE
		self.bus_name = settings.CANBUS_NAME
		self.bitrate = settings.CANBUS_BIT_RATE
		self.socket_type = settings.CANBUS_SOCKET_TYPE
		self.bms_path = settings.SOURCE_BMS_PATH
		self.destination_address = 0x00
		self.battery_priority = int(settings.BATTERY_PRIORITY).to_bytes(1, byteorder='little', signed = False)
		self.battery_id = int(settings.BATTERY_ID).to_bytes(1, byteorder='little', signed = False)
		self.product_id = bytes(settings.PRODUCT_ID, 'utf-8')
		self.message_priority = 2
		self.source = settings.SOURCE_ID
		self.logger = logging.getLogger(__name__)
		self.logger.setLevel(logging.DEBUG)
		self.file_handler = logging.FileHandler('dbus-to-rvc.log')
		self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
		self.file_handler.setFormatter(self.formatter)
		self.logger.addHandler(self.file_handler)

		self.dbus_bus = dbus.SystemBus()
		self.bus = can.interface.Bus(interface = self.socket_type, channel=self.bus_name, bitrate=self.bitrate, receive_own_messages=True )

		self.messages = {
			"ADDRESS_CLAIM" : {"dgn":0x0EEFF, "time":1000, "data":0, "arbitration_id":0},
			"ADDRESS_CLAIM_2" : {"dgn":0x0EE00, "time":1000, "data":0, "arbitration_id":0},
			"PRODUCT_ID" : {"dgn":0xFEEB, "time":5000, "data":0, "arbitration_id":0},
			"DM_RV" : {"dgn":0X1FECA, "time":0, "data":0, "arbitration_id":0},
			"DC_SOURCE_STATUS_1" : {"dgn":0x1FFFD, "time":500, "data":0, "arbitration_id":0},
			"DC_SOURCE_STATUS_2" : {"dgn":0x1FFFC, "time":500, "data":0, "arbitration_id":0},
			"DC_SOURCE_STATUS_3" : {"dgn":0x1FFFB, "time":500, "data":0, "arbitration_id":0},
			"DC_SOURCE_STATUS_4" : {"dgn":0x1FEC9, "time":5000, "data":0, "arbitration_id":0},
			"DC_SOURCE_STATUS_6" : {"dgn":0x1FEC7, "time":5000, "data":0, "arbitration_id":0},
			"DC_SOURCE_STATUS_11" : {"dgn":0x1FEA5, "time":1000, "data":0, "arbitration_id":0},
			"PROP_BMS_STATUS_1" : {"dgn":0x0FF80, "time":1000, "data":0, "arbitration_id":0},
			"PROP_BMS_STATUS_3" : {"dgn":0X0FF82, "time":5000, "data":0, "arbitration_id":0}
		}
		for key in self.messages :
			self.messages[key]["arbitration_id"] = self.get_arbitration_id(self.messages[key]["dgn"], self.message_priority, self.source)

		dummy = {"code": None, "whenToLog": "configChange", "accessLevel": None}
		self.monitorlist = {
			"com.victronenergy.battery": {
				"/Dc/0/Voltage": dummy,
				"/Dc/0/Current": dummy,
				"/Dc/0/Power": dummy,
				"/Capacity": dummy,
				"/InstalledCapacity": dummy,
				"/Info/MaxChargeVoltage": dummy,
				"/Info/MaxChargeCurrent": dummy,
				"/Info/MaxDischargeCurrent": dummy,
				"/Soc": dummy,
				"/System/NrOfModulesOnline": dummy,
				"/Dc/0/Voltage": dummy,
				"/Dc/0/Current": dummy,
				"/Dc/0/Temperature": dummy,
				"Alarms/BmsCable": dummy,
				"Alarms/CellImbalance": dummy,
				"Alarms/HighChargeCurrent": dummy,
				"Alarms/HighChargeTemperature": dummy,
				"Alarms/HighDischargeCurrent": dummy,
				"Alarms/HighTemperature": dummy,
				"Alarms/HighVoltage": dummy,
				"Alarms/InternalFailure": dummy,
				"Alarms/LowCellVoltage": dummy,
				"Alarms/LowChargeTemperature": dummy,
				"Alarms/LowSoc": dummy,
				"Alarms/LowTemperature": dummy,
				"Alarms/LowVoltage": dummy
			}
		}

		self.dbusmon = DbusMonitor(self.monitorlist)


	def get_arbitration_id(self, dgn, priority, source) :
		if (dgn < 0) or (dgn>2**17) or (priority < 0) or (priority>2**3) or (source < 0) or (source>2**8):
			return 0
		return ( priority << 26 ) + ( dgn << 8 ) + source

	# This isn't used at this time, added for future sending of messages to specific nodes
	def get_arbitration_id_2(self, dgn_high, dgn_low, priority, source) :
		if (dgn_high < 0) or (dgn_high>2**9) or (dgn_low < 0) or (dgn_low>2**8) or (priority < 0) or (priority>2**3) or (source < 0) or (source>2**8):
			return 0
		return ( priority << 26 ) + ( dgn_high << 16 )  + ( dgn_low << 8 ) + source

	# This isn't used at this time, added for future receiving of messages
	def decode_arbitration_id(self, arbitration_id) :
		if (arbitration_id < 0) or (arbitration_id>2**29):
			return {"dgn":0, "dgn_high":0, "dgn_low":0, "priority":0, "source":0 }
		i = arbitration_id
		priority = i>>26
		i = i - ( priority << 26 )
		dgn_high = i>>16
		i = i - ( dgn_high << 16 )
		dgn_low = i>>8
		i = i - ( dgn_low << 8 )
		source = i
		dgn = ( dgn_high << 8 ) + dgn_low
		return {"dgn":dgn, "dgn_high":dgn_high, "dgn_low":dgn_low, "priority":priority, "source":source }

	def send_canbus_message(self, message_key):
		if message_key in self.messages :
			message = self.messages[message_key]
			self.bus.send( can.Message(arbitration_id=message['arbitration_id'], is_extended_id=True, data=message['data'] ) )
		return True

	def get_time_remaining(self):
		capacity = float(self.dbusmon.get_value(self.bms_path, "/Capacity"))
		current = float(self.dbusmon.get_value(self.bms_path, "/Dc/0/Current"))
		installed_capacity = float(self.dbusmon.get_value(self.bms_path, "/InstalledCapacity"))
		if current == 0 :
			return 0
		if ( current > 0 ):
			hours_left = capacity / current
		else:
			hours_left = ( installed_capacity - capacity ) / (0-current)
		if (hours_left > 5) :
			hours_left = 5
		return hours_left * 60

	def build_data(self, data_id):
		def address_claim():
			beginning = ( int(0xD9).to_bytes(1, byteorder='little', signed = False) + int(0xEB).to_bytes(1, byteorder='little', signed = False)
				 + int(0xED).to_bytes(1, byteorder='little', signed = False) + int(0x0E).to_bytes(1, byteorder='little', signed = False)
			)
			instance = int(0).to_bytes(1, byteorder='little', signed = False)
			compatibility = int(0).to_bytes(1, byteorder='little', signed = False)
			compatibility2 = int(0).to_bytes(1, byteorder='little', signed = False)
			data = beginning + instance + compatibility + compatibility2
			return data

		
		# VenusOS uses python 3.8 at this point, no match case statement
		if data_id == 'ADDRESS_CLAIM':
			self.messages[data_id]['data'] = address_claim()

		elif data_id == 'ADDRESS_CLAIM_2':
			self.messages[data_id]['data'] = address_claim()

		elif data_id == 'PRODUCT_ID':
			self.messages[data_id]['data'] = self.product_id

		elif data_id == 'DM_RV':
			operating_status = int(0x01).to_bytes(1, byteorder='little', signed = False)
			source_address = int(0x45).to_bytes(1, byteorder='little', signed = False)
			spn = int(0x00).to_bytes(1, byteorder='little', signed = False)
			dsa = int(0xFF).to_bytes(1, byteorder='little', signed = False)
			self.messages[data_id]['data'] = operating_status + source_address + spn + spn + spn + dsa + dsa + dsa

		elif data_id == 'DC_SOURCE_STATUS_1':
			dc_voltage = int( self.dbusmon.get_value(self.bms_path, "/Dc/0/Voltage") / .05 ).to_bytes(2, byteorder='little', signed = False)
			dc_current = int ( 2000000000 - ( self.dbusmon.get_value(self.bms_path, "/Dc/0/Current") / .001 )).to_bytes(4, byteorder='little', signed = False)
			self.messages[data_id]['data'] = self.battery_id + self.battery_priority + dc_voltage + dc_current

		elif data_id == 'DC_SOURCE_STATUS_2':
			temperature = int ( ( 273 +  self.dbusmon.get_value(self.bms_path, "/Dc/0/Temperature") )  / 0.03125 ).to_bytes(2, byteorder='little', signed = False)
			state_of_charge = int ( ( self.dbusmon.get_value(self.bms_path, "/Soc") / .5 )).to_bytes(1, byteorder='little', signed = False)
			time_remaining = int (self.get_time_remaining() ).to_bytes(2, byteorder='little', signed = False)
			self.messages[data_id]['data'] = self.battery_id + self.battery_priority + temperature + state_of_charge + time_remaining

		elif data_id == 'DC_SOURCE_STATUS_3':
			state_of_health = int(0xC8).to_bytes(1, byteorder='little', signed = False)
			# These batteries dont' report state of health
			remaining_capacity = int ( self.dbusmon.get_value(self.bms_path, "/Capacity" )).to_bytes(2, byteorder='little', signed = False)
			state_of_charge = int ( ( self.dbusmon.get_value(self.bms_path, "/Soc") / .5 )).to_bytes(1, byteorder='little', signed = False)
			self.messages[data_id]['data'] = self.battery_id + self.battery_priority + state_of_health + remaining_capacity + state_of_charge

		elif data_id == 'DC_SOURCE_STATUS_4':
			desired_charge_state = int(0x00).to_bytes(1, byteorder='little', signed = False)
			desired_charge_voltage = int ( ( self.dbusmon.get_value(self.bms_path, "/Info/MaxChargeVoltage") / .05 )).to_bytes(2, byteorder='little', signed = False)
			desired_charge_current = int ( ( 1600 + self.dbusmon.get_value(self.bms_path, "/Info/MaxChargeCurrent") ) / 0.05 ).to_bytes(2, byteorder='little', signed = False)
			battery_type = int(0x03).to_bytes(1, byteorder='little', signed = False)
			self.messages[data_id]['data'] = self.battery_id + self.battery_priority + desired_charge_state + desired_charge_voltage + desired_charge_current + battery_type

		elif data_id == 'DC_SOURCE_STATUS_6':
			flag_1 = ''
			flag_2 = ''
			flag_3 = ''

			if self.dbusmon.get_value(self.bms_path, "/Alarms/HighVoltage") == 0 :
				flag_1 = flag_1 + '00'
			else :
				flag_1 = flag_1 + '11'
			if self.dbusmon.get_value(self.bms_path, "/Alarms/LowVoltage") == 0 :
				flag_1 = flag_1 + '00'
			else :
				flag_1 = flag_1 + '11'
			flag_1 = int(flag_1,2).to_bytes(1, byteorder='little')

			if self.dbusmon.get_value(self.bms_path, "/Alarms/LowSoc") == 0 :
				flag_2 = flag_2 + '00'
			else :
				flag_2 = flag_2 + '11'
			if self.dbusmon.get_value(self.bms_path, "/Alarms/LowTemperature") == 0 :
				flag_2 = flag_2 + '00'
			else :
				flag_2 = flag_2 + '11'
			flag_2 = int(flag_2,2).to_bytes(1, byteorder='little')

			if self.dbusmon.get_value(self.bms_path, "/Alarms/HighTemperature") == 0 :
				flag_3 = flag_3 + '00'
			else :
				flag_3 = flag_3 + '11'
			flag_3 = int(flag_3,2).to_bytes(1, byteorder='little')

			self.messages[data_id]['data'] = self.battery_id + self.battery_priority + flag_1 + flag_2 + flag_3

		elif data_id == 'DC_SOURCE_STATUS_11':
			flag_4 = '01010101' # The BMS doesn't report any of this
			flag_4 = int(flag_4,2).to_bytes(1, byteorder='little')

			full_battery_capacity = int ( self.dbusmon.get_value(self.bms_path, "/InstalledCapacity") ).to_bytes(2, byteorder='little', signed = False)
			dc_power = int ( abs( self.dbusmon.get_value(self.bms_path, "/Dc/0/Power") ) ).to_bytes(2, byteorder='little', signed = False)

			self.messages[data_id]['data'] = self.battery_id + self.battery_priority + flag_4 + full_battery_capacity + dc_power

		elif data_id == 'PROP_BMS_STATUS_1':
			number_of_modules = int ( self.dbusmon.get_value(self.bms_path, "/System/NrOfModulesOnline") ).to_bytes(1, byteorder='little', signed = False)
			bms_internal_temp = int ( 40 + ( self.dbusmon.get_value(self.bms_path, "/Dc/0/Temperature")  )).to_bytes(1, byteorder='little', signed = False)
			max_recorded_temp = int ( 40 + ( self.dbusmon.get_value(self.bms_path, "/Dc/0/Temperature")  )).to_bytes(1, byteorder='little', signed = False)
			min_recorded_temp = int ( 40 + ( self.dbusmon.get_value(self.bms_path, "/Dc/0/Temperature")  )).to_bytes(1, byteorder='little', signed = False)
			# These aren't reported in the BMS, so using the current temp. Could track it in here I suppose
			bms_status_code = int(0x000100).to_bytes(3, byteorder='little', signed = False)
			self.messages[data_id]['data'] = self.battery_id + number_of_modules + bms_internal_temp + max_recorded_temp + min_recorded_temp + bms_status_code

		elif data_id == 'PROP_BMS_STATUS_3':
			lifetime_ah_consumed = int(0x2710).to_bytes(4, byteorder='little', signed = False)
			# Our bms doesn't track this
			self.messages[data_id]['data'] = self.battery_id + self.battery_priority + lifetime_ah_consumed

		else :
			self.logger.debug('Received request to build invalid data_id ' + str(data_id) )

	def send_messages(self, time):

		for key in self.messages:
			message = self.messages[key]
			if message['time'] == time :
				try:
					self.build_data(key)
				except Exception as e:
					self.logger.debug('Exception caught in building data ' + key)
					self.logger.debug(e)
				try:
					self.send_canbus_message(key)
				except Exception as e:
					self.logger.debug('Exception caught in sending ' + key)
					self.logger.debug(e)
		return True

def main():
	DBusGMainLoop(set_as_default=True)
	dbusmon = DbusMon()

	keys = []
	for key in dbusmon.messages:
		if not dbusmon.messages[key]['time'] in keys and dbusmon.messages[key]['time'] != 0:
			keys.append(dbusmon.messages[key]['time'])
	
	for time in keys:
		GLib.timeout_add(time, dbusmon.send_messages, time)

	mainloop = GLib.MainLoop()
	mainloop.run()

def handler(signal_received, frame):
	# Handle any cleanup here
	print('Exiting')
	exit(0)

if __name__ == "__main__":
	signal(SIGINT, handler)
	main()
