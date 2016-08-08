#!/bin/csh
#dmandrcheck.sh <phase= initial|load|1|30|50|reconfig> [node type = cn|cc] 
#run after dm&r initial config, load_tpch, 15, 30, and 60 load, and after reconfiguration
#for phase="initial", save configuration
#for phase="load" save dbs info
#for phase=15, 30 and 60 only, run restart tests (needs to be done on CN)
#for phase=60, reduce to 60% first. Also do drive tests and scandisk tests
#for phase="reconfig", don't do restart tests, save system log, save configuration


set nodeoptions = "--xperclique --xpersystem"
if ($#argv > 0) then
  set phase = $argv[1]
  if ($#argv == 2) then
    if ($argv[2] == "cn") then  #control node
      set CN = True
      set nodeoptions = ""
    else if ($argv[2] == "cc") then  #clique controller
      set CC = True
      set nodeoptions = "--xpersystem"
    endif
  endif
else
  echo "Usage: dmandrcheck.sh <initial|load|15|30|60|reconfig> [cn]"
  exit
endif
echo "nodeoptions:" $nodeoptions

echo "phase" $phase
set bin = "/home/jk121222/dmandrbin"


#For testing
if ($phase == "testing") then
  date;
  echo "saving configuration to ./$phase"
  $bin/savesysteminfo.py --tvamconfig --pdestate --tpatrace_u --where1 -o $phase $nodeoptions
  if (CN)
    echo "Starting restart tests"
    $bin/dmandrrestart.py -h > $phase/restarts_`date +%Y-%m-%d.%T`
  endif
  date;
endif


#After initial configuration
if ($phase == "initial") then
  echo "saving configuration to ./$phase"
  #/home/jk121222/dmandrbin/savesysteminfo.py -c -o initial
  $bin/savesysteminfo.py --config -o initial -b $bin $nodeoptions
  date;
endif


#After load_tpch
if ($phase == "load") then
  date;
  echo "saving dbs info to ./$phase"
  $bin/savesysteminfo.py --dbs -o $phase $nodeoptions
  date;
endif


#After filling to 15% or 30%
if ($phase == 15 || $phase == 30) then
  date;
  echo "saving configuration to ./$phase"
  $bin/savesysteminfo.py --status --dbs -o $phase $nodeoptions
  if (CN)
    echo "Starting restart tests"
    $bin/dmandrrestart.py -t 1 -n 2 &> $phase/restarts_`date +%Y-%m-%d.%T`
  endif
  echo "restart tests complete"
  date;
endif


#After filling to 60%
if ($phase == 60) then
  date;
  #echo "dbs info, estimate compresson"
  #$bin/savesysteminfo.py --status --dbs --estcompr -o $phase $nodeoptions
  echo "dbs info, scandisk tests, estimate compresson"
  $bin/savesysteminfo.py --status --dbs --datacheck --estcompr -o $phase $nodeoptions
 
  if (CN)
    echo "permreduce to reduce to 60% fill"
    $bin/permreduce.py -v -p 60 --doit &> permreduce_`date +%Y-%m-%d.%T`

    echo "Starting restart tests"
    $bin/dmandrrestart.py -t 1 -n 2 &> $phase/restarts_`date +%Y-%m-%d.%T`

    echo "start disk tests"
    $bin/dothilldmandr.py -t 3 -v
  endif

  date;
endif


#After reconfiguring system
if ($phase == "reconfig") then
  if (CN)
    echo "Get reconfig times"
    $bin/getreconfigtimes.py > reconfigtimes_`date +%Y-%m-%d.%T`
  endif

  echo "saving config, status, dbs info, showwhere vproc 1, estimate compression, run scandisk/checktable"
  $bin/savesysteminfo.py --all --estcompr --datacheck --where1 -o initial -b $bin
  date;

endif


