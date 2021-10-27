## seg2dendrite


### 1. Convert .ims to .h5 for pixel classification in ilastik
Use the ImageJ macro `ims2h5.ijm` to convert .ims files to ilastik .h5 files.
Choose a folder with .ims files and a resolution level (default 2; down scaling by factor of 2).

### 2. Use ilastik pixel classificaiton
Use `Pixel Classification` workflow.
* Choose dendrite class as first class in training (yellow color)
* Make sure probability maps are exported as uint8 and renormalized to 0-255

### 3. Convert probability maps to dendrite objects and save as .swc for import in Imaris
Command line tool:

Trace dendrite and spine from ilastik dendrite probability maps and output .swc file for import into Imaris

```
usage: ilastik2dendrite.py [-h] [-ms MIN_SIZE] [-rl RESOLUTION_LEVEL]
                           [-s SMOOTH_SIGMA SMOOTH_SIGMA SMOOTH_SIGMA]
                           [-t THRESHOLD]
                           ilastik_h5 [ilastik_h5 ...]

Extract skeletons from ilastik dendrite probability maps and export to .swc
for import in Imaris

positional arguments:
  ilastik_h5            ilastik probability map (single channel) in 8-bit

optional arguments:
  -h, --help            show this help message and exit
  -ms MIN_SIZE, --min_size MIN_SIZE
                        Minimum object size in pixel
  -rl RESOLUTION_LEVEL, --resolution_level RESOLUTION_LEVEL
                        Resolution level used
  -s SMOOTH_SIGMA SMOOTH_SIGMA SMOOTH_SIGMA, --smooth_sigma SMOOTH_SIGMA SMOOTH_SIGMA SMOOTH_SIGMA
                        Smooth prob. map before thresholding. Gaussian sigma
                        in px for ZYX
  -t THRESHOLD, --threshold THRESHOLD
                        Probability map threshold
```

#### Example:
After pixel classification with ilastik on resolution level 2, which created a probability map volume_Probabilities.h5, use

```
python ilastik2dendrite.py volume_Probabilities.h5 --smooth 0.5 1 1 --threshold 0.5 -min_sizes 12000 --resolution_level 2
```

it will smooth the probability map with sigma ZYX of 0.5 x 1 x 1 and threshold at probability 0.5, filter dendrite objects for minimum size of 12000.

### ilastik2dendrite.py requires pip installable packages:
Python >3.6
* h5py
* skan
* numpy
* networkx
* skimage
