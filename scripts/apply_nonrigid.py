"""
This is a shortened script to do:
- apply nonrigid registration
- apply the deformations to the spectra
- calculate the averages after deformation
"""
import argparse
import subprocess
import logging
import os
import sys
from time import time

logging.basicConfig(level=logging.INFO)

def main():
    from pathlib import Path

    ownpath = os.path.abspath(__file__)
    folder, file = os.path.split(ownpath)
    folder = Path(folder)

    #sys.path.append(str(folder))
    sys.path.append(str(folder.parent))
    ptms = str(folder.parent)+"/match-series/quocGCC/projects/electronMicroscopy/"
    sys.path.append(ptms)
    print(sys.path)

    parser = argparse.ArgumentParser()
    parser.add_argument("config",
                        help = "Path to the config file for non-rigid registration")
    args = parser.parse_args()
    ptc = args.config
    #the command for nonrigid
    logging.info("------------------------------------------")
    logging.info("--------Non-rigid registration------------")
    logging.info("------------------------------------------")
    logging.info(f"Calling non-rigid registration on {ptc}")
    cmd = ["./matchSeries", f"{ptc}"]
    process1 = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd = ptms)
    process1.wait()
    logging.info(f"Finished non-rigid registration")
    logging.info(" ")
    logging.info("------------------------------------------")
    logging.info("--------Applying deformations-------------")
    logging.info("------------------------------------------")
    logging.info("Applying the calculated deformations to images and spectra")
    start = time()
    ptf, cff = os.path.split(ptc)
    #apply the spectra
    cmd = ["python3", "apply_deformations.py", f"{ptf}"]
    process2 = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd = folder)
    process2.wait()
    stop = time()
    totalsec = stop-start
    hours = totalsec//3600
    min = (totalsec - hours*3600)//60
    sec = int(totalsec%60)
    logging.info(f"Finished applying the calculated deformations to images \
                    and spectra in {hours}h:{min}m:{sec}s")
    logging.info(" ")
    logging.info("------------------------------------------")
    logging.info("--------Calculating averages--------------")
    logging.info("------------------------------------------")
    logging.info("Calculating the averaged image and total spectra")
    #Calculate the average
    start = time()
    cmd = ["python3", "process_results.py", f"{ptf}"]
    process3 = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd = folder)
    process3.wait()
    stop = time()
    totalsec = stop-start
    hours = totalsec//3600
    min = (totalsec - hours*3600)//60
    sec = int(totalsec%60)
    logging.info(f"Finished calculation of averages in {hours}h:{min}m:{sec}s")

if __name__ == '__main__':
    #snippet to be able to add the absolute parent folder path of the script on the path
    main()
