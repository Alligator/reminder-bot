import time
import os
import thread
import cPickle
from collections import defaultdict

import reminder as rem
import irc

irc = irc.IRC('irc.synirc.net', 6667)
try:
  f = open('reminder.pickle', 'r')
  ru = cPickle.load(f)
except IOError:
  ru = defaultdict(list)
bot = rem.RemBot(irc, ru)
thread.start_new_thread(bot.run, ())

print ru

fs = os.stat('reminder.py').st_mtime

try:
  while 1:
    # watch for changes innit
    try:
      stat = os.stat('reminder.py').st_mtime
    except OSError:
      pass
    if stat != fs:
      print '### reloading'
      fs = stat
      reload(rem)
      bot.stop()
      bot = rem.RemBot(irc, ru)
      thread.start_new_thread(bot.run, ())
    time.sleep(0.2)
except KeyboardInterrupt:
  cPickle.dump(ru, open('reminder.pickle', 'w'))
