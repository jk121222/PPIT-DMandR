#!/usr/bin/python

################################################################################
# savesysteminfo.py
# written for python 2.6.9 (Teradata module for bteq access supported in 2.7)
# DM&R script to capture configuration after configuration changes
# Written by: John Kim
# Date 2016-06-27
# 
# ex run all (run all if no functions specified) and save to ./initial: 
#  savesysteminfo.py -o initial -b ../bin
# ex run configuration status checks, quiet mode, save to full directory path: 
#  savesysteminfo.py --config -q -o /tmp
# ex get current status, verbose mo, savedi to current directory: 
#  savesysteminfo.py --status -v 2>&1 | tee  savesysteminfo.log
################################################################################

from __future__ import print_function
import sys
import time
import datetime
import re
import os
from subprocess import Popen, PIPE, STDOUT, call
from optparse import OptionParser, OptionGroup


now = datetime.datetime.now()
disksumscript = "getdisksum.sh"
#datacheckscript = "dmandr_datacheck.sh"  #scandisk/checktable
datacheckscript = "runscandisktests.sh"  #scandisk/checktable
estcomprscript = "estcompr.pl"
cwd = ""


def eprint(*args, **kwargs):
    """print to stderr"""
    print(*args, file=sys.stderr, **kwargs)

def get_timestr():
    """Return the current date/time as 'yyyy-mm-dd.hh:mm:ss'"""
    return datetime.datetime.now().strftime("%Y-%m-%d.%H:%M:%S")


def getcwd():
    cmd = 'pwd' 
    if verbose: print("cmd=" + cmd)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    stdout, stderr = p.communicate()
    line = stdout.splitlines()[0]
    if verbose: print("cwd=" + line)
    return line


def copy(dir, basename):
    """copy <dir>/<basename> to ./basename.<current time>, return filename"""
    outfile = basename + '.' + get_timestr()
    fqoutfile = outdir + '/' + outfile
    cmd = "cp " + dir + "/" + basename + " " + outfile
    if not quiet: print("cmd: " + cmd + " to " + fqoutfile)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT, cwd=outdir)
    stdout, stderr = p.communicate()
    return fqoutfile


def runcmd(cmd, basename=""):
    """Run cmd, save output in basename.<current time>, return filename"""
    outfile = basename + '.' + get_timestr()
    fqoutfile = outdir + '/' + outfile
    if not quiet: 
        if basename != "":
            print("cmd: " +  cmd + " to " + fqoutfile)
        else:
            print("cmd: " +  cmd)
    if not verbose:
        #print stderr but not stdout to screen
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, cwd=outdir)
        stdout, stderr = p.communicate()
        for line in stderr.splitlines():
            eprint(line)
    else:
        #print stderr and stdout to screen
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT, cwd=outdir)
        stdout, stderr = p.communicate()

    if basename != "":
        #print stdout to file
        with open(fqoutfile, "w") as f:
            for line in stdout.splitlines():
                if verbose: print(line)
                f.write(line + '\n')

    return fqoutfile


def pdestate(writetofile=False):
    """Check for PDE/DBS up"""
    #outdir must exist before calling
    
    #PDE state is RUN/STARTED.
    #DBS state is 4: Logons are enabled - Users are logged on
    #or
    #PDE state is RUN/STARTED.
    #DBS state is 5: Logons are enabled - The system is quiescent
    rup = re.compile('Logons are enabled')
    rrs = re.compile('PDE state is RUN/STARTED.')

    outfile = 'pdestate.' + datetime.datetime.now().strftime("%Y-%m-%d.%H:%M:%S")
    fqoutfile = outdir + '/' + outfile
    if writetofile: f = open(fqoutfile, "w")
  
    cmd = "pdestate -a"
    if not quiet: 
        if writetofile:
            print("cmd: " +  cmd + " to " + fqoutfile)
        else:
            print("cmd: " +  cmd)
    dbs_up = False
    pde_up = False
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    stdout, stderr = p.communicate()

    for line in stdout.splitlines():
        if writetofile: f.write(line + '\n')
        mrs = rrs.match(line)   #PDE state is RUN/STARTED.
        if mrs:
            pde_up = True
        mup = rup.search(line)     # Logons are enabled
        if mup:
            if debug: print("Found:  Logons are enabled")
            dbs_up = True
        if pde_up and dbs_up:
            break;

    if not quiet:
        if  pde_up: 
            print ("PDE is up")
        else:
            print ("PDE is down")
        if dbs_up: 
            print ("DBS is up")
        else: 
            print ("DBS is down")
    if writetofile: f.close()

    return (pde_up, dbs_up)


def whatsup():
    """execute whatsup"""
    basename = "whatsup"
    cmd = '/opt/teradata/TDput/bin/whatsup.sh'
    runcmd(cmd, basename)


def vprocstatus():
    """Get vprocmonitor status"""
    basename = "vprocmanager_status"
    if not pde_up:
        raise RuntimeError("can't get vprocmanager status, PDE not up")
    cmd = 'echo "status" | /usr/tdbms/bin/vprocmanager'
    runcmd(cmd, basename)


