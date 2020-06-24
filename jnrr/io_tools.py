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
                digits=4, image_post_processing=None, frames=None):
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
    """
    inp, ext = os.path.splitext(input_path)
    if not os.path.isfile(input_path) and ext == "emd":
        raise ValueError("{} is not a valid emd file path".format(input_path))

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
            export_frames(ima, output_folder=opath,
                          prefix=prefix,
                          digits=digits, frames=frames,
                          multithreading=True,
                          data_format="tiff")
            ima.metadata.to_file(f"{opath}/metadata_images.json")
        except Exception as e:
            logging.warning(f"Dataset {k} was not exported: {e}")
    # Spectrumstreams
    # are there any in the dataset?
    try:
        f["Data/SpectrumStream"]
    except Exception:
        logging.debug("There is no spectral data in this dataset")
        return
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
