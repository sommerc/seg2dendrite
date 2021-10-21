## seg2dendrite
Command line tool:

Trace dendrite and spine from ilastik segmentation and output .swc file for import into Imaris

#### Usage
```bash
usage: seg2dendrite.py [-h] [-ms MIN_SIZE] [-s SCALE]
                       ilastik_seg_h5 [ilastik_seg_h5 ...]

Extract skeletons from ilastik dendtite segmentation and export to .swc for
import in Imaris

positional arguments:
  ilastik_seg_h5

optional arguments:
  -h, --help            show this help message and exit
  -ms MIN_SIZE, --min_size MIN_SIZE
  -s SCALE, --scale SCALE
```
#### Requires
Python >3.6
* h5py
* skan
* numpy
* networkx
* skimage
