#! /usr/bin/env python

#this script will define the functions regarding processing STL files

from stl import mesh
import math

def rotate_stl(inputs):
    #and rotate it about a given euler angle
    #the euler angle will be a z-x-z extrinsic rotation
    #input is expected in degrees

    centered_mesh = mesh.Mesh.from_file(inputs.inputfile)
    #rotate around euler angle
    #z-x-z extrinsic rotation
    centered_mesh.rotate([0.0,0.0,1.0],math.radians(inputs.euler_angle[0]))
    centered_mesh.rotate([1.0,0.0,0.0],math.radians(inputs.euler_angle[1]))
    centered_mesh.rotate([0.0,0.0,1.0],math.radians(inputs.euler_angle[2]))
    centered_mesh.save(inputs.inputfile)
    
def orient_stl(inputs):
    #when double slicing, the second slice happens at a 90 degree angle
    #to the first orientation
    #this script assumes the STL file is in the correct orientation for
    #the first slice (i.e. rotate_stl has already been called)
    #it will then rotate it by the orientation amount (in degrees)
    #about the global z axis
    #then rotate it 90 degrees about the x axis and save
    centered_mesh = mesh.Mesh.from_file(inputs.inputfile)
    centered_mesh.rotate([0.0,0.0,1.0],math.radians(inputs.orient))
    centered_mesh.rotate([1.0,0.0,0.0],math.radians(90))
    centered_mesh.save(inputs.inputfile)
