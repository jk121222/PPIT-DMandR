#!/usr/bin/python 

################################################################################
# dothilldmandr.py
# Test DotHill drive down/copyback tests for DM&R
#   Currently support DH4544 with GL145R006 bundle, python 2.6.9
# Written by: John Kim
# Date: 2016-6-11
#
################################################################################

import time
import datetime
import sys
import re
import collections
from subprocess import Popen, PIPE, STDOUT
from optparse import OptionParser

################################################################################
reconstructcopyback_et = collections.namedtuple('reconstructcopyback_et', 
                                             'vdisk reconstruct_et copyback_et')

debug = 0
verbose = False

################################################################################
class disk:
    def __init__(self, enclosure, slot, vdisk):
        self.enclosure = enclosure
        self.slot = slot
        self.vdisk = vdisk

    @property
    def location(self):
        return str(self.enclosure) + '.' + str(self.slot)

################################################################################
class DotHillArray:
    pass
###End of Class DotHillArray###

################################################################################
class DotHillArrayGL(DotHillArray):
    #Tested on Product ID:DH4544, Bundle version:GL145R006
    #RE for version from show version
    controller = 1           # controller to access (1 for A or 2 for B)
    initialsleeptime = 60    # GL takes ~30s from disk down to RCON started
    startsleeptime = 15      # Sleep time waiting for initial state
    sleeptime = 60           # recheck interval
    defaultnumentries = 100  # default number of events to retrieve from log

    #delta from array time to local time
    timedelta = datetime.timedelta(seconds = time.altzone)


    #show version patterns:
    #Bundle Version, e.g. Bundle Version: GL145R006
    rbv = re.compile('Bundle Version: (?P<version>[A-Z][A-Z]\w{7})')  


    #show system patterns:
    #SCSI Product ID, e.g. SCSI Product ID: DH4544
    rpi = re.compile('SCSI Product ID: (?P<id>\w+)')


    #show vdisks patterns:
    #job and percent complete
    rjp = re.compile('(?P<job>\w+)\s+(?P<pct>\d+)%')  


    #event log patterns:
    rdt = re.compile('(?P<time>(?P<yyyy>\d\d\d\d)-(?P<mm>\d\d)-(?P<dd>\d\d) (?P<hour>\d\d):(?P<minute>\d\d):(?P<second>\d\d))')

    rrc = re.compile('Reconstruction of a vdisk completed.')
    rrs = re.compile('Vdisk reconstruction started.')
    rsu = re.compile('A spare disk was used in a vdisk to bring it back to a fault-tolerant state.')
    rdd = re.compile('A disk that was part of a vdisk is down.')

    rccs= re.compile('A disk copyback operation completed. The indicated disk was restored to being a spare.')
    rcc = re.compile('A disk copyback operation completed. [(]')
    rcf = re.compile('A disk copyback operation failed.')
    rcs = re.compile('A disk copyback operation started. The indicated disk is the source disk.')
    rcd = re.compile('A disk copyback operation started. The indicated disk is the destination disk.')
    rda = re.compile('A spare disk drive was added to a vdisk.')

    rvd = re.compile('vdisk: (?P<vdisk>vd\d+)')
    res = re.compile('enclosure: (?P<enclosure>\d+), slot: (?P<slot>\d+)')

    rs = re.compile('Success')


    def __init__(self, name):
        self.name = name
        self.get_version()
        self.getscsiproductid()


    def get_eventtime(self, line):
        pdt = self.rdt.search(line)  #search for date/time
        if pdt:
            year = pdt.group('yyyy')
            month = pdt.group('mm')
            day = pdt.group('dd')
            hour = pdt.group('hour')
            minute = pdt.group('minute')
            second = pdt.group('second')
            eventtime = datetime.datetime(int(year), int(month), int(day),
                                        int(hour), int(minute), int(second))
        else: 
            return 0  # couldn't find time in line
        return eventtime - self.timedelta #(won't work properly if DST changes)


    def getrshcmd(self, cmd):
        return 'rshfa -V dh ' + self.name + str(self.controller) + ' ' + cmd


    def sendrshcmd(self, rawcmd):
        cmd = self.getrshcmd(rawcmd)
        if debug >= 2: print "cmd = " + cmd
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        print p.communicate()


    def get_version(self):  
        """Return the bundle version of this array.
        """
        ## show version
        #Controller A Versions
        #---------------------
        #Bundle Version: GL145R006
        #Build Date: Fri Dec 11 10:24:33 MST 2015
        #
        #Controller B Versions
        #---------------------
        #Bundle Version: GL145R006
        #Build Date: Fri Dec 11 10:24:33 MST 2015
        #
        #Success: Command completed successfully. (2016-06-13 23:31:21)
        cmd = self.getrshcmd('show version')
        if debug >= 2: print "cmd = " + cmd
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        stdout, stderr = p.communicate()
        for line in stdout.splitlines():
            if debug >= 2: print line
            m = self.rbv.match(line)  #search for Bundle Version:
            if m:
                self.version =  m.group('version')
        if (self.version): 
            return self.version
        else:
            raise RuntimeError("Couldn't get bundle version.")


    def getscsiproductid(self):
        """Return the SCSI Product ID
        """
        ## show system
        #System Information
        #------------------
        #System Name: DAMC002-3
        #System Contact: Uninitialized Contact
        #System Location: B1 Lab station 46
        #System Information: pitg
        #Midplane Serial Number: 00C0FF1B50B6
        #Vendor Name:
        #Product ID: DH4544
        #Product Brand:
        #SCSI Vendor ID: DotHill
        #SCSI Product ID: DH4544
        #Enclosure Count: 2
        #Health: OK
        #Health Reason:
        #Other MC Status: Operational
        #PFU Status: Idle
        #Supported Locales: English (English), Spanish (espaol), French (franais), German (Deutsch), Italian (italiano), Japanese (), Dutch (Nederlands), Chinese-Simplified (), Chinese-Traditional (), Korean ()


        #Success: Command completed successfully. (2016-06-14 16:23:36)

        cmd = self.getrshcmd('show system')
        if debug >= 2: print "cmd = " + cmd

        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        stdout, stderr = p.communicate()
        for line in stdout.splitlines():
            if debug >= 2: print line
            m = self.rpi.match(line)  #search for SCSI Product ID:
            if m:
                self.scsiproductid =  m.group('id')
        if (self.scsiproductid):
            return self.scsiproductid
        else:
            raise RuntimeError("Couldn't get SCSI Product ID.")


    def down_disk(self, disk):  
        """Down the specified disk."
        """
        ## down disk 0.0
        #"Info: Disk 0.0 was placed in a down state. (0.0)
        #Success: Command completed successfully. (0.0) - Disk 0.0 was placed 
        #in a down state. (2016-06-01 19:08:12)"
        cmd = self.getrshcmd('down disk ' + disk.location)
        if debug >= 2: print "cmd = " + cmd
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        stdout, stderr = p.communicate()
        for line in stdout.splitlines():
            if debug >= 2: print line
            m = self.rs.match(line)  #search for Success
            if m:
                if debug == 1: print line
                return True
        raise RuntimeError("down disk failed")


    def clear_disk(self, disk):  
        """Clear disk-metadata for the specified disk.
        """
        ## clear disk-metadata 0.0
        #"Info: Updating disk list...
        #Info: Disk disk_00.00 metadata was cleared. (2016-06-01 21:32:46)"
        
        #"Error: The specified disk is not a leftover disk. (0.0)
        # - Metadata was not cleared for one or more disks. (2016-06-08 00:18:49)"

        pe = re.compile('Error')  
        pc = re.compile('metadata was cleared')  

        cmd = self.getrshcmd('clear disk-metadata ' + disk.location)
        if debug >= 2: print "cmd = " + cmd
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        stdout, stderr = p.communicate()
        for line in stdout.splitlines():
            if debug >= 2: print line
            se = pe.search(line)
            sc = pc.search(line)
            if sc:
                if debug == 1: print line
                return True
            elif se:
                raise RuntimeError(line)
        raise RuntimeError("Did not find metadata was cleared message")


    def get_job_pct(self, vdisk):  
        """Return the completion% of the current job for the specified vdisk.
        """
        #GL:
        ## show vdisks vd01
        #Name  Size    Free Own Pref   RAID   Disks Spr Chk  Status Jobs      Job%      Serial Number                    Drive Spin Down        Spin Down Delay       Health     Health Reason
        #  Health Recommendation
        #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        #vd01  899.2GB 0B   A   A      RAID1  2     0   N/A  FTOL   VRSC      35%       00c0ff1bce3c000029452a5700000000 Disabled               0                     OK

        ## show vdisks vd01
        #Name  Size    Free Own Pref   RAID   Disks Spr Chk  Status Jobs      Job%      Serial Number                    Drive Spin Down        Spin Down Delay       Health
        #  Health Reason Health Recommendation
        #------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        #vd01  899.2GB 0B   A   A      RAID1  2     0   N/A  FTOL                       00c0ff1bce3c000029452a5700000000 Disabled               0                     OK
        #
        #------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        #Success: Command completed successfully. (2016-06-01 21:30:01)

        if (self.version[0:2]=="GL"):
            cmd = self.getrshcmd('show vdisks ' + vdisk)
            if debug >= 2: print "cmd = " + cmd
            p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
            stdout, stderr = p.communicate()
            foundpct = False
            foundtime = False
            for line in stdout.splitlines():
                if debug >= 2: print line
                mjp = self.rjp.search(line)  # search for job and %complete
                if mjp:
                    if debug == 1: print line
                    foundpct = True
                    self.job = mjp.group('job')
                    self.pct = mjp.group('pct')
                    for line in stdout.splitlines():
                        ms = self.rs.match(line)  # search for "Success"
                        if ms:
                            if debug == 1: print line
                            eventtime = self.get_eventtime(line)
                            foundtime = True
                            break
                    break;
            if not foundtime:
                if debug > 0: print "Couldn't find eventtime, substituting local time"
                eventtime = datetime.datetime.now()
                
            if (foundpct):
                return (self.job, int(self.pct), eventtime)
            else:  # Job completed
                return ("Blank", 100, eventtime)


    #Jobs for GL
    #  - CPYBK: The disk is being used in a copyback operation.
    #  - DRSC: A disk is being scrubbed.
    #  - EXPD: The vdisk is being expanded.
    #  - INIT: The vdisk is initializing.
    #  - RCON: The vdisk is being reconstructed.
    #  - VRFY: The vdisk is being verified.
    #  - VRSC: The vdisk is being scrubbed.
    #  - Blank if no job is running.
    def wait_til_ready(self, vdisk):
        """Wait until the specified vdisk is not busy
        """
        time.sleep(self.initialsleeptime)
        job, pct, eventtime = self.get_job_pct(vdisk)
        initialpct = pct; initialtime = eventtime
        while ((job=="INIT") or (job=="RCON") or (job=="CPYBK")
                or (job=="EXPD")):
            time.sleep(self.sleeptime)
            job, pct = self.get_job_pct(vdisk)
            if verbose:
                if pct == initialpct or pct == 100:
                    print ('vdisk {0} job {1} {2}% complete at {3}'\
                          .format(vdisk, job, pct, eventtime))
                else:
                    #Note estcompletion will be off if a new job starts (not likely)
                    estcompletion = eventtime \
                        + (100-pct)*(eventtime - initialtime)/(pct - initialpct)
                    print ('vdisk {0} job {1} {2}% complete at {3}, estimated completion: {4}'\
                          .format(vdisk, job, pct, eventtime, estcompletion.strftime("%Y-%m-%d %H:%M:%S")))
        return True


    def wait_for_job(self, vdisk, myjob):
        """Wait until the specified vdisk starts and completes the specified job
        """
        time.sleep(self.startsleeptime)
        job, pct, eventtime = self.get_job_pct(vdisk)
        if verbose:
            print ('vdisk {0} job {1} {2}% complete at {3}'\
                  .format(vdisk, job, pct, eventtime))
        while (job != myjob):
            if debug >= 2: print line
            time.sleep(self.startsleeptime)
            job, pct, eventtime = self.get_job_pct(vdisk)
            if verbose:
                print ('vdisk {0} job {1} {2}% complete at {3}'\
                      .format(vdisk, job, pct, eventtime))
        initialpct = pct; initialtime = eventtime
        while (job == myjob):
            if debug >= 2: print line
            time.sleep(self.sleeptime)
            job, pct, eventtime = self.get_job_pct(vdisk)
            if verbose:
                if pct == initialpct or pct == 100:
                    print ('vdisk {0} job {1} {2}% complete at {3}'\
                          .format(vdisk, job, pct, eventtime))
                else:
                    estcompletion = eventtime \
                        + (100-pct)*(eventtime - initialtime)/(pct - initialpct)
                    print ('vdisk {0} job {1} {2}% complete at {3}, estimated completion: {4}'\
                          .format(vdisk, job, pct, eventtime, estcompletion.strftime("%Y-%m-%d %H:%M:%S")))

        return True


    def get_drive_down_copyback_results(self, disklist = []):
        """Get drive reconstruction/copyback times from the event log
        """
        # Tested on GL
        numentries = self.defaultnumentries  #number of events to retrieve from log

        vdisklist = []
        reconstructcompletetime = {}
        reconstructstarttime = {}
        reconstruct_et = {}
        copybackcompletetime = {}
        copybackstarttime = {}
        copyback_et = {}
        resultlist = []

        for disk in disklist:
            vdisklist.append(disk.vdisk)

        cmd = self.getrshcmd('show events last ' + str(numentries))
        if debug >= 2: print "cmd = " + cmd
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        stdout, stderr = p.communicate()
        for line in stdout.splitlines():
            if debug >= 2: print line
            #pdt = self.rdt.search(line)  #search for date/time
            #if pdt:
            #    year = pdt.group('yyyy')
            #    month = pdt.group('mm')
            #    day = pdt.group('dd')
            #    hour = pdt.group('hour')
            #    minute = pdt.group('minute')
            #    second = pdt.group('second')
            #    eventtime = datetime.datetime(int(year), int(month), int(day),
            #                                int(hour), int(minute), int(second))
            eventtime = self.get_eventtime(line)

            prc = self.rrc.search(line)
            prs = self.rrs.search(line)
            pcc = self.rcc.search(line)
            pcd = self.rcd.search(line)

            if pcc:  # "A disk copyback operation completed"
            #2016-06-01 23:50:00 [500] #A19792: DH4544 Array SN#00C0FF1BCE3C Controller A INFORMATIONAL A disk copyback operation completed. The indicated disk was restored to being a spare. (disk: channel: 0, ID: 20, SN: KXGN1Z0R, enclosure: 0, slot: 20)
                pvd = self.rvd.search(line)
                vdisk = pvd.group('vdisk')
                if debug == 1: 
                    print line
                elif verbose:
                    print ('{0} {1} copyback completed'.format(eventtime,vdisk))
                if vdisk in vdisklist:
                    copybackcompletetime[vdisk] = eventtime        
            #elif pcd and not vdisk in copybackstarttime:  
            elif pcd: # "A disk copyback operation started. The indicated disk is the destination disk."
                #2016-06-01 21:32:43 [499] #A19789: DH4544 Array SN#00C0FF1BCE3C Controller A INFORMATIONAL A disk copyback operation started. The indicated disk is the destination disk. (vdisk: vd01, SN: 00c0ff1bce3c000029452a5700000000) (to disk: channel: 0, ID: 0, SN: KPGJDL2F, enclosure: 0, slot: 0)
                pvd = self.rvd.search(line)
                vdisk = pvd.group('vdisk')
                # There can be more starts earlier if they failed so don't check 
                # for any more if already found.
                if not vdisk in copybackstarttime:
                    pes = self.res.search(line)  #search for enclosure and slot
                    enclosure = pes.group('enclosure')
                    slot = pes.group('slot')
                    if debug == 1: 
                        print line
                    elif verbose:
                        print('{0} {1}.{2} {3} copyback started' \
                            .format(eventtime, enclosure, slot, vdisk))
                    if vdisk in vdisklist:
                        copybackstarttime[vdisk] = eventtime        
                        if vdisk in copybackcompletetime:
                            copyback_et[vdisk] = (copybackcompletetime[vdisk]
                                              - eventtime)
                            print '{0} copyback time: {1}\n'\
                                  .format(vdisk, copyback_et[vdisk])
                        else:
                            print 'Error: Found copyback start without '\
                                  'copyback omplete for {0}. Might need to '\
                                  'wait longer.\n'\
                                  .format(vdisk)
            elif prc:  # "Reconstruction of a vdisk completed."
                #2016-06-01 21:27:35 [018] #A19785: DH4544 Array SN#00C0FF1BCE3C Controller A INFORMATIONAL Reconstruction of a vdisk completed. (vdisk: vd01, SN: 00c0ff1bce3c000029452a5700000000)  
                pvd = self.rvd.search(line)  #search for vdisk
                vdisk = pvd.group('vdisk')
                if debug == 1: 
                    print line
                elif verbose:
                    print('{0} {1} reconstruction completed'\
                           .format(eventtime, vdisk))
                if vdisk in vdisklist:
                    reconstructcompletetime[vdisk] = eventtime        
            elif prs:  # "Vdisk reconstruction started."
            #2016-06-01 19:08:14 [037] #A19784: DH4544 Array SN#00C0FF1BCE3C Controller A INFORMATIONAL Vdisk reconstruction started. (vdisk: vd01, SN: 00c0ff1bce3c000029452a5700000000) (disk: channel: 0, ID: 20, SN: KXGN1Z0R, enclosure: 0, slot: 20)
                pvd = self.rvd.search(line)  #search for vdisk
                vdisk = pvd.group('vdisk')
                pes = self.res.search(line)  #search for enclosure and slot
                enclosure = pes.group('enclosure')
                slot = pes.group('slot')
                if debug == 1: 
                    print line
                elif verbose:
                    print '{0} {1}.{2} {3} reconstruction started'\
                          .format(eventtime, enclosure, slot, vdisk)
                if vdisk in vdisklist:
                    # At this point should have found copyback complete, 
                    # copyback started, and reconstruction complete.
                    reconstructstarttime[vdisk] = eventtime        
                    if vdisk in reconstructcompletetime:
                        reconstruct_et[vdisk] = (reconstructcompletetime[vdisk]
                                              - eventtime)
                        print '{0} reconstruction time: {1}\n'\
                              .format(vdisk, reconstruct_et[vdisk])
                        resultlist.append([reconstructcopyback_et, vdisk, 
                                   reconstruct_et[vdisk], copyback_et[vdisk]])
                    else:
                        print 'Error: Found recontstruction start without '\
                              'reconstruction complete for {0}. Might need to '\
                              'wait longer\n'.format(vdisk)
                    vdisklist.remove(vdisk)
                    if len(vdisklist) == 0:  # Found all of them
                        break
        if len(vdisklist) != 0:
            print 'Error: did not find all expected entries. '\
                  'May need to read more entries\n'
        return resultlist


    def drive_down_drive_copyback(self, disklist = []):
        """ Drive down, drive copyback test.
        """
        #Check that drives are up and ready
        #Input is a list of namedtuple disk
        #Each disk will be downed. When the reconstructions are complete,
        #the disk-metadata will be cleared. When the copybacks are complete,
        #The completion times will be determined
        #Note: Only one drive per vdisk can be tested. 

        #Wait for disks ready
        for disk in disklist:
            vdisk = disk.vdisk
            print 'Wait for vdisk ready ' + vdisk
            self.wait_til_ready(vdisk)
        print 'Vdisks ready'

        #Down drives
        for disk in disklist:
            print 'Down disk {0}.{1} {2}'\
                  .format(str(disk.enclosure), str(disk.slot), disk.vdisk)
            try:
                self.down_disk(disk)
            except RuntimeError as e:
                print '%s\n' % e
            else:
                print "success"

        #Wait for reconstruction to complete
        for disk in disklist:
            vdisk = disk.vdisk
            print 'Wait for reconstruction of vdisk ' + vdisk
            self.wait_for_job(vdisk,"RCON")
        print 'Reconstruction complete'

        #Clear disk-metadata
        for disk in disklist:
            enclosure = disk.enclosure; drive = disk.slot; vdisk = disk.vdisk
            print 'Clear disk_metadata {0}.{1} {2}' \
                  .format(str(enclosure), str(drive), vdisk)
            try:
                self.clear_disk(disk)
            except RuntimeError as e:
                print '%s\n' % e
            else:
                print "success"

        #Wait for copyback to complete
        for disk in disklist:
            vdisk = disk.vdisk
            print 'Wait for copyback for vdisk ' + vdisk
            self.wait_for_job(vdisk,"CPYBK")
        print 'Copyback complete'


        #Get reconstruction and copyback times
        #return self.get_drive_down_copyback_results(disk)
        return self.get_drive_down_copyback_results(disklist)

