#!/usr/bin/python 

################################################################################
# getreconfigtimes.py
# Find reconfig times in log
# Written by: John Kim
# Date: 2016-6-22
#
# Examples:
#getreconfigtimes.py 
#getreconfigtimes.py -v --file "57684add.reconfig.out.log"
################################################################################

import datetime
import re
from subprocess import Popen, PIPE, STDOUT
from optparse import OptionParser


#Patterns
#*** 06/20/16 13:41:49 ***
r_datetime= re.compile(""" (?P<datetime>
                                  (?P<yy>\d+)/          #year
                                  (?P<mm>\d+)/          #month
                                  (?P<dd>\d+)\s+        #date
                                  (?P<hour>\d\d):       #hour
                                  (?P<minute>\d\d):     #minute
                                  (?P<second>\d\d))     #second
                       """, re.VERBOSE)
# 20439 INFO: Command loop: Input line is 1:System Time (Reconfiguration): 16/06/20 13:41:49. (TeradataUtilities.cpp+2506)
r_reconfig= re.compile("System Time \(Reconfiguration\):")
#
# 20439 INFO: RECONFIG has officially started, send first command (TeradataUtilities.cpp+2856)
#
# 20439 INFO: Command loop: Input line is 1:The current configuration has:               4 Nodes with 88 AMPs  (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:The new configuration will be:               4 Nodes with 176 AMPs  (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:There are 88 AMPs added to the new configuration (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:The system has:              10982 tables using 19.98TB of data (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:The estimated table redistribution time will be: (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:      2.01 hours (for offline reconfig). (TeradataUtilities.cpp+2506)
r_estredist= re.compile("(?P<hours>\d+.\d+) hours \(for offline reconfig\).")
# 20439 INFO: Command loop: Input line is 1:      3.14 hours (for online reconfig with system 25% busy). (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:      4.52 hours (for online reconfig with system 50% busy). (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:      6.16 hours (for online reconfig with system 75% busy). (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:      8.04 hours (for online reconfig with system 100% busy). (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:The estimated table deletion time will be: (TeradataUtilities.cpp+2506)
r_estdel= re.compile("The estimated table deletion time will be:")
# 20439 INFO: Command loop: Input line is 1:      2.03 hours. (TeradataUtilities.cpp+2506)
r_estdeltime= re.compile("(?P<hours>\d+.\d+) hours.")
# 20439 INFO: Command loop: Input line is 1: (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1: (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:This reconfig estimate is based upon 48XX/49XX/52XX OR LATER. (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1: (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:Reconfig waiting for Recovery to complete... (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:Recovery has been stopped (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/20 13:46:31 Hash Map Calculation Phase Begins (TeradataUtilities.cpp+2506)
r_hashmapbegin= re.compile("Hash Map Calculation Phase Begins")
#
#*** 06/20/16 13:47:51 ***
# 20439 INFO: Command loop: Input line is 1:16/06/20 13:47:51 Hash Map Calculation Phase Ends (TeradataUtilities.cpp+2506)
r_hashmapend=   re.compile("Hash Map Calculation Phase Ends")
# 20439 INFO: Command loop: Input line is 1:16/06/20 13:47:51 Table Redistribution Phase Begins (TeradataUtilities.cpp+2506)
r_redistbegin=   re.compile("Table Redistribution Phase Begins")
#
#*** 06/20/16 23:59:06 ***
# 20439 INFO: Command loop: Input line is 1:16/06/20 23:59:05  Task 07 End redistribution PPIT_ONE.lineitem_1272 (0000H 2BD7H). (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:  Statistics:        RowCount ByteCount TotSecs         CPUSecs         IOCount (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:     AllAmps:   1,464,723,162  769.76GB  16,039          95,750      75,498,508 (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/20 23:59:05 Table Redistribution Phase Ends (TeradataUtilities.cpp+2506)
r_redistend=   re.compile("Table Redistribution Phase Ends")
# 20439 INFO: Command loop: Input line is 1:16/06/20 23:59:05 Old Table Deletion Phase Begins (TeradataUtilities.cpp+2506)
r_delbegin=   re.compile("Old Table Deletion Phase Begins")
#
#*** 06/21/16 03:29:03 ***
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:03  Task 09 End deletion PPIT_ONE.lineitem_ppi_large_0002 (0000H 31D3H). (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:  Statistics:   FSysCallCount ByteCount TotSecs         CPUSecs         IOCount (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:     AllAmps:   2,782,454,604  145.51GB     507           9,278       2,810,590 (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:03 Old Table Deletion Phase Ends (TeradataUtilities.cpp+2506)
r_delend=   re.compile("Old Table Deletion Phase Ends")
#
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:03 Saving New Primary Hash Map Phase Begins (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:03 Saving New Primary Hash Map Phase Ends (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:03 Saving New Fallback Hash Map Phase Begins (TeradataUtilities.cpp+2506)
#*** 06/21/16 03:29:04 ***
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Saving New Fallback Hash Map Phase Ends (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Saving Current Primary Hash Map Phase Begins (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Saving Current Primary Hash Map Phase Ends (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Saving Current Fallback Hash Map Phase Begins (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Saving Current Fallback Hash Map Phase Ends (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Saving Backup IDs Phase Begins (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Saving Backup IDs Phase Ends (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Saving Current Configuration Map Phase Begins (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Saving Current Configuration Map Phase Ends (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Saving New Configuration Map Phase Begins (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Saving New Configuration Map Phase Ends (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Deleting New Hash Maps Phase Begins (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Deleting New Hash Maps Phase Ends (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Saving Bitmap Hash Table Phase Begins (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Saving Bitmap Hash Table Phase Ends (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Updating Disk Space Phase Begins (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Updating Disk Space Phase Ends (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Updating Vproc Configuration Begins (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:04 Updating Vproc Configuration Ends (TeradataUtilities.cpp+2506)
# 20439 INFO: Command loop: Input line is 1:System Time (Reconfiguration): 16/06/21 03:29:04 (TeradataUtilities.cpp+2506)
#r_reconfig= re.compile("System Time (Reconfiguration):")
# 20439 INFO: Command loop: Input line is 1:        6120: Restarting DBS due to completion of reconfiguration. (TeradataUtilities.cpp+2506)
#




debug = False
verbose = False

################################################################################

def time_from_str(timestr):
    #look for a time in the string, format yy/mm/dd hh:mm:ss
    #return it as a datetime object
    m_datetime = r_datetime.search(timestr)
    if m_datetime:
        year = m_datetime.group('yy')
        month =  m_datetime.group('mm')
        day = m_datetime.group('dd')
        hour = m_datetime.group('hour')
        min = m_datetime.group('minute')
        sec = m_datetime.group('second')
        thetime = datetime.datetime(2000 + int(year), int(month), int(day),
                                int(hour), int(min), int(sec))
    else:
        raise RuntimeError("Couldn't determine time from string: " + timestr)
    return thetime

def lookforpattern(f, pattern):
    #go through file f until pattern is found. Return the time in the found line
    if debug: print "Looking for:", pattern
    for line in f:
        if debug: print line
        m = pattern.search(line)
        if m:
            if verbose: print line
            time = time_from_str(line)
            return time
        else:
            continue
    else:
        raise RuntimeError("Did not find pattern")
        return

def lookforpatternwithgroup(f, pattern, group):
    #go through file f until pattern is found
    #retrun the specified group 
    if debug: print "Looking for:", pattern, group
    for line in f:
        if debug: print line
        m = pattern.search(line)
        if m:
            if verbose: print line
            hrs = m.group(group)
            return hrs
        else:
            continue
    else:
        raise RuntimeError("Did not find pattern")
        return

def lookforpatternwithgroupnextline(f, pattern1, pattern2, group):
    #go through file f until pattern1 is found
    #retrun the specified group for pattern2 on the next line
    found = False
    for line in f:
        if debug: print line
        m = pattern1.search(line)
        if m:
            if verbose: print line
            found = True
        elif found:
            m2 = pattern2.search(line)
            if m2:
                if verbose: print line
                hrs = m2.group('hours')
                return hrs
            else:
                raise RuntimeError("Did not find hours")
        else:
            continue
    else:
        raise RuntimeError("Did not find pattern")
        return


def get_reconfig_times(logname):
    """Find reconfig times in a reconfig log file"""

    if logname == "":
        lsdcmd = "ls -td /var/opt/teradata/TDput/fileservice/logs/pdeconfig_*"
        p1 = Popen(lsdcmd, shell=True, stdout=PIPE, stderr=STDOUT)
        stdout, stderr = p1.communicate()
        
        dir=stdout.splitlines()[0]
        p1.stdout.close()
        
        
        lscmd = "ls {0}/*reconfig.out.log".format(dir)
        p2 = Popen(lscmd, shell=True, stdout=PIPE, stderr=STDOUT)
        stdout, stderr = p2.communicate()
        logname = stdout.rstrip()
        p2.stdout.close()

    #copy reconfig log to local directory for archiving
    cpcmd = "cp {0} .".format(logname)
    if verbose: print cpcmd
    p2 = Popen(cpcmd, shell=True, stdout=PIPE, stderr=STDOUT)
    stdout, stderr = p2.communicate()

    if verbose: 
        print "Getting Reconfig Times from:"
        print logname
        localtime = datetime.datetime.now()
        print "Local time: {0}\n"\
              .format(localtime.strftime("%Y-%m-%d %H:%M:%S"))


    with open(logname, 'r') as f:


        if verbose: print "Looking for start -"
        #Looking for:
        # 20439 INFO: Command loop: Input line is 1:System Time (Reconfiguration): 16/06/20 13:41:49.
        starttime = lookforpattern(f, r_reconfig)

        if verbose: print "Looking for estimated redistribution time -"
        #Looking for:
        # 20439 INFO: Command loop: Input line is 1:      2.01 hours (for offline reconfig).
        estredisthrs = lookforpatternwithgroup(f, r_estredist,'hours')

        if verbose: print "Looking for estimated table deletion time -"
        #Looking for:
        # 20439 INFO: Command loop: Input line is 1:The estimated table deletion time will be:
        estdelhrs = lookforpatternwithgroupnextline(f, r_estdel, r_estdeltime, 'hours')

        if verbose: print "Looking for hash map calculation begins -"
        #Looking for: 
        # 20439 INFO: Command loop: Input line is 1:16/06/20 13:46:31 Hash Map Calculation Phase Begins
        hashmapbegintime = lookforpattern(f, r_hashmapbegin)

        if verbose: print "Looking for hash map calculation ends -"
        #Looking for: 
        # 20439 INFO: Command loop: Input line is 1:16/06/20 13:47:51 Hash Map Calculation Phase Ends
        hashmapendtime = lookforpattern(f, r_hashmapend)

        if verbose: print "Looking for table redistribution begins -"
        #Looking for: 
        # 20439 INFO: Command loop: Input line is 1:16/06/20 13:47:51 Table Redistribution Phase Begins
        redistbegintime = lookforpattern(f, r_redistbegin)

        if verbose: print "Looking for table redistribution ends -"
        #Looking for: 
        # 20439 INFO: Command loop: Input line is 1:16/06/20 23:59:05 Table Redistribution Phase Ends (TeradataUtilities.cpp+2506)
        redistendtime = lookforpattern(f, r_redistend)

        if verbose: print "Looking for table deletion begins -"
        #Looking for: 
        # 20439 INFO: Command loop: Input line is 1:16/06/20 23:59:05 Old Table Deletion Phase Begins
        delbegintime = lookforpattern(f, r_delbegin)

        if verbose: print "Looking for table deletion ends -"
        #Looking for: 
        # 20439 INFO: Command loop: Input line is 1:16/06/21 03:29:03 Old Table Deletion Phase Ends
        delendtime = lookforpattern(f, r_delend)

        if verbose: print "Looking for reconfiguration complete -"
        #Looking for:
        # 20439 INFO: Command loop: Input line is 1:System Time (Reconfiguration): 16/06/21 03:29:04
        endtime = lookforpattern(f, r_reconfig)


    redisttime =  redistendtime - redistbegintime
    deltime = delendtime - delbegintime
    redistplusdeltime = redisttime + deltime

    print "Reconfig start time:                     ", starttime
    print "Estimated table redistribution time:                  {0} hrs".format(estredisthrs)
    print "Estimated old table deletion time:                    {0} hrs".format(estdelhrs)
    print "hash map calculation phase begin time:   ", hashmapbegintime
    print "hash map calculation phase end time:     ", hashmapendtime
    print "redistribution begin time:               ", redistbegintime
    print "redistribution end time:                 ", redistendtime
    print "redistribution duration:                            ", redisttime
    print "old table deletion begin time:           ", delbegintime
    print "old table end begin time:                ", delendtime
    print "old table deletion duration:                        ", deltime
    print "Reconfig end time:                       ", endtime
    print "redistribution + table deletion duration:           ", redistplusdeltime
    print "Total reconfig time:                                ",  endtime - starttime


    return



############################################################################
def main():
    global debug
    global verbose

    usage="%prog [-h] [-d] [-v] [-f]"
    parser = OptionParser(usage, version="%prog 0.1")
    parser.add_option("-d", "--debug", 
                      action="store_true", dest="debug", default=False,
                      help="enable debug mode")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="enable vebose mode")
    parser.add_option("-f", "--file", dest="logname", default="",
                      help="log file, default=most recent /var/opt/teradata/TDput/fileservice/logs/pdeconfig_yy.mm.dd_hh.mm.ss/*reconfig.out.log")
    (options, args) = parser.parse_args()
    debug = options.debug
    verbose = options.verbose
    logname = options.logname


    get_reconfig_times(logname)


    if verbose: print "\nDone"
################################################################################
if __name__ == "__main__":
    main()


