#! /usr/bin/env python

#This program is intended to take outputs from slic3r's slice to svg
#and modify it to something that will work with inkscape 0.49
#This program will put each slice into its own layer
#Program has been updated to use the Shapely library for geometric actions
#First, it reads in the existing file, extracts the necessary information,
##and stores the information in appropriate class info

#####outstanding issues:
######inkscape uses a stupid right hand coordinate system
#######invert everything about the y-axis to correct
######it traces segments that shouldn't be traced because they are already cut

import os
import collections

from shapely.geometry import Polygon, LineString


##################################################
#create the styles to be used for objects in inkscape

cut_style = '"fill:#ffffff;stroke:#000000;stroke-opacity:1;stroke-width:0.1;stroke-miterlimit:4;stroke-dasharray:none;fill-opacity:1"'
layer_style = '"stroke-width:0.1;stroke-miterlimit:4;stroke-dasharray:none;stroke:#000000;stroke-opacity:1;fill:#ffffff;fill-opacity:1"'
trace_style = '"fill:none;stroke:#00ffff;stroke-opacity:1;stroke-width:0.1;stroke-miterlimit:4;stroke-dasharray:none;fill-opacity:0"'

px_to_mm = 3.54331

##################################################
#set path and file information.
#maybe one day replace this with some sort of GUI.
workingpath = os.path.abspath("/home/laz/Documents/Goldfinger/designs/yoda_bust")
in_name = "yodabust.svg"
out_name = "yodabust_mod.svg"
##################################################
#create a class for the overall svg, made up of layers
#a class for layers, made up of paths
#this version will use shapely to manage all geometry

class inkscape_svg:
    #This class defines the object that will hold all the information for the SVG file
    #it contains multiple layers, each corresponding to the sliced paths from Slic3r
    #it has properties that contain information used to construct
    #the SVG to be read by inkscape
    def __init__(self):
        self.layer_count = 0
        self.layer=list()
        self.first_line=""
        self.header=""
        
    def add_layer(self,layer_ob):
        self.layer.append(layer_ob)
        self.layer_count+=1
                       
class layer:
    #this class defines the layer object.  Each layer object will hold one or more objects
    #these objecs will correspond to the items to be drawn in inkscape
    def __init__(self,style_str):
        self.poly_count=0
        self.poly=list()
        self.style = style_str

    def add_poly(self,poly):
        self.poly.append(poly)
        self.poly_count+=1

class poly:
    #this class defines the inkscape polygon object.  Each path consists of:
    ##one Polygon object defined by shapely
    ##a style for the polygon
    #
    #A polygon will have one or more traces
    ##the traces will be polygons that represent where upper subsequent layers
    ##lay over the this polygon
    def __init__(self,point_str,style,poly_type):
        self.point_str = point_str
        self.shape=Polygon(point_str_to_list(point_str))
        self.style=style
        self.type = poly_type
        self.traces = list()
        self.trace_count = 0

    def add_trace(self, geom):
        #this function adds a shapely geometric object
        #to this polygon
        #each polygon may have zero to many traces
        #the traces represent areas on this polygon
        #where the layer above covers
        self.trace_count+=1
        self.traces.append(geom)
        
            
    

#create a function to extract the size information from the existing file
def extract_size(line):
    width_start = line.find("width=")+7
    width_end = line.find('"',width_start)
    width = line[width_start:width_end]
    height_start = line.find("height=")+8
    height_end = line.find('"',height_start)
    height = line[height_start:height_end]
    
    output_int = collections.namedtuple('doc_size',['width','height'])
    output=output_int(width,height)
    return output
    
#a function to extract the layer number for the existing file
def get_layer_number(line):
    layer_start = line.find('"layer')+6
    layer_end = line.find('"',layer_start)
    layer = line[layer_start:layer_end]
    return layer
    
#a function to extract the points string from the existing file
def get_points(line):
    points_start = line.find('points="')+8
    points_end = line.find('"',points_start)
    points = line[points_start:points_end]
    return points
    
