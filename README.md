# How to perform non-rigid registration on STEM-EDX datasets with the velox emd file format

## Download and compile the non-rigid registration software
Download and compile the match-series source code according to [the github page](https://github.com/berkels/match-series). Put the match series folder in this folder. Do not rename, paths are hard-coded!

## Extract the images and spectra from the EMD file
From the root folder `191205NonRigid` run
```
python3 ./scripts/extract_images.py "<absolute path to EMD file>"
```
Optional arguments are:
```
-o, --output [path to where all output should be stored. Defaults to current working directory.]
-n, --filename [name prefix the output files should have. Defaults to the name of the EMD file.]
-d, --detector [the index that corresponds to the dataset that contains the image frames [0-?]. The script will try to find this automatically but it may fail if multiple datasets are included with multiple frames in the same EMD file. You can visualise the emd structure with the get_emd_tree_view in TEMMETA/basictools/data_io.py or with a tool like HDFView. Script fails if the index is out of range.]
-s, --spectrumdetector [same as -d except for the SpectrumStream data. Defaults to 0, assuming only one dataset per emd file. Script fails if the index is out of range.]
-p, --padding [the frames will be exported with the filename_%0x.tiff pattern. p determines the number of counter digits. By default the minimum number of digits is calculated based on the number of frames. If p is less than the minimum number of digits required the script will fail.]
-m, --minimum [Minimum intensity to use for linear scaling]
-M, --maximum [Maximum intensity to use for linear scaling]
```
If the EMD file is well behaved and the image intensities are fine, typically you will want to run the command like this:
```
python3 ./scripts/extract_images.py "<absolute path to EMD file>" -o "<absolute path to output directory>" -n "name to give files. No spaces!"
```
If you want to adjust the brightness and contrast of the output images, you must use the `-m` and `-M` flags and provide an integer after each.

This script also creates a best guess config file: in and output paths are defaulted based on the `-o` flag and levels are calculated based on the recommendations on the github page (see below).

> ## Editing the config file
> An example config file is created by the previous script. It is based on the example found in `quocmesh/projects/electronMicroscopy/matchSeries.par`.
>
> 1. change `templateNamePattern` to the right path to the images. Make sure the end of the filename has the right counter pattern e.g. `%04d` meaning 4 counter digits.
> ```
> templateNumOffset 0     #the starting frame
> templateNumStep 1       #the step in the counter
> numTemplates 3          #how many total frames
> #templateSkipNums { 1 9 10 173 } #if some frames need to be discarded, uncomment and edit
> ```
>
> 2. (Optional) change the output path
> ```
> saveDirectory results/
> ```
>
> 3. Set the levels. This is the exponent `n` of the `pxp` size of the images, i.e. `2^n = p`. For `p=256` `n=8`, for `p=512` `n=9`, for `p=1024` `n=10`, etc.
> ```
> startLevel 6        #1 or 2 levels less than stoplevel. Must be so that you still see atoms if the images were binned to this level.
> stopLevel 8         #usually =precisionlevel
> precisionLevel 8    #The resolution of output. Must be same as input!
> refineStartLevel 7  #usually =precisionlevel
> refineStopLevel 8   #usually =precisionlevel
> ```

## Run non-rigid registration on the images
Run the python script `apply_nonrigid.py`. From the root directory this would look like:
```
python3 ./scripts/extract_images.py <path to config file>
```

This will actually run three independent scripts/programs:

1. Non-rigid registration

In the folder `match-series/quocGCC/projects/electronMicroscopy` you will find the executable `matchSeries`. Run this executable with the command. If you are currently in the folder, `<path>` is `.`. Executing `matchSeries` on 90 images took 5 hours 20 min on a 2015 Macbook pro with 2.5 GHz Intel I7 processor running Mac OS X Mojave.
```
<path>/matchSeries <path to config file>
```

2. Applying the deformation fields to the images and spectra with `scripts/apply_deformations.py`. From root:
```
python3 ./scripts/apply_deformations.py <path to folder containing config file>
```

3. Calculate the averaged images and total spectra before and after NRR using `script/process_results.py`. From root:
```
python3 ./scripts/process_results.py <path to folder containing config file>
```

If you don't need to run all of these, you can run each independently with the given command.
