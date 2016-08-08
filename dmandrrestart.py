#!/usr/bin/python 

################################################################################
# dmandrrestart.py
# Perform DM&R restart tests
# Written for python 2.6.9
# Tested on TD15.0, TD15.10
# Written by: John Kim
# Date: 2016-6-16
#
# Always goes in order 1. named test 2. warm, 3. forced, 4. down (x), 5. cold
# Then these are repeated n times
# Currently there is no difference between forced and cold
# Examples:
# where w==warm restart, x==down restart, f==forced restart
# # dmandrrestart.py -t1
# will run test 1 one time (w x f)
# # dmandrrestart.py -f -ddd -w -f
# will run w f f d d d
# # dmandrrestart.py -w -f -x -n2
# will run (w f x) (w f x)
# # dmandrrestart.py -t1 -n2 -ww -f -x -v
# Will run ((w x f) w w f x) ((w x f) w w f x)
################################################################################

import time
import datetime
import sys
import re
import collections
from subprocess import Popen, PIPE, STDOUT, call
from optparse import OptionParser
import abc


#patterns:
rdt = re.compile("""(?P<time>
                             (?P<Mon>[A-Z][a-z]{2,2})\s+   #month name
                             (?P<dd>\d+)\s+                #date
                             (?P<hour>\d\d):               #hour
                             (?P<minute>\d\d):             #minute
                             (?P<second>\d\d))             #second
                 """, re.VERBOSE)
rr = re.compile('#Force a TPA restart.')
rx = re.compile('#TPA START: "recond -S"')
rup = re.compile('Logons are enabled')
rrs = re.compile('PDE state is RUN/STARTED.')
rdn = re.compile('PDE state: DOWN/HARDSTOP')


months = {
    "Jan" : 1, "Feb" : 2, "Mar" : 3, "Apr" : 4, "May" : 5, "Jun" : 6,
    "Jul" : 7, "Aug" : 8, "Sep" : 9, "Oct" : 10, "Nov" : 11, "Dec" : 12
}


debug = False
verbose = False
localtime = datetime.datetime.now()
year = int(localtime.strftime("%Y"))

################################################################################

class Restart():
    testid = 0  #Unique id for each test instance

    def __init__(self):
        self.name = ""
        self.cmd = []
        self.kickofftime = 0 
        self.starttime = 0
        self.endtime = 0
        self.elapsedtime = 0
        Restart.testid += 1

    @abc.abstractmethod
    def update_total(self, elapsedtime):
        """ update total elapsed time """
        #This abstract method is so Restart.do_resetart() can update the
        #total_et for the class of the derived object. Not needed for
        #derived classes that override do_restart

    def do_restart(self):
        """Perform the restart test"""
        self.kickofftime =  datetime.datetime.now().replace(microsecond=0)
        if verbose:
            print "Test id:", self.testid
        if debug: 
            print "restart cmd=", self.cmd
        if verbose: print "Executing command: ", " ".join(self.cmd)
        call(self.cmd)
        wait_til_up()
        #time.sleep(2)  #In case there is a delay from pdestate up to writing to log
        try:
            (starttime, endtime, elapsedtime) = get_restart_times(self.kickofftime)
        except RunTimeError:  # try one more time
            print "Re-trying get_restart_times()"
            (starttime, endtime, elapsedtime) = get_restart_times(self.kickofftime)
        self.update_total(elapsedtime)

        return (starttime, endtime, elapsedtime)


class Warmrestart(Restart):
    count = 0  # Number of warm restart tests
    total_et = datetime.timedelta(0)

    def __init__(self):
        Restart.__init__(self)
        self.name = "Warm restart"
        Warmrestart.count += 1
        self.testid = Restart.testid
        self.cmd = ['tpareset', '-yes', 'warm', 'restart']

    def update_total(self, elapsedtime):
        """ update total elapsed time """
        Warmrestart.total_et += elapsedtime


class Forcerestart(Restart):
    count = 0  # Number of warm restart tests
    total_et = datetime.timedelta(0)

    def __init__(self):
        Restart.__init__(self)
        self.name = "Forced restart"
        Forcerestart.count += 1
        self.testid = Restart.testid
        self.cmd = ['tpareset', '-yes', '-f', 'force', 'restart']

    def update_total(self, elapsedtime):
        """ update total elapsed time """
        Forcerestart.total_et += elapsedtime


