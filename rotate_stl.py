#! /usr/bin/env python

#this script will take an STL file
#and rotate it about a given euler angle
#the euler angle will be a z-x-z extrinsic rotation
#input is expected in degrees

from stl import mesh
import math

def rotate_stl(inputs):
    centered_mesh = mesh.Mesh.from_file(inputs.inputfile)
    #rotate around euler angle
    #z-x-z extrinsic rotation
    centered_mesh.rotate([0.0,0.0,1.0],math.radians(inputs.euler_angle[0]))
    centered_mesh.rotate([1.0,0.0,0.0],math.radians(inputs.euler_angle[1]))
    centered_mesh.rotate([0.0,0.0,1.0],math.radians(inputs.euler_angle[2]))
    centered_mesh.save(inputs.inputfile)
    
