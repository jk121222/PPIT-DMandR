#!/usr/bin/python 

################################################################################
# findrestarts.py
# Find restart times in log given optional restart type and beginning and ending 
# time. Displays average time for each type
# restart type (d
# Written by: John Kim
# Date: 2016-6-21
#
# Examples:
# findrestarts.py -h
# findrestarts.py -v
# findrestarts.py -w -d -b"Jun 21 16:49:50"  -e"Jun 21 17:08:32"
# findrestarts.py -l"/var/log/messages"
################################################################################

#Example Log messages for different restart types:
#Down restart (/etc/init.d/tpa start):
#May 29 18:26:13 pitg1 recond[947]: INFO: TdatTools: 29001 #TPA START: "recond -S", NODE UPTIME: 5 Days, 7 Hours, 47 Minutes, 24 Seconds
#...
#May 29 18:27:27 pitg1 Teradata[2025]: INFO: Teradata: 2900 # 16/05/29 18:27:27 Logons are enabled

#Warm restart (tpareset <reason>):
#Jun 20 15:00:02 pit31 Teradata[25784]: DEGRADED: Teradata: 10198 #Force a TPA restart.
#Jun 20 15:00:02 pit31 Teradata[25784]:Restart reason is: warm restart
#...
#Jun 20 15:01:47 pit31 Teradata[32017]: INFO: Teradata: 2900 # 16/06/20 15:01:47 Logons are enabled

#Force restart (tpareset -f <reason>):
#Jun 20 16:58:03 pit31 Teradata[25061]: DEGRADED: Teradata: 10198 #Force a TPA restart.
#Jun 20 16:58:03 pit31 Teradata[25061]:Restart reason is: force restart
#...
#Jun 20 16:58:32 pit31 recond[1764]: INFO: TdatTools: 29001 #RESET START: "recond -L", NODE UPTIME: 189 Days, 6 Hours, 44 Minutes, 5 Seconds
#...
#Jun 20 17:00:11 pit31 Teradata[6326]: INFO: Teradata: 2900 # 16/06/20 17:00:11 Logons are enabled

#cold restart (vprocmanager restart cold)
#Note: this seems to be the same as a warm restart
#Jun 21 11:15:07 pit31 Teradata[28276]: DEGRADED: Teradata: 10198 #Force a TPA restart.
#Jun 21 11:15:07 pit31 Teradata[28276]:Restart reason is:  System restarted by VprocManager.
#...
#Jun 21 11:16:46 pit31 Teradata[28598]: INFO: Teradata: 2900 # 16/06/21 11:16:46 Logons are enabled


import datetime
import re
from optparse import OptionParser


#patterns:
#System log time format:  Jun 21 11:16:46
rdt = re.compile("""(?P<time>
                             (?P<Mon>[A-Z][a-z]{2})\s+     #short month name
                               (?P<dd>\d\d?)\s+              #date
                             (?P<hour>\d\d):               #hour
                               (?P<minute>\d\d):             #minute
                                 (?P<second>\d\d)              #second
                    )""", re.VERBOSE)
#datetime format:  2016-06-23 10:09:05
rdt2 = re.compile("""(?P<time>
                             (?P<yyyy>\d{4})-              #year
                               (?P<mm>\d\d)-                 #month 
                                 (?P<dd>\d\d)\s+               #date
                             (?P<hour>\d\d):               #hour
                               (?P<minute>\d\d):             #minute
                                 (?P<second>\d\d)              #second
                     )""", re.VERBOSE)
#time only format:  10:09:05
rt = re.compile("""(?P<time>
                             (?P<hour>\d\d):               #hour
                               (?P<minute>\d\d):             #minute
                                 (?P<second>\d\d)              #second
                     )""", re.VERBOSE)
rr = re.compile('#Force a TPA restart.')   #start of warm, force, or cold
rx = re.compile('#TPA START: "recond -S"') #start of down
rup = re.compile('Logons are enabled')     #end of any
rrr = re.compile('Restart reason is:\s+(?P<reason>[\w\s]*)')  #warm, force, or cold
rf = re.compile('#RESET START: "recond -L"')  #force


months = {
    "Jan" : 1, "Feb" : 2, "Mar" : 3, "Apr" : 4, "May" : 5, "Jun" : 6,
    "Jul" : 7, "Aug" : 8, "Sep" : 9, "Oct" : 10, "Nov" : 11, "Dec" : 12
}


debug = False
verbose = False
localtime = datetime.datetime.now()
nowyear = int(localtime.strftime("%Y"))

