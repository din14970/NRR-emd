import os
import sys
import logging
logging.basicConfig(level=logging.INFO)

from apply_deformations import write_as_png
import hyperspy.api as hs
import json
import argparse
import imageio
import numpy as np

from scipy.sparse import load_npz, save_npz, spmatrix


def save_hyperspy_image(path, image, metadata, original_metadata = None):
    """
    Saves the image as a hyperspy object which can be easily loaded in a notebook
    The advantage is that the scale in the image is preserved

    Args:
    path (str): The path to where the image should be saved
    image (np.ndarray): the array that must be converted to a hyperspy image
    metadata (dict): the simplified dictionary from which scale is read
    original_metadata: if provided, the original emd metadata is also stored in the object.

    Returns:
    hs.signals.Signal2D
    """
    hsim = hs.signals.Signal2D(image)
    hsim.axes_manager[0].name = 'x'
    hsim.axes_manager['x'].units = metadata["Scan"]["Width"]["PixelSize_Units"]
    hsim.axes_manager['x'].scale = metadata["Scan"]["Width"]["PixelSize"]
    hsim.axes_manager[1].name = 'y'
    hsim.axes_manager['y'].units = metadata["Scan"]["Height"]["PixelSize_Units"]
    hsim.axes_manager['y'].scale = metadata["Scan"]["Height"]["PixelSize"]
    if original_metadata:
        hsim.original_metadata=original_metadata
    hsim.save(path)
    return hsim


def save_hyperspy_spectrum(path, spec, metadata, original_metadata = None):
    """
    Saves the spectrum as a hyperspy object which can be easily loaded in a notebook
    The advantage is that the scale and dispersion are preserved

    Args:
    path (str): The path to where the image should be saved
    image (np.ndarray or scipy.sparse): the array that must be converted to a hyperspy image
    metadata (dict): the simplified dictionary from which scale is read
    original_metadata: if provided, the original emd metadata is also stored in the object.

    Returns:
    hs.signals.Signal1D
    """
    channels = metadata["EDX"]["Channels"]
    height = metadata["Scan"]["Height"]["Pixels"]
    width = metadata["Scan"]["Width"]["Pixels"]
    if isinstance(spec, spmatrix):
        specar = spec.toarray()
        spec = specar.T.reshape(channels, height, width).T
    spec = hs.signals.Signal1D(spec)
    spec.set_signal_type("EDS_TEM")
    spec.axes_manager[-1].name = 'E'
    spec.axes_manager['E'].units = metadata["EDX"]["Dispersion_Unit"]
    spec.axes_manager['E'].scale = metadata["EDX"]["Dispersion"]
    spec.axes_manager['E'].offset = metadata["EDX"]["EnergyOffset"]
    spec.axes_manager[0].name = 'x'
    spec.axes_manager['x'].units = metadata["Scan"]["Width"]["PixelSize_Units"]
    spec.axes_manager['x'].scale = metadata["Scan"]["Width"]["PixelSize"]
    spec.axes_manager[1].name = 'y'
    spec.axes_manager['y'].units = metadata["Scan"]["Height"]["PixelSize_Units"]
    spec.axes_manager['y'].scale = metadata["Scan"]["Height"]["PixelSize"]
    if original_metadata:
        spec.original_metadata=original_metadata
    spec.save(path)
    return spec


def get_mean_image(inpath, oupath = None):
    """
    Calculates the mean image from a list of images in a folder.
    Optionally writes out the result to a file if oupath is provided.
    The folder must contain only images or the script fails!

    Args:
    inpath: path to the folder containing the image series
    oupath: the path to the image that should be written out

    Returns:
    np.ndarray: the averaged image
    """
    firstiteration = True
    filelist = os.listdir(inpath)
    counter = 0
    for file in filelist:
        #ignore hidden files
        if file[0]!=".":
            try:
                image = imageio.imread(os.path.join(inpath, file))
            except:
                logging.error(f"Something went wrong reading file {file}")
                return
            if firstiteration:
                original_dtype = image.dtype
                av = np.zeros(shape = [image.shape[0], image.shape[1]], dtype="uint64")
                firstiteration = False
            av+=image
            counter+=1 #counter bc len filelist is unreliable
    av = av//counter
    logging.info(f"Succesfully read {counter} frames and averaged them")
    if not oupath is None:
        try:
            write_as_png(av.astype(original_dtype), oupath) #to get a quick view
            logging.info(f"Succesfully saved the averaged image as 8-bit png")
        except:
            logging.error("Something went wrong saving the averaged image")
    return av

