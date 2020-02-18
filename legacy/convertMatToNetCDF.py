#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import numpy as np
import scipy.io as sio
from msiplib.io import saveArrayAsNetCDF

if __name__ == '__main__':
    for filename in os.listdir("."):
        if filename.endswith(".mat"):
            print('Converting {}'.format(os.path.join(".", filename)))

            # Read data
            input_data = sio.loadmat(filename)
            for key in input_data.keys():
                if isinstance(input_data[key], np.ndarray):
                    print('Exporting', key)
                    image_array = input_data[key]
                    num_frames = image_array.shape[2]
                    basename = os.path.splitext(filename)[0].replace(' ', '_')
                    for i in range(num_frames):
                        saveArrayAsNetCDF(image_array[:, :, i], "{}_{}_{:03d}.nc".format(basename, key, i))
