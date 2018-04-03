#! /user/bin/env python

#this function will take an STL file, and return paths representing slices

import numpy as np
from stl import mesh


def process_triangle(tri_arr, cut_z):
	#this function gets passed a triangle 
	#it will process the triangle to determine if it is used in the cut
	#if it is, it will process the triangle and return a type number
	#default type is zero, which means triangle not used
	t_type = 0
	#counter for the number of zeros
	zero_count = 0
	#get the z coords
	z1 = tri_arr[0][2]-cut_z
	if z1 == 0:
		zero_count= zero_count +1
	z2 = tri_arr[1][2]-cut_z
	if z2 == 0:
		zero_count=zero_count + 1
	z3 = tri_arr[2][2]-cut_z
	if z3 == 0:
		zero_count = zero_count + 1
	#check conditions for triangle
	if z1>0 and z2 > 0 and z3> 0 :
		#triangle not needed
		#all verticies above the cutline
		pass
	elif z1<0 and z2<0 and z3<0:
		#triangle not needed
		#all verticies below the cutline
		pass
	elif zero_count == 3:
		#triangle not needed
		#flat surface will be picked up elsewhere
		pass
	elif zero_count ==2:
		#this type of triangle has two points on the cutline
		#we can take the segment from this triangle as is
		#it will be processed in one fashion
		t_type = 1
	elif zero_count == 1:
		#this case we need to test
		#if there is one point on the cut line
		#then the other two points are either across the cutline
		#or both on the same side
		#if they cross, then we want the triangle
		#if they are both on the same side, then we don't
		if z1==0:
			if z2*z3>0:
				#in this case, same side
				#do nothing
				pass
			else:
				t_type = 2
		elif z2==0:
			if z1*z3>0:
				pass
			else:
				t_type = 2
		else:
			if z1*z2>0:
				pass
			else:
				t_type = 2
	else:
		#in this case, one vertex is on opposite sides of the other two
		t_type = 3
	
	return t_type
	
def get_segment(tri_arr,t_type,cut_z):
	#this function will take a triangle and type 
	#and process the triangle to return a segment
	#the segement represents the boundry on the cut plane
	#format is a 2x2 array
	#z coordinate will be cut_z for every point
	#[[x1,y1]
	# [x2,y2]]	
	segment = np.zeros((2,2))
	if t_type == 1:
		#in this case two of the vertices are on the cut plane
		#those two verticies define the segment
		curr_vert = 0
		for vertex in tri_arr:
			if vertex[2] == cut_z:
				segment[curr_vert] = vertex[:2]
				curr_vert = curr_vert + 1
				
	elif t_type == 2:
		#in this case, one of the verticies is on the cut plane
		#the other two verticies will be needed to get the other point
		#i can't figure out how to do this more clever
		vorder = range(3)
		while tri_arr[vorder[0]] != cut_z:
				vorder.insert(0,vorder.pop())
			
		#at this point, the vertex on the cut plane is located at vorder[0]
		segment[0] = tri_arr[vorder[0][:2]]
		segment[1] = get_intersect(tri_arr[vorder[1]],tri_arr[vorder[2]],cut_z)
		
		
	elif t_type ==3:
		#in this case, one point is on one side of the cut plane
		#the other two are on the opposite side
		#we need to use the two segments to calculate intersection with
		#the cut plane, and those two intersections will define the segment
		
		#this is also the opposite of clever
		signs = list()
		for i in range(3):
			if tri_arr[i][2]-cut_z > 0:
				signs.append(1)
			else:
				signs.append(-1)
			
		product = signs[0]*signs[1]*signs[2]
		vorder = range(3)
		while signs[vorder[0]] != product:
			vorder.insert(0,vorder.pop())
			
		#at this point, vorder[0] gives the position of the one vertex
		#on opposite side of the cut plane from the other two
		
		segment[0] = get_intersect(tri_arr[vorder[0]],tri_arr[vorder[1]],cut_z)
		segment[1] = get_intersect(tri_arr[vorder[0]],tri_arr[vorder[2]],cut_z)
		
				
	else:
		#this is an error
		print("Something has gone wrong with Triangle Type")
		
	return segment
	
def get_intersect(v1,v2,cut_z):
	#this function takes two verticies of a triangle
	#and returns the the one point where the line segment
	#intersects the z-plane at the given cut_z
	z_const = (cut_z-v1[2])/(v2[2]-v1[2])
	x_coord = z_const*(v2[0]-v1[0]) + v1[0]
	y_coord = z_const * (v2[1]-v1[1]) + v1[1]
	return [x_coord,y_coord]
		
def segments_test(seg_status):
	#this function will test every element in the seg status array
	#if any segment is unused (ie value of seg_status is 0)
	#it will return true
	#else it will return false
	
	for status in seg_status:
		if status ==0:
			return True
		
	#if no zeros found, return false
	return False

	
