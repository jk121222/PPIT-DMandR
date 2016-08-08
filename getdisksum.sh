bteq<<[bteq]
.logon dbc/dbc, dbc;
sel date, time;
sel diskspace.databasename,
sum(currentperm) (format 'zzz,zzz,zzz,zzz,zz9.99')
,sum(maxperm) (format 'zzz,zzz,zzz,zzz,zz9.99')
group by databasename
order by databasename
with sum(currentperm)(format 'zzz,zzz,zzz,zzz,zz9.99')
,sum(maxperm)(format 'zzz,zzz,zzz,zzz,zz9.99');
        .logoff
.quit
[bteq]