###End of Class DotHillArrayGL###
################################################################################
        
    
#Use "show vdisks" to show all vdisks in the array
#Use "show disk vdisk <vdisk>" to show the disks used by a vdisk
################################################################################
def main():
    usage="%prog [-d] [-v] [-t]"
    parser = OptionParser(usage, version="%prog 0.14")
    #debug = 0  # 0=Debug off,
    #           # 1=show info such as DotHill commands
    #           # 2=show more such as event log lines
    parser.add_option("-d", "--debug", dest="debug", default=0, type="int",
                      help="specify debug level 0-2")
    #verbose = True # show progress
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="enable vebose mode")
    #test = 0   # test to run 
    parser.add_option("-t", "--test", type="int", dest="test", default=3,
                      help="specify test 0-3: 0=wait_for_copy,1=1down1back,2=2down2back,3=1down1back+2down2back")
    (options, args) = parser.parse_args()
    debug = options.debug
    verbose = options.verbose
    test = options.test


####
    array3 = DotHillArrayGL("damc002-3")
    print "Array: " + array3.name
    print "SCSI Product ID: " + array3.scsiproductid
    print "Bundle version: " + array3.version

    localtime = datetime.datetime.now()
    print "Local time: {0}\n".format(localtime.strftime("%Y-%m-%d %H:%M:%S"))

    disk1 = disk(0,0, "vd01")
    disk2 = disk(0,1, "vd02")

    print "Running test", test

    if test == 0:
        print "Wait for copyback"
        array3.wait_for_job("vd01", "CPYBK")
        array3.get_drive_down_copyback_results([disk(0,0, "vd01")])

    elif test == 1:
        print "Starting one drive down, one drive copyback test"
        array3.drive_down_drive_copyback([disk1])

    elif test == 2:
        print "Starting two drives down, two drives copyback"
        array3.drive_down_drive_copyback([disk1, disk2])

    elif test == 3:
        print "Starting one drive down, one drive copyback test"
        array3.drive_down_drive_copyback([disk1])

        print "Starting two drives down, two drives copyback"
        array3.drive_down_drive_copyback([disk1, disk2])

    print "Done"


################################################################################
if __name__ == "__main__":
    main()


