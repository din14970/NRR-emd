"""
Module that includes tools for converting experimental data into the
file structure required for match-series
"""
from temmeta import data_io as dio
from PIL import Image
import concurrent.futures as cf
import logging
from pathlib import Path
import os
import numpy as np
import re
import bz2


def export_frame(frame, path):
    """Export a single numpy array as an image at path"""
    img = Image.fromarray(frame)
    img.save(path)


def _save_frame_to_file(i, data, path, name, counter, data_format="tiff"):
    """Helper function for multithreading, saving frame i of stack"""
    c = str(i).zfill(counter)
    fp = str(Path(f"{path}/{name}_{c}.{data_format}"))
    frm = data[i]
    img = Image.fromarray(frm)
    img.save(fp)


class FrameByFrame(object):
    """A pickle-able wrapper for doing a function on all frames of a stack"""
    def __init__(self, do_in_loop, stack, *args, **kwargs):
        self.func = do_in_loop
        self.stack = stack
        self.args = args
        self.kwargs = kwargs

    def __call__(self, index):
        self.func(index, self.stack, *self.args, **self.kwargs)


def export_frames(stack, output_folder=None, prefix="frame",
                  digits=None, frames=None, multithreading=True,
                  data_format="tiff"):
    """
    Export a 3D data array as individual images
    """
    if frames is None:
        toloop = range(stack.frames)
    elif isinstance(frames, list):
        toloop = frames
    else:
        raise TypeError("Argument frames must be a list")
    if multithreading:
        with cf.ThreadPoolExecutor() as pool:
            pool.map(FrameByFrame(_save_frame_to_file, stack.data,
                                  output_folder, prefix, digits, data_format),
                     toloop)
    else:
        for i in toloop:
            _save_frame_to_file(i, stack.data, output_folder, prefix, digits,
                                data_format)


