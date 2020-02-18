#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hyperspy.api as hs
from tqdm import tqdm
import numpy as np
from scipy import ndimage
import os
import netCDF4 as nc4
import bz2


def loadFromQ2bz(path):
    filename, file_extension = os.path.splitext(path)

    if(file_extension == '.q2bz' or file_extension == '.bz2'):
        fid = bz2.open(path, 'rb')
    else:
        fid = open(path, 'rb')
    # Read magic number
    line = fid.readline().rstrip().decode('ascii')
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
    fid.readline().rstrip()  # Skip header

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


if __name__ == '__main__':
    dataFolder = os.environ['QUOC_DATA_DIR'] + "/emic/data/MacArthur/Ni-Zr_EDX/"
    defFolder = os.environ['QUOC_OUTPUT_DIR'] + "/results-Ni-Zr_EDX/stage3/"
    dataBaseName = "ADF_image_"
    for i in range(80):
        print("Processing frame {}".format(i))
        image = readArrayFromNetCDF("{}{}{:02d}.nc".format(dataFolder, dataBaseName, i))
        defX = loadFromQ2bz("{}{}{:02d}_def_0.dat.bz2".format(defFolder, dataBaseName, i))
        defY = loadFromQ2bz("{}{}{:02d}_def_1.dat.bz2".format(defFolder, dataBaseName, i))
        coords = \
            np.mgrid[0:image.shape[0], 0:image.shape[1]] + np.multiply([defY, defX], (np.max(image.shape)-1))
        deformedImage = ndimage.map_coordinates(image, coords, order=0, mode='constant', cval=image.mean())
        saveArrayAsNetCDF(deformedImage, "{}{:02d}.nc".format(dataBaseName, i))
        print("Reading spectra ... ", end='', flush=True)
        spectra = hs.load("{}{}.hspy".format(dataFolder, i))
        print("done")
        numChannels = spectra.data.shape[2]
        pbar = tqdm(range(numChannels))
        for chan in pbar:
            spectra.data[:, :, chan] = ndimage.map_coordinates(
                spectra.data[:, :, chan], coords, order=0, mode='constant')
        saveArrayAsNetCDF(spectra.data, "EDX_{:02d}.nc".format(i), optimizeDataType=True)