def vprocstatnot():
    """Get vprocmonitor status"""
    basename = "vprocmanager_statnot"
    if not pde_up:
        raise RuntimeError("can't get vprocmanager status, PDE not up")
    cmd = 'echo "stat not" | vprocmanager'
    runcmd(cmd, basename)


def hostname(copy = True):
    """Get hostname"""
    cmd = "hostname"
    basename = "hostname"
    outfile = basename + '.' + get_timestr()
    fqoutfile = outdir + '/' + outfile
    if not quiet:
        if basename != "":
            print("cmd: " +  cmd + " to " + fqoutfile)
        else:
            print("cmd: " +  cmd)
    if not verbose:
        #print stderr but not stdout to screen
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, cwd=outdir)
        stdout, stderr = p.communicate()
        for line in stderr.splitlines():
            eprint(line)
    else:
        #print stderr and stdout to screen
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT, cwd=outdir)
        stdout, stderr = p.communicate()

    #print stdout to file
    if copy: fo = open(fqoutfile, "w")

    line = stdout.rstrip()

    if verbose: print("hostname: ", line)
    if copy: 
        fo.write(line)
        fo.close()

    return line




def psh_hostname(copy = True):
    """get psh hostname, write output if copy==True get node ip to hostname dictionary"""
    global nodeip2hostname
    nodeip2hostname = {}

    cmd = 'psh hostname'
    #<---------------------  39.48.8.2  -------------------------------->
    #ppit11
    #rip = re.compile('<---------------------\s+(?P<ip>\d+.\d+.\d+.\d+)')
    rip = re.compile('(?P<ip>\d+.\d+.\d+.\d+)')

    basename = "psh_hostname"
    outfile = basename + '.' + get_timestr()
    fqoutfile = outdir + '/' + outfile
    if not quiet:
        if basename != "":
            print("cmd: " +  cmd + " to " + fqoutfile)
        else:
            print("cmd: " +  cmd)
    if not verbose:
        #print stderr but not stdout to screen
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, cwd=outdir)
        stdout, stderr = p.communicate()
        for line in stderr.splitlines():
            eprint(line)
    else:
        #print stderr and stdout to screen
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT, cwd=outdir)
        stdout, stderr = p.communicate()

    #print stdout to file
    if copy:
        fo =  open(fqoutfile, "w")

    found_ip = False
    for line in stdout.splitlines():
        if verbose:
            print(line)
        if copy:
            fo.write(line + '\n')

        mip = rip.search(line)
        if mip:  #found ip address
            ip = mip.group('ip')
            found_ip = True #look for hostname on next line
            if debug:
                print("ip address: ", ip)
        elif found_ip:
            hostname = line.strip()
            if hostname=="":
                raise RuntimeError("psh hostname returned ip address with no hostname")
            nodeip2hostname[ip] = hostname
            if debug:
                print("hostname: ", hostname)
            found_ip = False


    if copy: fo.close()


def psh_i_s(copy = True):
    """Get psh info sys, get cn, cliqreplist, nodelist"""
    #Requires nodeip2hostname map to exist (from hostname)
    #!!! If output is sorted by ip rather than node_id, the cn might not be selected corrrectly
 
    global nodeip2hostname
    global cn      #The lowest numbered node (control node)
    global cliqreplist  #A list of the lowest numbered node in each clique, except the cn
    global nodelist#list of nodes other than cn or cc
    cn = ""
    cliqreplist = []
    nodelist = []
    current_clique = -1 

    cmd = 'psh i s'
#<---------------------  cliq_00  -------------------------------->
#39.48.8.2 001-02 34 (45) :   0    3    4    7    8   11   12   29   30   33   34   37   38   55   56   59   60   63   64   67   80   83   84   87   88   91   92  109  110  113  114  117  118  135  136  139  140  143  144  147 22528 26623 28671 30718 30719

    rcliq = re.compile('cliq_(?P<clique_id>\d+)')
    rnode = re.compile('(?P<node_ip>\d+.\d+.\d+.\d+)')

    basename = "pshis"
    outfile = basename + '.' + get_timestr()
    fqoutfile = outdir + '/' + outfile
    if not quiet:
        if basename != "":
            print("cmd: " +  cmd + " to " + fqoutfile)
        else:
            print("cmd: " +  cmd)
    if not verbose:
        #print stderr but not stdout to screen
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, cwd=outdir)
        stdout, stderr = p.communicate()
        for line in stderr.splitlines():
            eprint(line)
    else:
        #print stderr and stdout to screen
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT, cwd=outdir)
        stdout, stderr = p.communicate()

    #print stdout to file
    if copy:
        fo =  open(fqoutfile, "w")

    for line in stdout.splitlines():
        if verbose:
            print(line)
        if copy:
            fo.write(line + '\n')

        mcliq = rcliq.search(line)
        mnode = rnode.match(line)
        if mcliq:  #found clique devision
            clique = mcliq.group('clique_id')
            found_clique = True #look for nodes in following lines
            if debug: print("found clique: ", clique)
        elif mnode:
            node_ip  = mnode.group('node_ip')
            hostname = nodeip2hostname[node_ip]
            if debug: print("found node", node_ip, hostname)
            if cn == "":
                cn = hostname
                found_clique = False
            elif found_clique == True:
                print("Adding ", hostname, " to clique node list")
                cliqreplist.append(hostname)
                found_clique = False
            else:
                nodelist.append(hostname)

    if copy: fo.close()

    if not quiet:
        print("control node (cn): " + cn)
        print("lowest node on each clique (except cn): ", cliqreplist)
        print("other nodes: ", nodelist)