class new_loop:
	def __init__(self,first_segment):
		self.start_x = first_segment[0][0]
		self.start_y = first_segment[0][1]
		self.search_x = first_segment[1][0]
		self.search_y = first_segment[1][1]
		self.points_string = str(self.start_x)+ ',' + str(self.start_y) + ' '
		self.points_string += str(self.search_x)+ ',' + str(self.search_y) + ' '
		self.closed = False
		
	def add_point(self,segment,max_err):
		if not self.closed:
			self.points_string+=str(segment[1][0]) + ',' + str(segment[1][1]) + ' '
			self.search_x=segment[1][0]
			self.search_y=segment[1][1]
			
			if abs(self.search_x - self.start_x)<max_err and abs(self.search_y - self.start_y)<max_err:
				self.closed=True
		else:
			print "Error! Trying to add point to closed loop"
		
		
def call_layermaker(inputs,cut_z):		
	#load values from inputs
	newmesh = inputs.current_mesh
	max_err = inputs.max_error
	
	print "Testing Cutting Plane: ", cut_z
	
	#count triangles to size arrays
	tri_count = len(newmesh.vectors)
	tri_status = np.zeros(tri_count)
	
	if inputs.verbose:
		print "Evaluating triangles in mesh"
	#iterate through every triangle
	for i,tri_arr in enumerate(newmesh.vectors):
		tri_status[i]=process_triangle(tri_arr,cut_z)
		
	#now we have an array that tells us the status of every triangle
	#count the number of nonzeros
	tri_useful = 0
	for tri_stat in tri_status:
		if tri_stat >0:
			tri_useful= tri_useful+ 1
	
	if inputs.verbose:
		print "Creating Segment List"
	#tri_useful is the count of needed triangles
	#each triangle will yield one segment
	#create an array to hold the segments
	seg_arr = np.zeros((tri_useful,2,2))
	#create an index for the current segment
	#initialize to -1
	curr_seg = -1
	for i, tri_stat in enumerate(tri_status):
		if tri_stat>0:
			#in this case, the triangle is needed
			#index segment number
			curr_seg = curr_seg + 1
			seg_arr[curr_seg] = get_segment(newmesh.vectors[i],tri_stat,cut_z)
			
	#seg_arr now contains an unsorted list of all segments required to build
	#all the loops for this slice
	#create an array that tracks segment status
	seg_status = np.zeros(len(seg_arr))
	
	if inputs.verbose:
		print "Matching segments"
	#segment status will be 0 if the segment is unused
	#change to 1 when the segment is included in an existing loop
	pointstr_list = list()
	while segments_test(seg_status):
		#find the first unused segment
		for i,status in enumerate(seg_status):
			if status == 0:
				#found an unused segment
				#set status to used
				seg_status[i]=1
				print "\nCreating New Loop\n"
				current_loop = new_loop(seg_arr[i])
				#if inputs.verbose:
				#	print "Creating new loop using segment: ", i
				while not current_loop.closed:
					found_segment = False
					for j,curr_status in enumerate(seg_status):
						if seg_status[j]==0:
							#check to see if this unused status matches
							#if inputs.verbose:
							#	print "Checking segment: ", j ," of ", len(seg_status)
							
							if abs(seg_arr[j][0][0] - current_loop.search_x)<max_err:
								#x coordinates match
								if abs(seg_arr[j][0][1] - current_loop.search_y)<max_err:
									#and y coordinates match
									#this is the next segment in the loop
									#no need to modify order
									#if inputs.verbose:
									#	print "Matched Segment ", j
									seg_status[j]=1
									current_loop.add_point(seg_arr[j],max_err)
									found_segment = True
									break
									
							
							if abs(seg_arr[j][1][0] - current_loop.search_x)<max_err:
								#x coordinates match
								if abs(seg_arr[j][1][1] - current_loop.search_y)<max_err:
									#and y coordinates match
									#this is the next segment in the loop
									#need to modify to put in correct order
									#if inputs.verbose:
									#	print "Matched Segment ", j
									seg_status[j]=1
									temp_array = np.zeros((2,2))
									temp_array[0] = seg_arr[j][1]
									temp_array[1] = seg_arr[j][0]
									current_loop.add_point(temp_array,max_err)
									found_segment = True
									break
									
									
					if not found_segment:
						#first check if there if all the segments have been used
						#if so, close the loop
						all_used = True
						for i in seg_status:
							if i==0:
								all_used = False
								break
						#if possible close loop
						if all_used:
							current_loop.closed= True
						#if the loop isn't closed, then throw error
						if not current_loop.closed:	
							print "Error! No segment found on search."
							
							
						
				pointstr_list.append(current_loop.points_string)
				#print current_loop.points_string
	return pointstr_list
	
