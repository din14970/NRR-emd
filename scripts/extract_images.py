"""
From the root folder NRR run
```
python3 ./scripts/extract_images.py "<absolute path to EMD file>"
```
Optional arguments are:
```
-o, --output [path to where all output should be stored. Defaults to current
working directory.]
-n, --filename [name prefix the output files should have. Defaults to the
name of the EMD file.]
-d, --detector [the index that corresponds to the dataset that contains the
image frames [0-?]. The script will try to find this automatically but it may
fail if multiple datasets are included with multiple frames in the same EMD
file. You can visualise the emd structure with the get_emd_tree_view in
TEMMETA/basictools/data_io.py or with a tool like HDFView. Script fails if the
index is out of range.]
-s, --spectrumdetector [same as -d except for the SpectrumStream data.
Defaults to 0, assuming only one dataset per emd file. Script fails if the
index is out of range.]
-p, --padding [the frames will be exported with the filename_%0x.tiff pattern.
p determines the number of counter digits. By default the minimum number of
digits is calculated based on the number of frames. If p is less than the
minimum number of digits required the script will fail.]
-m, -M minimum and maximum intensity to use for rescaling to 8 bit
```
"""

import argparse
import logging
import os
import numpy as np
from pathlib import Path
from temmeta import data_io as bo

logging.basicConfig(level=logging.DEBUG)


def main():

    extension = "png"
    # set up the argparser
    parser = argparse.ArgumentParser()
    parser.add_argument("input",
                        help="path to EMD file")
    parser.add_argument("-o", "--output",
                        help="path to where output should be stored",
                        default=".")
    parser.add_argument("-n", "--filename", type=str,
                        help="name given to the output image frames",
                        default=None)
    parser.add_argument("-d", "--detector", type=int,
                        help=("the index of the dataset containing the image"
                              " frames. Only try if the right dataset is not"
                              " found automatically."),
                        default=None)
    parser.add_argument("-s", "--spectrumdetector", type=int,
                        help=("the index of the dataset containing the"
                              " spectrum frames. only try if the right dataset"
                              " is not found automatically."),
                        default=None)
    parser.add_argument("-p", "--padding", type=int,
                        help=("number of digits in the frame counter. If not"
                              " used will default to just the necessary "
                              "amount."),
                        default=None)
    parser.add_argument("-m", "--minimum", type=int,
                        help="Minimum intensity to use for linear scaling",
                        default=None)
    parser.add_argument("-M", "--maximum", type=int,
                        help="Maximum intensity to use for linear scaling",
                        default=None)
    args = parser.parse_args()  # read the arguments, store in args

    # get input path and extension
    inpath = args.input
    _, ext = os.path.splitext(inpath)
    if not os.path.isfile(inpath) and ext == "emd":
        logging.error("{} is not a valid emd file path".format(inpath))
        return

    # get the output path
    oupath = args.output
    if not os.path.isdir(oupath):
        logging.error("{} is not a valid directory".format(oupath))
        logging.error("Will attempt to create this directory")
        os.makedirs(oupath)

    # No filename provided? Take the name of the emd file without spaces
    if args.filename is None:
        fullname = inpath.split("/")[-1]
        expname, _ = os.path.splitext(fullname)
        expname = expname.replace(" ", "")
    else:
        expname = args.filename

    # read in the file
    try:
        f = bo.EMDFile(inpath)
        logging.debug("Opened file {}".format(inpath))
    except OSError:
        logging.error("Did not manage to open file {}".format(inpath))
        return

    # setting some variables that may be useful at later stages
    det_no = 0
    det_uuid = 0
    num_frames = 0
    # if no specific dataset is mentioned, try and find it
    if args.detector is None:
        oup = f._guess_multiframe_dataset()
        if oup:  # something was found
            det_no, det_uuid, num_frames = oup
            stack = f.get_dataset("Image", det_uuid)
        else:
            return
    else:
        try:
            det_no = args.detector
            det_uuid = f._get_ds_uuid("Image", det_no)
            stack = f.get_dataset("Image", det_uuid)
            num_frames = stack.frames
        except (ValueError, KeyError, IndexError):
            logging.error(f"{det_no} is an invalid dataset number")
            return

    # write out the simplified metadata to a json file
    try:
        logging.debug("Writing out the metadata...")
        stack.metadata.to_file(f"{oupath}/metadata_images.json")
    except OSError:
        logging.error("Error reading or writing the metadata")

    imsize = stack.width
    outlevel = int(np.log2(imsize))
    logging.debug(f"The images are {imsize}x{imsize}. "
                  f"There are {num_frames} frames.")
    logging.debug(f"The images dataset UUID is {det_uuid} and detector"
                  f" index is {det_no}")
    # output path for images
    path = str(Path(oupath+"/images/"))

    stack.export_frames(path, expname, counter=args.padding,
                        dtype=np.uint8, min=args.minimum, max=args.maximum)
    logging.debug(f"Wrote the image frames out to files in {path}")

    # which dataset to export
    if not args.spectrumdetector:
        det_no_spec = 0
    else:
        det_no_spec = args.spectrumdetector
    # output path for spectra
    path = str(Path(oupath+"/spectra/"))
    logging.debug("Trying to write out the spectral frames to {}".format(path))
    try:
        spec_uuid = f._get_ds_uuid("SpectrumStream", det_no_spec)
        spectrumstream = f.get_dataset("SpectrumStream", spec_uuid)
        spectrumstream.write_streamframes(path, expname, counter=args.padding)
        logging.debug(f"Wrote the spectral frames out to files in {path}")
    except (KeyError, ValueError):
        logging.error("""Failed to write out spectral frames.
                        Likely the emd file
                        does not contain a spectrum stream""")

    # we have to calculate the counter anyway now... At this point an error
    # should already have been raised if the counter is too small
    if args.padding:
        counter = args.padding
    else:
        counter = bo._get_counter(num_frames)

    # construct the config file
    filename = str(Path(oupath+"/matchSeries_{}.par".format(expname)))
    pathpattern = str(Path(oupath+"/images/{}_%0{}d.{}".format(expname,
                                                               counter,
                                                               extension)))
    abspath = str(Path(oupath))
    # already create the folder for the output
    outputpath = str(Path("{}/nonrigid_results/".format(abspath)))
    if not os.path.isdir(outputpath):
        os.makedirs(outputpath)
    write_config_file(filename, pathpattern, abspath, outlevel, num_frames)