def extract_emd(input_path, output_folder=None, prefix="frame",
                image_dataset_index=None, spectrum_dataset_index=None,
                digits=None, image_post_processing=None, frames=None,
                extension="tiff", multithreading=True, **kwargs):
    """
    Extract images and spectrum data from Velox emd files using TEMMETA.

    Creates a folder structure that is required for match-series

    Parameters
    ----------
    input_path : str
        path to the emd file
    output_folder : str, optional
        path to the folder where the output files should be saved. Defaults
        to the folder in which the emd file is saved.
    prefix : str, optional
        easy name for the individual image and spectrum frames. It should
        not include spaces - they will be deleted
    image_dataset_index : int, list of ints, optional
        integer or list of integers to indicate which image datasets must be
        extracted. By default, all are extracted.
    spectrum_dataset_index : int, list of ints, optional
        integer or list of integers to indicate which spectrumstream datasets
        must be extracted. By default, all are extracted.
    digits : int, optional
        how many counter digits are to be added to each frame. Defaults to the
        minimum necessary
    image_post_processing: callable, optional
        callable that acts on the images to process them before they are
        exported.
    frames: list, optional
        a list of indexes of frames that should be exported if not all.
    extension: str, optional
        extension of the exported images
    multithreading : bool, optional
        whether to use multithreading to export

    Additional parameters
    ---------------------
    See kwargs of processing.write_config method
    """
    if not os.path.isfile(input_path) and ext == "emd":
        raise ValueError("{} is not a valid emd file path".format(input_path))
    input_path = os.path.abspath(input_path)
    inp, ext = os.path.splitext(input_path)
    if output_folder is None:
        output_folder = os.path.dirname(input_path)
    elif not os.path.isdir(output_folder):
        logging.error("{} is not a valid directory".format(output_folder))
        logging.error("Will attempt to create this directory")
        os.makedirs(output_folder)
    # remove spaces in the prefix if any
    prefix = prefix.replace(" ", "")
    # read the file
    try:
        f = dio.EMDFile(input_path)
        logging.debug("Opened file {}".format(input_path))
    except Exception as e:
        raise Exception(f"Something went wrong reading the file: {e}")
    # Images
    # if no dataset is given we extract all of them
    if image_dataset_index is None:
        dsets = enumerate(f["Data/Image"].keys())
    elif isinstance(image_dataset_index, list):
        dsets = enumerate([f._get_ds_uuid("Image", i)
                           for i in image_dataset_index])
    elif isinstance(image_dataset_index, int):
        dsets = enumerate([f._get_ds_uuid("Image", image_dataset_index)])
    else:
        raise TypeError("image_dataset_index received unexpected type:"
                        f"{type(image_dataset_index)}")
    image_paths = []
    output_paths = []
    config_paths = []
    for j, k in dsets:
        try:
            ima = f.get_dataset("Image", k)
            logging.debug(f"Succesfully read dataset {k}")
            # apply filter function to image stack if given
            if image_post_processing is not None:
                try:
                    ima.apply_filter(image_post_processing, inplace=True)
                except Exception as e:
                    raise Exception(f"Could not apply post-process: {e}")
            c = str(j).zfill(3)
            opath = str(Path(f"{output_folder}/images_{c}/"))
            if not os.path.isdir(opath):
                os.makedirs(opath)
            if digits is None:
                digits = dio._get_counter(ima.frames)
            else:
                digits = digits
            export_frames(ima, output_folder=opath,
                          prefix=prefix,
                          digits=digits, frames=frames,
                          multithreading=multithreading,
                          data_format=extension)
            ima.metadata.to_file(f"{opath}/metadata_images.json")
            # also create a config file for all datasets
            # construct the config file
            filename = str(Path(output_folder+f"/matchSeries_{c}.par"))
            pathpattern = str(Path(
              output_folder+f"/images_{c}/{prefix}_%0{digits}d.{extension}"))
            abspath = str(Path(output_folder))
            # already create the folder for the output
            outputpath = str(Path(f"{abspath}/nonrigid_results_{c}/"))
            outlevel = int(np.log2(ima.width))
            if not os.path.isdir(outputpath):
                os.makedirs(outputpath)
            write_config_file(filename, pathpattern=pathpattern,
                              savedir=outputpath,
                              preclevel=outlevel, num_frames=ima.frames,
                              **kwargs)
            print(f"Dataset {k} was exported to {opath}. A config file "
                  f"{filename} was created.")
            image_paths.append(opath)
            output_paths.append(outputpath)
            config_paths.append(filename)
        except Exception as e:
            logging.warning(f"Dataset {k} was not exported: {e}")
    # Spectrumstreams
    # are there any in the dataset?
    try:
        f["Data/SpectrumStream"]
    except Exception:
        logging.debug("There is no spectral data in this dataset")
        return {"image_folder_paths": image_paths,
                "output_folder_paths": output_paths,
                "spectrum_folder_paths": None,
                "config_file_paths": config_paths}
    spectrum_paths = []
    # if no dataset is given we extract all of them
    if spectrum_dataset_index is None:
        ssets = enumerate(f["Data/SpectrumStream"].keys())
    elif isinstance(spectrum_dataset_index, list):
        ssets = enumerate([f._get_ds_uuid("SpectrumStream", i)
                           for i in spectrum_dataset_index])
    elif isinstance(spectrum_dataset_index, int):
        ssets = enumerate([f._get_ds_uuid("SpectrumStream",
                                          image_dataset_index)])
    else:
        raise TypeError("spectrum_dataset_index received unexpected type:"
                        f"{type(spectrum_dataset_index)}")
    for j, k in ssets:
        try:
            spec = f.get_dataset("SpectrumStream", k)
            logging.debug(f"Succesfully read dataset {k}")
            c = str(j).zfill(3)
            opath = str(Path(f"{output_folder}/spectra_{c}/"))
            spec.export_streamframes(opath, prefix, counter=digits)
            logging.debug(f"Wrote the spectral frames out to files in {opath}")
        except Exception as e:
            logging.warning(f"Dataset {k} was not exported: {e}")
        spectrum_paths.append(opath)
    return {"image_folder_paths": image_paths,
            "output_folder_paths": output_paths,
            "spectrum_folder_paths": spectrum_paths,
            "config_file_paths": config_paths}


