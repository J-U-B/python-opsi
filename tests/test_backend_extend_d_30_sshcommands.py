#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2017 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Testing CRUD Methods for sshcommands (read from / write to jsonfile).

:author: Anna Sucher <a.sucher@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import json
import unittest
import pytest
from contextlib import contextmanager

from .Backends.File import FileBackendBackendManagerMixin
from .helpers import workInTemporaryDirectory, mock


@contextmanager
def workWithEmptyCommandFile(backend):
	with workInTemporaryDirectory():
		filename = u'test_file.conf'
		with open(filename, "w"):
			pass
		with mock.patch.object(backend, '_getSSHCommandCustomFilename', return_value=filename):
			with mock.patch.object(backend, '_getSSHCommandFilenames', return_value=[filename]):
				with mock.patch.object(backend, '_isBuiltIn', return_value=False):
					yield


@contextmanager
def workWithBrokenCommandFile(backend):
	with workInTemporaryDirectory():
		filename = u'test_file.conf'
		element = {
			"id": "rechte_setzen",
			"menuText : Rechte setzen": "",  # <-- This is broken
			"commands": ["opsi-set-rights"],
			"position": 30,
			"needSudo": True,
			"tooltipText": "Rechte mittels opsi-set-rights setzen",
			"parentMenuText": "opsi"
		}

		with open(filename, "w") as f:
			json.dump(element, f)

		with mock.patch.object(backend, '_getSSHCommandCustomFilename', return_value=filename):
			with mock.patch.object(backend, '_getSSHCommandFilenames', return_value=[filename]):
				with mock.patch.object(backend, '_isBuiltIn', return_value=False):
					yield


def getTestCommands():
	(com1, com1_full) = getTestCommand(u'utestmenu1', u'UTestMenu1', [u'test 1'], 5, True,  u'Test Tooltip1', u'Test Parent1')
	(com2, com2_full) = getTestCommand(u'utestmenu2', u'UTestMenu2', [u'test 2'], 52, True,  u'Test Tooltip2', u'Test Parent2')
	(com3, com3_full) = getTestCommand(u'utestmenu3', u'UTestMenu3', [u'test 3'], 53, True,  u'Test Tooltip3', u'Test Parent3')
	return (com1, com1_full), (com2, com2_full), (com3, com3_full)


def getTestCommand(mid, menuText, commands, position, needSudo, tooltipText, parentMenuText):
	thisid = mid
	thismenuText = menuText
	thiscommands = commands
	thisposition = position
	thisneedSudo = needSudo
	thistooltipText = tooltipText
	thisparentMenuText = parentMenuText
	this = {
		u'menuText': thismenuText,
		u'commands': thiscommands
	}
	thisfull = {
		u'id': thisid,
		u'menuText': thismenuText,
		u'commands': thiscommands,
		u'needSudo': thisneedSudo,
		u'position': thisposition,
		u'tooltipText': thistooltipText,
		u'parentMenuText': thisparentMenuText
	}
	return (this, thisfull)


def getTestOneCommand(mid, menuText, commands, position, needSudo, tooltipText, parentMenuText):
	(_, thisfull) = getTestCommand(mid, menuText, commands, position, needSudo, tooltipText, parentMenuText)
	return thisfull


def getTestCommandWithDefault(existingcom):
	com = {
		u'needSudo': False,
		u'position': 0,
		u'tooltipText': u'',
		u'parentMenuText': None
	}

	com[u'id'] = existingcom["id"]
	com[u'menuText'] = existingcom[u'menuText']
	com[u'commands'] = existingcom[u'commands']
	return com


def getSSHCommandCreationParameter():
	(com1_min, com1_full), (com2_min, com2_full), (com3_min, com3_full) = getTestCommands()
	return [
		[[com1_min], [getTestCommandWithDefault(com1_full)]],
		[[com1_min, com2_min], [getTestCommandWithDefault(com1_full), getTestCommandWithDefault(com2_full)]],
		[[com1_min, com2_min, com3_min], [getTestCommandWithDefault(com1_full), getTestCommandWithDefault(com2_full), getTestCommandWithDefault(com1_full)]],
	]


