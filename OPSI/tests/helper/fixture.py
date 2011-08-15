# -*- coding: utf-8 -*-
"""
   Copyright (C) 2010 uib GmbH
   
   http://www.uib.de/
   
   All rights reserved.
   
   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.
   
   This program is distributed in the hope thatf it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
   
   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
   
   @copyright: uib GmbH <info@uib.de>
   @author: Christian Kampka <c.kampka@uib.de>
   @license: GNU General Public License version 2
"""

import os

from testtools.monkey import patch
from fixtures import Fixture
import fixtures

from OPSI.Util.File.Opsi import BackendDispatchConfigFile, HostKeyFile
from OPSI.Util import generateOpsiHostKey

class FQDNFixture(Fixture):
	
	def __init__(self, fqdn="opsi.uib.local", address="172.16.0.1"):
		
		self.hostname = fqdn.split(".")[0]
		self.fqdn = fqdn
		self.address = address
		
	def setUp(self):
		super(FQDNFixture, self).setUp()
		
		def getfqdn(_ignore):
			return self.fqdn
		
		def gethostbyaddr(_ignore):
			return (self.fqdn, [self.hostname], [self.address])
		
		self.useFixture(fixtures.MonkeyPatch('socket.getfqdn', getfqdn))
		self.useFixture(fixtures.MonkeyPatch('socket.gethostbyaddr', gethostbyaddr))

class ConfigFixture(Fixture):
	
	template = None
	name = None
	
	def __init__(self, prefix=None, dir=None):
		
		super(ConfigFixture, self).__init__()
		self.prefix = prefix
		self.dir = dir
		self.data = None
	
		self.config = None
	
	def setUp(self):
		super(ConfigFixture, self).setUp()
		
		if self.dir is None:
			self.dir = self.useFixture(fixtures.TempDir()).path
		if self.prefix is not None:
			self.dir = os.path.join(self.dir, self.prefix)
			if not os.path.exists(self.dir):
				os.mkdir(self.dir)
		self.path = os.path.join(self.dir, self.name)
	
	def _write(self, data):
		self.data = data
		f = file(self.path, "w")
		try:
			f.write(data)
			f.close()
		except Exception, e:
			self.addDetail("conferror", e)
			self.test.fail("Could not generate global.conf.")
			f.close()

	
class GlobalConfFixture(ConfigFixture):
	
	template = """[global]
hostname = #hostname#
"""	
	name = "global.conf"
	
	def __init__(self, fqdn="opsi.uib.local", prefix=None, dir=None):
		super(GlobalConfFixture, self).__init__(prefix=prefix, dir=dir)
		self.fqdn = fqdn
		
	def setUp(self):
		super(GlobalConfFixture, self).setUp()
		
		s = self.template.replace("#hostname#", self.fqdn)
		self._write(s)

class DispatchConfigFixture(ConfigFixture):
	
	template = """
	backend_.*         : #backend#, opsipxeconfd, #dhcp#
	host_.*            : #backend#, opsipxeconfd, #dhcp#
	productOnClient_.* : #backend#, opsipxeconfd
	configState_.*     : #backend#, opsipxeconfd
	.*                 : #backend#
	"""
	
	name = "dispatch.conf"
	
	def __init__(self, prefix="backendManager", dir=None):
		super(DispatchConfigFixture, self).__init__(prefix=prefix, dir=dir)
	
	
	def _generateDispatchConf(self, data):
		self._write(data)
		self.config = BackendDispatchConfigFile(self.path)

	def setupFile(self):
		conf = self.template.replace("#backend#", "file")
		self._generateDispatchConf(conf)
		
	def setupMySQL(self):
		conf = self.template.replace("#backend#", "mysql")
		self._generateDispatchConf(conf)
		
	def setupLDAP(self):
		conf = self.template.replace("#backend#", "ldap")
		self._generateDispatchConf(conf)
		
	def setupDHCP(self):
		if self.data is not None:
			conf = self.data.replace("#dhcp#", "dhcpd")
		else:
			conf = self.template.replace("#dhcp#", "dhcpd")
		self._generateDispatchConf(conf)