def write_dict_to_config_file(filename, dic):
    """Write a dictionary to the match-series config file format"""
    p = ""
    for k, v in dic.items():
        p = p+k+" "+v+"\n"
    with open(filename, mode="w") as f:
        f.write(p)


def read_config_file(filename):
    """
    Returns the contents of a config file in a dict form.
    Comment lines are as of now not ignored!
    """
    with open(filename) as f:
        txt = f.read()
    configs = re.findall(r"([a-zA-Z0-9]+) (.+)\n", txt)
    return dict(configs)


def write_config_file(filename, pathpattern=" ", savedir=" ",
                      preclevel=8, num_frames=1, numoffset=0,
                      numstep=1, skipframes=[], presmooth=False,
                      saverefandtempl=False, numstag=2, normalize=True,
                      enhancefraction=0.15, mintozero=True, regularization=200,
                      regfactor=1, gditer=500, epsilon=1e-6,
                      startleveloffset=2,
                      extralambda=0.1):
    """
    Wrapper function to create a standard config file

    Parameters
    ----------
    filename : str
        path to the config file
    pathpattern : str, optional
        string pattern for image files
    savedir : str, optional
        path to output folder
    preclevel : int, optional
        base2 power of the images
    num_frames : int, optional
        number of images to process
    numoffset : int, optional
        index of first image to process
    numstep : int, optional
        to skip frames at regular interval
    skipframes : list, optional
        to kick out certain frames
    presmooth : bool, optional
        to smooth images before usage
    saverefandtempl : bool, optional
        save both the reference and the template
    numstage : int, optional
        number of stages
    normalize : bool, optional
        normalize the images
    enhancefraction : float, optional
        brightness/contrast adjustment
    mintozero : bool, optional
        minimum intensity mapped to 0
    regularization : int, optional
        regularization factor used in optimization level 1
    regfactor : float, optional
        adjustment of reg parameter with different binnings
    gditer : int, optional
        max number of iterations
    epsilon : float, optional
        desired precision
    startleveloffset : int, optional
        offset of the start level
    extralambda : int, optional
        adjustment of regularization with subsequent steps
    """
    if normalize:
        normalize = 0
    else:
        normalize = 1
    skipframes = " ".join(map(str, skipframes))
    cnfgtmpl = (f"templateNamePattern {pathpattern}\n"
                f"templateNumOffset {numoffset}\n"
                f"templateNumStep {numstep}\n"
                f"numTemplates {num_frames}\n"
                f"templateSkipNums {{ {skipframes} }}\n"
                "\n"
                f"preSmoothSigma {presmooth*1}\n"
                "\n"
                f"saveRefAndTempl {saverefandtempl*1}\n"
                "\n"
                f"numExtraStages {numstag}\n"
                "\n"
                f"saveDirectory {savedir}\n"
                "\n"
                f"dontNormalizeInputImages {normalize*1}\n"
                f"enhanceContrastSaturationPercentage {enhancefraction}\n"
                f"normalizeMinToZero {mintozero*1}\n"
                "\n"
                f"lambda {regularization}\n"
                f"lambdaFactor {regfactor}\n"
                "\n"
                f"maxGDIterations {gditer}\n"
                f"stopEpsilon {epsilon}\n"
                "\n"
                f"startLevel {preclevel-startleveloffset}\n"
                f"stopLevel {preclevel}\n"
                f"precisionLevel {preclevel}\n"
                f"refineStartLevel {preclevel-1}\n"
                f"refineStopLevel {preclevel}\n"
                "\n"
                f"checkboxWidth {preclevel}\n"
                "\n"
                f"resizeInput 0\n"
                "\n"
                f"dontAccumulateDeformation 0\n"
                f"reuseStage1Results 1\n"
                f"extraStagesLambdaFactor {extralambda}\n"
                f"useMedianAsNewTarget 1\n"
                f"calcInverseDeformation 0\n"
                f"skipStage1 0\n"
                "\n"
                f"saveNamedDeformedTemplates 1\n"
                f"saveNamedDeformedTemplatesUsing"
                f"NearestNeighborInterpolation 1\n"
                f"saveNamedDeformedTemplatesExtendedWithMean 1\n"
                f"saveDeformedTemplates 1\n"
                f"saveNamedDeformedDMXTemplatesAsDMX 1")
    with open(filename, "w") as file:
        file.write(cnfgtmpl)

    logging.debug("Wrote the config file with an initial parameter guess")