@pytest.mark.parametrize("val,expected_result", getSSHCommandCreationParameter())
def testSSHCommandCreations(backendManager, val, expected_result):
	with workWithEmptyCommandFile(backendManager._backend):
		assert backendManager.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
		result = backendManager.SSHCommand_createObjects(val)
		compareLists(result, expected_result)


@pytest.mark.parametrize("val,expected_result", getSSHCommandCreationParameter())
def testSSHCommandCreation(backendManager, val, expected_result):
	with workWithEmptyCommandFile(backendManager._backend):
		assert backendManager.SSHCommand_getObjects() == [], "first return of SSHCommand_getObjects should be an empty list"
		for x in range(0, len(val)):
			command = val[x]
			result = backendManager.SSHCommand_createObject(
				command.get("menuText"),
				command.get("commands"),
				command.get("position"),
				command.get("needSudo"),
				command.get("tooltipText"),
				command.get("parentMenuText")
			)
		compareLists(result, expected_result)


def compareLists(list1, list2):
	assert len(list1) == len(list2)
	for dictcom in list2:
		assert dictcom in list1
	for dictcom in list2:
		my_item = next((item for item in list1 if item["menuText"] == dictcom["menuText"]), None)
		assert dictcom["menuText"] == my_item["menuText"]
		assert dictcom["id"] == my_item["id"]
		assert dictcom["commands"] == my_item["commands"]
		assert dictcom["position"] == my_item["position"]
		assert dictcom["needSudo"] == my_item["needSudo"]
		assert dictcom["tooltipText"] == my_item["tooltipText"]
		assert dictcom["parentMenuText"] == my_item["parentMenuText"]


def getSSHCommandCreationExceptionsParameter():
	return [
		[getTestOneCommand(None, None, None, 10, True, u'', None)],
		[getTestOneCommand(None, u'TestMenuText1', {}, 10, True, u'', None)],
		[getTestOneCommand(None, u'TestMenuText2', [], u'', True, u'', None)],
		[getTestOneCommand(None, u'TestMenuText3', [], u'10', u'True', u'', None)],
		[getTestOneCommand(None, u'TestMenuText4', [u'foo'], 10, u'True', u'', None)],
		[getTestOneCommand(None, u'TestMenuText5', [u'foo'], 10, u'True', u'', None)]
	]


@pytest.mark.parametrize("commandlist", getSSHCommandCreationExceptionsParameter())
def testSSHCommandCreationExceptions(backendManager,  commandlist):
	with workWithEmptyCommandFile(backendManager._backend):
		with pytest.raises(Exception):
			if len(commandlist) <= 1:
				command = commandlist[0]
				backendManager.SSHCommand_createObject(
					command.get("menuText"),
					command.get("commands"),
					command.get("position"),
					command.get("needSudo"),
					command.get("tooltipText"),
					command.get("parentMenuText")
				)
			backendManager.SSHCommand_createObjects(commandlist)


def getSSHCommandUpdateExceptionsParameter():
	return [
		[getTestOneCommand(None, None, None, 10, True, u'', None)],
		[getTestOneCommand(None, u'TestMenuText1', {}, 10, True, u'', None)],
		[getTestOneCommand(None, u'TestMenuText2', [], u'10', u'True', u'', None)],
		[getTestOneCommand(None, u'TestMenuText3', [u'foo'], 10, u'True', u'', None)]
	]


@pytest.mark.parametrize("commandlist", getSSHCommandCreationExceptionsParameter())
def testSSHCommandUpdateExceptions(backendManager,  commandlist):
	with workWithEmptyCommandFile(backendManager._backend):
		with pytest.raises(Exception):
			if len(commandlist) <= 1:
				command = commandlist[0]
				backendManager.SSHCommand_updateObject(
					command.get("menuText", None),
					command.get("commands", None),
					command.get("position", None),
					command.get("needSudo", None),
					command.get("tooltipText", None),
					command.get("parentMenuText", None)
				)
			backendManager.SSHCommand_updateObjects(commandlist)