################################################################################

def time_from_str(timestr, logformat=True):
#return the datetime from a string
#if logformat, only use system log format (with year set to current year)
#otherwise allow datetime format or hh:mm:ss with date set to current date)
    global nowyear
    nowmonth = int(localtime.strftime("%m"))
    nowdate = int(localtime.strftime("%d"))

    if debug: print "time_from_str", timestr
    if debug: print "logformat", logformat

    mdt = rdt.search(timestr)
    mdt2 = rdt2.search(timestr)
    mt = rt.search(timestr)
    if mdt:  #systm log format
        if debug: "print in mdt"
        mon =  mdt.group('Mon')
        day = mdt.group('dd')
        hour = mdt.group('hour')
        min = mdt.group('minute')
        sec = mdt.group('second')
        if debug: print "sec:", sec 
        thetime = datetime.datetime(nowyear, months[mon], int(day),
                                int(hour), int(min), int(sec))
        return thetime
    elif logformat:
        raise RuntimeError("Couldn't determine time from string: " + timestr)
    elif mdt2:  #datetime format
        if debug: "print in mdt2"
        yyyy = mdt2.group('yyyy')
        mm =  mdt2.group('mm')
        dd = mdt2.group('dd')
        hour = mdt2.group('hour')
        min = mdt2.group('minute')
        sec = mdt2.group('second')
        thetime = datetime.datetime(int(yyyy), int(mm), int(dd),
                                int(hour), int(min), int(sec))
        return thetime
    elif mt:  #hh:mm:ss
        if debug: "print in mt"
        hour = mt.group('hour')
        min = mt.group('minute')
        sec = mt.group('second')
        thetime = datetime.datetime(nowyear, nowmonth, nowdate,
                                int(hour), int(min), int(sec))
        return thetime
    else:
        raise RuntimeError("Couldn't determine time from string: " + timestr)
    return thetime


def get_restart_times(logname, begintime, endtime, 
                      checkwarm, checkforce, checkdown, checkcold):
    """Find restarts in a log file"""
    global nowyear  #need this since year isn't in system log
                 #alternatively just ignore the year

    startfound = False
    stopfound = False
    with open(logname, 'r') as f:
        #Look for start
        for line in f:
            if debug: print line
            entrytime = time_from_str(line)
            if entrytime > begintime:
                startfound = True
                if debug: print "Found start time"
                break
            else:
                continue
         
        if not startfound:
            print "Did not find the start time"
            return


        warmcount = 0
        downcount = 0
        coldcount = 0
        forcecount = 0
        warmrestart_total_et = datetime.timedelta(0)
        downrestart_total_et = datetime.timedelta(0)
        coldrestart_total_et = datetime.timedelta(0)
        forcerestart_total_et = datetime.timedelta(0)

        while not stopfound:
            isdownrestart = False
            iscoldrestart = False
            isforcerestart = False

            #Look for a test
            for line in f: 
                if debug: print "Look for restart: ", line

                entrytime = time_from_str(line)
                if entrytime > endtime:
                    stopfound = True
                    if debug: print "Found end time"
                    break  #done looking at log

                mr = rr.search(line)   # warm, force, or cold restart
                mx = rx.search(line)   # down restart
                if mr or mx:
                    begintime = entrytime
                    if verbose or debug: 
                        print "Found restart:"
                        print line
                    if mx:
                        isdownrestart = True
                    break
                else:
                    continue  #keep looking for restart
            else:  # no more lines
                stopfound = True

            if stopfound:
                break
           
            #get the restart reason in the next line unless it's a down restart
            if not isdownrestart:
                for line in f:
                    mrr = rrr.search(line)
                    if mrr:
                        reason = mrr.group('reason') 
                        if reason == "System restarted by VprocManager":
                           iscoldrestart = True
                    break  # only wanted to read one line
                else:
                    raise RuntimeError("End of file before finding end of test")
 
            #go until end of test (logons enabled)
            for line in f: 
                if debug: print "Look for end of test:", line

                mf = rf.search(line) #recond -L
                mup = rup.search(line)  #Logons are enabled
                if mf:  # force restart
                    isforcerestart = True
                    if debug: 
                        print line
                elif mup:
                    if verbose or debug: 
                        print "Found end of test:"
                        print line
                    enabledtime = time_from_str(line)
                    break
                else:
                    continue  # keep looking for end of test
            else:
                raise RuntimeError("End of file before finding end of test")


            if debug: print "Continuing from end of test"

            #Found end of test
            elapsedtime = enabledtime - begintime

            if verbose: print
            if isdownrestart:
                if checkdown:
                    downcount += 1
                    print "Down restart {0}".format(downcount)
                    downrestart_total_et += elapsedtime
                    print "Start: {0}, End: {1}, ET: {2}\n"\
                          .format(begintime, enabledtime, elapsedtime)
            elif isforcerestart:
                if checkforce:
                    forcecount += 1
                    print "Force restart {0}".format(forcecount)
                    forcerestart_total_et += elapsedtime
                    print "Start: {0}, End: {1}, ET: {2}"\
                          .format(begintime, enabledtime, elapsedtime)
                    print "Reason:", reason
            elif iscoldrestart:
                if checkcold:
                    coldcount += 1
                    print "Cold restart {0}".format(coldcount)
                    coldrestart_total_et += elapsedtime
                    print "Start: {0}, End: {1}, ET: {2}\n"\
                          .format(begintime, enabledtime, elapsedtime)
                    #print "Reason:", reason, "\n"
            else:  #must be warmrestart
                if checkwarm:
                    warmcount += 1
                    print "Warm restart {0}".format(warmcount)
                    warmrestart_total_et += elapsedtime
                    print "Start: {0}, End: {1}, ET: {2}"\
                          .format(begintime, enabledtime, elapsedtime)
                    print "Reason:", reason

        ### end while not stopfound
        if debug: print "Done going through log"
        if verbose: print

        if warmcount > 0:
            print "Warm restart average of {0} tests: {1}"\
                  .format(warmcount, str(warmrestart_total_et/warmcount).split(".")[0])
                  #print the time delta without microseconds

        if forcecount > 0:
            print "Force restart average of {0} tests: {1}"\
                  .format(forcecount, str(forcerestart_total_et/forcecount).split(".")[0])

        if coldcount > 0:
            print "Cold restart average of {0} tests: {1}"\
                  .format(coldcount, str(coldrestart_total_et/coldcount).split(".")[0])

        if downcount > 0:
            print "Down restart average of {0} tests: {1}"\
              .format(downcount, str(downrestart_total_et/downcount).split(".")[0])


        return


