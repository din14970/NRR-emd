import logging
import os
import subprocess
import imageio
from PIL import Image
from scipy import ndimage
from pathlib import Path
from .io_tools import read_config_file, loadFromQ2bz, _getNameCounterFrames
import numpy as np
from scipy.sparse import load_npz, save_npz, csr_matrix
import hyperspy.api as hs


def write_as_png(img, path):
    defimg = Image.fromarray(img)
    defimg.save(path)


def calculate_non_rigid_registration(config_file):
    cmd = [str("matchSeries"), f"{config_file}", ">", "output.log"]
    process1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    process1.wait()
    logging.info("Finished non-rigid registration")


def apply_deformations(result_folder, image_folder=None,
                       spectra_folder=None):
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
    #set the path to the deformed images folder
    defImagesFolder = parfolder+f"/deformedImages_{numbering}/"
    if not os.path.isdir(defImagesFolder):
        os.makedirs(defImagesFolder)
    # read in the data
    images = dio.import_files_to_stack(imfolder)
    if spectra_folder is not None:
        spectra = dio.import_files_to_spectrumstream(spectra_folder)
    # loop over files
    for i in range(frames):
        c = str(i).zfill(counter)
        imname = str(Path(f"{parfolder}/{imfolder}/image_{c}.{imgext}"))
        image = images.data[0]
        logging.info(f"Processing frame {i}: {imname}")
        #first frame is a bit of an exception
        if firstframe:
            defX = loadFromQ2bz(f"{result_folder}/stage{stage}/{i}/deformation_{bznumber}_0.dat.bz2")
            defY = loadFromQ2bz(f"{result_folder}/stage{stage}/{i}/deformation_{bznumber}_1.dat.bz2")
            firstframe = False
        else:
            defX = loadFromQ2bz(f"{result_folder}/stage{stage}/{i}_r/deformation_{bznumber}_0.dat.bz2")
            defY = loadFromQ2bz(f"{result_folder}/stage{stage}/{i}_r/deformation_{bznumber}_1.dat.bz2")
        h, w = image.shape
        coords = \
            np.mgrid[0:h, 0:w] + np.multiply([defY, defX], (np.max([h, w])-1))
        deformedImage = ndimage.map_coordinates(image, coords, order=0, mode='constant', cval=image.mean())
        # order is the order of the spline interpolation
        # mode constant means everything outside the range is assumed a constant value
        # cval is the constant value, we take it as the mean
        defimpath = f"{defImagesFolder}/{dataBaseName}_{c}.{imgext}")
        write_as_png(deformedImage, defimpath)
        logging.info(f"Wrote out the deformed image to {defimpath}")
        if spectra_folder is not None:
            logging.info("Reading spectra ... ")
            spectra = load_npz(f"{spectra_folder}/{dataBaseName}_{c}.npz")
            logging.info("done")
            spectradef = spectra.T.toarray().reshape(numChannels, h, w)
            logging.info("Applying the deformations")
            image_stack = hs.signals.Signal2D(spectradef)
            image_stack.axes_manager[1].name = "x"
            image_stack.axes_manager[2].name = "y"
            result = image_stack.map(lambda x: ndimage.map_coordinates(x, coords, order=0, mode = "constant"),
                        inplace = False, parallel = True)
            result.unfold()
            defspec_sp = csr_matrix(result.data.T) #sparse matrix rep
            save_npz(f"{defSpectraFolder}{dataBaseName}_{c}.npz", defspec_sp)
            logging.info("Wrote out the deformed spectrum")