def get_total_spectrum(inpath, oupath = None):
    """
    Calculates the total spectrum from a list of frame spectra in a folder (npz sparse format).
    Returns a sparse matrix format. Metadata is required to transform this to a useful format!
    The sparse format can be written to a file if oupath is specified.

    Args:
    inpath: path to the folder containing the spectral frame series
    oupath: the path to the file where the spectrum that should be written out. Default none.

    Returns:
    scipy.sparse.csv_matrix
    """
    av = 0
    files = os.listdir(inpath)
    counter = 0
    for i in files:
        #ignore hidden files
        if i[0]!=".":
            spec = load_npz(os.path.join(inpath, i))
            av += spec.astype("uint64")
            counter +=1
    logging.info(f"Succesfully read {counter} frames and added them")
    if not oupath is None:
        try:
            save_npz(oupath, av)
            logging.info(f"Succesfully saved the total spectrum")
        except:
            logging.error("The output path is not valid")
    return av


def calculate(folder):
    """
    Calculates a bunch of averaged/summed results for spectrum and image data
    """
    imF = folder +"/images/"
    defImF = folder +"/deformedImages/"
    spF = folder +"/spectra/"
    defSpF = folder +"/deformedSpectra/"

    #set the path to the deformed images folder
    res = folder+"/processed_results/"
    if not os.path.isdir(res):
        os.makedirs(res)

    #load the metadata
    try:
        with open(f"{folder}/metadata.json") as f:
            metadata = json.load(f)
    except:
        logging.error("No metadata file was found, will not write out hyperspy objects.")
        metadata = None

    #average of the normal images
    logging.info("Writing out the original average image")
    avimo = get_mean_image(imF, res+"averaged_original.png")
    #average of the deformed images
    logging.info("Writing out the deformed average image")
    avimp = get_mean_image(defImF, res+"averaged_deformed.png")
    #average of the original spectra
    try:
        logging.info("Writing out the original total spectrum")
        totspeco = get_total_spectrum(spF, res+"averaged_original_spectrum")
        #average of the deformed spectra
        logging.info("Writing out the deformed total spectrum")
        totspecp = get_total_spectrum(defSpF, res+"averaged_deformed_spectrum")
    except:
        logging.warning("No spectrum info found")

    if metadata:
        logging.info("Hyperspy and metadata found, repeating with units")
        logging.info("Writing out the original average image")
        save_hyperspy_image(res+"averaged_original", avimo, metadata)
        logging.info("Writing out the deformed average image")
        save_hyperspy_image(res+"averaged_deformed", avimp, metadata)
        try:
            logging.info("Writing out the original total spectrum")
            save_hyperspy_spectrum(res+"averaged_original_spectrum", totspeco, metadata)
            logging.info("Writing out the deformed total spectrum")
            save_hyperspy_spectrum(res+"averaged_deformed_spectrum", totspecp, metadata)
        except:
            logging.warning("No spectrum info found")

    #difference of the averaged images
    logging.info("Saving the difference between images")
    difim = avimp-avimo
    write_as_png(difim.astype("uint16"), res+"difference_images.png")
    if metadata:
        logging.info("Also in hyperspy format")
        save_hyperspy_image(res+"difference_images", difim, metadata)
    #difference of the averaged spectra
    try:
        logging.info("Saving the difference between spectra")
        difspec = totspecp-totspeco
        save_npz(res+"difference_spectrum", difspec)
        save_hyperspy_spectrum(res+"difference_spectrum", totspecp, metadata)
    except:
        logging.warning("No spectrum info found")
    logging.info("Done")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder",
                        help = "root folder containing the metadata, config, images and spectra")
    args = parser.parse_args()
    calculate(args.folder)


if __name__=="__main__":
    from pathlib import Path

    ownpath = os.path.abspath(__file__)
    folder, file = os.path.split(ownpath)
    folder = Path(folder)

    sys.path.append(str(folder.parent))
    sys.path.append(str(folder))

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    main()
