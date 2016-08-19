#!/bin/csh
#usage: dmandrcheck.sh <phase> <bindir> <outdir> [node type]
# phase = initial|load|15|30|60|reconfig|all|testing (default=initial)
# node type = control|clique|ordinary|auto (default=auto)
#  if node type = control, runs only functions that should only be done on the CN
#   this is so that tests that bring pde/dbs down or change the database don't affect other funtions
#  if node type = clique, runs functions that only need to be done once per clique as well as functions that run on all nodes
#  auto automatically determines the node type
#run after dm&r initial config, load_tpch, 15, 30, and 60 load, and after reconfiguration
#for phase="initial", save configuration
#for phase="load" save dbs info on CN
#for phase=15, 30 and 60 only, run restart tests on CN
#for phase=60, reduce to 60% on ON first. Also do drive tests for each clique and scandisk tests on CN
#for phase="reconfig", get reconfig times on CN, save system log, save configuration

#2016-08-17 John Kim v1.0
#2016-08-19 John Kim v1.1


if ($#argv > 2) then
  set phase = $argv[1]
  set bin = $argv[2]
  set out = $argv[3]
  if ($#argv > 3) then
    set type = $argv[4]
  else
    set type = "auto"
  endif
  if ($type == "auto") then  # auto determine node type
    set typestr = `$bin/savesysteminfo.py --nodetype -q`
    set type = $typestr[4]
  endif
else
  echo "Usage: dmandrcheck.sh <phase> <bindir> <outdir> [node type]"
  echo " phase = initial|load|15|30|60|reconfig|all|testing (default=initial)"
  echo " node type = control|clique|ordinary|auto|test (default=auto)"
  exit
endif

echo " type:" $type
if ($type == "control") then
  set nodeoptions = ""
else if ($type == "clique") then
  set nodeoptions = "--xpersystem"  # don't run functions that are only done on the CN
else if ($type == "ordinary") then
  set nodeoptions = "--xperclique --xpersystem"  #don'r run functions that are only done on the CN or clique reps
else
  echo " Unknown node type"
  exit 1
endif

echo " phase:" $phase
set options = "$nodeoptions -b $bin"
echo " options:" $options


#For testing
if ($phase == "testing") then
  date;
  echo " saving configuration to ./$phase"
  echo " " $bin/savesysteminfo.py --ctl --tvamconfig --pdestate --tpatrace_u --vprocstatus -o $out/$phase $options
  $bin/savesysteminfo.py --ctl --tvamconfig --pdestate --tpatrace_u --vprocstatus -o $out/$phase $options
  date;
endif


#After initial configuration
if ($phase == "initial") then
  echo " saving configuration to ./$phase"
  echo " " $bin/savesysteminfo.py --config -o $out/initial $options
  $bin/savesysteminfo.py --config -o $out/$phase $options
  date;
endif


#After load_tpch
if ($phase == "load") then
  date;
  echo " saving dbs info to ./$phase"
  echo " " $bin/savesysteminfo.py --dbs -o $out/$phase $options
  $bin/savesysteminfo.py --dbs -o $out/$phase $options
  date;
endif


#After filling to 15% or 30%
if ($phase == 15 || $phase == 30) then
  date;
  echo " saving configuration to ./$phase"
  echo " " $bin/savesysteminfo.py --status --dbs -o $out/$phase $options
  $bin/savesysteminfo.py --status --dbs -o $out/$phase $options
  date;
endif


#After filling to 60%
if ($phase == 60) then
  date;
  echo " dbs info, scandisk tests, estimate compresson"
  echo " " $bin/savesysteminfo.py --status --dbs --datacheck --estcompr -o $out/$phase $options
  $bin/savesysteminfo.py --status --dbs --datacheck --estcompr -o $out/$phase $options
 
  if ($type == "control" || $type == "clique") then
    echo " start disk tests"
    echo " " $bin/dothilldmandr.py -t 3 -v
#    $bin/dothilldmandr.py -t 3 -v
  endif
  date;
endif


#After reconfiguring system
if ($phase == "reconfig") then
  echo " saving config, status, dbs info, showwhere vproc 1, estimate compression, run scandisk/checktable"
  echo " " $bin/savesysteminfo.py --all --estcompr --datacheck --where1 -o $out/$phase $options
  $bin/savesysteminfo.py --all --estcompr --datacheck --where1 -o $out/$phase $options
  date;
endif