def vconfig():
    """save vconfig settings."""
    copy('/etc/opt/teradata/tdconfig', 'vconfig.txt')

#def vconfig(copy = True):
#    """save vconfig settings. Find control node and first node in each clique"""
#    global cn       #The lowest numbered node (control node)
#    global cclist  #A list of the lowest numbered node in each clique, except the cn
#    global nodelist#list of nodes other than cn or cc
#    cn = ""
#    cclist = []
#    nodelist = []
#    current_clique = 0
#
#    #Pattern to find node
#    #NODE
#    ##CL_ID  NODE_ID KIND    SLAN    CLAN    PDN     TPA_OK SYSTEMFAMILY
#    #   0    002-02  XEON      N       N      N         Y    FAMILY_2850
#    rn = re.compile("""(?P<cl_id>\d+)\s+
#                       (?P<node_id>\d+-\d+)\s+
#                       (?P<kind>\w+)\s+
#                       (?P<slan>[YN])\s+
#                       (?P<clan>[YN])\s+
#                       (?P<pdn>[YN])\s+
#                       (?P<tpa_ok>[YN])\s+
#                       (?P<family>FAMILY_\d+)
#                    """, re.VERBOSE)
#
#    vconfigfile = "/etc/opt/teradata/tdconfig/vconfig.txt"
#    basename = "vconfig"
#    outfile = basename + '.' + get_timestr()
#    fqoutfile = outdir + '/' + outfile
#    if copy and not quiet: print("copying /etc/opt/teradata/tdconfig/vconfig.txt to " + outdir)
#    with open(vconfigfile, "r") as fi:
#        if copy: fo = open(fqoutfile, "w")
#        for line in fi:
#            if copy and verbose: print(line.rstrip())
#            if copy: fo.write(line)
#            mn = rn.search(line)
#            if mn: # Node found
#                node = mn.group('node_id')
#                clique = int(mn.group('cl_id'))
#                if cn=="":
#                    cn = node
#                elif clique > current_clique:
#                    current_clique =  clique
#                    cclist.append(node)
#                else:
#                    nodelist.append(node)
#
#    if copy: fo.close()
#    if verbose:
#        print("control node (cn): " + cn)
#        print("lowest node on each clique (except cn): ", cclist)
#        print("other nodes: ", nodelist)



def messages():
    """save /var/log/messages"""
    copy('/var/log', 'messages')


def rpm_qa():
    """execute rpm -qa"""
    basename = "rpm_qa"
    cmd = 'rpm -qa'
    runcmd(cmd, basename)


def bam_a():
    """Get bam -a"""
    basename = 'bam_a'
    cmd = '/opt/teradata/bynet/bin/bam -a'
    runcmd(cmd, basename)


def ifconfig_a():
    """Get ifconfig -a"""
    basename = 'ifconfig_a'
    cmd = 'ifconfig -a'
    runcmd(cmd, basename)


def hwinfo():
    """Get hwinfo"""
    basename = 'hwinfo'
    cmd = 'hwinfo'
    runcmd(cmd, basename)


def tpatrace_u(tpatrace_ucycles=5):
    """Get tpatrace -u"""
    basename = 'tpatrace_u'
    cmd = 'tpatrace -u ' + str(tpatrace_ucycles)
    runcmd(cmd, basename)


def verifypdisks():
    """Get verify_pdisks"""
    basename = 'verify_pdisks'
    cmd = 'verify_pdisks'
    runcmd(cmd, basename)


def isdell():
    "return True if dell node"
    dellfound = os.path.exists("/opt/dell")
    if not quiet: 
        if dellfound: print("Dell node")
        else: print("Intel node")
    return dellfound
 
    
def omreport():
    """Get omreport system summary"""
    #Get dell system summary
    basename = 'omreport'
    cmd = '/opt/dell/srvadmin/bin/omreport system summary'
    runcmd(cmd, basename)


def nodehw():
    if isdell():
        omreport()
    else:  #intel
        pass


#Could use "{:,}".format(value) in python 2.7
def commafy(n):
    """Add commas to an integer, return as string"""
    return ''.join(reversed([x + (',' if i and not i % 3 else '') 
                   for i, x in enumerate(reversed(str(n)))]))


def writebteqhead(f, logonstr="dbc/dbc, dbc"):
    """Write the start of a bteq script to a file"""
    f.write("bteq<<[bteq]\n")
    f.write(".logon " + logonstr + ";\n")


def writebteqtail(f):
    """Write the end of a bteq script to a file"""
    f.write(".logoff\n")
    f.write(".quit\n")
    f.write("[bteq]\n")


def makeexecutable(filename):
    call(['chmod', 'a+x', filename])


