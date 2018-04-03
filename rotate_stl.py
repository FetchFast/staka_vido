#! /usr/bin/env python

#this script will define the functions regarding processing STL files

from stl import mesh
import math
from stl_prep import stl_prep

def get_bounds(mesh):
	#get the length of the x and y dimension of a mesh
	mesh_min = mesh.min_
	mesh_max = mesh.max_
	widths = list()
	widths.append(mesh_max[0]-mesh_min[0])
	widths.append(mesh_max[1]-mesh_min[1])
	widths.append(mesh_max[2]-mesh_min[2])
	return widths
	

def rotate_stl(inputs):
	#and rotate it about a given euler angle
	#the euler angle will be a z-x-z extrinsic rotation
	#input is expected in degrees
	if inputs.verbose:
		print "Rotating Mesh"
	centered_mesh = inputs.current_mesh
	#rotate around euler angle
	#z-x-z extrinsic rotation
	centered_mesh.rotate([0.0,0.0,1.0],math.radians(inputs.euler_angle[0]))
	centered_mesh.rotate([1.0,0.0,0.0],math.radians(inputs.euler_angle[1]))
	centered_mesh.rotate([0.0,0.0,1.0],math.radians(inputs.euler_angle[2]))
	#after rotating objects, we need to recenter
	stl_prep(inputs)
	centered_mesh.update_min()
	centered_mesh.update_max()
	
	
	ret_val = get_bounds(centered_mesh)
	print centered_mesh.min_
	return ret_val
	
	
def orient_stl(inputs):
	#when double slicing, the second slice happens at a 90 degree angle
	#to the first orientation
	#this script assumes the STL file is in the correct orientation for
	#the first slice (i.e. rotate_stl has already been called)
	#it will then rotate it by the orientation amount (in degrees)
	#about the global z axis
	#then rotate it 90 degrees about the x axis and save
	centered_mesh = inputs.current_mesh
	centered_mesh.rotate([0.0,0.0,1.0],math.radians(inputs.orient))
	centered_mesh.rotate([1.0,0.0,0.0],math.radians(90))
	#centered_mesh.save(inputs.inputfile)
	return get_bounds(centered_mesh)
