#!/bin/csh
#usage: dmandrcheck.sh <phase> <bindir> <outdir>
# phase = initial|load|15|30|60|reconfig|all|testing (default=initial)
#First run dm&r tests that should only be run on one node (CN) without any other tests running,
# then call dmandrcheck.sh on all nodes to collect config/status
#run after dm&r initial config, load_tpch, 15, 30, and 60 load, and after reconfiguration
#for phase="initial", save configuration
#for phase="load" save dbs info on CN
#for phase=15, 30 and 60 only, run restart tests on CN
#for phase=60, reduce to 60% on ON first. Also do drive tests for each clique and scandisk tests on CN
#for phase="reconfig", get reconfig times on CN, save system log, save configuration

#2016-08-19 John Kim v1.0


if ($#argv < 2 || $argv[1] == "-h") then
  echo "  Usage: dmandrcheckcn.sh <phase> <dm&r bin dir> <out dir>"
  echo "         phase = initial|load|15|30|60|reconfig|all|testing"
  exit
else
  set phase = $argv[1]
  set bin = $argv[2]
  set out = $argv[3]
endif

echo "  phase:" $phase
mkdir -p $out/$phase  #creeate output directory if it doesn't exist


#After filling to 15% or 30%
if ($phase == 15 || $phase == 30) then
  echo "  Starting restart tests"
  echo "  $bin/dmandrrestart.py -t 1 -n 2 >& $out/$phase/restarts_`date +%Y-%m-%d.%T`"
  $bin/dmandrrestart.py -t 1 -n 2 >& $phase/restarts_`date +%Y-%m-%d.%T`
  echo "  restart tests complete"
endif


#After filling to 60%
if ($phase == 60) then
    echo "  permreduce to reduce to 60% fill"
    echo "  $bin/permreduce.py -v -p 60 --doit >& $out/$phase/permreduce_`date +%Y-%m-%d.%T`"
    $bin/permreduce.py -v -p 60 --doit >& $out/$phase/permreduce_`date +%Y-%m-%d.%T`

    echo "  Starting restart tests"
    echo "  $bin/dmandrrestart.py -t 1 -n 2 >& $out/$phase/restarts_`date +%Y-%m-%d.%T`"
    $bin/dmandrrestart.py -t 1 -n 2 >& $out/$phase/restarts_`date +%Y-%m-%d.%T`
exit 1

endif


#After reconfiguring system
if ($phase == "reconfig") then
  echo "  reconfig"
  if ($type = "control") then
    echo "  Get reconfig times"
    echo "  $bin/getreconfigtimes.py > $out/$phase/reconfigtimes_`date +%Y-%m-%d.%T`"
    $bin/getreconfigtimes.py >& $out/$phase/reconfigtimes_`date +%Y-%m-%d.%T`
  endif

endif


echo "  calling $bin/dmandrcheck.sh $1 $2 $3 on all nodes"
psh $bin/dmandrcheck.sh $1 $2 $3

