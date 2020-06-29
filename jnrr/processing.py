import logging
import os
import subprocess
from PIL import Image
from scipy import ndimage
from pathlib import Path
from .io_tools import read_config_file, loadFromQ2bz, _getNameCounterFrames
import numpy as np
import hyperspy.api as hs
from scipy.sparse import csr_matrix
from temmeta import data_io as dio

logger = logging.Logger(name="Processing", level=logging.INFO)


def write_as_image(img, path):
    defimg = Image.fromarray(img)
    defimg.save(path)


def calculate_non_rigid_registration(config_file):
    cmd = [str("matchSeries"), f"{config_file}", ">", "output.log"]
    process1 = subprocess.Popen(cmd, stderr=subprocess.PIPE)
    process1.wait()
    logger.info("Finished non-rigid registration")
    return read_config_file(config_file)["saveDirectory"]


def apply_deformations_spectra():
    pass


def apply_deformations_images():
    pass


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
    spec_list = []
    if spectra_folder is not None:
        specstr = dio.import_files_to_spectrumstream(spectra_folder)
        spec_list = specstr._get_frame_list()
        defSpectraFolder = parfolder+f"/deformedSpectra_{numbering}/"
        if not os.path.isdir(defSpectraFolder):
            os.makedirs(defSpectraFolder)
    # loop over files
    im_frm_list = []
    spec_frm_list = []
    firstframe = True
    for i in range(frames):
        if i in skipframes:
            continue
        c = str(i).zfill(counter)
        imname = str(Path(
            f"{parfolder}/{imfolder}/{dataBaseName}_{c}.{imgext}"))
        image = images.get_frame(i)
        logger.info(f"Processing frame {i}: {imname}")
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
        w = image.width
        h = image.height
        coords = \
            np.mgrid[0:h, 0:w] + np.multiply([defY, defX], (np.max([h, w])-1))
        deformedData = ndimage.map_coordinates(image.data, coords, order=0,
                                               mode='constant',
                                               cval=image.data.mean())
        defImage = dio.create_new_image(deformedData, image.pixelsize,
                                        image.pixelunit, parent=image,
                                        process=("Applied non rigid "
                                                 "registration"))
        im_frm_list.append(defImage)
        if spec_list:
            logger.info("Correcting corresponding spectrum frame")
            spectra = spec_list[i]
            spectradef = dio.SpectrumStream._reshape_sparse_matrix(
                                spectra, specstr.dimensions)
            image_stack = hs.signals.Signal2D(spectradef)
            image_stack.axes_manager[1].name = "x"
            image_stack.axes_manager[2].name = "y"
            result = image_stack.map(
                        lambda x: ndimage.map_coordinates(
                            x, coords, order=0, mode="constant"),
                        inplace=False, parallel=True)
            result.unfold()
            defspec_sp = csr_matrix(result.data.T)  # sparse matrix rep
            spec_frm_list.append(defspec_sp)
    # also do the post processing, with temmeta it's a minor thing
    logger.info("Calculating average image (undeformed)")
    resultFolder = str(Path(parfolder+f"/results_{numbering}/"))
    if not os.path.isdir(resultFolder):
        os.makedirs(resultFolder)
    # average image
    averageUndeformed = images.average()
    averageUndeformed.to_hspy(str(Path(resultFolder+"/imageUndeformed.hspy")))
    write_as_image(averageUndeformed.data,
                   str(Path(resultFolder+f"/imageUndeformed.{imgext}")))
    # average image from deformed
    logger.info("Calculating average image (deformed)")
    defstack = dio.images_to_stack(im_frm_list)
    averageDeformed = defstack.average()
    averageDeformed.to_hspy(str(Path(resultFolder+"/imageDeformed.hspy")))
    write_as_image(averageDeformed.data,
                   str(Path(resultFolder+f"/imageDeformed.{imgext}")))
    # also write out frames to individual files
    defstack.export_frames(defImagesFolder, name=dataBaseName, counter=counter)
    if spectra_folder is not None:
        # averaged spectrum
        logger.info("Calculating average spectrum (undeformed)")
        spectrumUndeformed = specstr.spectrum_map
        spectrumUndeformed.to_hspy(str(Path(
            resultFolder+"/spectrumUndeformed.hspy")))
        # averaged spectrum deformed
        logger.info("Calculating average spectrum (deformed)")
        specstr_data = dio.SpectrumStream._stack_frames(spec_frm_list)
        specstr_def = dio.SpectrumStream(specstr_data,
                                         specstr.metadata)
        # edit the number of frames
        specstr_def.metadata.data_axes["frame"]["bins"] = len(spec_frm_list)
        specstr_def.export_streamframes(defSpectraFolder,
                                        pre=dataBaseName,
                                        counter=counter)
        spectrumDeformed = specstr_def.spectrum_map
        spectrumDeformed.to_hspy(str(Path(
                resultFolder+"/spectrumDeformed.hspy")))
        return (averageUndeformed, averageDeformed,
                spectrumUndeformed, spectrumDeformed)
    else:
        return (averageUndeformed, averageDeformed,
                None, None)
