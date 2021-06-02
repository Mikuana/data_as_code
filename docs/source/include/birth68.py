import csv
import gzip
import shutil
from collections import defaultdict
from ftplib import FTP
from zipfile import ZipFile

from data_as_code import Recipe, Step, result, ingredient


class BirthData(Recipe):
    """ Aggregate CDC Vital Statistics data to count births in 1968 """

    class Get68(Step):
        """ Download 1968 U.S. birth data file from FTP """

        def instructions(self):
            with FTP('ftp.cdc.gov') as ftp:
                ftp.login()
                ftp.cwd('/pub/Health_Statistics/NCHS/Datasets/DVS/natality')
                with self.output.open('wb') as f:
                    ftp.retrbinary(f'RETR {self.output.name}', f.write)

    class Convert68(Step):
        """ Extract PUB file from Zip and recompress as Gzip """
        z = ingredient('Get68')

        def instructions(self):
            with ZipFile(self.z.as_posix()) as zf:
                with zf.open(self.output.stem) as pf:
                    with gzip.open(self.output.as_posix(), 'wb') as gf:
                        shutil.copyfileobj(pf, gf)

    class Reduce68(Step):
        """ Extract month column from PUB file an count births """
        output = result('nat1968.csv')
        g = ingredient('Convert68')

        def instructions(self):
            def handle_int(x: bytes):
                x = x.decode('utf8')
                return int(x) if x.strip() else None

            with gzip.open(self.g, 'rb') as gf:
                counts = defaultdict(lambda: 0)
                for line in gf:
                    if not line.isspace():
                        k = (1968, handle_int(line[31:33]))
                        counts[k] += 2  # 1968 is a 50% sample of birth records

            with self.output.open('w', newline='') as cf:
                w = csv.writer(cf)
                w.writerow(['Year', 'Month', 'Count'])
                for k in sorted(counts.keys()):
                    w.writerow([*k] + [counts[k]])