class SSHCommandsTestCase(unittest.TestCase, FileBackendBackendManagerMixin):
	"""
	Testing the crud methods for json commands .
	"""

	def setUp(self):
		self.maxDiff = None
		self.setUpBackend()

		(self.com1_min, self.com1_full), (self.com2_min, self.com2_full), (self.com3_min, self.com3_full) = getTestCommands()
		self.com1_withDefaults = getTestCommandWithDefault(self.com1_full)
		self.com2_withDefaults = getTestCommandWithDefault(self.com2_full)
		self.com3_withDefaults = getTestCommandWithDefault(self.com3_full)
		(self.com_withFailures_min, self.com_withFailures) = getTestCommand(u'utestmenu1', 20, u'test 1', u'O', u'Nein', False, False)

	def tearDown(self):
		self.tearDownBackend()

	def testExceptionGetCommand(self):
		with workWithBrokenCommandFile(self.backend._backend):
			self.assertRaises(Exception, self.backend.SSHCommand_deleteObjects)

	def testGetCommand(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			result = self.backend.SSHCommand_createObjects([self.com1_min])
			compareLists(result, [self.com1_withDefaults])

	def setNewSSHCommand(self, c, com, p, ns, ttt, pmt):
		c["commands"] = com
		c["position"] = p
		c["needSudo"] = ns
		c["tooltipText"] = ttt
		c["parentMenuText"] = pmt
		return c

	def testUpdateCommand(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.backend.SSHCommand_createObject(self.com1_full["menuText"], self.com1_full["commands"])
			com1_new_full = self.com1_full
			com1_new_full = self.setNewSSHCommand(com1_new_full, [u'MyNewTestCom'], 10, True, u'MyNewTooltipText', u'myParent')
			return_command = self.backend.SSHCommand_updateObject(
				self.com1_full["menuText"],
				com1_new_full["commands"],
				com1_new_full["position"],
				com1_new_full["needSudo"],
				com1_new_full["tooltipText"],
				com1_new_full["parentMenuText"]
			)

			compareLists(return_command, [com1_new_full])

	def testUpdateCommands(self):
		with workWithEmptyCommandFile(self.backend._backend):
			com123_new_full = [self.com1_full, self.com2_full, self.com3_full]
			com123_new_full[0] = self.setNewSSHCommand(com123_new_full[0], [u'MyNewTestCom1'], 11, True, u'MyNewTooltipText1', u'myParent1')
			com123_new_full[1] = self.setNewSSHCommand(com123_new_full[1], [u'MyNewTestCom2'], 12, False, u'MyNewTooltipText2', u'myParent2')
			com123_new_full[2] = self.setNewSSHCommand(com123_new_full[2], [u'MyNewTestCom3'], 13, False, u'MyNewTooltipText3', u'myParent3')
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.backend.SSHCommand_createObjects([self.com1_min, self.com2_min])
			return_command = self.backend.SSHCommand_updateObjects(com123_new_full)
			compareLists(return_command, com123_new_full)

	def testDeleteCommand(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.backend.SSHCommand_createObjects([self.com1_min, self.com2_min])
			compareLists(self.backend.SSHCommand_deleteObject(self.com2_min["menuText"]), [self.com1_withDefaults])

	def testDeleteCommands(self):
		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.backend.SSHCommand_createObjects([self.com1_min, self.com2_min, self.com3_min])
			compareLists(self.backend.SSHCommand_deleteObjects([self.com1_min["menuText"], self.com2_min["menuText"], self.com3_min["menuText"]]), [])

		with workWithEmptyCommandFile(self.backend._backend):
			self.assertEqual(self.backend.SSHCommand_getObjects(), [], "first return of SSHCommand_getObjects should be an empty list")
			self.backend.SSHCommand_createObjects([self.com1_min, self.com2_min, self.com3_min])
			compareLists(self.backend.SSHCommand_deleteObjects([self.com1_min["menuText"], self.com2_min["menuText"]]), [self.com3_withDefaults])


if __name__ == '__main__':
	unittest.main()