class Coldrestart(Restart):
    count = 0  # Number of cold restart tests
    total_et = datetime.timedelta(0)

    def __init__(self):
        Restart.__init__(self)
        self.name = "Cold restart"
        Coldrestart.count += 1
        self.testid = Restart.testid
        self.cmd = ['tpareset', '-f', '-yes', 'force', 'restart']

    def update_total(self, elapsedtime):
        """ update total elapsed time """
        Coldrestart.total_et += elapsedtime


class Downrestart(Restart):
    count = 0  # Number of down restart tests
    total_et = datetime.timedelta(0)

    def __init__(self):
        Restart.__init__(self)
        self.name = "Down restart"
        Downrestart.count += 1
        self.testid = Restart.testid
        self.cmd = ['/etc/init.d/tpa', 'start']

    def update_total(self, elapsedtime):
        """ update total elapsed time """
        Downrestart.total_et += elapsedtime

    def do_restart(self):
        """Perform the down restart test"""
        force_down()
        wait_til_down()

        self.kickofftime = datetime.datetime.now().replace(microsecond=0)
        if verbose: print "Executing command: ", " ".join(self.cmd)
        call(self.cmd)
        wait_til_up()
        (starttime, endtime, elapsedtime) = get_restart_times(self.kickofftime)
        self.update_total(elapsedtime)

        return (starttime, endtime, elapsedtime)


def wait_til_up():
    """Wait for PDE/DBS up"""
    #PDE state is RUN/STARTED.
    #DBS state is 4: Logons are enabled - Users are logged on

    #PDE state is RUN/STARTED.
    #DBS state is 5: Logons are enabled - The system is quiescent
    if verbose: print "Waiting for:  Logons are enabled"
    cmd = "pdestate -a"
    if debug: print "Executing command: ", cmd
    while True:
        dbsup = False
        pdeup = False
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        stdout, stderr = p.communicate()

        for line in stdout.splitlines():
            mrs = rrs.match(line)   #PDE state is RUN/STARTED.
            if mrs:
                pdeup = True
            mup = rup.search(line)     # Logons are enabled
            if mup:
                if verbose: print "Found:  Logons are enabled"
                dbsup = True
            if pdeup and dbsup:
                if verbose: print "PDE and DBS up"
                return


def force_down():
    """Bring down PDE/DBS"""
    cmd = ['tpareset', '-x', '-yes', 'down']
    if verbose: print "Executing command: ", " ".join(cmd)
    call(cmd)


def wait_til_down():
    """Wait for PDE/DBS down"""
    #PDE state: DOWN/HARDSTOP

    if verbose: print "Waiting for:  PDE state is DOWN/HARDSTOP"
    cmd = "pdestate -a"
    if debug: print "Executing command: ", cmd
    while True:
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        stdout, stderr = p.communicate()

        for line in stdout.splitlines():
            mdn = rdn.match(line)   #PDE state: DOWN/HARDSTOP
            if mdn:
                if verbose: print "Found:  PDE state is DOWN/HARDSTOP"
                return


def get_restart_times(kickofftime):
    """Determine the restart times from the system log"""
    global year  #need this since year isn't in system log
                 #alternatively just ignore the year

    log = "/var/log/messages"
    if verbose: print "Kickofftime:", kickofftime
    with open(log, 'r') as f:
        line = f.readline()
        while line:  # read to the time the test started
            mt = rdt.match(line)  #search date/time
            if mt:
                mon =  mt.group('Mon')
                day = mt.group('dd')
                hour = mt.group('hour')
                min = mt.group('minute')
                sec = mt.group('second')
                logtime = datetime.datetime(year, months[mon], int(day),
                                        int(hour), int(min), int(sec))
                if logtime >= kickofftime:
                    if debug: print "Found kickofftime time:", line
                    break
            line = f.readline()

        if debug: print "Look for start of test"
        while line: # find the start of the test
            if debug: print line
            mr = rr.search(line)   # warm start
            mx = rx.search(line)   # down start
            if mr or mx:
                if debug: print "Found start of test:", line
                if verbose: print line
                mt = rdt.match(line)  #search date/time
                if mt:
                    mon =  mt.group('Mon')
                    day = mt.group('dd')
                    hour = mt.group('hour')
                    min = mt.group('minute')
                    sec = mt.group('second')
                    starttime = datetime.datetime(year, months[mon], int(day),
                                            int(hour), int(min), int(sec))
                    break
                else:
                    raise RuntimeError("Couldn't find the time")
            line = f.readline()
 
        if debug: print "Look for end of test"
        while line: # find the end of the test
            mup = rup.search(line)  
            if mup:
                if debug: print "Found end of test:", line
                if verbose: print line
                mt = rdt.match(line)  #search date/time
                if mt:
                    mon =  mt.group('Mon')
                    day = mt.group('dd')
                    hour = mt.group('hour')
                    min = mt.group('minute')
                    sec = mt.group('second')
                    endtime = datetime.datetime(year, months[mon], int(day),
                                            int(hour), int(min), int(sec))
                    break
                else:
                    raise RuntimeError("Couldn't find the time")
            line = f.readline()

        if not line:
            raise RuntimeError("Couldn't find test")
            
        elapsedtime = endtime - starttime
        return(starttime, endtime, elapsedtime)


