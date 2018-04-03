#Staka Vido

This software is written to take an STL file and cut it into layers.
The code will cut the object into layers, and output the information as as SVG or SCAD file.

There are two main modes of operation.  The first mode will cut the STL file into layers that are intended to stacked directly on top of each other.

The second operation will cut the object into pieces at right angles that are intended to interlock to support each other.  (currently not implemented)

The software is written in Python and uses the shapely library:
  https://pypi.python.org/pypi/Shapely

It also requires the numpy-stl library:
  https://pypi.python.org/pypi/numpy-stl

The software to generate G-code for Goldfinger is found at:
  https://github.com/KnoxMakers/KM-Laser

Current Usage:

staka_vido.py
   -i, --ifile input STL file
   -o, --ofile output SVG file
   -t specify the thickness the material in mm
   --t1 if using two materials for opposite directions, specify the thickness of the first material
   --t2 if using two materials for opposite directions, specify the thickness of the second material
   -r specify the euler angle rotation z-x-z (extrinsic) used for stacking
   --r1 specify the first euler angle rotation for crossed cut assembly
   --r2 specify the second euler angle rotation for crossed cut assembly
   --s1 specify the spacing between the centers of the cuts for the first axis
   --s2 specify the spacing between the centers of the cuts for the second axis
   --n1 specify the number of layers for the first axis
   --n2 specify the number of layers for the second axis
   --add-traces this option adds traces to layers
   --verbose this option will enable additional output text
