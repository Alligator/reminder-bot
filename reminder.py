import Queue
import socket
import thread
import re
import time
import os
from datetime import datetime
from collections import defaultdict

import parsedatetime.parsedatetime as pdt

class RemBot(object):
  def __init__(self, irc, reminders_user=defaultdict(list)):
    self.irc = irc
    # http://mybuddymichael.com/writings/a-regular-expression-for-irc-messages.html
    self.reg = re.compile(r'^(?:[:](?P<host>\S+) )?(?P<cmd>\S+)(?: (?!:)(?P<chan>.+?))?(?: [:](?P<params>.+))?$')
    self.re_messages = [
      (re.compile(    r'^help\s?(.*)$'), self.handle_help),
      (re.compile(r'^([^,]+),\s?(.*)$'), self.handle_new_reminder),
      (re.compile(    r'^list\s?(.*)$'), self.handle_list),
      (re.compile(  r'^remove\s?(.*)$'), self.handle_remove)
    ]
    self.reminders_user = reminders_user
    self.cal = pdt.Calendar()
    self.timefmt = '%H:%M %Y-%m-%d'
    self.nick = 'rembot'
    try:
      self.irc.connect()
      self.irc.send('NICK :' + self.nick)
      self.irc.send('USER ' + self.nick + ' 8 * ' + self.nick + ' :hello')
    except socket.error:
      # we were likey given an already connected socket
      pass
    self.quit = False

  def run(self):
    while 1:
      try:
        if self.quit:
          return
        self.check_reminders()
        line = self.irc.rxq.get_nowait()
        self.parse_line(line)
      except Queue.Empty, e:
        time.sleep(0.1)

  def stop(self):
    self.quit = True

  def parse_line(self, line):
    m = self.reg.match(line).groupdict()
    if m['cmd'] == 'PRIVMSG':
      self.handle_privmsg(m)

  def handle_privmsg(self, msg):
    nick = msg['host'].split('!')[0]
    for regex, fn in self.re_messages:
      m = regex.match(msg['params'])
      if m:
        fn(nick, *m.groups())

  def handle_help(self, nick, msg):
    if msg == 'examples':
      self.msg(nick, 'examples:')
      self.msg(nick, '    in 2 hours, pet a dog')
      self.msg(nick, '    next monday at 4:00pm, pet a dog')
      self.msg(nick, '    tomorrow morning, pet a dog (sets reminder for 6:00)')
      self.msg(nick, '    tomorrow evening, pet a dog (sets reminder for 18:00)')
      self.msg(nick, 'these aren\'t the only formats {} understands, try whatever!'.format(self.nick))
    elif msg == 'remove':
      self.msg(nick, 'remove usage:')
      self.msg(nick, '    remove id   - remove reminder at id (use list to see ids)')
      self.msg(nick, '    remove last - remove last reminder set')
      self.msg(nick, '    remove all  - remove all reminders')
    elif msg == 'list':
      self.msg(nick, 'list usage:')
      self.msg(nick, '    list - list the reminders you have set')
    else:
      self.msg(nick, 'r e m e m b e r  m e')
      self.msg(nick, 'commands:')
      self.msg(nick, '    time, reminder - set reminder')
      self.msg(nick, '    remove - remove reminder')
      self.msg(nick, '    list   - list reminders')
      self.msg(nick, '    help   - get help')
      self.msg(nick, 'use help command for more information, or help examples for examples of settings a reminder')

  def handle_new_reminder(self, nick, tm, reminder):
    tm = self.cal.parse(tm)
    dt = datetime.fromtimestamp(time.mktime(tm[0]))
    if dt < datetime.now():
      self.msg(nick, 'time is in the past, idiot')
      return
    t = int(time.mktime(dt.utctimetuple()))/60
    fmt = dt.strftime(self.timefmt)
    reminder = (nick, tm, fmt, reminder)
    self.reminders_user[nick].append(reminder)
    self.msg(nick, 'reminder set for ' + fmt)

  def handle_remove(self, nick, msg):
    try:
      ind = int(msg)-1
    except ValueError, e:
      if msg == 'last':
        ind = -1
      elif msg == 'all':
        del self.reminders_user[nick]
        self.msg(nick, 'removing all reminders');
        return
      else:
        self.handle_help(nick, 'remove')
        return
    try:
      rem = self.reminders_user[nick][ind]
    except IndexError, e:
      self.msg(nick, 'either there\'s no reminders left or not one at that id')
      return
    self.msg(nick, 'removing {} {}'.format(rem[2], rem[3]))
    del self.reminders_user[nick][ind]

  def remove(self, nick, ind):
    pass

  def handle_list(self, nick, msg):
    if nick in self.reminders_user:
      for i, (nick, tm, fmt, rem) in enumerate(self.reminders_user[nick]):
        self.msg(nick, '{} - {} {}'.format(i+1, fmt, rem))

  def check_reminders(self):
    t = int(time.time())/60
    reminders_time = defaultdict(list)
    [reminders_time[int(time.mktime(u[1][0]))/60].append(u) for x in self.reminders_user.itervalues() for u in x]
    if t in reminders_time:
      for nick, a, b, rem in reminders_time[t]:
        self.remind(nick, rem)
        self.reminders_user[nick] = [x for x in self.reminders_user[nick] if x != (nick, a, b, rem)]

  def remind(self, nick, rem):
    self.irc.privmsg(nick, rem)

  def msg(self, nick, msg):
    self.irc.notice(nick, msg)