def point_list_to_str(point_list):
    #use this to make an inkscape-compatible string
    #this should be used to write paths from existing polygons
    point_str=""
    for point in point_list:
        point_str+= str(point[0]) + ',' + str(point[1]) + " "

    #remove the last space as extraneous
    point_str=point_str[:-1]

    return point_str
    
def point_str_to_list(point_str):
    #this function will create a list of tuples (x,y)
    #that correspond to the geometry of a polygon
    #it will take the string, strip off one point at a time
    #store it in the list, then cut the string to remove the point
    #it will repeat until the string is empty
    
    point_list=list()
    while len(point_str)>0:
        #search for the comma that separates the x from the y
        x_end=point_str.find(',')
        x=float(point_str[:x_end])
        #split out the remaining string
        point_str=point_str[x_end+1:]
        #search for the space that separates the y from the next coord
        y_end=point_str.find(' ')
        #if we return a value, use it
        #otherwise, we've hit the end of the string, and this is the last coord
        #use the remaining string
        if y_end>=0:
            y=float(point_str[:y_end])
            point_str=point_str[y_end+1:]
        else:
            y=float(point_str)
            point_str=list()
        #take the coordinate pair and add it to the list
        point_list.append((x,y))
    return point_list

def get_traces(layer_above,layer_below):
    #this function takes as an input, two layer objects
    #it will trace the layer above onto the layer below
    #and clip any excess lines
    #this will provide alignment lines for stacking the cut objects
    for curr_poly in layer_below.poly:
        #start by checking each poly in the lower layer
        #and see if it interacts with each poly in the upper layer
        for check_poly in layer_above.poly:
            if curr_poly.shape.intersects(check_poly.shape):
                #in this case, the two interact
                #we will take the intersection of the two
                #and convert it to a path to draw the boundary
                trace_poly = curr_poly.shape.intersection(check_poly.shape)
                if trace_poly.type == 'Polygon':
                    #we make only one path
                    curr_poly.add_trace(trace_poly)
                elif trace_poly.type == 'MultiPolygon':
                    #in this case, we have a multipolygon
                    #we need to extract each polygon and make a path
                    for part in trace_poly:
                        curr_poly.add_trace(part)
                else:
                    print "Crazy intersection: " + trace_poly.type
 
#Set the path for files to read and write
infilepath = os.path.join(workingpath,in_name)
outfilepath = os.path.join(workingpath,out_name)


#create the top level list
doc = inkscape_svg()