def loadFromQ2bz(path):
    """
    Opens a bz2 or q2bz file and returns an "image" = the deformations
    """
    filename, file_extension = os.path.splitext(path)
    # bz2 compresses only a single file
    if(file_extension == '.q2bz' or file_extension == '.bz2'):
        # read binary mode, r+b would be to also write
        fid = bz2.open(path, 'rb')
    else:
        fid = open(path, 'rb')  # read binary mode, r+b would be to also write
    # Read magic number - only possible when bz2.open is called! Will not see
    # it in hex fiend!
    # rstrip removes trailing zeros
    binaryline = fid.readline()  # will look like "b"P9\n""
    line = binaryline.rstrip().decode('ascii')  # this will look like "P9"
    if(line[0] != 'P'):
        raise ValueError("Invalid array header, doesn't start with 'P'")
    if(line[1] == '9'):
        dtype = np.float64
    elif(line[1] == '8'):
        dtype = np.float32
    else:
        dtype = None

    if not dtype:
        raise NotImplementedError(
            f"Invalid data type ({line[1]}), only float and "
            "double are supported currently")
    # Skip header = b'# This is a QuOcMesh file of type 9 (=RAW DOUBLE)
    # written 17:36 on Friday, 07 February 2020'
    _ = fid.readline().rstrip()

    # Read width and height
    arr = fid.readline().rstrip().split()
    width = int(arr[0])
    height = int(arr[1])

    # Read max, but be careful not to read more than one new line after max.
    # The binary data could start with a value that is equivalent to a
    # new line.
    max = ""
    while True:
        c = fid.read(1)
        if c == b'\n':
            break
        max = max + str(int(c))

    max = int(max)

    # Read image to vector
    x = np.frombuffer(fid.read(), dtype)
    img = x.reshape(height, width)
    return img


def _getNameCounterFrames(path):
    """
    Extract relevant information from the config file for processing

    Parameters
    ----------
    path : str
        path to the .par config file

    Returns:
    tuple of (base name, number of counter digits, extension, number of frames,
              skipped frames, stoplevel, number of stages)
    """
    with open(path) as f:
        text = f.read()

    basename, counter, ext = re.findall(
        r"[\/\\]([^\/\\]+)_%0(.+)d\.([A-Za-z0-9]+)", text)[0]
    counter = int(counter)
    numframes = int(re.findall(r"numTemplates ([0-9]+)", text)[0])
    try:
        skipframes_line = re.findall(r"[^\# *]templateSkipNums (.*)", text)[0]
        skipframes = re.findall(r"([0-9]+)[^0-9]", skipframes_line)
        skipframes = list(map(int, skipframes))
    except Exception:  # when commented out, will give error
        skipframes = []
    bznumber = re.findall(r"stopLevel +([0-9]+)", text)[0].zfill(2)
    stages = int(re.findall(r"numExtraStages +([0-9]+)", text)[0])+1

    return (basename, counter, ext, numframes, skipframes, bznumber, stages)
