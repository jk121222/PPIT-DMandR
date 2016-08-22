#!/bin/csh
#Start iostat and sar
#This should be run on each node before PUT starts reconfig
#2016-08-19 John Kim

set nodename = `hostname`

if ($#argv> 0) then
  if ($argv[1] == "-h") then
    echo "Start iostat and sar"
    echo "Usage: run_sar_iostat.sh [out dir] [integer hours]"
    echo "       default output dir = /var/opt/teradata/tddump"
    echo "       default hours = 7"
    exit 0
  else
    set out = $argv[1]
    mkdir -p $out
  endif
else
  set out = "/var/opt/teradata/tddump"
endif

if ($#argv> 1) then
  @ hours = $argv[2]
else
  @ hours = 7
endif

echo "output dir:" $out
   
set interval = 5  #seconds
@ count = ($hours * 60 *  60) / $interval
echo "interval: " $interval
echo "count: " $count
echo "hours: " $hours

#Run iostat to collect i/o statistics
set date = `date +%Y-%m-%d.%T`
echo "nohup iostat -txk $interval $count > $out/$nodename.iostat.$date.log &"
nohup iostat -txk $interval $count > $out/$nodename.iostat.$date.log &

#Run sar -n to collect network statistics
set date = `date +%Y-%m-%d.%T`
echo "nohup sar -n DEV $interval $count > $out/$nodename.sar.$date.log &"
nohup sar -n DEV $interval $count > $out/$nodename.sar.$date.log &

