#!/usr/bin/python

import socket, threading, json
from time import sleep
from collections import defaultdict
from inspect import getargspec

def main():
  threads = []
  webSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  webSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  webSocket.bind(('', 80))
  webSocket.listen(5)
  while True:
    (clientSocket, clientAddress) = webSocket.accept()
    RequestHandler(clientSocket = clientSocket, clientAddress = clientAddress).start()

class RequestHandler(threading.Thread):
  routingTable = defaultdict(lambda: -1)
  routingTable = {
    'GET' : {
      # Workaround for empty non terminals :-) Every e.n.t. should have a _root method
      '_root' : {
        'numArgs' : 0,
        'embedded' : True,
        'function' : lambda: {'availableMethods' : {
          'calculator' : { }
        }}
      },
      'calculator': {
        '_root' : {
          'numArgs' : 0,
          'embedded' : True,
          'function' : lambda: {'availableMethods' : {
            'sum' : { 'args' : 
              getargspec(RequestHandler.routingTable['GET']['calculator']['sum']['function']).args
            },
            'substract' : { 'args' : 
              getargspec(RequestHandler.routingTable['GET']['calculator']['substract']['function']).args
            },
            'divide' : { 'args' : 
              getargspec(RequestHandler.routingTable['GET']['calculator']['divide']['function']).args
            },
            'multiply' : { 'args' : 
              getargspec(RequestHandler.routingTable['GET']['calculator']['multiply']['function']).args
            },
             'wait' : { 'args' : 
              getargspec(RequestHandler.routingTable['GET']['calculator']['wait']['function']).args
            }
         }}
        },
        'wait' : {
          'numArgs' : 0,
          'embedded' : True,
          'function' : lambda: sleep(10),
          'returnType' : None
        },
        'sum' : {
          'numArgs' : 2,
          'embedded' : True,
          'function' : lambda x, y: x + y,
          'returnType' : float
        },
        'substract' : {
          'numArgs' : 2,
          'embedded' : True,
          'function' : lambda x, y: x - y,
          'returnType' : float
        },
        'divide' : {
          'numArgs' : 2,
          'embedded' : True,
          'function' : lambda x, y: x / y if y != 0 else -1,
          'returnType' : float
        },
        'multiply' : {
          'numArgs' : 2,
          'embedded' : True,
          'function' : lambda x, y: x * y,
          'returnType' : float
        }
      }
    }
  }

  def __init__(self, clientSocket = None, clientAddress = str):
    threading.Thread.__init__(self)
    self.clientSocket = clientSocket
    self.clientAddress = clientAddress

  def run(self):
    self.requestData = self.clientSocket.recv(1024)
    self.requestData = bytes.decode(self.requestData)
    self.parseHTTPHeader(self.requestData.split('\r\n\r\n')[0])
    if not hasattr(self, 'responseData'): self.routeRequest()
    self.createHeaders()
    self.responseMessage = self.createBody()
    self.clientSocket.send((self.resultHeaders + self.responseMessage + '\n').encode())
    self.clientSocket.close()

  def parseHTTPHeader(self, headerData):
    self.requestData = dict()
    self.requestMethod = headerData.split(' ')[0]
    self.requestUri = headerData.split(' ')[1].split('?')[0].rstrip('/')
    if '?' in headerData.split(' ')[1]:
      self.requestQuery = headerData.split(' ')[1].split('?')[1].decode()
    else:
      self.requestQuery = ''
    self.requestHttpVersion = headerData.split(' ')[2]
    requestHeaderFields = headerData.split('\r\n')[1:]
    for line in requestHeaderFields:
      self.requestData[line.split(':')[0]] = ''.join(line.split(': ')[1:])

  def parseQuery(self, routingTableEntry):
    self.query = dict()
    if routingTableEntry.get('numArgs') > 0:
      try:
        queries = self.requestQuery.split('&')
        for query in queries:
          self.query[query.split('=')[0]] = float(query.split('=')[1])
      except (IndexError, ValueError):
        self.serveBadRequest()
        return False
      if len(self.query) < routingTableEntry.get('numArgs'):
        self.serveBadRequest()
        return False
      for arg in getargspec(routingTableEntry.get('function', None)).args:
        if arg not in self.query:
          self.serveBadRequest()
          return False
    return True

  def serveBadRequest(self):
    self.responseData = -1
    self.responseStatus = 400
    self.responseStatusMsg = 'Bad Request'

  def serveNotFound(self):
    self.responseData =  -1
    self.responseStatus = 404
    self.responseStatusMsg = 'Not Found'

  def serveOk(self):
    self.responseStatus = 200
    self.responseStatusMsg = 'OK'

  def routeRequest(self):
    self.route = self.requestUri.split('/')[1:]
    element = self.routingTable
    element = element.get(self.requestMethod)
    print self.route
    for key in self.route:
      if not element:
        break
      element = element.get(key, False)
    if element:
      if element.get('_root', False):
        element = element.get('_root', False)
      if element.get('numArgs') == 2:
        if self.parseQuery(element):
          self.responseData = element.get('function')(self.query['x'], self.query['y'])
          self.serveOk()
      else:
        print element
        self.responseData = element.get('function')()
        self.serveOk()
    else:
      self.serveNotFound()
    
  def createHeaders(self):
    headers = 'HTTP/1.1'
    headers += ' ' + str(self.responseStatus) + ' ' + self.responseStatusMsg + '\n'
    headers += 'Server: WorldWideJeroen 0.1 Essential\n\n'
    self.resultHeaders = headers

  def createBody(self):
    return json.dumps({'calculator' : {
      'result' : self.responseData
    }}, sort_keys=True, indent=2)

if __name__ == "__main__":
    main()