class HwAuditConfigFixture(ConfigFixture):
	
	template = """
#
# -*- coding: utf-8 -*-
#
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# =     HARDWARE CLASSES                                                =
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
global OPSI_HARDWARE_CLASSES
OPSI_HARDWARE_CLASSES = [

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     DEVICE_ID                                                       -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "VIRTUAL",
      "Opsi":   "DEVICE_ID"
   },
   "Values": [
      {
         "Type":   "varchar(10)",
         "Scope":  "g",
         "Opsi":   "deviceType",
         "WMI":    "PNPDeviceID.split('\\\\')[0]"
      },
      {
         "Type":   "varchar(4)",
         "Scope":  "g",
         "Opsi":   "vendorId",
         "WMI":    "PNPDeviceID.split('\\\\')[1].split('&')[0].split('_')[1]",
         "Linux":  "vendorId"
      },
      {
         "Type":   "varchar(4)",
         "Scope":  "g",
         "Opsi":   "deviceId",
         "WMI":    "PNPDeviceID.split('\\\\')[1].split('&')[1].split('_')[1]",
         "Linux":  "deviceId"
      },
      {
         "Type":   "varchar(4)",
         "Scope":  "g",
         "Opsi":   "subsystemVendorId",
         "WMI":    "PNPDeviceID.split('\\\\')[1].split('&')[2].split('_')[1][:4]",
         "Linux":  "subsystemVendorId"
      },
      {
         "Type":   "varchar(4)",
         "Scope":  "g",
         "Opsi":   "subsystemDeviceId",
         "WMI":    "PNPDeviceID.split('\\\\')[1].split('&')[2].split('_')[1][4:]",
         "Linux":  "subsystemDeviceId"
      },
      {
         "Type":   "varchar(8)",
         "Scope":  "g",
         "Opsi":   "revision",
         "WMI":    "PNPDeviceID.split('\\\\')[1].split('&')[3].split('_')[1]",
         "Linux":  "revision"
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     BASIC_INFO                                                      -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "VIRTUAL",
      "Opsi":   "BASIC_INFO"
   },
   "Values": [
      {
         "Type":   "varchar(100)",
         "Scope":  "g",
         "Opsi":   "name",
         "WMI":    "Name",
         "Linux":  "product"
      },
      {
         "Type":   "varchar(100)",
         "Scope":  "g",
         "Opsi":   "description",
         "WMI":    "Description",
         "Linux":  "description"
      },
      #{
      #   "Type":   "varchar(60)",
      #   "Scope":  "g",
      #   "Opsi":   "caption",
      #   "WMI":    "Caption"
      #}
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     HARDWARE_DEVICE                                                 -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "VIRTUAL",
      "Super":  [ "BASIC_INFO" ],
      "Opsi":   "HARDWARE_DEVICE"
   },
   "Values": [
      {
         "Type":   "varchar(50)",
         "Scope":  "g",
         "Opsi":   "vendor",
         "WMI":    "Manufacturer",
         "Linux":  "vendor"
      },
      {
         "Type":   "varchar(100)",
         "Scope":  "g",
         "Opsi":   "model",
         "WMI":    "Model",
         "Linux":  "product"
      },
      {
         "Type":   "varchar(50)",
         "Scope":  "i",
         "Opsi":   "serialNumber",
         "WMI":    "SerialNumber",
         "Linux":  "serial"
      },
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     COMPUTER_SYSTEM                                                 -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "HARDWARE_DEVICE" ],
      "Opsi":   "COMPUTER_SYSTEM",
      "WMI":    "select * from Win32_ComputerSystem",
      "Linux":  "[lshw]system"
   },
   "Values": [
      {
         "Type":   "varchar(100)",
         "Scope":  "i",
         "Opsi":   "name",
         "WMI":    "Name",
         "Linux":  "id"
      },
      {
         "Type":   "varchar(50)",
         "Scope":  "i",
         "Opsi":   "systemType",
         "WMI":    "SystemType",
         "Linux":  "configuration/chassis"
      },
      {
         "Type":   "bigint",
         "Scope":  "i",
         "Opsi":   "totalPhysicalMemory",
         "WMI":    "TotalPhysicalMemory",
         "Linux":  "core/memory/size",
         "Unit":   "Byte"
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     CHASSIS                                                         -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "BASIC_INFO" ],
      "Opsi":   "CHASSIS",
      "WMI":    "Select * from Win32_SystemEnclosure",
      "Linux":  "[lshw]system"
   },
   "Values": [
      {
         "Type":   "varchar(64)",
         "Scope":  "g",
         "Opsi":   "name",
         "WMI":    "Caption",
         "Linux":  "configuration/chassis"
      },
      {
         "Type":   "varchar(40)",
         "Scope":  "g",
         "Opsi":   "chassisType",
         "WMI":    "ChassisTypes",
         "Linux":  "configuration/chassis"
      },
      {
         "Type":   "varchar(40)",
         "Scope":  "i",
         "Opsi":   "installDate",
         "WMI":    "InstallDate",
         "Linux":  ""
      },
      {
         "Type":   "varchar(50)",
         "Scope":  "i",
         "Opsi":   "serialNumber",
         "WMI":    "SerialNumber",
         "Linux":  "serial"
      },
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     BASE_BOARD                                                      -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "HARDWARE_DEVICE" ],
      "Opsi":   "BASE_BOARD",
      "WMI":    "select * from Win32_BaseBoard",
      "Linux":  "[lshw]bus:^core"
   },
   "Values": [
      {
         "Type":   "varchar(100)",
         "Scope":  "g",
         "Opsi":   "name",
         "WMI":    "Product",
         "Linux":  "description"
      },
      {
         "Type":   "varchar(100)",
         "Scope":  "g",
         "Opsi":   "product",
         "WMI":    "Product",
	 "Linux":  "product"
      },
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     BIOS                                                            -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "HARDWARE_DEVICE" ],
      "Opsi":   "BIOS",
      "WMI":    "select * from Win32_BIOS",
      "Linux":  "[lshw]memory:^firmware"
   },
   "Values": [
      {
         "Type":   "varchar(100)",
         "Scope":  "g",
         "Opsi":   "name",
         "WMI":    "Product",
         "Linux":  "description"
      },
      {
         "Type":   "varchar(50)",
         "Scope":  "i",
         "Opsi":   "version",
         "WMI":    "Version",
         "Linux":  "version"
      },
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     SYSTEM_SLOT                                                     -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "BASIC_INFO" ],
      "Opsi":   "SYSTEM_SLOT",
      "WMI":    "select * from Win32_SystemSlot",
      "Linux":  "[dmidecode]System Slot Information"
   },
   "Values": [
      {
         "Type":   "varchar(20)",
         "Scope":  "i",
         "Opsi":   "currentUsage",
         "WMI":    "CurrentUsage",
         "Linux":  "Current Usage"
      },
      #{
      #   "Type":   "varchar(20)",
      #   "Scope":  "i",
      #   "Opsi":   "slotDesignation",
      #   "WMI":    "SlotDesignation",
      #   "Linux":  "version"
      #},
      {
         "Type":   "varchar(50)",
         "Scope":  "g",
         "Opsi":   "name",
         "WMI":    "SlotDesignation",
         "Linux":  "Designation"
      },
      {
         "Type":   "varchar(20)",
         "Scope":  "i",
         "Opsi":   "status",
         "WMI":    "Status"
      },
      {
         "Type":   "int",
         "Scope":  "i",
         "Opsi":   "maxDataWidth",
         "WMI":    "MaxDataWidth",
         "Linux":  "Type.split('-bit')[0]",
         "Unit":   "Bit"
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     PORT_CONNECTOR                                                  -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "BASIC_INFO" ],
      "Opsi":   "PORT_CONNECTOR",
      "WMI":    "select * from Win32_PortConnector",
      "Linux":  "[dmidecode]Port Connector Information"
   },
   "Values": [
      {
         "Type":   "varchar(60)",
         "Scope":  "i",
         "Opsi":   "connectorType",
         "WMI":    "ConnectorType",
         "Linux":  "Port Type"
      },
      {
         "Type":   "varchar(60)",
         "Scope":  "i",
         "Opsi":   "name",
         "WMI":    "ExternalReferenceDesignator || InternalReferenceDesignator",
         "Linux":  "External Reference Designator || Internal Reference Designator"
      },
      {
         "Type":   "varchar(60)",
         "Scope":  "i",
         "Opsi":   "internalDesignator",
         "WMI":    "InternalReferenceDesignator",
         "Linux":  "Internal Reference Designator"
      },
      {
         "Type":   "varchar(60)",
         "Scope":  "i",
         "Opsi":   "internalConnectorType",
         "WMI":    "InternalConnectorType",
         "Linux":  "Internal Connector Type"
      },
      {
         "Type":   "varchar(60)",
         "Scope":  "i",
         "Opsi":   "externalDesignator",
         "WMI":    "ExternalReferenceDesignator",
         "Linux":  "External Reference Designator"
      },
      {
         "Type":   "varchar(60)",
         "Scope":  "i",
         "Opsi":   "externalConnectorType",
         "WMI":    "ExternalConnectorType",
         "Linux":  "External Connector Type"
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     PROCESSOR                                                       -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "HARDWARE_DEVICE" ],
      "Opsi":   "PROCESSOR",
      "WMI":    "select * from Win32_Processor",
      "Linux":  "[dmidecode]Processor Information"
   },
   "Values": [
      {
         "Type":   "varchar(100)",
         "Scope":  "g",
         "Opsi":   "name",
         "WMI":    "Name",
         "Linux":  "Version"
      },
      {
         "Type":   "varchar(100)",
         "Scope":  "g",
         "Opsi":   "description",
         "WMI":    "Description",
         "Linux":  "Signature"
      },
      {
         "Type":   "varchar(50)",
         "Scope":  "g",
         "Opsi":   "vendor",
         "WMI":    "Manufacturer",
         "Linux":  "Manufacturer"
      },
      {
         "Type":   "varchar(50)",
         "Scope":  "i",
         "Opsi":   "serialNumber",
         "WMI":    "ProcessorId",
         "Linux":  "ID"
      },
      {
         "Type":   "varchar(50)",
         "Scope":  "g",
         "Opsi":   "architecture",
         "WMI":    "Architecture",
      },
      {
         "Type":   "varchar(50)",
         "Scope":  "g",
         "Opsi":   "family",
         "WMI":    "Family",
         "Linux":  "Family"
      },
      {
         "Type":   "bigint",
         "Scope":  "i",
         "Opsi":   "currentClockSpeed",
         "WMI":    "CurrentClockSpeed*1000*1000",
         "Linux":  "Current Speed",
         "Unit":   "Hz"
      },
      {
         "Type":   "bigint",
         "Scope":  "g",
         "Opsi":   "maxClockSpeed",
         "WMI":    "MaxClockSpeed*1000*1000",
         "Linux":  "Max Speed",
         "Unit":   "Hz"
      },
      {
         "Type":   "int",
         "Scope":  "i",
         "Opsi":   "extClock",
         "WMI":    "ExtClock*1000*1000",
         "Linux":  "External Clock",
         "Unit":   "Hz"
      },
      {
         "Type":   "int",
         "Scope":  "g",
         "Opsi":   "addressWidth",
         "WMI":    "AddressWidth",
         "Unit":   "Bit"
      },
      {
         "Type":   "varchar(100)",
         "Scope":  "i",
         "Opsi":   "socketDesignation",
         "WMI":    "SocketDesignation",
         "Linux":  "Socket Designation"
      },
      {
         "Type":   "double",
         "Scope":  "i",
         "Opsi":   "voltage",
         "WMI":    "CurrentVoltage/10.0",
         "Linux":  "Voltage",
         "Unit":   "V"
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     MEMORY_BANK                                                     -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "BASIC_INFO" ],
      "Opsi":   "MEMORY_BANK",
      "WMI":    "select * from Win32_PhysicalMemoryArray",
      "Linux":  "[dmidecode]Physical Memory Array"
   },
   "Values": [
      {
         "Type":   "varchar(100)",
         "Scope":  "g",
         "Opsi":   "name",
         "WMI":    "Use",
         "Linux":  "Use"
      },
      {
         "Type":   "varchar(50)",
         "Scope":  "i",
         "Opsi":   "location",
         "WMI":    "Location",
         "Linux":  "Location"
      },
      {
         "Type":   "bigint",
         "Scope":  "g",
         "Opsi":   "maxCapacity",
         "WMI":    "MaxCapacity*1024",
         "Linux":  "Maximum Capacity",
         "Unit":   "Byte"
      },
      {
         "Type":   "tinyint",
         "Scope":  "g",
         "Opsi":   "slots",
         "WMI":    "MemoryDevices",
         "Linux":  "Number Of Devices",
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     MEMORY_MODULE                                                   -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "HARDWARE_DEVICE" ],
      "Opsi":   "MEMORY_MODULE",
      "WMI":    "select * from Win32_PhysicalMemory",
      "Linux":  "[dmidecode]Memory Device:Size.find('No Module') == -1"
   },
   "Values": [
      {
         "Type":   "varchar(100)",
         "Scope":  "g",
         "Opsi":   "name",
         "WMI":    "DeviceLocator",
         "Linux":  "Locator"
      },
      {
         "Type":   "bigint",
         "Scope":  "g",
         "Opsi":   "capacity",
         "WMI":    "Capacity",
         "Linux":  "Size",
         "Unit":   "Byte"
      },
      {
         "Type":   "varchar(100)",
         "Scope":  "i",
         "Opsi":   "deviceLocator",
         "WMI":    "DeviceLocator",
         "Linux":  "Bank Locator"
      },
      {
         "Type":   "varchar(10)",
         "Scope":  "g",
         "Opsi":   "formFactor",
         "WMI":    "FormFactor",
         "Linux":  "Form Factor"
      },
      {
         "Type":   "int",
         "Scope":  "g",
         "Opsi":   "speed",
         "WMI":    "Speed*1000*1000",
         "Unit":   "Hz"
      },
      {
         "Type":   "varchar(20)",
         "Scope":  "g",
         "Opsi":   "memoryType",
         "WMI":    "MemoryType",
         "Linux":  "Type"
      },
      {
         "Type":   "int",
         "Scope":  "g",
         "Opsi":   "dataWidth",
         "WMI":    "DataWidth",
         "Linux":  "Data Width",
         "Unit":   "Bit"
      },
      {
         "Type":   "varchar(100)",
         "Scope":  "i",
         "Opsi":   "tag",
         "WMI":    "Tag"
      },
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     CACHE_MEMORY                                                    -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "BASIC_INFO" ],
      "Opsi":   "CACHE_MEMORY",
      "WMI":    "select * from Win32_CacheMemory",
      "Linux":  "[dmidecode]Cache Information"
   },
   "Values": [
      {
         "Type":   "varchar(50)",
         "Scope":  "g",
         "Opsi":   "name",
         "WMI":    "Purpose",
         "Linux":  "Socket Designation"
      },
      {
         "Type":   "int",
         "Scope":  "g",
         "Opsi":   "installedSize",
         "WMI":    "InstalledSize*1024",
         "Linux":  "Installed Size",
         "Unit":   "Byte"
      },
      {
         "Type":   "int",
         "Scope":  "g",
         "Opsi":   "maxSize",
         "WMI":    "MaxCacheSize*1024",
         "Linux":  "Maximum Size",
         "Unit":   "Byte"
      },
      {
         "Type":   "varchar(10)",
         "Scope":  "g",
         "Opsi":   "location",
         "WMI":    "Location",
         "Linux":  "Location"
      },
      {
         "Type":   "varchar(10)",
         "Scope":  "g",
         "Opsi":   "level",
         "WMI":    "Level",
         "Linux":  "Configuration.split(',')[-1].strip()"
      },
      #{
      #   "Type":   "varchar(100)",
      #   "Scope":  "i",
      #   "Opsi":   "purpose",
      #   "WMI":    "Purpose"
      #}
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     PCI_DEVICE                                                      -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "DEVICE_ID", "HARDWARE_DEVICE" ],
      "Opsi":   "PCI_DEVICE",
      "WMI":    "select * from Win32_PNPEntity where DeviceID like 'PCI\\%'",
      "Linux":  "[lshw].*:.*:businfo.startswith('pci@')"
   },
   "Values": [
      {
         "Type":   "varchar(60)",
         "Scope":  "i",
         "Opsi":   "busId",
         "WMI":    "",
         "Linux":  "businfo.split('@')[-1]"
      },
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     CONTROLLER                                                      -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "VIRTUAL",
      "Super":  [ "DEVICE_ID", "HARDWARE_DEVICE" ],
      "Opsi":   "CONTROLLER"
   },
   "Values": [
      #{
      #   "Type":   "varchar(100)",
      #   "Scope":  "g",
      #   "Opsi":   "name",
      #   "WMI":    "Name",
      #   "Linux":  "model"
      #},
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     NETWORK_CONTROLLER                                              -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "CONTROLLER" ],
      "Opsi":   "NETWORK_CONTROLLER",
      # not supported by win2k # "WMI":    "select * from Win32_NetworkAdapter where NetConnectionID <> NULL",
      # where Win32_NetworkAdapter.IPenabled=True
      "WMI":    "Select * from Win32_NetworkAdapter&Win32_NetworkAdapterSetting",
      "Linux":  "[lshw]network|bridge:^bridge:description.find('interface') != -1"
   },
   "Values": [
      {
         "Type":   "varchar(40)",
         "Scope":  "g",
         "Opsi":   "adapterType",
         "WMI":    "AdapterType",
         "Linux":  "configuration/port"
      },
      {
         "Type":   "int",
         "Scope":  "g",
         "Opsi":   "maxSpeed",
         "WMI":    "MaxSpeed",
         "Linux":  "capacity",
         "Unit":   "Bit/s"
      },
      {
         "Type":   "varchar(20)",
         "Scope":  "i",
         "Opsi":   "macAddress",
         "Linux":  "serial",
         "WMI":    "MACAddress"
      },
      {
         "Type":   "varchar(20)",
         "Scope":  "i",
         "Opsi":   "netConnectionStatus",
         "Linux":  "configuration/link",
         "WMI":    "NetConnectionStatus"
      },
      {
         "Type":   "varchar(20)",
         "Scope":  "g",
         "Opsi":   "autoSense",
         "Linux":  "configuration/autonegotiation",
         "WMI":    "AutoSense"
      },
      {
         "Type":   "varchar(60)",
         "Scope":  "i",
         "Opsi":   "ipEnabled",
         "WMI":    "IPEnabled",
         "Linux":  ""
      },
      {
         "Type":   "varchar(60)",
         "Scope":  "i",
         "Opsi":   "ipAddress",
         "WMI":    "IPAddress",
         "Linux":  "configuration/ip"
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     AUDIO_CONTROLLER                                                  -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "CONTROLLER" ],
      "Opsi":   "AUDIO_CONTROLLER",
      "WMI":    "select * from Win32_SoundDevice",
      "Linux":  "[lshw]multimedia"
   },
   "Values": [
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     HDAUDIO_DEVICE                                                  -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "BASIC_INFO", "DEVICE_ID" ],
      "Opsi":   "HDAUDIO_DEVICE",
      "WMI":    "",
      "Linux":  "[hdaudio]"
   },
   "Values": [
      {
         "Type":   "varchar(100)",
         "Scope":  "g",
         "Opsi":   "name",
         "WMI":    "",
         "Linux":  "codec"
      },
      {
         "Type":   "varchar(10)",
         "Scope":  "g",
         "Opsi":   "address",
         "WMI":    "",
         "Linux":  "address"
      },
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     IDE_CONTROLLER                                                  -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "CONTROLLER" ],
      "Opsi":   "IDE_CONTROLLER",
      "WMI":    "select * from Win32_IdeController",
      "Linux":  "[lshw]storage:^ide"
   },
   "Values": [
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     SCSI_CONTROLLER                                                 -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "CONTROLLER" ],
      "Opsi":   "SCSI_CONTROLLER",
      "WMI":    "select * from Win32_ScsiController",
      "Linux":  "[lshw]storage:^scsi"
   },
   "Values": [
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     FLOPPY_CONTROLLER                                               -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "CONTROLLER" ],
      "Opsi":   "FLOPPY_CONTROLLER",
      "WMI":    "select * from Win32_FloppyController"
   },
   "Values": [
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     USB_CONTROLLER                                                  -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "CONTROLLER" ],
      "Opsi":   "USB_CONTROLLER",
      "WMI":    "select * from Win32_UsbController",
      "Linux":  "[lshw]bus:^usb"
   },
   "Values": [
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     1394_CONTROLLER                                                 -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "CONTROLLER" ],
      "Opsi":   "1394_CONTROLLER",
      "WMI":    "select * from Win32_1394Controller",
      "Linux":  "[lshw]bus:^firewire"
   },
   "Values": [
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     PCMCIA_CONTROLLER                                               -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "CONTROLLER" ],
      "Opsi":   "PCMCIA_CONTROLLER",
      "WMI":    "select * from Win32_PCMCIAController",
      "Linux":  "[lshw]bus:^pcmcia"
   },
   "Values": [
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     VIDEO_CONTROLLER                                                -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "CONTROLLER" ],
      "Opsi":   "VIDEO_CONTROLLER",
      "WMI":    "select * from Win32_VideoController",
      "Linux":  "[lshw]display"
   },
   "Values": [
     {
         "Type":   "varchar(20)",
         "Scope":  "g",
         "Opsi":   "videoProcessor",
         "WMI":    "VideoProcessor"
     },
     {
         "Type":   "bigint",
         "Scope":  "g",
         "Opsi":   "adapterRAM",
         "WMI":    "AdapterRAM",
         "Linux":  "size",
         "Unit":   "Byte"
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     DRIVE                                                           -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "ABSTARCT",
      "Super":  [ "HARDWARE_DEVICE" ],
      "Opsi":   "DRIVE"
   },
   "Values": [
      {
         "Type":   "bigint",
         "Scope":  "i",
         "Opsi":   "size",
         "WMI":    "Size",
         "Linux":  "size",
         "Unit":   "Byte"
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     FLOPPY_DRIVE                                                    -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "DRIVE" ],
      "Opsi":   "FLOPPY_DRIVE",
      "WMI":    "select * from Win32_FloppyDrive"
   },
   "Values": [
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     TAPE_DRIVE                                                      -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "DRIVE" ],
      "Opsi":   "TAPE_DRIVE",
      "WMI":    "select * from Win32_TapeDrive"
   },
   "Values": [
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     HARDDISK_DRIVE                                                  -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "DRIVE" ],
      "Opsi":   "HARDDISK_DRIVE",
      "WMI":    "select * from Win32_DiskDrive&Win32_DiskDrivePhysicalMedia",
      "Linux":  "[lshw]disk:^disk"
   },
   "Values": [
      {
         "Type":   "varchar(100)",
         "Scope":  "g",
         "Opsi":   "name",
         "Linux":  "product",
         "WMI":    "Model"
      },
      {
         "Type":   "int",
         "Scope":  "g",
         "Opsi":   "cylinders",
         "WMI":    "TotalCylinders"
      },
      {
         "Type":   "int",
         "Scope":  "g",
         "Opsi":   "heads",
         "WMI":    "TotalHeads"
      },
      {
         "Type":   "bigint",
         "Scope":  "g",
         "Opsi":   "sectors",
         "WMI":    "TotalSectors"
      },
      {
         "Type":   "tinyint",
         "Scope":  "i",
         "Opsi":   "partitions",
         "WMI":    "Partitions"
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     DISK_PARITION                                                   -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "BASIC_INFO" ],
      "Opsi":   "DISK_PARTITION",
      "WMI":    "select * from Win32_DiskPartition&Win32_LogicalDiskToPartition",
      "Linux":  "[lshw]volume:^volume"
   },
   "Values": [
      {
         "Type":   "varchar(50)",
         "Scope":  "g",
         "Opsi":   "name",
         "WMI":    "Name",
         "Linux":  "logicalname"
      },
      {
         "Type":   "bigint",
         "Scope":  "i",
         "Opsi":   "size",
         "WMI":    "Size", # DiskPartition
         "Linux":  "capacity",
         "Unit":   "Byte"
      },
      {
         "Type":   "bigint",
         "Scope":  "i",
         "Opsi":   "startingOffset",
         "WMI":    "StartingOffset" # DiskPartition
      },
      {
         "Type":   "int",
         "Scope":  "i",
         "Opsi":   "index",
         "Linux":  "businfo.split(',', 1)[1]",
         "WMI":    "Index" # DiskPartition
      },
      {
         "Type":   "varchar(50)",
         "Scope":  "i",
         "Opsi":   "filesystem",
         "Linux":  "description.replace('partition', '')",
         "WMI":    "LogicalDisk::FileSystem"
      },
      {
         "Type":   "bigint",
         "Scope":  "i",
         "Opsi":   "freeSpace",
         "WMI":    "LogicalDisk::FreeSpace",
         "Unit":   "Byte"
      },
      {
         "Type":   "varchar(2)",
         "Scope":  "i",
         "Opsi":   "driveLetter",
         "WMI":    "LogicalDisk::Caption"
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     OPTICAL_DRIVE                                                   -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "DRIVE" ],
      "Opsi":   "OPTICAL_DRIVE",
      "WMI":    "select * from Win32_CDROMDrive",
      "Linux":  "[lshw]disk:^cdrom"
   },
   "Values": [
     {
         "Type":   "varchar(2)",
         "Scope":  "i",
         "Opsi":   "driveLetter",
         "WMI":    "Drive"
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     USB_DEVICE                                                      -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "HARDWARE_DEVICE" ],
      "Opsi":   "USB_DEVICE",
      "WMI":    "select * from Win32_PNPEntity where DeviceID like 'USB\\%'",
      "Linux":  "[lsusb]"
   },
   "Values": [
      {
         "Type":   "varchar(50)",
         "Scope":  "g",
         "Opsi":   "vendor",
         "WMI":    "Manufacturer",
         "Linux":  "device/idVendor.split(' ', 1)[1]"
      },
      {
         "Type":   "varchar(100)",
         "Scope":  "g",
         "Opsi":   "model",
         "WMI":    "Caption",
         "Linux":  "device/iProduct.split(' ', 1)[1]"
      },
      {
         "Type":   "varchar(100)",
         "Scope":  "g",
         "Opsi":   "name",
         "WMI":    "Caption",
         "Linux":  "device/iProduct.split(' ', 1)[1]"
      },
      {
         "Type":   "varchar(4)",
         "Scope":  "g",
         "Opsi":   "vendorId",
         "WMI":    "PNPDeviceID.split('VID_')[1][0:4]",
         "Linux":  "device/idVendor.split()[0].split('x')[1]"
      },
      {
         "Type":   "varchar(4)",
         "Scope":  "g",
         "Opsi":   "deviceId",
         "WMI":    "PNPDeviceID.split('PID_')[1][0:4]",
         "Linux":  "device/idProduct.split()[0].split('x')[1]"
      },
      {
         "Type":   "varchar(8)",
         "Scope":  "g",
         "Opsi":   "usbRelease",
         "Linux":  "device/bcdUSB"
      },
      {
         "Type":   "int",
         "Scope":  "g",
         "Opsi":   "maxPower",
         "Linux":  "configuration/MaxPower.split('m')[0]",
         "Unit":   "mA"
      },
      {
         "Type":   "varchar(500)",
         "Scope":  "g",
         "Opsi":   "interfaceClass",
         "WMI":    "Service",
         "Linux":  "interface/bInterfaceClass.split(' ', 1)[1]"
      },
      {
         "Type":   "varchar(500)",
         "Scope":  "g",
         "Opsi":   "interfaceSubClass",
         "Linux":  "interface/bInterfaceSubClass.split(' ', 1)[1]"
      },
      {
         "Type":   "varchar(200)",
         "Scope":  "g",
         "Opsi":   "interfaceProtocol",
         "Linux":  "interface/bInterfaceProtocol.split(' ', 1)[1]"
      },
      {
         "Type":   "varchar(200)",
         "Scope":  "g",
         "Opsi":   "status",
         "WMI":    "Status",
         "Linux":  "status.partition(',')[2].strip()"
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     MONITOR                                                         -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "HARDWARE_DEVICE" ],
      "Opsi":   "MONITOR",
      "WMI":    "select * from Win32_DesktopMonitor"
   },
   "Values": [
      {
         "Type":   "varchar(50)",
         "Scope":  "g",
         "Opsi":   "vendor",
         "WMI":    "MonitorManufacturer"
      },
      {
         "Type":   "int",
         "Scope":  "i",
         "Opsi":   "screenWidth",
         "WMI":    "ScreenWidth"
      },
      {
         "Type":   "int",
         "Scope":  "i",
         "Opsi":   "screenHeight",
         "WMI":    "ScreenHeight"
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     KEYBOARD                                                        -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "HARDWARE_DEVICE" ],
      "Opsi":   "KEYBOARD",
      "WMI":    "select * from Win32_Keyboard"
   },
   "Values": [
      {
         "Type":   "int",
         "Scope":  "g",
         "Opsi":   "numberOfFunctionKeys",
         "WMI":    "NumberOfFunctionKeys"
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     POINTING_DEVICE                                                 -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "HARDWARE_DEVICE" ],
      "Opsi":   "POINTING_DEVICE",
      "WMI":    "select * from Win32_PointingDevice"
   },
   "Values": [
      {
         "Type":   "tinyint",
         "Scope":  "g",
         "Opsi":   "numberOfButtons",
         "WMI":    "NumberOfButtons"
      }
   ]
},

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -     PRINTER                                                         -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{
   "Class": {
      "Type":   "STRUCTURAL",
      "Super":  [ "HARDWARE_DEVICE" ],
      "Opsi":   "PRINTER",
      "WMI":    "select * from Win32_Printer"
   },
   "Values": [
      {
         "Type":   "int",
         "Scope":  "g",
         "Opsi":   "horizontalResolution",
         "WMI":    "HorizontalResolution",
         "Unit":    "dpi"
      },
      {
         "Type":   "int",
         "Scope":  "g",
         "Opsi":   "verticalResolution",
         "WMI":    "VerticalResolution",
         "Unit":   "dpi"
      },
      {
         "Type":   "varchar(200)",
         "Scope":  "g",
         "Opsi":   "capabilities",
         "WMI":    "Capabilities"
      },
      {
         "Type":   "varchar(200)",
         "Scope":  "g",
         "Opsi":   "paperSizesSupported",
         "WMI":    "PaperSizesSupported"
      },
      {
         "Type":   "varchar(100)",
         "Scope":  "i",
         "Opsi":   "driverName",
         "WMI":    "DriverName"
      },
      {
         "Type":   "varchar(20)",
         "Scope":  "i",
         "Opsi":   "port",
         "WMI":    "PortName"
      }
   ]
}

]

"""

	name = "opsihwaudit.conf"
	
	def setUp(self):
		super(HwAuditConfigFixture, self).setUp()
		
		data = {}
		exec self.template in data, data
		
		self.config = data["OPSI_HARDWARE_CLASSES"]
		
		self._write(self.template)
		
		
class OpsiHostKeyFileFixture(ConfigFixture):
	
	template = ""
	name = "pckey"

	def addHostKey(self, hostId, hostkey):
		pass
