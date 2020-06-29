# Non-rigid-registration on Velox-EMD datasets
## About
This repo is a collection of scripts, modules and examples with which the
image and spectroscopy data inside Velox-EMD files can be corrected for
non-linear distortions which result from scan artifacts. It aims to make
the process of using the [match-series](https://github.com/berkels/match-series) code more accessible and useable
in a python/jupyter notebook environment. To see how it works, check out
the example:

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/din14970/NRR-emd/master)

## Useage
If you want to use this on your own computer, download the source
code to somewhere on your system. **These instructions only apply to a Linux system
and presumes you have conda/miniconda installed**

```
$ cd <folder/where/you/want/to/save/this/repo>
$ git clone https://github.com/din14970/NRR-emd
```

Create a conda virtual environment. Probably it is easiest to create it
in this folder

```
$ conda create --prefix ./.venv pip
$ conda activate ./.venv
```

Install match-series in the virtual environment.

```
$ conda install -c conda-forge match-series
```

Install [temmeta](https://github.com/din14970/TEMMETA) in the virtual environment.

```
$ pip install temmeta
```

Open the example by starting jupyter notebook

```
$ jupyter notebook
```

At the moment there is no easy conda or pip install for this tool as it may be
integrated into some other tool at some point.

## Notes

* everything in the `scripts` folder is legacy and will no longer function