def writedisksumscript(qualdisksumscript, logonstr="dbc/dbc, dbc"): 
    """Create a bteq script to get the disksum"""
    with open(qualdisksumscript, "w") as f:
        writebteqhead(f, logonstr)
        f.write("""\
sel diskspace.databasename,
sum(currentperm) (format 'zzz,zzz,zzz,zzz,zz9.99')
,sum(maxperm) (format 'zzz,zzz,zzz,zzz,zz9.99')
group by databasename
order by databasename
with sum(currentperm)(format 'zzz,zzz,zzz,zzz,zz9.99')
,sum(maxperm)(format 'zzz,zzz,zzz,zzz,zz9.99')
,100*sum(currentperm)/sum(maxperm)(format 'zz9.99');
""")
        writebteqtail(f)
        makeexecutable(qualdisksumscript)


def ctl():
    """get ctl settings"""
    #Only needs to be run on one node
    basename = 'ctl'
    cmd =  'ctl -first "print; quit"'
    runcmd(cmd, basename)


def dbscontrol():
    """get dbscontrol settings"""
    #Only needs to be run on one node
    basename = 'dbscontrol'
    cmd = 'dbscontrol -a' 
    runcmd(cmd, basename)


def tvamconfig():
    """Get tvam configuration"""
    #Only needs to be run on one node
    basename = 'tvam_config'
    cmd = 'tvam -display -config'  #Run on one node per clique
    #cmd = 'globaltvam -c'  # only needs to be run on one node but not as reliable
    runcmd(cmd, basename)


def mapsummary():
    """Get tvam map summary"""
    #Only needs to be run on one node
    basename = 'tvam_map_summary'
    cmd = 'tvam -display -map -summary' #Run on one node per clique
    #cmd = 'globaltvam -s'  #only needs to be run on one node but not as reliable
    runcmd(cmd, basename)


def profilercheck():
    """Run tvsaProfilerCheck.sh"""
    #Run on one node per clique
    #could run tvsa -display -profile -summary for more details
    basename = 'tvsaProfilerCheck'
    cmd = 'tvsaProfilerCheck.sh'
    runcmd(cmd, basename)


def disksum():
    """Get disk summary"""
    #Only needs to be run on one node
    if not dbs_up:
        raise RuntimeError("Can't get disk summary, dbs not up")

    fqdisksumscript = bindir+'/'+disksumscript
    if not os.path.exists(fqdisksumscript):
        if not quiet:
            print(fqdisksumscript + " does not exist, creating")
        logonstr = "dbc/dbc, dbc"
        writedisksumscript(fqdisksumscript, logonstr)
        makeexecutable(fqdisksumscript)

    basename = 'disksum'
    #cmd = bindir + '/' + disksumscript
    #runcmd(cmd, basename)
    runcmd(fqdisksumscript, basename)


def datacheck():
    """Call script that runs scandisk and checktable for DM&R"""
    #Only needs to be run on one node
    #cmd = bindir + '/dmandr_datacheck.sh'
    if not dbs_up:
        raise RuntimeError("Can't run scandisk/checktable, dbs not up")
    cmd = bindir + '/' + datacheckscript
    runcmd(cmd)


def showwhere(scope="all"):
    """Run ferret showwhere"""
    #Only needs to be run on one node
    if not dbs_up:
        raise RuntimeError("Can't run showwhere, dbs not up")
    basename = 'showwhere_' + scope.replace(" ",'')
    cmd = '/usr/pde/bin/cnsrun -multi -utility ferret -commands \
           "{enable script} {scope ' + scope + ';} {showwhere;} {y} {quit}" -debug 1'
    runcmd(cmd, basename)


def showcylalloc(scope="all"):
    """Run ferret showcylalloc"""
    #Only needs to be run on one node
    if not dbs_up:
        raise RuntimeError("Can't run showcylalloc, dbs not up")
    basename = 'showcylalloc_' + scope.replace(" ",'')
    cmd = '/usr/pde/bin/cnsrun -multi -utility ferret -commands \
           "{enable script} {scope ' + scope + ';} {showcylalloc;} {y} {quit}" -debug 1'
    runcmd(cmd, basename)


def showblocks(scope="all"):
    """Run ferret showblocks"""
    #Only needs to be run on one node
    if not dbs_up:
        raise RuntimeError("Can't run showblocks, dbs not up")
    basename = 'showblocks_' + scope.replace(" ",'')
    cmd = '/usr/pde/bin/cnsrun -multi -utility ferret -commands \
           "{enable script} {scope ' + scope + '} {showblocks;} {y} {quit}" -debug 1'
    runcmd(cmd, basename)


def estcompr():
    """Run script to estimate compression ratio"""
    #Only needs to be run on one node
    if not dbs_up:
        raise RuntimeError("Can't estimate compression, dbs not up")
    """Call script to estimate compression ratio"""
    basename = 'estcompr'
    #cmd = bindir + '/estcompr.pl'
    cmd = bindir + '/' + estcomprscript
    runcmd(cmd, basename)


