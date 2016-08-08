/usr/pde/bin/cnsrun -multi  -utility ferret -commands "{enable script} {scope all;} {scandisk;} {y} {quit}" -debug 1 > all_vprocs_scandisk_`date +%a%b%d%T%Z%Y`.out
/usr/pde/bin/cnsrun -multi  -utility ferret -commands "{enable script} {scope all;} {scandisk cr;} {y} {quit}" -debug 1 > all_vprocs_scandisk_cr_`date +%a%b%d%T%Z%Y`.out
/usr/pde/bin/cnsrun -multi  -utility ferret -commands "{enable script} {scope all;} {scandisk freeci;} {y} {quit}" -debug 1 > all_vprocs_scandisk_freeci_`date +%a%b%d%T%Z%Y`.out

#/usr/pde/bin/cnsrun -multi  -utility ferret -commands "{enable script} {scope vproc 4;} {scandisk;} {y} {quit}" -debug 1 > vproc4_scandisk_`date +%a%b%d%T%Z%Y`.out
#/usr/pde/bin/cnsrun -multi  -utility ferret -commands "{enable script} {scope vproc 4;} {scandisk cr;} {y} {quit}" -debug 1 > vproc4_scandisk_cr_`date +%a%b%d%T%Z%Y`.out
#/usr/pde/bin/cnsrun -multi  -utility ferret -commands "{enable script} {scope vproc 4;} {scandisk freeci;} {y} {quit}" -debug 1 > vproc4_scandisk_freeci_`date +%a%b%d%T%Z%Y`.out

/usr/pde/bin/cnsrun -multi  -utility ferret -commands "{enable script} {scope vproc 2;} {scandisk;} {y} {quit}" -debug 1 > vproc2_scandisk_`date +%a%b%d%T%Z%Y`.out
/usr/pde/bin/cnsrun -multi  -utility ferret -commands "{enable script} {scope vproc 2;} {scandisk cr;} {y} {quit}" -debug 1 > vproc2_scandisk_cr_`date +%a%b%d%T%Z%Y`.out
/usr/pde/bin/cnsrun -multi  -utility ferret -commands "{enable script} {scope vproc 2;} {scandisk freeci;} {y} {quit}" -debug 1 > vproc2_scandisk_freeci_`date +%a%b%d%T%Z%Y`.out

/usr/pde/bin/cnsrun -multi  -utility checktableb -commands "{check all tables at level three in parallel;} {quit;}" -debug 1 > chktable_l1_$1_`date +%a%b%d%T%Z%Y`.out
