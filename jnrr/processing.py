import logging
import os
import subprocess
import imageio
from pathlib import Path
from .io_tools import read_config_file, loadFromQ2bz, _getNameCounterFrames


def calculate_non_rigid_registration(config_file):
    cmd = [str("matchSeries"), f"{config_file}", ">", "output.log"]
    process1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    process1.wait()
    logging.info("Finished non-rigid registration")


def apply_deformations(result_folder, image_folder, spectra_folder=None):
    # # get the path to the image files
    # conf = read_config_file(config_file)
    # if image_folder is None:
    #     imfolder, _ = os.path.split(conf["templateNamePattern"])
    # else:
    #     imfolder = image_folder
    # # get basic info about the images
    # (dataBaseName, counter, imgext, frames, skipframes, bznumber,
    #     stage) = _getNameCounterFrames(config_file)
    # # get the matching number
    # _, index = config_file.split("_")
    # if spectra_folder is None:
    #     # check whether there is a first spectrum folder
    #     rootfolder, _ = os.path.split(imfolder)
    #     spectra_folder = str(Path(rootfolder+"/spectra_000"))
    #     if not os.path.isdir(spectra_folder):
    #         spectra_folder = None

    imfiles = os.listdir(image_folder)
    for i in imfiles:
        if os.path.splitext(i)[-1]=="json":
            continue
        logging.info("Processing frame {}".format(i))
        image = imageio.imread(str(Path(image_folder+f"/{i}")))
        #first frame is a bit of an exception
        if firstframe:
            defX = loadFromQ2bz("{}{}/deformation_{}_0.dat.bz2".format(defFolder, i, bznumber))
            defY = loadFromQ2bz("{}{}/deformation_{}_1.dat.bz2".format(defFolder, i, bznumber))
            firstframe = False
        else:
            defX = loadFromQ2bz("{}{}-r/deformation_{}_0.dat.bz2".format(defFolder, i, bznumber))
            defY = loadFromQ2bz("{}{}-r/deformation_{}_1.dat.bz2".format(defFolder, i, bznumber))

        coords = \
            np.mgrid[0:h, 0:w] + np.multiply([defY, defX], (np.max([h, w])-1))
        deformedImage = ndimage.map_coordinates(image, coords, order=0, mode='constant', cval=image.mean())
        #order is the order of the spline interpolation
        #mode constant means everything outside the range is assumed a constant value
        #cval is the constant value, we take it as the mean
        write_as_png(deformedImage, f"{defImagesFolder}{dataBaseName}_{c}.{imgext}")
        logging.info(f"Wrote out the deformed image to {imgext}")
        #saveArrayAsNetCDF(deformedImage, "{}{:02d}.nc".format(dataBaseName, i))

        if there_is_edx:
            logging.info("Reading spectra ... ")
            #spectra = hs.load("{}{}.hspy".format(dataFolder, i))
            spectra = load_npz(f"{specfolder}{dataBaseName}_{c}.npz")
            logging.info("done")
            #for the 3D coordinates, the channel remains unchanged, we add a third axis with channels

            #print(numChannels, type(numChannels))
            # d3dcoords = \
            #     np.mgrid[0:numChannels, 0:h, 0:w]\
            #     + np.multiply([np.tile(np.zeros([h, w]), (numChannels, 1, 1)),\
            #                     np.tile(defY, (numChannels, 1, 1)),\
            #                     np.tile(defX, (numChannels, 1, 1))], (np.max([h, w])-1))
            spectradef = spectra.T.toarray().reshape(numChannels, h, w) #unravel, make full 3D array
            #we have to loop, 3D coordinate transformation doesn't fit in memory
            logging.info("Applying the deformations")
            image_stack = hs.signals.Signal2D(spectradef)
            image_stack.axes_manager[1].name = "x"
            image_stack.axes_manager[2].name = "y"
            result = image_stack.map(lambda x: ndimage.map_coordinates(x, coords, order=0, mode = "constant"),
                        inplace = False, parallel = True)
            # for j in tqdm(range(numChannels)):
            #     slice = spectradef[j, :, :]
            #     defslice = ndimage.map_coordinates(slice, coords, order=0, mode='constant')
            #     spectradef[j, :, :] = defslice
            result.unfold()
            defspec_sp = csr_matrix(result.data.T) #sparse matrix rep
            save_npz(f"{defSpectraFolder}{dataBaseName}_{c}.npz", defspec_sp)
            logging.info("Wrote out the deformed spectrum")
            #saveArrayAsNetCDF(spectra.data, "EDX_{:02d}.nc".format(i), optimizeDataType=True) 