####################################################
#This section reads in the data and puts it into the SVG structure
with open(infilepath,'r') as infile:
    #create an output file to write lines to
    #scan through the input file a line at a time
    #modify each line as necessary
    #then save the information in the SVG data structure
    for line in infile:
        if line.find("?xml")>=0:
            #in this case, this is the first line
            #output a reprocessed new first line
            doc.first_line='<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
            
        elif line.find("<svg")>=0:
            #in this case, we've found the second line
            #it contains the document size
            #we want to extract the sizes
            #then write a header based on inkscape inputs
            size = extract_size(line)
            doc.header +='<svg\n'
            doc.header +='   xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
            doc.header +='   xmlns:cc="http://creativecommons.org/ns#"\n'
            doc.header +='   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
            doc.header +='   xmlns:svg="http://www.w3.org/2000/svg"\n'
            doc.header +='   xmlns="http://www.w3.org/2000/svg"\n'
            doc.header +='   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"\n'
            doc.header +='   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"\n'
            doc.header +='   width="' + size.width + '"\n'
            doc.header +='   height="' + size.height + '"\n'
            doc.header +='   id="' + out_name + '"\n'
            doc.header +='   version="1.1"\n'
            doc.header +='   inkscape:version="0.91 r13725"\n'
            doc.header +='   sodipodi:docname="' + out_name + '">\n'
            doc.header +='  <sodipodi:namedview\n'
            doc.header +='     pagecolor="#ffffff"\n'
            doc.header +='     bordercolor="#666666"\n'
            doc.header +='     borderopacity="1"\n'
            doc.header +='     objecttolerance="10"\n'
            doc.header +='     gridtolerance="10"\n'
            doc.header +='     guidetolerance="10"\n'
            doc.header +='     inkscape:pageopacity="0"\n'
            doc.header +='     inkscape:pageshadow="2"\n'
            doc.header +='     inkscape:window-width="1920"\n'
            doc.header +='     inkscape:window-height="1005"\n'
            doc.header +='     id="namedview5887"\n'
            doc.header +='     showgrid="false"\n'
            doc.header +='     inkscape:zoom="1.0"\n'
            doc.header +='     inkscape:cx="58.152"\n'
            doc.header +='     inkscape:cy="261.96802"\n'
            doc.header +='     inkscape:window-x="-9"\n'
            doc.header +='     inkscape:window-y="-9"\n'
            doc.header +='     inkscape:window-maximized="1"\n'
            doc.header +='     inkscape:current-layer="layer0" />\n'
            
        elif line.find('<g id="layer')>=0:
            #in this case, we are indicating a new layer
            #then create a layer that inkscape will recognize
            #create layer object
            new_layer = layer(layer_style)
                                
        elif line.find('<polygon')>=0:
            #in this case, we are indicating a path in the original SVG
            #we will extract the geometry data
            #then add it to the appropriate layer
            point_str = get_points(line)
            #check to see if this is a contour (outer boundary of a piece we keep)
            #or hole (outer boundary of a piece we toss
            if line.find('contour')>=0:
                poly_type='contour'
            elif line.find('hole')>=0:
                poly_type='hole'
            #create the new poly object
            #all polys defined in the original document are to be cut
            #so always use the cut_style
            new_poly = poly(point_str,cut_style,poly_type)
            #add the poly object to the layer object
            new_layer.add_poly(new_poly)
            
        
        elif line.find('</g>')>=0:
            #add the layer object to the SVG object
            doc.add_layer(new_layer)

        elif line.find('</svg>')>=0:
            pass
        
        else:
            print 'we missed line:\n' + line
        
    infile.closed


#########################################
#This section will add traces
#we want to add traces to every layer except the last
for i in range(len(doc.layer)-1):
    print "Fixing layer: " + str(i)
    get_traces(doc.layer[i+1],doc.layer[i])
    
    

#########################################
#This section will write out the data from the SVG Structure
with open(outfilepath,'w') as outfile:
    #write out starting information
    outfile.write(doc.first_line)
    outfile.write(doc.header)
    for layer_num, curr_layer in enumerate(doc.layer):
        #cycle through each layer
        #start by writing the appropriate intro information for this layer
        layer_str=str(layer_num)
        outfile.write('  <g\n')
        outfile.write('     inkscape:groupmode="layer"\n')
        outfile.write('     id="layer' +layer_str +'"\n')
        outfile.write('     inkscape:label="Layer ' + layer_str+ '">\n')
        #outfile.write('     style="' + curr_layer.style + '">\n')

        #group all polygons in this layer together
        #NOTE: GCodeTools doesn't recognize polygons
        #so this will be formatted as a path in inkscape
        outfile.write('    <g\n')
        outfile.write('       id="poly_group' + layer_str + '">\n')
        for poly_num,curr_poly in enumerate(curr_layer.poly):
            #go through each polygon in the current layer
            #then write the appropriate info to the output
            poly_str=str(poly_num)            
            outfile.write('      <path\n')
            outfile.write('         d="M ' + curr_poly.point_str + ' Z"\n')
            outfile.write('         style=' + curr_poly.style + '/>\n')
            for trace_poly in curr_poly.traces:
                #include all the traces in the same group
                outfile.write('      <path\n')
                outfile.write('         d="M ' + point_list_to_str(trace_poly.exterior.coords[:]) + ' Z"\n')
                outfile.write('         style=' + trace_style + '/>\n')
                
        #after writing all the polygons
        #group close the group around them
        outfile.write('    </g>\n')
        #write out the close for the layer
        outfile.write('  </g>\n')
    #after writing all the layers
    #close out the SVG
    outfile.write('</svg>\n')
    outfile.closed 

