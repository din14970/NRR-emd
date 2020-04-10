
import argparse
import logging
import sys
import os
from pathlib import Path


logging.basicConfig(level=logging.DEBUG)


def main():
    from TEMMETA.basictools import data_io as bo
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
        f = bo.EMDFile(inpath)
        logging.debug("Opened file {}".format(inpath))
    except OSError:
        logging.error("Did not manage to open file {}".format(inpath))
        return

    f.print_simple_structure()


if __name__ == "__main__":
    ownpath = os.path.abspath(__file__)
    folder, file = os.path.split(ownpath)
    folder = Path(folder)
    sys.path.append(str(folder.parent))

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    main()
