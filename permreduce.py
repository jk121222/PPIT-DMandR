#!/usr/bin/python

################################################################################
# permreduce.py
# written for python 2.6.9 (Teradata module for bteq access supported in 2.7)
# Remove DM&R populate tables until the specified fill percent is reached
# Written by: John Kim
# Date 2016-06-23
#
# Examples:
# permreduce.py -v -p 30 --doit
################################################################################

import time
import datetime
import re
import os
from subprocess import Popen, PIPE, STDOUT, call
from optparse import OptionParser
from collections import deque


debug = False
verbose = True


def getperm(bindir, disksumscript):
    #execute getdisksum.sh and return (currentperm, maxperm)
    #              Sum(CurrentPerm)  22,141,472,559,104.00   73,154,258,515,888.
    re_currperm = re.compile("""Sum\(CurrentPerm\)\s+
                                    (?P<currentperm>\d{1,3}(,\d{3})*(\.\d+)?)\s+
                                    (?P<maxperm>\d{1,3}(,\d{3})*(\.\d+)?)
                             """, re.VERBOSE)

    cmd="{0}/{1}".format(bindir,disksumscript)
    if debug: print "cmd=", cmd
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    stdout, stderr = p.communicate()
    for line in stdout.splitlines():
        if debug: print line
        s = re_currperm.search(line)
        if s:
            currentperm = int(float(s.group('currentperm').replace(',','')))
            maxperm = int(float(s.group('maxperm').replace(',','')))
            if debug: print "currentperm {0}, maxperm: {1}"\
                            .format(currentperm, maxperm)
            return currentperm, maxperm
    else:
        raise RuntimeError("Couldn't find currentperm/maxperm")


#TableName                            sumcurrentperm
#------------------------------  -------------------
##?                                21,503,711,211,520
#lineitem_0000                               720,896
#...
#ordertbl_ppi_small_0053             139,155,255,296
#
#+---------+---------+---------+---------+---------+---------+---------+----
def get_ppit_one(bindir, ppitonescript):
    table_list = []
    #Execute get_ppit_one_tables.sh and return a list of 
    #(tablename, sumcurrentperm) sorted by sumcurrentperm
    if debug: print "get_ppit_one", bindir, ppitonescript
    cmd="{0}/{1}".format(bindir, ppitonescript)
    if debug: print "cmd=", cmd
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    stdout, stderr = p.communicate()
    it = iter(stdout.splitlines())
    line = it.next()
    if debug: print line
    re_header=re.compile("TableName                            sumcurrentperm")
    re_header2=re.compile("TableName                          Sum\(CurrentPerm\)")
    s = re_header.match(line)
    s2 = re_header2.match(line)
    headerfound=False
    if s or s2:  #only if file was truncated
        #TableName                            sumcurrentperm
        if debug: print "header found"
        headerfound=True
    while not headerfound:
        line = it.next()
        if debug: print line
        s = re_header.match(line)
        s2 = re_header2.match(line)
        if s or s2:
            #TableName                            sumcurrentperm
            if debug: print "header found"
            headerfound=True
      
    #read the underline and discard
    #------------------------------  -------------------
    line = it.next()
    if debug: print "read underline:", line

    #read the sum and discard
    ##?                                21,503,711,211,520
    line = it.next()
    if debug: print "read sum:", line

    endfound=False
    if debug: print "Reading tables"
    while not endfound:
        line = it.next()
        if debug: print line
        re_table = re.compile("""(?P<tablename>\w[\w_]*\d+)\s+
                                 (?P<sumcurrentperm>\d{1,3}(,\d{3})*)
                             """, re.VERBOSE)
        re_end = re.compile("\+---------\+---------\+---------\+---------\+---------\+---------\+---------\+----")

        s_table = re_table.search(line)
        s_end = re_end.search(line)
        if s_end:
            #+---------+---------+---------+---------+---------+---------+---------+----
            if debug: print "end found"
            break
        elif s_table:
            #lineitem_0000                               720,896
            table = s_table.group('tablename')
            sumcurrentperm = s_table.group('sumcurrentperm')
            table_list.append((table, sumcurrentperm))

    if debug: 
        print "Table list:"
        print table_list

    #sort table list by size, largest first
    #could have had bteq do the sorting but this way it doen't matter
    def getkey(item):
        return int(item[1].replace(",",""))
    sorted_table_list = sorted(table_list, key=getkey, reverse=True)

    if debug: 
        print "Sorted Table list:"
        print sorted_table_list

    return sorted_table_list


