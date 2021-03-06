#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2010-2016 uib GmbH <info@uib.de>

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
Testing threading utilities.

:author: Christian Kampka <c.kampka@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import datetime
import time
import threading
from collections import namedtuple
from contextlib import contextmanager

from OPSI.Util.Thread import ThreadPoolException, getGlobalThreadPool, ThreadPool
from OPSI.Util.Thread import KillableThread

import pytest


@pytest.fixture(params=[10])
def threadPool(request):
    '''Returns an already started ThreadPool.'''
    pool = ThreadPool(size=request.param, autostart=False)
    pool.start()
    try:
        yield pool
    finally:
        pool.stop()


def testStopThreadPool(threadPool):
    numThreads = threading.activeCount() - len(threadPool.worker)
    threadPool.stop()

    assert 0 == len(threadPool.worker)
    assert not threadPool.started, "Expected pool to have stopped, but it hasn't"
    assert numThreads == threading.activeCount()


def testThreadPoolWorkerHandlingCallback(threadPool):
    returnedParams = namedtuple("r", ["success", "returned", "errors"])

    result = []

    def assertCallback(success, returned, errors):
        result.append(returnedParams(success, returned, errors))

    threadPool.addJob(function=lambda: 'test', callback=assertCallback)

    time.sleep(0.1)  # give thread time to finish

    assert 1 == len(result)
    r = result[0]
    assert r.success is True
    assert r.returned == 'test'
    assert r.errors is None


def testThreadPoolWorkerHandlingCallbackWithException(threadPool):
    returnedParams = namedtuple("r", ["success", "returned", "errors"])

    result = []

    def assertCallback(success, returned, errors):
        result.append(returnedParams(success, returned, errors))

    def raiseError():
        raise Exception("TestException")

    threadPool.addJob(function=raiseError, callback=assertCallback)

    time.sleep(0.1)  # give thread time to finish

    assert len(result) == 1
    r = result[0]
    assert r.success is False
    assert r.returned is None
    print(repr(r.errors))
    assert r.errors is not None
    assert "TestException" in r.errors


@pytest.mark.parametrize("value", [-1])
def testSettinginvalidThreadPoolSizeResultsInException(threadPool, value):
    with pytest.raises(ThreadPoolException):
        threadPool.adjustSize(value)


def testAdjustingThreadPoolSize(threadPool):
    threadPool.adjustSize(size=23)  # Different from default of 10
    assert 23 == threadPool.size
    assert 23 == len(threadPool.worker)

    threadPool.adjustSize(size=2)
    assert 2 == threadPool.size
    assert 2 == len(threadPool.worker)


def testSmallThreadPoolHandlingManyLongRunningTasks(threadPool):
    threadPool.adjustSize(2)

    results = []

    def callback(success, returned, errors):
        results.append(success)

    def waitJob():
        time.sleep(3)

    for _ in range(5):
        threadPool.addJob(waitJob, callback=callback)

    assert 2 == len(threadPool.worker)
    assert threadPool.jobQueue.unfinished_tasks > len(threadPool.worker), "Expected more tasks in Queue than workers in pool, but got %s tasks and %s worker" % (threadPool.jobQueue.unfinished_tasks, len(threadPool.worker))

    time.sleep(4)
    assert 5 == len(results)


def testContinueWorkingAfterStandingStill(threadPool):
    results = []

    def callback(success, returned, errors):
        results.append(success)

    def shortJob():
        return 10 * 10

    for _ in range(10):
        threadPool.addJob(shortJob, callback=callback)

    time.sleep(0.1)  # Let the pool handle the work...
    assert 10 == len(results)

    time.sleep(1)  # Wait some time...

    results = []  # Resetting our results
    for _ in range(10):
        threadPool.addJob(shortJob, callback=callback)
    time.sleep(0.1)
    assert 10 == len(results)


def testGrowThreadPool(threadPool):
    threadPool.adjustSize(2)
    threadPool.stop()
    threadPool.start()

    results = []

    def callback(success, returned, errors):
        results.append(success)

    def sleepJob():
        time.sleep(2)

    for _ in range(10):
        threadPool.addJob(sleepJob, callback=callback)
    time.sleep(3)
    assert 2 == len(results)

    threadPool.adjustSize(10)
    time.sleep(3)
    assert 10 == len(results)


def testShrinkThreadPool(threadPool):
    threadPool.adjustSize(5)
    threadPool.stop()
    threadPool.start()

    results = []

    def callback(success, returned, errors):
        results.append(success)

    def sleepJob():
        time.sleep(2)

    for _ in range(12):
        threadPool.addJob(sleepJob, callback=callback)
    time.sleep(3)

    assert 5 == len(results)

    threadPool.adjustSize(1)
    time.sleep(2)
    assert 10 == len(results)

    time.sleep(2)
    assert 11 == len(results)

    time.sleep(2)
    assert 12 == len(results)


def testThreadPoolIncreasingAndDecreasingUsageCount(threadPool):
    threadPool.increaseUsageCount()
    assert 2 == threadPool.usageCount

    threadPool.decreaseUsageCount()
    assert 1 == threadPool.usageCount


def testThreadPoolDecreasingUsageCountBelowZeroStopsThreadPool(threadPool):
    assert threadPool.started
    assert 1 == threadPool.usageCount
    threadPool.decreaseUsageCount()
    assert 0 == threadPool.usageCount
    assert not threadPool.started


def testGetGlobalThreadPoolReturnsTheSamePool():
    pool1 = getGlobalThreadPool()
    pool2 = getGlobalThreadPool()

    assert isinstance(pool1, ThreadPool)
    assert isinstance(pool2, ThreadPool)
    assert pool1 is pool2

    pool2.adjustSize(5)
    assert 5 == pool1.size

    pool1.stop()  # without this running threads will prevent test from stopping


@pytest.mark.xfail(strict=False)  # This test is not stable.
def testTerminatingKillableThread(self):
    """
    It must be possible to interrupt running threads even though
    they may still be processing.
    """

    class ThreadWithTimeout(KillableThread):
        def __init__(self, testCase):
            super(ThreadWithTimeout, self).__init__()

            self.testCase = testCase

        def run(self):
            start = datetime.datetime.now()
            timeout = datetime.timedelta(seconds=30)

            while datetime.datetime.now() < (start + timeout):
                time.sleep(0.1)

            self.testCase.fail("Thread did not get killed in time.")

    @contextmanager
    def getTestThread():
        runningThread = ThreadWithTimeout(self)
        runningThread.start()
        try:
            yield runningThread
        finally:
            runningThread.join(2)

    with getTestThread() as runningThread:
        assert runningThread.isAlive()

        runningThread.terminate()

        runChecks = 0
        while runningThread.isAlive():
            time.sleep(0.1)
            runChecks += 1

            if runChecks > 30:
                assert False, "Thread should be stopped by now."

        assert not runningThread.isAlive(), "Thread should be killed."
