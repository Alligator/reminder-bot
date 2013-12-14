import socket
import Queue
import thread
import time

class IRC(object):
  def __init__(self, host, port):
    self.host = host
    self.port = port
    self.sock = socket.socket(socket.AF_INET, socket.TCP_NODELAY)
    self.rxq = Queue.Queue()
    self.txq = Queue.Queue()
    self.rxb = ''

  def connect(self):
    self.sock.connect((self.host, self.port))
    thread.start_new_thread(self.recv_loop, ())
    thread.start_new_thread(self.send_loop, ())

  def recv_loop(self):
    while 1:
      data = self.sock.recv(4096)
      self.rxb += data
      while '\r\n' in self.rxb:
        line, self.rxb = self.rxb.split('\r\n', 1)
        if line.startswith('PING'):
          self.txq.put('PONG :' + line.split(':')[1])
        else:
          print time.strftime('%T') + ' ' + line
        self.rxq.put(line)

  def send_loop(self):
    while 1:
      line = self.txq.get()
      if not line.startswith('PONG'):
        print time.strftime('%T') + ' >>>', line
      self.sock.sendall(line + '\r\n')

  def send(self, msg):
    self.txq.put(msg)

  def privmsg(self, nick, msg):
    self.send('PRIVMSG {} :{}'.format(nick, msg))

  def notice(self, nick, msg):
    self.send('NOTICE {} :{}'.format(nick, msg))
