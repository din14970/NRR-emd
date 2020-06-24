import logging
from pathlib import Path
from pyiron.base.job.template import TemplateJob




def write_config_file(filename, pathpattern=" ", abspath=" ",
                      preclevel=8, num_frames=1):
    savedir = str(Path(f"{abspath}/nonrigid_results/"))
    cnfgtmpl = ("templateNamePattern {}\n"
                "templateNumOffset 0\n"
                "templateNumStep 1\n"
                "numTemplates {}\n"
                "#templateSkipNums {{ }}\n"
                "\n"
                "cropInput 0\n"
                "cropStartX 0\n"
                "cropStartY 0\n"
                "dontResizeOrCropReference 0\n"
                "\n"
                "preSmoothSigma 0\n"
                "\n"
                "saveRefAndTempl 0\n"
                "\n"
                "numExtraStages 2\n"
                "\n"
                "saveDirectory {}\n"
                "\n"
                "dontNormalizeInputImages 0\n"
                "enhanceContrastSaturationPercentage 0.15\n"
                "normalizeMinToZero 1\n"
                "\n"
                "# lambda weights the deformation regularization term\n"
                "lambda         200\n"
                "# lambdaFactor scales lambda dependening on the current level"
                ": On level d, lambda is multiplied by pow ( lambdaFactor, "
                "stopLevel - d )\n"
                "lambdaFactor   1\n"
                "\n"
                "maxGDIterations 500\n"
                "stopEpsilon 1e-6\n"
                "\n"
                "startLevel {}\n"
                "stopLevel {}\n"
                "precisionLevel {}\n"
                "refineStartLevel {}\n"
                "refineStopLevel {}\n"
                "\n"
                "checkboxWidth {}\n"
                "\n"
                "resizeInput 0\n"
                "\n"
                "dontAccumulateDeformation 0\n"
                "reuseStage1Results 1\n"
                "extraStagesLambdaFactor 0.1\n"
                "useMedianAsNewTarget 1\n"
                "calcInverseDeformation 0\n"
                "skipStage1 0\n"
                "\n"
                "saveNamedDeformedTemplates 1\n"
                "saveNamedDeformedTemplatesUsing"
                "NearestNeighborInterpolation 1\n"
                "saveNamedDeformedTemplatesExtendedWithMean 1\n"
                "saveDeformedTemplates 1\n"
                "saveNamedDeformedDMXTemplatesAsDMX 1")
    cnfg = cnfgtmpl.format(pathpattern, num_frames, savedir, preclevel-2,
                           preclevel, preclevel, preclevel-1, preclevel,
                           preclevel)
    with open(filename, "w") as file:
        file.write(cnfg)

    logging.debug("Wrote the config file with an initial parameter guess")