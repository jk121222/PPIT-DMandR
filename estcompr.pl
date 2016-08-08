#!/usr/bin/perl
`/usr/pde/bin/cnsrun -multi  -utility ferret -commands "{enable script} {scope table all;} {showblocks;} {y} {quit}" -debug 1 > testblc.out`;
`cat testblc.out |grep 0|  grep C |grep %> t1`;  # filter stuff out
#
my $rowcomprblk=0;
my $sumblocks=0;
my $sumcomprblocks=0;
my $comprratio=0;
open (file , "t1");
my @rows = <file>;
foreach my $row (@rows) {
        (@item)=split(/\|/, $row);
        $item[3]=~ s/%//;
$rowcomprblk=$item[3]*$item[23]/100;
print "$item[3]$item[23]$rowcomprblk\n";
$sumblocks += $item[23];
$sumcomprblocks += $rowcomprblk;
}
print "Sum of Blocks:                   ";
print "$sumblocks\n";
print "Sum of Compression Blocks:       ";
print "$sumcomprblocks\n";
$comprratio=$sumcomprblocks*100/$sumblocks;
print "Estimated Compression Ratio:     ";
$answer=sprintf ('%.2f', $comprratio);
print "$answer";
print "%\n";