def hosts(copy = True):
    """read hosts file, copy if specified, create arraylist"""
    #ra = re.compile("(?P<ip>(\d+.\d+.\d+.\d+))\s+(?P<name>(damc\d\d\d(-\d+)*-\d+))", re.IGNORECASE)
    # Assumes arrays are named damc*
    global arraylist 
    arraylist = []

    ra = re.compile("(?P<ip>(\d+.\d+.\d+.\d+))\s+(?P<name>(DAMC\d\d\d(-\d+)*-\d+))", 
                     re.IGNORECASE)
    hostsfile = "/etc/hosts"
    outfile = "hosts." + datetime.datetime.now().strftime("%Y-%m-%d.%H:%M:%S")
    fqoutfile = outdir + '/' + outfile
    if copy and not quiet: print("copying /etc/hosts to " + outdir)
    with open(hostsfile, "r") as fi:
        if copy: fo = open(fqoutfile, "w")
        for line in fi:
            if verbose: print(line.rstrip())
            if copy: fo.write(line)
            ma = ra.search(line)
            if ma:
                arraylist.append((ma.group('ip'), ma.group('name')))
    if copy: fo.close()
    if debug: print(arraylist)


# SMcli completed successfully.

#SMcli doesn't exist:
#bash: SMcli: command not found

#SMcli exists but not netapp:
#There are currently no storage systems listed in the configuration file. Add
#storage systems using the Add Storage System option in the storage management
#software or by command line.
#
#SMcli failed.
def isnetapp():
    """Return true if arrays are netapp""" 
    rs = re.compile("SMcli completed successfully.")
    rn = re.compile("SMcli: command not found")
    rf = re.compile("SMcli failed.")
    netapppath = "/usr/bin/SMcli"  
    netapppathfound = os.path.exists(netapppath)  #not proof it's netapp though
    if netapppathfound:
        cmd = "SMcli -d -v"
        if verbose: print("Trying cmd=" + cmd + " to see if there are NetApp arrays.")
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        stdout, stderr = p.communicate()
        for line in stdout.splitlines():
            if verbose: print(line)
            if rs.search(line): 
                if verbose or debug: print("NetApp arrays")
                return True
            elif rn.search(line):
                if verbose or debug: print("Assume DotHill arrays")
                return False
            elif rf.search(line):
                if verbose or debug: print("Assume DotHill arrays")
                return False
    #raise RuntimeError("Can't figure out if this has NetApp arrays")
    return False


def netappconfig():
    """get netapp configuration"""
    # SMcli <conroller> -c "show allVolumes;"
    # hosts() needs to have run to get arraylist
    global arraylist
    for array in arraylist:
        controller = array[1]
        basename = controller
        cmd = 'SMcli ' + controller + ' -c "show allVolumes;"'

        runcmd(cmd, basename)


def dothillconfig():
    """get dothill array configuration"""
    # Assumes arrays are named damc*
    basename = 'dothillconfig' 
    cmd = 'rshfa -V dh damc* show configuration'
    runcmd(cmd, basename)
 

def arrayconfig():
    """get array configuration"""
    if isnetapp():
        if not quiet: print("Get NetApp array configuration")
        netappconfig()
    else: # dot hill
        if not quiet: print("Get DotHill array configuration")
        dothillconfig()


def getdir(path, base=""):
    """Return full path from path which may be a relative or full path"""
    #(returns directory without / at the end)
    if base=="":
        base = cwd
    if debug: print("getdir() base: " + base + " path: " + path)
    baselist = base.split("/")  #e.g. ['', 'home', 'jk121222', 'dmandrbin']

    if path == "":
        #no directory specified, use base
        dir = cwd
    elif path[0] == '/':
        #full path specified, use it
        dir = path
    elif path[0:2] == "..":
        #parent path specified
        #go up to the desired parent
        while re.match( '\.\.', path):
            path = re.sub('\.\./?', '', path, count=1)
            baselist.pop()

        dir = ''
        #make the baselist (now parent directory) back into a string
        for i in baselist:
            dir += i + '/'
        #add the path from the parent
        dir += path
        #if path is empty, there will be a / at the end, remove
        dir = re.sub('/$', '', dir)
    elif path[0:1] == ".":
        #relative path specified with current directory
        dir = base + path[1:]
        #if path is ./, there will be a / at the end, remove
        dir = re.sub('/$', '', dir)
    else:
        #relative path specified
        dir = base + '/' + path
    return dir

