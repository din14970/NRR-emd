import logging
import os
import subprocess
from PIL import Image
from scipy import ndimage
from pathlib import Path
from .io_tools import read_config_file, loadFromQ2bz, _getNameCounterFrames
import numpy as np
from scipy.sparse import save_npz, csr_matrix
import hyperspy.api as hs
from temmeta import data_io as dio


def write_as_image(img, path):
    defimg = Image.fromarray(img)
    defimg.save(path)


def calculate_non_rigid_registration(config_file):
    cmd = [str("matchSeries"), f"{config_file}", ">", "output.log"]
    process1 = subprocess.Popen(cmd, stderr=subprocess.PIPE)
    process1.wait()
    logging.info("Finished non-rigid registration")
    return read_config_file(config_file)["saveDirectory"]


def apply_deformations(result_folder, image_folder=None,
                       spectra_folder=None):
    """
    Apply the deformations calculated by match-series to images and
    optionally spectra. The resulting deformed images and spectra are
    written out to a folder for later import if necessary.

    Parameters
    ----------
    result_folder : str
        path to the folder where non rigid registration saved its result
    image_folder : str, optional
        path to the folder where the images are stored to which the
        deformations need to be applied. By default it takes the images
        used for the calculation.
    spectra_folder : str, optional
        path to the folder where the spectrum stream frames reside to which
        the deformation should be applied. If None, then no spectra are
        corrected

    Returns
    -------
    averageUndeformed: temmeta.GeneralImage object
        The averaged image of the undeformed dataset
    averageDeformed: temmeta.GeneralImage object
        The averaged image of the corrected dataset
    spectrumUndeformed: temmeta.SpectrumMap object or None
        The sum of all the spectrum frames in the uncorrected dataset
    spectrumDeformed: temmeta.SpectrumMap object or None
        The sum of all the spectrum frames in the corrected dataset
    """
    config_file = str(Path(result_folder + "/parameter-dump.txt"))
    # get the path to the image files
    conf = read_config_file(config_file)
    imfolder, _ = os.path.split(conf["templateNamePattern"])
    if image_folder is not None:
        imfolder = image_folder
    parfolder, imsubfolder = os.path.split(imfolder)
    _, numbering = imsubfolder.split("_")
    # get basic info about the images
    (dataBaseName, counter, imgext, frames, skipframes, bznumber,
        stage) = _getNameCounterFrames(config_file)
    # read in the data
    images = dio.import_files_to_stack(imfolder)
    # set the path to the deformed images folder
    defImagesFolder = parfolder+f"/deformedImages_{numbering}/"
    if not os.path.isdir(defImagesFolder):
        os.makedirs(defImagesFolder)
    images.metadata.to_file(defImagesFolder+"/metadata.json")
    spec_list = []
    if spectra_folder is not None:
        specstr = dio.import_files_to_spectrumstream(spectra_folder)
        spec_list = specstr._get_frame_list()
        defSpectraFolder = parfolder+f"/deformedSpectra_{numbering}/"
        if not os.path.isdir(defSpectraFolder):
            os.makedirs(defSpectraFolder)
        images.metadata.to_file(defSpectraFolder+"/metadata.json")
    # loop over files
    firstframe = True
    for i in range(frames):
        if i in skipframes:
            continue
        c = str(i).zfill(counter)
        imname = str(Path(f"{parfolder}/{imfolder}/image_{c}.{imgext}"))
        image = images.data[i]
        logging.info(f"Processing frame {i}: {imname}")
        if firstframe:
            defX = loadFromQ2bz(str(Path(f"{result_folder}/stage{stage}/{i}/"
                                f"deformation_{bznumber}_0.dat.bz2")))
            defY = loadFromQ2bz(str(Path(f"{result_folder}/stage{stage}/{i}/"
                                f"deformation_{bznumber}_1.dat.bz2")))
            firstframe = False
        else:
            defX = loadFromQ2bz(str(Path(f"{result_folder}/stage{stage}/{i}-r/"
                                f"deformation_{bznumber}_0.dat.bz2")))
            defY = loadFromQ2bz(str(Path(f"{result_folder}/stage{stage}/{i}-r/"
                                f"deformation_{bznumber}_1.dat.bz2")))
        h, w = image.shape
        coords = \
            np.mgrid[0:h, 0:w] + np.multiply([defY, defX], (np.max([h, w])-1))
        deformedImage = ndimage.map_coordinates(image, coords, order=0,
                                                mode='constant',
                                                cval=image.mean())
        defimpath = str(Path(f"{defImagesFolder}/{dataBaseName}_{c}.{imgext}"))
        write_as_image(deformedImage, defimpath)
        logging.info(f"Wrote out the deformed image to {defimpath}")
        if spec_list:
            logging.info("Reading spectra ... ")
            spectra = spec_list[i]
            logging.info("done")
            spectradef = dio.SpectrumStream._reshape_sparse_matrix(
                                spectra, specstr.dimensions)
            logging.info("Applying the deformations")
            image_stack = hs.signals.Signal2D(spectradef)
            image_stack.axes_manager[1].name = "x"
            image_stack.axes_manager[2].name = "y"
            result = image_stack.map(
                        lambda x: ndimage.map_coordinates(
                            x, coords, order=0, mode="constant"),
                        inplace=False, parallel=True)
            result.unfold()
            defspec_sp = csr_matrix(result.data.T)  # sparse matrix rep
            save_npz(str(Path(
                f"{defSpectraFolder}/{dataBaseName}_{c}.npz")), defspec_sp)
            logging.info("Wrote out the deformed spectrum")
    # also do the post processing, with temmeta it's a minor thing
    resultFolder = str(Path(parfolder+f"/results_{numbering}/"))
    if not os.path.isdir(resultFolder):
        os.makedirs(resultFolder)
    # average image
    averageUndeformed = images.average()
    averageUndeformed.to_hspy(str(Path(resultFolder+"/imageUndeformed.hspy")))
    write_as_image(averageUndeformed.data,
                   str(Path(resultFolder+f"/imageUndeformed.{imgext}")))
    # average image from deformed
    averageDeformed = dio.import_files_to_stack(defImagesFolder)
    averageDeformed._create_child_stack(
        True, averageDeformed.data, averageDeformed.pixelsize,
        averageDeformed.pixelunit, averageDeformed,
        ("Performed non-rigid registration alignment with "
         f"config file {config_file}")
    )
    averageDeformed = averageDeformed.average()
    averageDeformed.to_hspy(str(Path(resultFolder+"/imageDeformed.hspy")))
    write_as_image(averageDeformed.data,
                   str(Path(resultFolder+f"/imageDeformed.{imgext}")))
    if spectra_folder is not None:
        # averaged spectrum
        spectrumUndeformed = specstr.spectrum_map
        spectrumUndeformed.to_hspy(str(Path(
            resultFolder+"/spectrumUndeformed.hspy")))
        # averaged spectrum deformed
        spectrumDeformed = dio.import_files_to_spectrumstream(defSpectraFolder)
        spectrumDeformed = spectrumDeformed.spectrum_map
        spectrumDeformed = spectrumDeformed._create_child_map(
            True, spectrumDeformed.data, spectrumDeformed.pixelsize,
            spectrumDeformed.dispersion, spectrumDeformed.spectrum_offset,
            ("Performed non-rigid registration alignment with "
                f"config file {config_file}")
        )
        return (averageUndeformed, averageDeformed,
                spectrumUndeformed, spectrumDeformed)
    else:
        return (averageUndeformed, averageDeformed,
                None, None)