def write_config_file(filename, pathpattern=" ", abspath=" ",
                      preclevel=8, num_frames=1):
    savedir = str(Path(f"{abspath}/nonrigid_results/"))
    cnfgtmpl = ("templateNamePattern {}\n"
                "templateNumOffset 0\n"
                "templateNumStep 1\n"
                "numTemplates {}\n"
                "#templateSkipNums {{ }}\n"
                "\n"
                "cropInput 0\n"
                "cropStartX 0\n"
                "cropStartY 0\n"
                "dontResizeOrCropReference 0\n"
                "\n"
                "preSmoothSigma 0\n"
                "\n"
                "saveRefAndTempl 0\n"
                "\n"
                "numExtraStages 2\n"
                "\n"
                "saveDirectory {}\n"
                "\n"
                "dontNormalizeInputImages 0\n"
                "enhanceContrastSaturationPercentage 0.15\n"
                "normalizeMinToZero 1\n"
                "\n"
                "# lambda weights the deformation regularization term\n"
                "lambda         200\n"
                "# lambdaFactor scales lambda dependening on the current level"
                ": On level d, lambda is multiplied by pow ( lambdaFactor, "
                "stopLevel - d )\n"
                "lambdaFactor   1\n"
                "\n"
                "maxGDIterations 500\n"
                "stopEpsilon 1e-6\n"
                "\n"
                "startLevel {}\n"
                "stopLevel {}\n"
                "precisionLevel {}\n"
                "refineStartLevel {}\n"
                "refineStopLevel {}\n"
                "\n"
                "checkboxWidth {}\n"
                "\n"
                "resizeInput 0\n"
                "\n"
                "dontAccumulateDeformation 0\n"
                "reuseStage1Results 1\n"
                "extraStagesLambdaFactor 0.1\n"
                "useMedianAsNewTarget 1\n"
                "calcInverseDeformation 0\n"
                "skipStage1 0\n"
                "\n"
                "saveNamedDeformedTemplates 1\n"
                "saveNamedDeformedTemplatesUsing"
                "NearestNeighborInterpolation 1\n"
                "saveNamedDeformedTemplatesExtendedWithMean 1\n"
                "saveDeformedTemplates 1\n"
                "saveNamedDeformedDMXTemplatesAsDMX 1")
    cnfg = cnfgtmpl.format(pathpattern, num_frames, savedir, preclevel-2,
                           preclevel, preclevel, preclevel-1, preclevel,
                           preclevel)
    with open(filename, "w") as file:
        file.write(cnfg)

    logging.debug("Wrote the config file with an initial parameter guess")


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    main()
