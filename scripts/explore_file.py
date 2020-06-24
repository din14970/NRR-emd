"""
This script prints out the contents of a Velox EMD file
"""
import argparse
import logging
import sys
from pathlib import Path
import os
from temmeta import data_io as dio

def main(): 
    parser = argparse.ArgumentParser()
    parser.add_argument("input",
                        help="path to EMD file")
    args = parser.parse_args()
    # read the arguments, store in args

    # get input path and extension
    inpath = args.input
    _, ext = os.path.splitext(inpath)
    if not os.path.isfile(inpath) and ext == "emd":
        logging.error("{} is not a valid emd file path".format(inpath))
        return

    # read in the file
    try:
        f = dio.EMDFile(inpath)
        logging.debug("Opened file {}".format(inpath))
    except OSError:
        logging.error("Did not manage to open file {}".format(inpath))
        return
    except Exception as e:
        logging.error("Unknown error: {e}")

    f.print_simple_structure()


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    main()
