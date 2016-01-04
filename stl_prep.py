#! /usr/bin/env python
#this function is used to prepare STL files for use with staka vido
#it will take the input file, move the center of the file
#to the origin of the coordinate system
#then save a copy of the file to be modified for use

from stl import mesh

temp_file_name = 'centered.stl'

def stl_prep(inputfile):
    #get the info from the input file
    original_mesh = mesh.Mesh.from_file(inputfile)
    #find the bounds of the object
    original_min = original_mesh.min_
    original_max = original_mesh.max_
    #move the center of the object to the origin
    original_mesh.x += (original_min[0]-original_max[0])/2-original_min[0]
    original_mesh.y += (original_min[1]-original_max[1])/2-original_min[1]
    original_mesh.z += (original_min[2]-original_max[2])/2-original_min[2]
    #update values
    original_mesh.update_min()
    original_mesh.update_max()
    #save the modified mesh to a file
    original_mesh.save(temp_file_name)
    #return the handle to the modified file
    return temp_file_name
