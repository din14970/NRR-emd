#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#import hyperspy.api as hs
from PIL import Image
import logging
import argparse
import sys
import re

from tqdm import tqdm #adds a progress bar
import numpy as np
from scipy import ndimage
import imageio
import os
import netCDF4 as nc4
import bz2

import hyperspy.api as hs

logging.basicConfig(level=logging.INFO)

from scipy.sparse import load_npz, save_npz, csr_matrix


def loadFromQ2bz(path):
    filename, file_extension = os.path.splitext(path)
    #bz2 compresses only a single file
    if(file_extension == '.q2bz' or file_extension == '.bz2'):
        fid = bz2.open(path, 'rb') #read binary mode, r+b would be to also write
    else:
        fid = open(path, 'rb') #read binary mode, r+b would be to also write
    # Read magic number - only possible when bz2.open is called! Will not see it in hex fiend!
    # rstrip removes trailing zeros
    binaryline = fid.readline() #will look like "b"P9\n""
    line = binaryline.rstrip().decode('ascii') #this will look like "P9"
    if(line[0] != 'P'):
        raise ValueError("Invalid array header, doesn't start with 'P'")
    if(line[1] == '9'):
        dtype = np.float64
    elif(line[1] == '8'):
        dtype = np.float32
    else:
        dtype = None

    if not dtype:
        raise NotImplementedError("Invalid data type ({}), only float and double are supported currently".format(line[1]))
    header = fid.readline().rstrip()  # Skip header = b'# This is a QuOcMesh file of type 9 (=RAW DOUBLE) written 17:36 on Friday, 07 February 2020'

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


def saveArrayAsNetCDF(data, filename, optimizeDataType: bool = False):
    # If the input data type is non-integer, check whether the
    # actual data is integer. If so, save as integer.
    if(optimizeDataType and (not np.issubdtype(data.dtype, np.integer)) and (np.all(np.mod(data, 1) == 0))):
        dataMin = np.amin(data)
        dataMax = np.amax(data)
        if(dataMin >= 0):
            if(dataMax <= np.iinfo(np.uint8).max):
                data = data.astype(np.uint8)
            elif(dataMax <= np.iinfo(np.uint16).max):
                data = data.astype(np.uint16)
            elif(dataMax <= np.iinfo(np.uint32).max):
                data = data.astype(np.uint32)
            elif(dataMax <= np.iinfo(np.uint64).max):
                data = data.astype(np.uint64)
        else:
            if((dataMin >= np.iinfo(np.int8).min) and (dataMax <= np.iinfo(np.int8).max)):
                data = data.astype(np.int8)
            elif((dataMin >= np.iinfo(np.int16).min) and (dataMax <= np.iinfo(np.int16).max)):
                data = data.astype(np.int16)
            elif((dataMin >= np.iinfo(np.int32).min) and (dataMax <= np.iinfo(np.int32).max)):
                data = data.astype(np.int32)
            elif((dataMin >= np.iinfo(np.int64).min) and (dataMax <= np.iinfo(np.int64).max)):
                data = data.astype(np.int64)
        print("Converted data type to {} before saving.".format(data.dtype))

    if (data.dtype == np.float64):
        dataType = 'd'
    elif (data.dtype == np.float32):
        dataType = 'f4'
    elif (data.dtype == np.int64):
        dataType = 'i8'
    elif (data.dtype == np.int32):
        dataType = 'i4'
    elif (data.dtype == np.int16):
        dataType = 'i2'
    elif (data.dtype == np.int8):
        dataType = 'i1'
    elif (data.dtype == np.uint16):
        dataType = 'u2'
    elif (data.dtype == np.uint8):
        dataType = 'u1'
    else:
        warnings.warn("Data type {} not explicitly handled, saving as double.".format(data.dtype))
        dataType = 'd'
    a = nc4.Dataset(filename, 'w', format='NETCDF4')
    if (data.ndim == 1):
        a.createDimension('x', data.shape[0])
        temp = a.createVariable('data', dataType, ('x'), zlib=True, complevel=5)
    elif (data.ndim == 2):
        a.createDimension('x', data.shape[0])
        a.createDimension('y', data.shape[1])
        temp = a.createVariable('data', dataType, ('x', 'y'),
                                zlib=True, complevel=5)
    elif (data.ndim == 3):
        a.createDimension('x', data.shape[0])
        a.createDimension('y', data.shape[1])
        a.createDimension('z', data.shape[2])
        temp = a.createVariable(
            'data', dataType, ('x', 'y', 'z'), zlib=True, complevel=5)
    else:
        raise NotImplementedError("Unsupported dimension")
    temp[:] = data
    a.history = 'Created ' + time.ctime(time.time())
    a.args = sys.argv
    a.close()


