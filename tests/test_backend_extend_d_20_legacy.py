#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2017 uib GmbH <info@uib.de>

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
Tests for the dynamically loaded legacy extensions.

This tests what usually is found under
``/etc/opsi/backendManager/extend.de/20_legacy.conf``.

The legacy extensions are to maintain backwards compatibility for scripts
that were written for opsi 3.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import pytest

from OPSI.Object import LocalbootProduct, ProductDependency, ProductOnDepot
from .test_hosts import getDepotServers


def testGetGeneralConfigValueFailsWithInvalidObjectId(backendManager):
    with pytest.raises(ValueError):
        backendManager.getGeneralConfig_hash('foo')


def testGetGeneralConfig(backendManager):
    """
    Calling the function with some valid FQDN must not fail.
    """
    values = backendManager.getGeneralConfig_hash('some.client.fqdn')
    print(values)


def testSetGeneralConfigValue(backendManager):
    backendManager.host_createOpsiClient('some.client.fqdn')  # required by File-backend
    backendManager.setGeneralConfigValue('foo', 'bar', 'some.client.fqdn')

    assert 'bar' == backendManager.getGeneralConfigValue('foo', 'some.client.fqdn')


def testGetDomainShouldWork(backendManager):
    assert backendManager.getDomain()


@pytest.mark.parametrize("value", [None, ""])
def testGetGeneralConfigValueWithoutConfigReturnsNoValue(backendManager, value):
    assert backendManager.getGeneralConfigValue(value) is None


def testGetGeneralConfigIsEmptyAfterStart(backendManager):
    assert {} == backendManager.getGeneralConfig_hash()


@pytest.mark.parametrize("value", [
    {"test": True},
    {"test": 1},
    {"test": None}
])
def testSetGeneralConfigIsUnabledToHandleNonTextValues(backendManager, value):
    with pytest.raises(Exception):
        backendManager.setGeneralConfig(value)


def testSetGeneralConfigValueAndReadValues(backendManager):
    config = {"test.truth": "True", "test.int": "2"}
    backendManager.setGeneralConfig(config)

    for key, value in config.items():
        assert value == backendManager.getGeneralConfigValue(key)

    assert {} != backendManager.getGeneralConfig_hash()
    assert 2 == len(backendManager.getGeneralConfig_hash())


@pytest.mark.parametrize("value, expected", [
    ('yes', "True"),
    ('on', "True"),
    ('1', "True"),
    ('true', "True"),
    ('no', "False"),
    ('off', "False"),
    ('0', "False"),
    ('false', "False"),
    ("noconversion", "noconversion")
])
def testSetGeneralConfigValueTypeConversion(backendManager, value, expected):
    backendManager.setGeneralConfig({"bool": value})
    assert expected == backendManager.getGeneralConfigValue("bool")


def testSetGeneralConfigIsAbleToRemovingMissingValue(backendManager):
    config = {"test.truth": "True", "test.int": "2"}
    backendManager.setGeneralConfig(config)
    assert 2 == len(backendManager.getGeneralConfig_hash())

    del config["test.int"]
    backendManager.setGeneralConfig(config)
    assert 1 == len(backendManager.getGeneralConfig_hash())


def generateLargeConfig(numberOfConfigs):
    numberOfConfigs = 50  # len(config) will be double

    config = {}
    for value in range(numberOfConfigs):
        config["bool.{0}".format(value)] = str(value % 2 == 0)
        config["normal.{0}".format(value)] = "norm-{0}".format(value)

    assert numberOfConfigs * 2 == len(config)

    return config


@pytest.mark.parametrize("config",
    [generateLargeConfig(50), generateLargeConfig(250)],
    ids=['50', '250']
)
def testMassFilling(backendManager, config):
    backendManager.setGeneralConfig(config)

    assert config == backendManager.getGeneralConfig_hash()


def testDeleteProductDependency(backendManager):
    firstProduct = LocalbootProduct('prod', '1.0', '1.0')
    secondProduct = LocalbootProduct('dependency', '1.0', '1.0')
    backendManager.product_insertObject(firstProduct)
    backendManager.product_insertObject(secondProduct)

    prodDependency = ProductDependency(
        productId=firstProduct.id,
        productVersion=firstProduct.productVersion,
        packageVersion=firstProduct.packageVersion,
        productAction='setup',
        requiredProductId=secondProduct.id,
        requiredAction='setup',
        requirementType='after'
    )
    backendManager.productDependency_insertObject(prodDependency)

    depots = getDepotServers()
    depot = depots[0]
    backendManager.host_insertObject(depot)

    productOnDepot = ProductOnDepot(
        productId=firstProduct.getId(),
        productType=firstProduct.getType(),
        productVersion=firstProduct.getProductVersion(),
        packageVersion=firstProduct.getPackageVersion(),
        depotId=depot.id,
        locked=False
    )
    backendManager.productOnDepot_createObjects([productOnDepot])

    assert backendManager.productDependency_getObjects()

    backendManager.deleteProductDependency(firstProduct.id, "", secondProduct.id, requiredProductClassId="unusedParam", requirementType="unused")

    assert not backendManager.productDependency_getObjects()
