#! /usr/bin/env python

#this function is intended to be called by staka_vido
#it will slice an object into stackable layers for laser cutting

from rotate_stl import rotate_stl
from call_slic3r import call_slic3r


def stacker(inputs):
    #take the input file and rotate it according to
    #input.euler_angle
    rotate_stl(inputs)
    #pass the rotated STL to slic3r
    call_slic3r(inputs)
    #the result is an SVG file saved to inputs.outputfile
    
    
    