def readArrayFromNetCDF(filename):
    a = nc4.Dataset(filename, 'r')
    return a['data'][:]


def getNameCounterFrames(path):
    """Returns the base name (bn), the number of counting digits, the number of frames,
    and an array of skipped frames. This information is read from the .par config file.

    Args:
        path (str): the path to the config file

    Returns:
        tuple of (base name, number of counter digits, number of frames, skipped frames)
    """
    with open(path) as f:
        text = f.read()

    basename, counter, ext = re.findall(r"\/([^\/]+)_%0(.+)d\.([A-Za-z0-9]+)", text)[0]
    counter = int(counter)
    numframes = int(re.findall(r"numTemplates ([0-9]+)", text)[0])
    skipframes_line = re.findall(r"templateSkipNums (.*)", text)[0]
    skipframes = re.findall(r"([0-9]+)[^0-9]", skipframes_line)
    skipframes = list(map(int, skipframes))
    bznumber = re.findall(r"stopLevel +([0-9]+)", text)[0].zfill(2)
    stages = int(re.findall(r"numExtraStages +([0-9]+)", text)[0])+1

    return (basename, counter, ext, numframes, skipframes, bznumber, stages)


def write_as_png(img, path):
    defimg = Image.fromarray(img)
    defimg.save(path)


def apply_deformations(folder: str):

    #reading the config file for the parameters that were used in the NRR
    try:
        configfile = ""
        logging.info("Looking for config file to extract NRR parameters.")
        for file in os.listdir(folder):
            if file.endswith(".par"):
                configfile = os.path.join(folder, file)
                break
        else:
            logging.error("No valid config file found in this location; can't process images.")
            return
        logging.info("Found config file {}. Reading the parameters...".format(configfile))
        dataBaseName, counter, imgext, frames, skipframes, bznumber, stage = getNameCounterFrames(configfile)
        logging.info("Succesfully read parameters")
    except:
        raise ValueError("Something went wrong reading the parameters from the config file")

    #reading the metadata
    meta = dio.read_meta_json(f"{folder}/metadata.json")
    there_is_edx = True
    try:
        meta["EDX"]
    except:
        there_is_edx = False

    imgfolder = folder+"/images/"
    defFolder = folder+"/nonrigid_results/stage{}/".format(stage)

    #set the path to the deformed images folder
    defImagesFolder = folder+"/deformedImages/"
    if not os.path.isdir(defImagesFolder):
        os.makedirs(defImagesFolder)

    #some values commonly used in the loop
    h=meta["Scan"]["Height"]["Pixels"]
    w=meta["Scan"]["Width"]["Pixels"]

    #set the path to the deformed spectra folder
    if there_is_edx:
        specfolder = folder+"/spectra/"
        defSpectraFolder = folder+"/deformedSpectra/"
        if not os.path.isdir(defSpectraFolder):
            os.makedirs(defSpectraFolder)
        numChannels = meta["EDX"]["Channels"]

    firstframe = True
    for i in range(frames):
        if not i in skipframes:
            logging.info("Processing frame {}".format(i))
            #image = readArrayFromNetCDF("{}{}{:02d}.nc".format(dataFolder, dataBaseName, i))
            c = str(i).zfill(counter)
            image = imageio.imread("{}{}_{}.{}".format(imgfolder, dataBaseName, c, imgext))
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder",
                        help = "root folder containing the metadata, config, images and spectra")
    args = parser.parse_args()
    apply_deformations(args.folder)


if __name__ == '__main__':
    #snippet to be able to add the absolute parent folder path of the script on the path
    from pathlib import Path

    ownpath = os.path.abspath(__file__)
    folder, file = os.path.split(ownpath)
    folder = Path(folder)

    sys.path.append(str(folder.parent))

    from TEMMETA.basictools import data_io as dio
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    main()