#Add commas to an integer, return as string
#Could use "{:,}".format(value) in python 2.7
def commafy(n):
    return ''.join(reversed([x + (',' if i and not i % 3 else '') 
                   for i, x in enumerate(reversed(str(n)))]))


def writebteqhead(f, logonstr="dbc/dbc, dbc"):
    f.write("bteq<<[bteq]\n")
    #f.write(".logon dbc/dbc, dbc;\n")
    f.write(".logon " + logonstr + ";\n")


def writebteqtail(f):
    f.write(".logoff\n")
    f.write(".quit\n")
    f.write("[bteq]\n")


def makeexecutable(filename):
    call(['chmod', 'a+x', filename])


def writedisksumscript(qualdisksumscript, logonstr="dbc/dbc, dbc"): 
    with open(qualdisksumscript, "w") as f:
        writebteqhead(f, logonstr)
        f.write("""\
sel diskspace.databasename,
sum(currentperm) (format 'zzz,zzz,zzz,zzz,zz9.99')
,sum(maxperm) (format 'zzz,zzz,zzz,zzz,zz9.99')
group by databasename
order by databasename
with sum(currentperm)(format 'zzz,zzz,zzz,zzz,zz9.99')
,sum(maxperm)(format 'zzz,zzz,zzz,zzz,zz9.99');
""")
        writebteqtail(f)
        makeexecutable(qualdisksumscript)


def writegetppitonescript(qualppitonescript, databasename, logonstr="dbc/dbc, dbc"): 
    #qualppitonescript = bindir+'/'+ppitonescript
    with open(qualppitonescript, "w") as f:
        writebteqhead(f, logonstr)
        f.write("SELECT TABLENAME, SUM(CURRENTPERM) AS sumcurrentperm\n")
        f.write(" FROM DBC.TABLESIZE\n")
        f.write(" WHERE DATABASENAME = '{0}'\n".format(databasename))
        f.write("GROUP BY rollup (TABLENAME)\n")
        f.write("ORDER BY sumcurrentperm DESC;\n")
        writebteqtail(f)
        makeexecutable(qualppitonescript)


