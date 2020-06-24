import logging
from pathlib import Path


def write_config_file(filename, pathpattern=" ", abspath=" ",
                      preclevel=8, num_frames=1, numoffset=0,
                      numstep=1, skipframes=[], presmooth=False,
                      saverefandtempl=False, numstag=2, normalize=True,
                      enhancefraction=0.15, mintozero=True, regularization=200,
                      regfactor=1, gditer=500, epsilon=1e-6, startleveloffset=2,
                      extralambda=0.1):
    """
    Wrapper function to create a standard config file

    Parameters
    ----------
    filename : str
        path to the config file
    pathpattern : str, optional
        string pattern for image files
    abspath : str, optional
        path to root folder where results will be stored
    preclevel : int, optional
        base2 power of the images
    num_frames : int, optional
        number of images to process
    numoffset : int, optional
        index of first image to process
    numstep : int, optional
        to skip frames at regular interval
    skipframes : list, optional
        to kick out certain frames
    presmooth : bool, optional
        to smooth images before usage
    saverefandtempl : bool, optional
        save both the reference and the template
    numstage : int, optional
        number of stages
    normalize : bool, optional
        normalize the images
    enhancefraction : float, optional
        brightness/contrast adjustment
    mintozero : bool, optional
        minimum intensity mapped to 0
    regularization : int, optional
        regularization factor used in optimization level 1
    regfactor : float, optional
        adjustment of reg parameter with different binnings
    gditer : int, optional
        max number of iterations
    epsilon : float, optional
        desired precision
    startleveloffset : int, optional
        offset of the start level
    extralambda : int, optional
        adjustment of regularization with subsequent steps
    """
    savedir = str(Path(f"{abspath}/nonrigid_results/"))
    if normalize:
        normalize=0
    else:
        normalize=1
    cnfgtmpl = (f"templateNamePattern {pathpattern}\n"
                f"templateNumOffset {numoffset}\n"
                f"templateNumStep {numstep}\n"
                f"numTemplates {num_frames}\n"
                f"templateSkipNums {{ {skipframes} }}\n"
                "\n"
                f"preSmoothSigma {presmooth*1}\n"
                "\n"
                f"saveRefAndTempl {saverefandtempl*1}\n"
                "\n"
                f"numExtraStages {numstag}\n"
                "\n"
                f"saveDirectory {savedir}\n"
                "\n"
                f"dontNormalizeInputImages {normalize*1}\n"
                f"enhanceContrastSaturationPercentage {enhancefraction}\n"
                f"normalizeMinToZero {mintozero*1}\n"
                "\n"
                f"# lambda weights the deformation regularization term\n"
                f"lambda {regularization}\n"
                "# lambdaFactor scales lambda dependening on the current level"
                ": On level d, lambda is multiplied by pow ( lambdaFactor, "
                "stopLevel - d )\n"
                f"lambdaFactor {lambdafactor}\n"
                f"\n"
                f"maxGDIterations {gditer}\n"
                f"stopEpsilon {epsilon}\n"
                f"\n"
                f"startLevel {preclevel-startleveloffset}\n"
                f"stopLevel {preclevel}\n"
                f"precisionLevel {preclevel}\n"
                f"refineStartLevel {preclevel-1}\n"
                f"refineStopLevel {preclevel}\n"
                f"\n"
                f"checkboxWidth {preclevel}\n"
                f"\n"
                f"resizeInput 0\n"
                f"\n"
                f"dontAccumulateDeformation 0\n"
                f"reuseStage1Results 1\n"
                f"extraStagesLambdaFactor {extralambda}\n"
                f"useMedianAsNewTarget 1\n"
                f"calcInverseDeformation 0\n"
                f"skipStage1 0\n"
                f"\n"
                f"saveNamedDeformedTemplates 1\n"
                f"saveNamedDeformedTemplatesUsing"
                f"NearestNeighborInterpolation 1\n"
                f"saveNamedDeformedTemplatesExtendedWithMean 1\n"
                f"saveDeformedTemplates 1\n"
                f"saveNamedDeformedDMXTemplatesAsDMX 1")
    with open(filename, "w") as file:
        file.write(cnfg)

    logging.debug("Wrote the config file with an initial parameter guess")
