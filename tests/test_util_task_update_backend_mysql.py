#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2016 uib GmbH <info@uib.de>

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
Testing the update of the MySQL backend from an older version.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os

from contextlib import contextmanager

from OPSI.Backend.MySQL import MySQL
from OPSI.Util.Task.UpdateBackend.MySQL import (disableForeignKeyChecks,
    getTableColumns, updateMySQLBackend)
from OPSI.Util.Task.ConfigureBackend import updateConfigFile

from .Backends.MySQL import MySQLconfiguration
from .helpers import workInTemporaryDirectory

import pytest


@contextmanager
def cleanDatabase(database):
    def cleanDatabase():
        with disableForeignKeyChecks(database):
            for tableName in getTableNames(database):
                try:
                    database.execute(u'DROP TABLE `{0}`;'.format(tableName))
                except Exception as error:
                    print("Failed to drop {0}: {1}".format(tableName, error))

    cleanDatabase()
    try:
        yield database
    finally:
        cleanDatabase()


@pytest.fixture
def mysqlBackendConfig():
    if not MySQLconfiguration:
        pytest.skip("Missing configuration for MySQL.")

    return MySQLconfiguration


@pytest.fixture
def mySQLBackendConfigFile(mysqlBackendConfig):
    with workInTemporaryDirectory() as tempDir:
        configFile = os.path.join(tempDir, 'asdf')
        with open(configFile, 'w'):
            pass

        updateConfigFile(configFile, mysqlBackendConfig)

        yield configFile


def testCorrectingLicenseOnClientLicenseKeyLength(mysqlBackendConfig, mySQLBackendConfigFile):
    """
    Test if the license key length is correctly set.

    An backend updated from an older version has the field 'licenseKey'
    on the LICENSE_ON_CLIENT table as VARCHAR(100).
    A fresh backend has the length of 1024.
    The size should be the same.
    """
    with cleanDatabase(MySQL(**mysqlBackendConfig)) as db:
        createRequiredTables(db)

        updateMySQLBackend(backendConfigFile=mySQLBackendConfigFile)

        for tableName in ('LICENSE_ON_CLIENT', 'SOFTWARE_CONFIG', 'SOFTWARE_LICENSE_TO_LICENSE_POOL'):
            print("Checking {0}...".format(tableName))

            assert tableName in getTableNames(db)

            assertColumnIsVarchar(db, tableName, 'licenseKey', 1024)


def testCorrectingProductIdLength(mysqlBackendConfig, mySQLBackendConfigFile):
    """
    Test if the product id length is correctly set.
    """
    with cleanDatabase(MySQL(**mysqlBackendConfig)) as db:
        createRequiredTables(db)

        updateMySQLBackend(backendConfigFile=mySQLBackendConfigFile)

        for tableName in ('PRODUCT_PROPERTY', ):
            print("Checking {0}...".format(tableName))

            assert tableName in getTableNames(db)

            assertColumnIsVarchar(db, tableName, 'productId', 255)


