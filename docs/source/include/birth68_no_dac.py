import csv
import gzip
import shutil
from collections import defaultdict
from ftplib import FTP
from pathlib import Path
from zipfile import ZipFile

zp = Path('Nat1968.ZIP')

with FTP('ftp.cdc.gov') as ftp:
    ftp.login()
    ftp.cwd('/pub/Health_Statistics/NCHS/Datasets/DVS/natality')
    with zp.open('wb') as f:
        ftp.retrbinary(f'RETR {zp.name}', f.write)

gp = Path('NATL1968.PUB.gz')

with ZipFile(zp.as_posix()) as zf:
    with zf.open(gp.stem) as pf:
        with gzip.open(gp.as_posix(), 'wb') as gf:
            shutil.copyfileobj(pf, gf)

cp = Path('nat1968.csv')


def handle_int(x: bytes):
    x = x.decode('utf8')
    return int(x) if x.strip() else None


with gzip.open(gp, 'rb') as gf:
    counts = defaultdict(lambda: 0)
    for line in gf:
        if not line.isspace():
            k = (1968, handle_int(line[31:33]))
            counts[k] += 2  # 1968 is a 50% sample of birth records

with cp.open('w', newline='') as cf:
    w = csv.writer(cf)
    w.writerow(['Year', 'Month', 'Count'])
    for k in sorted(counts.keys()):
        w.writerow([*k] + [counts[k]])