###########################################################################
def main():

    global debug
    global verbose #even print things that are being saved in a file
    global quiet

    global pde_up
    global dbs_up

    global cwd
    global outdir # directory to put results in
    global bindir # directory for commands requiring a script
    global arraylist
    arraylist= list()
    global cn
    global cliqreplist
    global nodelist
    global nodeip2hostname


    tpatrace_ucycles = 5  # number of cycles to retrieve for tpatrace_u


    usage="%prog [-h] "
    parser = OptionParser(usage, version="%prog 1.4")
    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="enable debug mode")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="enable vebose mode")
    parser.add_option("-q", "--quiet",
                      action="store_true", dest="quiet", default=False,
                      help="enable quiet mode")
    parser.add_option("-x", 
                      action="store_true", dest="dontrun", default=False,
                      help="don't run the fns")
    parser.add_option("-b", "--bindir",  dest="binpath", default="",
                      help="directory to find scripts \
                      estcompr.pl, runscandiskfns.sh, getdisksum.sh")
    parser.add_option("-o", "--outdir",  dest="outpath", default="",
                      help="directory to put results in")

    group = OptionGroup(parser, "Grouping options",
                                "If no functions are specified, --all will be run")
    group.add_option("-a", "--all",
                      action="store_true", dest="runall", default=False,
                      help="run all config, status, and dbs")
    group.add_option("-c", "--config",
                      action="store_true", dest="getconfig", default=False,
                      help="run all config")
    group.add_option("-s", "--status",
                      action="store_true", dest="getstatus", default=False,
                      help="run all status")
    group.add_option("-D", "--dbs",
                      action="store_true", dest="getdbs", default=False,
                      help="run all dbs")
    group.add_option("--persystem", 
                      action="store_true", dest="persystem", default=False,
                      help="run functions that only need to run on 1 node*")
    group.add_option("--perclique", 
                      action="store_true", dest="perclique", default=False,
                      help="run fns that only need to run on 1 node per clique**")
    group.add_option("--xpersystem", 
                      action="store_true", dest="xpersystem", default=False,
                      help="don't run fns that only need to run on 1 node")
    group.add_option("--xperclique", 
                      action="store_true", dest="xperclique", default=False,
                      help="don't run fns that only need to run on 1 node per clique")
    group.add_option("--pertype", 
                      action="store_true", dest="pertype", default=False,
                      help="only run fns appropriate for this node type")
    parser.add_option_group(group)

    group = OptionGroup(parser, "Config functions")
    group.add_option("--whatsup",
                      action="store_true", dest="getwhatsup", default=False,
                      help="run whatsup")
    group.add_option("--rpm_qa",
                      action="store_true", dest="getrpm_qa", default=False,
                      help="run rpm -qa")
    group.add_option("--ctl",
                      action="store_true", dest="getctl", default=False,
                      help="get ctl settings*")
    group.add_option("--dbscontrol",
                      action="store_true", dest="getdbscontrol", default=False,
                      help="get dbscontrol settings*")
    group.add_option("--vconfig",
                      action="store_true", dest="getvconfig", default=False,
                      help="save vconfig.txt")
    group.add_option("--hosts",
                      action="store_true", dest="gethosts", default=False,
                      help="save /etc/hosts")
    group.add_option("--tvamconfig",
                      action="store_true", dest="gettvamconfig", default=False,
                      help="run tvam -display -config**")
    group.add_option("--profilercheck",
                      action="store_true", dest="getprofilercheck", default=False,
                      help="run tvsaProfilerCheck.sh**")
    group.add_option("--ifconfig",
                      action="store_true", dest="getifconfig_a", default=False,
                      help="get ifconfig -a ")
    group.add_option("--bam",
                      action="store_true", dest="getbam_a", default=False,
                      help="get bam -a ")
    group.add_option("--nodehw",
                      action="store_true", dest="getnodehw", default=False,
                      help="get node hw setup")
    group.add_option("--hwinfo",
                      action="store_true", dest="gethwinfo", default=False,
                      help="get hwinfo")
    parser.add_option_group(group)

    group = OptionGroup(parser, "Status functions")
    group.add_option("--pdestate",
                      action="store_true", dest="savepdestate", default=False,
                      help="save pde/dbs state")
    group.add_option("--mapsummary",
                      action="store_true", dest="getmapsummary", default=False,
                      help="run tvam -display -map -summary**")
    group.add_option("--array",
                      action="store_true", dest="getarray", default=False,
                      help="get array configuration**")
    group.add_option("--vprocstatus",
                      action="store_true", dest="getvprocstatus", default=False,
                      help="run vprocmanager status*")
    group.add_option("--tpatrace_u", 
                      action="store_true", dest="gettpatrace_u", default=False,
                      help="get tpatrace_u -u 5")
    group.add_option("--verifypdisks", 
                      action="store_true", dest="getverifypdisks", default=False,
                      help="get verify_pdisks**")
    group.add_option("--messages", 
                      action="store_true", dest="getmessages", default=False,
                      help="save /var/log/messages")
    parser.add_option_group(group)

    group = OptionGroup(parser, "DBS functions")
    group.add_option("--disksum",
                      action="store_true", dest="getdisksum", default=False,
                      help="get disk summary*")
    group.add_option("--where",
                      action="store_true", dest="getshowwhere", default=False,
                      help="run ferret showwhere scope all*")
    group.add_option("--blocks",
                      action="store_true", dest="getshowblocks", default=False,
                      help="run ferret showblocks scope all*")
    group.add_option("--cylalloc",
                      action="store_true", dest="getshowcylalloc", default=False,
                      help="run ferret showcylalloc scope all*")
    parser.add_option_group(group)

    group = OptionGroup(parser, "Stand-alone functions not run with any groups")
    group.add_option("--datacheck",
                      action="store_true", dest="getdatacheck", default=False,
                      help="run <bin>/dmandr_datacheck.sh for scandisk/checktable*")
    group.add_option("--estcompr",
                      action="store_true", dest="getestcompr", default=False,
                      help="run <bin>/estcompr.pl script to estimate compression*")
    group.add_option("--vprocstatnot",
                      action="store_true", dest="getvprocstatnot", default=False,
                      help="run vprocmanager stat not*")
    group.add_option("--where1",
                      action="store_true", dest="getshowwhere1", default=False,
                      help="run ferret showwhere scope vproc 1*")
    group.add_option("--nodetype",
                      action="store_true", dest="getnodetype", default=False,
                      help="determine type of node: CN (control node), CR (clique representative), ON (ordinary node)")
    group.add_option("--hostname",
                      action="store_true", dest="gethostname", default=False,
                      help="get hostname")
    group.add_option("--pshhostname",
                      action="store_true", dest="getpsh_hostname", default=False,
                      help="get psh hostname")
    group.add_option("--pshis",
                      action="store_true", dest="getpsh_i_s", default=False,
                      help="get psh info sys")
    parser.add_option_group(group)

    (options, args) = parser.parse_args()


    debug = options.debug
    verbose = options.verbose
    quiet = options.quiet
    dontrun = options.dontrun
    outpath = options.outpath
    binpath = options.binpath

    runall = options.runall
    getconfig = options.getconfig
    getstatus = options.getstatus
    getdbs = options.getdbs
    persystem = options.persystem
    perclique = options.perclique
    xpersystem = options.xpersystem
    xperclique = options.xperclique
    pertype = options.pertype

    getwhatsup = options.getwhatsup
    getrpm_qa = options.getrpm_qa
    getctl = options.getctl
    getdbscontrol = options.getdbscontrol
    getvconfig = options.getvconfig
    gethosts = options.gethosts
    gettvamconfig = options.gettvamconfig
    getprofilercheck = options.getprofilercheck
    getifconfig_a = options.getifconfig_a
    getbam_a = options.getbam_a
    getnodehw = options.getnodehw
    gethwinfo = options.gethwinfo

    savepdestate = options.savepdestate
    getmapsummary = options.getmapsummary
    getarray = options.getarray
    getvprocstatus = options.getvprocstatus
    gettpatrace_u = options.gettpatrace_u
    getmessages = options.getmessages
    getverifypdisks = options.getverifypdisks

    getdisksum = options.getdisksum
    getdatacheck = options.getdatacheck
    getshowwhere = options.getshowwhere
    getshowwhere1 = options.getshowwhere1
    getshowblocks = options.getshowblocks
    getshowcylalloc = options.getshowcylalloc
    getestcompr = options.getestcompr
    getnodetype = options.getnodetype
    gethostname = options.gethostname
    getpsh_hostname = options.getpsh_hostname
    getpsh_i_s = options.getpsh_i_s

    getvprocstatnot = options.getvprocstatnot

    if debug: print("Options: ", options)

    config_fns = set([rpm_qa, ctl, dbscontrol, vconfig, hosts, tvamconfig, 
        hwinfo, whatsup, bam_a, nodehw, arrayconfig, ifconfig_a, profilercheck])
    status_fns = set([pdestate, vprocstatus, mapsummary, tpatrace_u, 
                        verifypdisks, messages])
    dbs_fns = set([disksum, showwhere, showblocks, showcylalloc])
    all_fns = config_fns | status_fns | dbs_fns
    #fns that only need to be run on one node per system
    persystem_fns = dbs_fns | set([vprocstatus, dbscontrol, ctl])
    #fns that only need to be run on one node per system including stand-alones
    persystem_xfns = persystem_fns | set([datacheck, estcompr, vprocstatnot])
    #fns that only need to be run on one node per clique
    perclique_fns = set([verifypdisks, mapsummary, tvamconfig, arrayconfig, 
                           profilercheck])
    #fns that requie PDE to be up:
    pdeup_fns = set([vprocstatus, vprocstatnot])
    #fns that requie DBS to be up:
    dbsup_fns = dbs_fns | set([dbscontrol])
    #fns needing scripts in bindir:
    needbindir_fns = set([datacheck, estcompr])


    fns_to_run = set()
    if runall:
        fns_to_run = all_fns 
    else:
        if persystem:
            fns_to_run |= persystem_fns
        if perclique: 
            fns_to_run |= perclique_fns
        if getconfig:
            fns_to_run |= config_fns
        if getstatus:
            fns_to_run |= status_fns
        if getdbs:
            fns_to_run |= dbs_fns
        if getwhatsup:
            fns_to_run.add(whatsup)
        if getrpm_qa:
            fns_to_run.add(rpm_qa)
        if getctl:
            fns_to_run.add(ctl)
        if getdbscontrol:
            fns_to_run.add(dbscontrol)
        if getvconfig:
            fns_to_run.add(vconfig)
        if gethosts:
            fns_to_run.add(hosts)
        if getbam_a:
            fns_to_run.add(bam_a)
        if getnodehw:
            fns_to_run.add(nodehw)
        if getarray:
            fns_to_run.add(arrayconfig)
        if getifconfig_a:
            fns_to_run.add(ifconfig_a)
        if savepdestate:
            fns_to_run.add(pdestate)
        if gethwinfo:
            fns_to_run.add(hwinfo)
        if getvprocstatus:
            fns_to_run.add(vprocstatus)
        if gettvamconfig:
            fns_to_run.add(tvamconfig)
        if getmapsummary:
            fns_to_run.add(mapsummary)
        if getprofilercheck:
            fns_to_run.add(profilercheck)
        if getdisksum:
            fns_to_run.add(disksum)
        if getshowwhere:
            fns_to_run.add(showwhere)
        if getshowblocks:
            fns_to_run.add(showblocks)
        if getshowcylalloc:
            fns_to_run.add(showcylalloc)
        if gettpatrace_u:
            fns_to_run.add(tpatrace_u)
        if getverifypdisks:
            fns_to_run.add(verifypdisks)
        if getmessages:
            fns_to_run.add(messages)
        if gethostname:
            fns_to_run.add(hostname)
        if getpsh_hostname:
            fns_to_run.add(psh_hostname)
        if getpsh_i_s:
            fns_to_run.add(psh_i_s)
    #stand-alone fns:
    if getdatacheck:
        fns_to_run.add(datacheck)
    if getestcompr:
        fns_to_run.add(estcompr)
    if getvprocstatnot:
        fns_to_run.add(vprocstatnot)


    if debug:    
        print("Functions to run before pruning:")
        for x in fns_to_run: print(x.__name__)

    if xpersystem:
        #remove per-system fns
        if verbose or debug:
            print("removing per-system fns:")
            for x in persystem_xfns: print(x.__name__)
        fns_to_run -= persystem_xfns

    if xperclique:
        #remove per-clique fns
        if verbose or debug:
            print("removing per-clique fns:")
            for x in perclique_fns: print(x.__name__)
        fns_to_run -= perclique_fns

    needbindir = not needbindir_fns.isdisjoint(fns_to_run)
    if debug: print("needbindir:", needbindir)

    cwd = getcwd()
    if verbose or debug: print("cwd: " + cwd)
    bindir = getdir(binpath)
    outdir = getdir(outpath)
    if debug: print("outdir: " + outdir)

    #if debug: print("needbindir: " + needbindir)
    if needbindir:
        if not quiet:
            print("bin directory: " + bindir)
        if not os.path.exists(bindir):
            eprint("bin directory: " + bindir + " does not exist")
            #remove fns requiring bin directory
            if not quiet:
                print("Removing bin functions:")
                for x in needbindir_fns: print(x.__name__)
            fns_to_run -= needbindir_fns

    if not quiet:
        print    ("output directory: " + outdir)
    if not os.path.exists(outdir):
        if not quiet:
            print("                  does not exist, creating")
        #os.mkdir(outdir)  #this method doesn't create parent directories
        call(['mkdir', '-p', outdir])

    #call pdestate and remove it from test list
    #(pde_up, dbs_up) = pdestate(savepdestate)
    (pde_up, dbs_up) = pdestate(writetofile= pdestate in fns_to_run)
    fns_to_run.discard(pdestate)

    if not pde_up:
        #remove fns requiring PDE up
        if not quiet:
            print("PDE not up, removing PDE dependent fns:")
            for x in pdeup_fns: print(x.__name__)
        fns_to_run -= pdeup_fns
    if not dbs_up:
        #remove fns requiring DBS up
        if not quiet:
            print("DBS not up, removing dependent DBS fns:")
            for x in dbsup_fns: print(x.__name__)
        fns_to_run -= dbsup_fns

    
    #Some functions we want to call even if not specified
    if arrayconfig in fns_to_run:
        #need to run hosts() first
        hosts(copy= hosts in fns_to_run) 
        #remove hosts from test set
        fns_to_run.discard(hosts)   #could alternatively make a separate list for these funcitons
    if getnodetype:
        #get cn and node lists cliqreplist and nodelist
        myname = hostname(copy= hostname in fns_to_run) 
        fns_to_run.discard(hostname)   
        psh_hostname(copy= psh_hostname in fns_to_run) 
        fns_to_run.discard(psh_hostname)   
        psh_i_s(copy= psh_i_s in fns_to_run) 
        fns_to_run.discard(psh_i_s)  
        i_am_the_cn = (myname == cn)
        i_am_a_clique_representative = (myname in cliqreplist)
        if verbose:
            print("My name is", myname)
        if i_am_the_cn: 
            print("this is the control node")
        elif i_am_a_clique_representative: 
            print("this is a clique representative")
        else: 
            print("this is an ordinary node")

    if pertype:
        if not i_am_the_cn:
            if verbose or debug:
                print("removing per-system fns:")
                for x in persystem_xfns: print(x.__name__)
            fns_to_run -= persystem_xfns
            if not i_am_a_clique_representative:
                if verbose or debug:
                    print("removing per-clique fns:")
                    for x in perclique_fns: print(x.__name__)
                fns_to_run -= perclique_fns

    #Functions requiring arguments
    if getshowwhere1 and not xpersystem:
        showwhere("vproc 1")
    

    if verbose or debug:    
        print("Functions to run:")
        for x in fns_to_run: print(x.__name__)
    if not dontrun:
        [f() for f in fns_to_run]


################################################################################
if __name__ == "__main__":
    main()