def createRequiredTables(database):
    table = u'''CREATE TABLE `LICENSE_POOL` (
            `licensePoolId` VARCHAR(100) NOT NULL,
            `type` varchar(30) NOT NULL,
            `description` varchar(200),
            PRIMARY KEY (`licensePoolId`)
        ) %s;
        ''' % database.getTableCreationOptions('LICENSE_POOL')
    database.execute(table)
    database.execute('CREATE INDEX `index_license_pool_type` on `LICENSE_POOL` (`type`);')

    table = u'''CREATE TABLE `LICENSE_CONTRACT` (
            `licenseContractId` VARCHAR(100) NOT NULL,
            `type` varchar(30) NOT NULL,
            `description` varchar(100),
            `notes` varchar(1000),
            `partner` varchar(100),
            `conclusionDate` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
            `notificationDate` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
            `expirationDate` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
            PRIMARY KEY (`licenseContractId`)
        ) %s;
        ''' % database.getTableCreationOptions('LICENSE_CONTRACT')
    database.execute(table)
    database.execute('CREATE INDEX `index_license_contract_type` on `LICENSE_CONTRACT` (`type`);')

    table = u'''CREATE TABLE `SOFTWARE_LICENSE` (
            `softwareLicenseId` VARCHAR(100) NOT NULL,
            `licenseContractId` VARCHAR(100) NOT NULL,
            `type` varchar(30) NOT NULL,
            `boundToHost` varchar(255),
            `maxInstallations` integer,
            `expirationDate` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
            PRIMARY KEY (`softwareLicenseId`),
            FOREIGN KEY (`licenseContractId`) REFERENCES `LICENSE_CONTRACT` (`licenseContractId`)
        ) %s;
        ''' % database.getTableCreationOptions('SOFTWARE_LICENSE')
    database.execute(table)
    database.execute('CREATE INDEX `index_software_license_type` on `SOFTWARE_LICENSE` (`type`);')
    database.execute('CREATE INDEX `index_software_license_boundToHost` on `SOFTWARE_LICENSE` (`boundToHost`);')

    database.execute("""CREATE TABLE `PRODUCT_PROPERTY` (
        `productId` varchar(128) NOT NULL,
        `productVersion` varchar(32) NOT NULL,
        `packageVersion` varchar(16) NOT NULL,
        `propertyId` varchar(200) NOT NULL,
        `type` varchar(30) NOT NULL,
        `description` TEXT,
        `multiValue` bool NOT NULL,
        `editable` bool NOT NULL,
        PRIMARY KEY (`productId`, `productVersion`, `packageVersion`, `propertyId`)
    ) ENGINE=InnoDB DEFAULT CHARSET utf8 COLLATE utf8_general_ci """)

    database.execute("""CREATE TABLE `BOOT_CONFIGURATION` (
        `name` varchar(64) NOT NULL,
        `clientId` varchar(255) NOT NULL,
        `priority` integer DEFAULT 0,
        `description` TEXT,
        `netbootProductId` varchar(255),
        `pxeTemplate` varchar(255),
        `options` varchar(255),
        `disk` integer,
        `partition` integer,
        `active` bool,
        `deleteAfter` integer,
        `deactivateAfter` integer,
        `accessCount` integer,
        `osName` varchar(128),
        PRIMARY KEY (`name`, `clientId`)
    ) ENGINE=InnoDB DEFAULT CHARSET utf8 COLLATE utf8_general_ci """)

    database.execute(u'''CREATE TABLE `SOFTWARE_LICENSE_TO_LICENSE_POOL` (
        `softwareLicenseId` VARCHAR(100) NOT NULL,
        `licensePoolId` VARCHAR(100) NOT NULL,
        `licenseKey` VARCHAR(100),
        PRIMARY KEY (`softwareLicenseId`, `licensePoolId`),
        FOREIGN KEY (`softwareLicenseId`) REFERENCES `SOFTWARE_LICENSE` (`softwareLicenseId`),
        FOREIGN KEY (`licensePoolId`) REFERENCES `LICENSE_POOL` (`licensePoolId`)
    ) %s;''' % database.getTableCreationOptions('SOFTWARE_LICENSE_TO_LICENSE_POOL'))

    database.execute("""CREATE TABLE `LICENSE_USED_BY_HOST` (
        `softwareLicenseId` VARCHAR(100) NOT NULL,
        `licensePoolId` VARCHAR(100) NOT NULL,
        `hostId` varchar(255),
        `licenseKey` VARCHAR(100),
        `notes` VARCHAR(1024)
    ) ENGINE=InnoDB DEFAULT CHARSET utf8 COLLATE utf8_general_ci """)

    database.execute(u'''CREATE TABLE `SOFTWARE_CONFIG` (
        `config_id` integer NOT NULL AUTO_INCREMENT,
        `clientId` varchar(255) NOT NULL,
        `name` varchar(100) NOT NULL,
        `version` varchar(100) NOT NULL,
        `subVersion` varchar(100) NOT NULL,
        `language` varchar(10) NOT NULL,
        `architecture` varchar(3) NOT NULL,
        `uninstallString` varchar(200),
        `binaryName` varchar(100),
        `firstseen` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
        `lastseen` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
        `state` TINYINT NOT NULL,
        `usageFrequency` integer NOT NULL DEFAULT -1,
        `lastUsed` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
        `licenseKey` VARCHAR(100),
        PRIMARY KEY (`config_id`)
    ) %s;
    ''' % database.getTableCreationOptions('SOFTWARE_CONFIG'))


def getTableNames(database):
    return set(i.values()[0] for i in database.getSet(u'SHOW TABLES;'))


def assertColumnIsVarchar(database, tableName, columnName, length):
    for column in getTableColumns(database, tableName):
        if column.name.lower() == columnName.lower():
            assert column.type.lower().startswith('varchar(')

            _, currentLength = column.type.split('(')
            currentLength = int(currentLength[:-1])

            assert currentLength == length
            break
    else:
        raise ValueError("Missing column '{1}' in table {0!r}".format(tableName, columnName))