############################################################################

############################################################################
def main():
    global debug
    global verbose

    usage="%prog [-h] [-d] [-v] [-l] [-b] [-e] [-w] [-f] [-x] [-c]"
    parser = OptionParser(usage, version="%prog 0.8")
    parser.add_option("-d", "--debug", 
                      action="store_true", dest="debug", default=False,
                      help="enable debug mode")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="enable vebose mode")
    parser.add_option("-l", "--log", dest="logname", default="/var/log/messages",
                      help="log file, default='/var/log/messages'")
    parser.add_option("-b", "--begintime", dest="begintimestr",
                      help="start time, e.g. 'Jun 18 10:30:01' or '2016-06-23 10:09:05' or '10:00:00'")
    parser.add_option("-e", "--endtime", dest="endtimestr",
                      help="end time (same format as begintime)")
    parser.add_option("-w", "--warmrestart", 
                      action="store_true", dest="checkwarm", default=False,
                      help="look for warm restarts")
    parser.add_option("-f", "--forcerestart", 
                      action="store_true", dest="checkforce", default=False,
                      help="look for force restarts")
    parser.add_option("-x", "--downrestart", 
                      action="store_true", dest="checkdown", default=False,
                      help="look for down restarts")
    parser.add_option("-c", "--coldrestart", 
                      action="store_true", dest="checkcold", default=False,
                      help="look for cold restarts")
    (options, args) = parser.parse_args()

    debug = options.debug
    verbose = options.verbose
    logname = options.logname
    if options.begintimestr:
        begintime = time_from_str(options.begintimestr, False)
    else:
        begintime = datetime.datetime.min

    if options.endtimestr:
        endtime = time_from_str(options.endtimestr, False)
    else: 
        endtime = datetime.datetime.max

    checkwarm = options.checkwarm
    checkforce = options.checkforce
    checkdown = options.checkdown
    checkcold = options.checkcold
    if not (checkwarm or checkforce or checkdown or checkcold):
        checkwarm = True
        checkforce = True
        checkdown = True
        checkcold = True


    if verbose: 
        print "Restart Check"
        print "Local time: {0}\n"\
              .format(localtime.strftime("%Y-%m-%d %H:%M:%S"))


    get_restart_times(logname, begintime, endtime, checkwarm, checkforce, checkdown, checkcold)

    print "\nDone"

################################################################################
if __name__ == "__main__":
    main()


