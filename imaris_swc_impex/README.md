# Imaris XT for Import/Export SWC
This is Python XTensions for importing/exporting SWC files into/from Imaris

by Sarun Gulyanon, 28 July 2018
(adapted by Christoph Sommer 31 January 2022)

## Installation ##
  - Install [Python Anaconda](https://www.anaconda.com/download/) (tested on Anaconda 5.2)
  - Open "Anaconda prompt" from windows Start menu
  - Create new python environment by typing and execute command: `conda create -n imaris_XT_py27 python=2.7 numpy -y`
  - Activate that environment by: `conda activate imaris_XT_py27`
  - Retrieve full path of environment's python executable: `where python` and copy displayed path to clip-board (used later)
  - Put `importswc.py` and `exportswc.py` in Python XTensions folder, e.g., `C:\Program Files\Bitplane\Imaris x64 9.2.0\XT\python`
  - Link Python to Imaris by select Files > Preferences.. > CustomTools, and browse the Python 2.7 Application, e.g., `<folder>/Anaconda2/python.exe` <-- (copy from clip-board)
  - Link the Python XTensions folder by select Files > Preferences.. > CustomTools, and add the XTensions Folders, e.g., `C:\Program Files\Bitplane\Imaris x64 9.2.0\XT\python\`

## How to Use ##
To import SWC,
  1. First, open the image volume.
  2. Go to Image Processing > Import SWC as Filament
  3. Select the SWC file using the dialog.

To export SWC,
  1. First, open the image volume with Filament.
  2. Second, select the Filament you want to export.
  3. Go to Image Processing > Export Filament as SWC
  4. Select the save location using the dialog.

#### Requirements ####
  - Numpy
  - ImarisLib (given in Python XTensions folder)

#### Note ####
  - [Tutorial for making Imaris XT](http://www.scs2.net/next/files/courses/iic/ImarisXTCourse.pdf)
  - [pIceImarisConnector](http://www.scs2.net/next/index.php?id=110) for testing the code.