############################################################################
def main():
    global debug
    global verbose

    usage="%prog [-h] [-d] [-v] [-t] [-n] [-w] [-f] [-x] [-c]"
    parser = OptionParser(usage, version="%prog 0.7")
    parser.add_option("-d", "--debug", 
                      action="store_true", dest="debug", default=False,
                      help="enable debug mode")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="enable vebose mode")
    parser.add_option("-t", "--test", type="int", dest="test", default=0,
                      help="specify test 0-2")
    parser.add_option("-n", "--testreps", type="int", dest="testreps", default=1,
                      help="number of times to perform test")
    parser.add_option("-w", "--warmrestart", 
                      action="count", dest="addedwarms", default=0,
                      help="add a warm restart")
    parser.add_option("-f", "--forcerestart", 
                      action="count", dest="addedforces", default=0,
                      help="add a force restart")
    parser.add_option("-x", "--downrestart", 
                      action="count", dest="addeddowns", default=0,
                      help="add a down restart")
    parser.add_option("-c", "--coldrestart", 
                      action="count", dest="addedcolds", default=0,
                      help="add a cold restart")
    (options, args) = parser.parse_args()

    debug = options.debug
    verbose = options.verbose
    test = options.test
    testreps = options.testreps
    addedwarms = options.addedwarms
    addedforces = options.addedforces
    addeddowns = options.addeddowns
    addedcolds = options.addedcolds

    if verbose: 
        print "Restart Test"
        print "Local time: {0}\n"\
              .format(localtime.strftime("%Y-%m-%d %H:%M:%S"))


    #Make a list of tests to run
    testlist = []

    for n in range (0,testreps):
        if test == 0:
            pass
        elif test == 1:
            testlist.append(Warmrestart())
            testlist.append(Downrestart())
            testlist.append(Forcerestart())
        elif test == 2:
            testlist.append(Warmrestart())
            testlist.append(Downrestart())
        else:
            print "No test", test

        if addedwarms > 0:
            for m in range (0,addedwarms):
                testlist.append(Warmrestart())
        if addedforces > 0:
            for m in range (0,addedforces):
                testlist.append(Forcerestart())
        if addeddowns > 0:
            for m in range (0,addeddowns):
                testlist.append(Downrestart())
        if addedcolds > 0:
            for m in range (0,addedcolds):
                testlist.append(Coldrestart())


    #Run the tests
    for t in testlist:
        print "Test {0} - {1}:".format(t.testid, t.name)
        (starttime, endtime, elapsedtime) =  t.do_restart()
        print "Start: {0}, End: {1}, ET: {2}\n"\
              .format(starttime, endtime, elapsedtime)


    #Print stats
    warmcount = Warmrestart.count
    if warmcount > 0:
        print "Warm restart average of {0} tests: {1}"\
              .format(warmcount, str(Warmrestart.total_et/warmcount).split(".")[0])
              #print the time delta without microseconds

    forcecount = Forcerestart.count
    if forcecount > 0:
        print "Force restart average of {0} tests: {1}"\
              .format(forcecount, str(Forcerestart.total_et/forcecount).split(".")[0])

    coldcount = Coldrestart.count
    if coldcount > 0:
        print "Cold restart average of {0} tests: {1}"\
              .format(coldcount, str(Coldrestart.total_et/coldcount).split(".")[0])

    downcount = Downrestart.count
    if downcount > 0:
        print "Down restart average of {0} tests: {1}"\
              .format(downcount, str(Downrestart.total_et/downcount).split(".")[0])

    print "\nDone"


################################################################################
if __name__ == "__main__":
    main()