###########################################################################
def main():

    global debug
    global verbose

    delay = 10  #seconds to delay before deleting

    usage="%prog [-h] [-d] [-q] [-p] [-m] [-b] [--db] [-s] [-g] [-o] [-l] [--doit]"
    parser = OptionParser(usage, version="%prog 0.5")
    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="enable debug mode")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="disable vebose mode")
    parser.add_option("-p", "--percent", type="int", dest="percent", default=60,
                      help="percent of perm fill desired, default=60")
    parser.add_option("-m", "--margin", type="float", dest="margin", default=0.0001,
                      help="allowed margin of error, default=0.0001")
    parser.add_option("-b", "--bin",  dest="bindir", default="/home/jk121222/bin",
                      help="directory for disksum and get_ppit_one_tables commands, default=/home/jk121222/bin")
    parser.add_option("--db",  dest="databasename", default="ppit_one",
                      help="database to reduce, default=ppit_one")
    parser.add_option("-s", "--disksum",  dest="disksumscript", default="getdisksum.sh",
                      help="disksum command, default=getdisksum.sh")
    parser.add_option("-g", "--getppitone",  dest="ppitonescript", default="get_ppit_one_tables.sh",
                      help="command to get the database tables, default=get_ppit_one_tables.sh")
    parser.add_option("-o", "--outbteqscript",  dest="bteqscript", default="deletetables.sh",
                      help="created script to reduce the database, default=deletetables.sh")
    parser.add_option("-l", "--logon",  dest="logonstr", default="dbc/dbc, dbc",
                      help="bteq logon string, default='dbc/dbc, dbc'")
    parser.add_option("--doit",
                      action="store_true", dest="doit", default=False,
                      help="Do the deletion, default=False")
    (options, args) = parser.parse_args()

    debug = options.debug
    verbose = options.verbose
    targetpct = options.percent
    margin = options.margin
    bindir = options.bindir
    databasename = options.databasename
    disksumscript = options.disksumscript
    ppitonescript = options.ppitonescript
    bteqscript = options.bteqscript
    logonstr = options.logonstr
    doit = options.doit

    if not os.path.isdir(bindir):
        print "bin directory:", bindir, "does not exist."
        createit = raw_input("Create it? (y/n)")
        if createit=="y":
            call(['mkdir', bindir])
        else:
            quit()

    qualdisksumscript = bindir+'/'+disksumscript
    if not os.path.exists(qualdisksumscript):
        print "get disksum script:",qualdisksumscript, "does not exist."
        createit = raw_input("Create it? (y/n)")
        if createit=="y":
            writedisksumscript(qualdisksumscript, logonstr)
        else:
            quit()
    elif not os.access(qualdisksumscript, os.X_OK):
        print "get disksum script:",qualdisksumscript, "is not executable."
        fixit = raw_input("Fix it? (y/n)")
        if fixit=="y":
            makeexecutable(qualdisksumscript)
        else:
            quit()

    qualppitonescript = bindir+'/'+ppitonescript
    if not os.path.exists(qualppitonescript):
        print "get ppit_one_tables script:",qualppitonescript, "does not exist."
        createit = raw_input("Create it? (y/n)")
        if createit=="y":
            writegetppitonescript(qualppitonescript, databasename, logonstr) 
        else:
            quit()
    elif not os.access(qualppitonescript, os.X_OK):
        print "get ppit_one_tables script:",qualppitonescript, "is not executable."
        fixit = raw_input("Fix it? (y/n)")
        if fixit=="y":
            makeexecutable(qualppitonescript)
        else:
            quit()

    
    #Execute disksum to get the currentperm and maxperm
    (currentperm, maxperm) = getperm(bindir, disksumscript)
    currentpct = float(currentperm)/float(maxperm)*100
    targetcurrentperm = int(round(float(targetpct)/100 * maxperm))
    if verbose:
        print "MaxPerm            = {0:>20s}" .format(commafy(maxperm))
        print "CurrentPerm        = {0:>20s}".format(commafy(currentperm))
        print "pct        = {0:0.2f}%".format(currentpct)
        print "target pct = {0:0.2f}%".format(targetpct)
        print "Target CurrentPerm = {0:>20s}".format(commafy(targetcurrentperm))
    if targetcurrentperm < (1 - margin) * currentperm:
        targetreduction = currentperm - targetcurrentperm
        if verbose:
            print "Target Reduction   = {0:>20s}".format(commafy(targetreduction))
            print

        #get sorted list of tables
        #(not necessary to sort if already sorted but can't be sure)
        table_list = get_ppit_one(bindir, ppitonescript)

        newperm = currentperm
        tableit = iter(table_list)
        if verbose: 
            print "Creating", bteqscript
        with open(bteqscript, "w") as f:
            writebteqhead(f, logonstr)

            while newperm > (1 + margin) * targetcurrentperm:
                table = next(tableit, ("no_more_tables",0))
                if table == ("no_more_tables",0): 
                    if verbose: 
                        print "No more tables"
                    break
                tablename = table[0]
                tablesize = int(table[1].replace(",",""))
                if newperm - tablesize >= (1 - margin) * targetcurrentperm:
                    newperm -= tablesize
                    newpct = float(newperm)/float(maxperm)*100
                    f.write("delete {0}.{1};\n".format(databasename, tablename))
                    if verbose: 
                        print "delete {0}.{1:<23};   size: {2:>16}, new pct: {3:0.2f}%"\
                              .format(databasename, tablename, commafy(tablesize), newpct)
            writebteqtail(f)
            call(['chmod', 'a+x', bteqscript])
    else:
        if verbose:
            print "Nothing to do"

    
    if doit:  # delete the tables
        print "Deletion will begin in {0} seconds.".format(delay)
        for t in reversed(xrange(delay)):
            time.sleep(1)
            if verbose:
                print t

        os.system(bteqscript)
        (currentperm, maxperm) = getperm(bindir, disksumscript)
        currentpct = float(currentperm)/float(maxperm)*100
        if verbose:
            print "CurrentPerm        = {0}".format(commafy(currentperm))
            print "MaxPerm            = {0}" .format(commafy(maxperm))
            print "pct                = {0:0.2f}%".format(currentpct)

    if verbose: print "\nDone"
           

################################################################################
if __name__ == "__main__":
    main()

