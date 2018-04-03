#! /usr/bin/env python
#this function is used to prepare STL files for use with staka vido
#it will take the input file, move the center of the file
#to the origin of the coordinate system
#then save a copy of the file to be modified for use

from stl import mesh


def stl_prep(inputfile):
    #get the info from the input file
    if inputfile.verbose:
		print "Loading Mesh"
    original_mesh = inputfile.current_mesh
    #find the bounds of the object
    original_min = original_mesh.min_
    original_max = original_mesh.max_
    #move the center of the object to the origin
    #move the z up to a minimum of zero
    if inputfile.verbose:
		print "Centering mesh"
    trans_x = (original_min[0]-original_max[0])/2-original_min[0]
    trans_y = (original_min[1]-original_max[1])/2-original_min[1]
    trans_z = -1*original_min[2]
    
    original_mesh.translate((trans_x,trans_y,trans_z))
    #update values
    original_mesh.update_min()
    original_mesh.update_max()
    
    
		
    #the mesh is updated directly, nothing to return
    return
