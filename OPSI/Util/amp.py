#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   This module is part of the desktop management solution opsi
   
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2010 Andrey Petrov
   Copyright (C) 2010 uib GmbH
   
   http://www.uib.de/
   
   All rights reserved.
   
   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.
   
   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
   
   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
   
   @copyright:	uib GmbH <info@uib.de>
   @author: Christian Kampka <c.kampka@uib.de>
   @license: GNU General Public License version 2
"""

from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.internet.protocol import ReconnectingClientFactory, ClientCreator
from twisted.internet.defer import DeferredList, maybeDeferred, Deferred, succeed
from twisted.internet.unix import Connector
from twisted.protocols.amp import Argument, String, Integer, Boolean, Command, AMP, MAX_VALUE_LENGTH
from twisted.python.failure import Failure


import base64, hashlib
from pickle import dumps, loads, HIGHEST_PROTOCOL
from types import StringType
from OPSI.Logger import *
logger = Logger()

try:
	import cStringIO as StringIO
except ImportError:
	import StringIO



USE_BUFFERED_RESPONSE = "__USE_BUFFERED_RESPONSE__"

class RemoteArgument(Argument):
	
	def toString(self, obj):
		return dumps(obj, HIGHEST_PROTOCOL)
	
	def fromString(self, str):
		return loads(str)

class RemoteProcessException(Exception):
	pass

class RemoteProcessCall(Command):
	
	arguments = [	('name', String()),
			('argString', String()),
			('tag', Integer())]
	
	response = [	('tag', Integer()),
			('result', RemoteArgument())]

	errors = {RemoteProcessException: 'RemoteProcessError'}
	
	requiresAnswer = True
	
class ChunkedArgument(Command):
	
	arguments = [	('tag', Integer()),
			('argString', String())]

	response = [('result', Integer())]
	
	errors = {RemoteProcessException: 'RemoteProcessError'}
	
	requiresAnswer = True

class ResponseBufferPush(Command):
	
	arguments = [	('tag', Integer()),
			('chunk', String())]

	response = [('result', Integer())]
	
	errors = {RemoteProcessException: 'RemoteProcessError'}
	
	requiresAnswer = True
	
class OpsiQueryingProtocol(AMP):
	
	def __init__(self):
		AMP.__init__(self)
		self.tag = 1
		self.responseBuffer = {}
		self.dataSink = None
		
	def getNextTag(self):
		self.tag += 1
		return self.tag
	
	def openDataSink(self):
		try:
			self.dataSink = reactor.listenUNIX("%s.dataport" % self.addr.name, OpsiProcessProtocolFactory(self))
		except Exception, e:
			logger.error("Could not open data socket %s: %s" ("%s.dataport" % self.addr.name, e))
			raise e
	
	def closeDataSink(self):
		
		self.dataSink.factory.stopTrying()
		self.dataSink.transport.loseConnection()
		
	def _callRemote(self, command, **kwargs):
		
		deferred = Deferred()

		def p(response):
			deferred.callback(response)
		result = self.callRemote(command, **kwargs)
		result.addBoth(p)
		return deferred
	
	def sendRemoteCall(self, method, args=[], kwargs={}):
		
		d = Deferred()
		result = Deferred()
		
		argString = dumps((args,kwargs), HIGHEST_PROTOCOL)
		tag = self.getNextTag()
		
		chunks = [argString[i:i + MAX_VALUE_LENGTH] for i in xrange(0, len(argString), MAX_VALUE_LENGTH)]

		if len(chunks) > 1:
			for chunk in chunks[:-1]:
				def sendChunk(tag, chunk):
					deferedSend = lambda x: self.dataport.callRemote(
							commandType=ResponseBufferPush, tag=tag, chunk=chunk)
					return deferedSend
					
				d.addCallback(sendChunk(tag=tag, argString=chunk))
		d.addCallback(lambda x: self.callRemote(RemoteProcessCall, name=method, tag=tag, argString=chunks[-1]))
		d.addCallback(lambda x: )
		d.callback(None)
		return d

	@ResponseBufferPush.responder
	def chunkedResponseReceived(self, tag, chunk):
		self.responseBuffer.setdefault(tag, StringIO.StringIO()).write(chunk)
		return {'result': tag}
	

	def getResponseBuffer(self,tag):
		return self.dataSink.factory._protocol.responseBuffer.pop(tag)
	
class OpsiResponseProtocol(AMP):
	
	def __init__(self):
		AMP.__init__(self)
		self.buffer = {}
		self.dataport = None

	def assignDataPort(self, protocol):
		self.dataport = protocol

	def closeDataPort(self, result=None):
		if self.dataport is not None:
			self.dataport.transport.loseConnection()
			self.dataport = None
		return result
		
	@RemoteProcessCall.responder
	def remoteProcessCallReceived(self, tag, name, argString):

		args = self.buffer.pop(tag, argString)
		
		if type(args) is not StringType:
			args.write(argString)
			args, closed = args.getvalue(), args.close()
				
		args, kwargs = loads(args)

		method = getattr(self.factory._remote, name, None)
		

		if method is None:
			raise RemoteProcessException(u"Daemon has no method %s" % (name))
		rd = Deferred()
		d = maybeDeferred(method, *args, **kwargs)
		
		d.addCallback(lambda result: self.processResult(result, tag))
		d.addCallback(rd.callback)
		d.addErrback(self.processFailure)
		d.addErrback(rd.errback)
		return rd
	
	def processResult(self, result, tag):

		r = dumps(result, HIGHEST_PROTOCOL)
		chunks = [r[i:i + MAX_VALUE_LENGTH] for i in xrange(0, len(r), MAX_VALUE_LENGTH)]
		dd = Deferred()
		
		def handleConnectionFailure(fail):
			logger.error("Failed to connect to socket %s: %s" %(self.factory._dataport, fail.getErrorMessage()))
			return fail
		
		if len(chunks) > 1:
			if self.dataport is None:
				dd.addCallback(lambda x: ClientCreator(reactor, AMP).connectUNIX(self.factory._dataport))
				dd.addErrback(handleConnectionFailure)
				dd.addCallback(self.assignDataPort)
			else:
				dd = succeed(None)
			
			for chunk in chunks:
				def sendChunk(tag, chunk):
					deferedSend = lambda x: self.dataport.callRemote(
							commandType=ResponseBufferPush, tag=tag, chunk=chunk)
					return deferedSend
				dd.addCallback(sendChunk(tag, chunk))
			
			dd.addCallback(lambda x: {"tag": tag, "result": USE_BUFFERED_RESPONSE})
			
		else:
			dd.addCallback(lambda x: {"tag": tag, "result":result})
		dd.addCallback(self.closeDataPort)
		dd.callback(None)
		return dd

	@ChunkedArgument.responder
	def chunkReceived(self, tag, argString):
		buffer = self.buffer.setdefault(tag, StringIO.StringIO())
		buffer.write(argString)
		return {'result': tag}
	

	def processFailure(self, failure):
		logger.logFailure(failure)
		raise RemoteProcessException(failure.value)


class OpsiProcessProtocol(OpsiQueryingProtocol, OpsiResponseProtocol):
	def __init__(self):
		OpsiQueryingProtocol.__init__(self)
		OpsiResponseProtocol.__init__(self)


class OpsiProcessProtocolFactory(ReconnectingClientFactory):
	
	protocol = OpsiProcessProtocol
	
	def __init__(self, remote=None, dataport = None, reactor=reactor):
		self._remote = remote
		self._dataport = dataport
		self._protocol = None
		self._notifiers = []
		self._reactor = reactor
		
	def buildProtocol(self, addr):
		p = ReconnectingClientFactory.buildProtocol(self, addr)
		p.addr = addr
		p.openDataSink()
		self._protocol = p
		self.notifySuccess(p)
		return p
	
	def addNotifier(self, callback, errback=None):
		self._notifiers.append((callback, errback))
	
	def removeNotifier(self, callback, errback=None):
		self._notifiers.remove((callback, errback))
	
	def notifySuccess(self, *args, **kwargs):
		for callback, errback in self._notifiers:
			self._reactor.callLater(0, callback, *args, **kwargs)
	
	def notifyFailure(self, failure):
		for callback, errback in self._notifiers:
			if errback is not None:
				self._reactor.callLater(0, errback, failure)
				
	def clientConnectionFailed(self, connector, reason):
		ReconnectingClientFactory.clientConnectionFailed(self, connector,
							 reason)
		if self.maxRetries is not None and (self.retries > self.maxRetries):
			self.notifyFailure(reason) # Give up

	def shutdown(self):
		if self._protocol is not None:
			if self._protocol.transport is not None:
				self._protocol.transport.loseConnection()

class RemoteDaemonProxy(object):
	
	def __init__(self, protocol):
		
		self._protocol = protocol
	
	def __getattr__(self, method):
		
		def callRemote(*args, **kwargs):
			result = Deferred()
			
			def processResponse(response):
				r = response["result"]
				if r == USE_BUFFERED_RESPONSE:
					buffer = self._protocol.getResponseBuffer(response["tag"])
					
					if buffer is None:
						raise Exception("Expected a buffered response but no response buffer was found for tag %s" % r["tag"])

					s = buffer.getvalue()
					
					buffer.close()
					
					obj = loads(s)

					result.callback(obj)
				else:
					result.callback(r)
			
			def processFailure(failure):
				logger.logFailure(failure, logLevel=LOG_ERROR)
				result.errback(failure)
			d = self._protocol.sendRemoteCall(	method=method,
								args=args,
								kwargs=kwargs)
			d.addCallback(processResponse)
			d.addErrback(processFailure)
			return result
		return callRemote
	
class OpsiProcessConnector(object):
	
	factory = OpsiProcessProtocolFactory
	remote = RemoteDaemonProxy
	
	def __init__(self, socket, timeout=None, reactor=reactor):
		self._factory = OpsiProcessProtocolFactory()
		self._connected = None
		self._socket = socket
		self._timeout = timeout
		self._reactor = reactor
		self._protocol = None

	def connect(self):
		self._connected = Deferred()
		
		def success(result):
			self._factory.removeNotifier(success, failure)
			self._protocol = result
			self._remote = self.remote(self._protocol)
			self._connected.callback(self._remote)
		
		def failure(fail):
			self._factory.removeNotifier(success, failure)
			self._connected.errback(fail)
		
		self._factory = self.factory(reactor = self._reactor)
		try:
			self._reactor.connectUNIX(self._socket, self._factory)
			self._factory.addNotifier(success, failure)
		except Exception, e:
			logger.error("Failed to connect to socket %s: %s"(self._socket,e))
			self._connected.errback(Failure())
		
		return self._connected
	
	def connectionFailed(self, reason):
		Connector.connectionFailed(self, reason)
		self._connected.errback(reason)
	
	def disconnect(self):
		if self._factory:
			self._factory.stopTrying()
		if self._remote:
			if self._remote._protocol.transport:
				self._remote._protocol.transport.loseConnection()
			self._remote = None

