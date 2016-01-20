#! /usr/bin/env python

#take command line inputs, and call appropriate subroutines

import sys
import getopt
import string
import math
from stl_prep import stl_prep
from stacker import stacker
from shapely.geometry import Polygon, LineString, Point
from hersheydata import font_data


##################################################
#create the styles to be used for objects in inkscape
cut_style = '"fill:#ffffff;stroke:#000000;stroke-opacity:1;stroke-width:0.1;stroke-miterlimit:4;stroke-dasharray:none;fill-opacity:1"'
layer_style = '"stroke-width:0.1;stroke-miterlimit:4;stroke-dasharray:none;stroke:#000000;stroke-opacity:1;fill:#ffffff;fill-opacity:1"'
trace_style = '"fill:none;stroke:#00ffff;stroke-opacity:1;stroke-width:0.1;stroke-miterlimit:4;stroke-dasharray:none;fill-opacity:0"'
mark_area_style = '"fill:#ffffff;stroke:#ff00ff;stroke-opacity:1;stroke-width:0.1;stroke-miterlimit:4;stroke-dasharray:none;fill-opacity:1"'


class input_class:
    def __init__(self):
        self.inputfile = ''
        self.outputfile = ''
        self.thickness = ''
        self.t1 = ''
        self.t2 = ''
        self.euler_angle = ''
        self.orient = ''
        self.space1 = ''
        self.space2 = ''
        self.count1 = ''
        self.count2 = ''
        self.single = False
        self.double = False
        self.traces = False
        self.verbose = True
        self.mark_areas = False
        self.openscad = False

class svg_data:
    #this class holds all the information for an SVG document
    #it contains multiple layer objects
    def __init__(self):
        self.layer_count = 0
        self.layer=list()
        self.first_line=""
        self.header=""
        self.height = 0
        self.width = 0
        
    def add_layer(self,layer_ob):
        self.layer.append(layer_ob)
        self.layer_count+=1

class layer:
    #this class defines the layer object
    #each layer will hold one or more objects
    def __init__(self,style_str):
        self.poly_count=0
        self.poly=list()
        self.style = style_str

    def add_poly(self,poly):
        self.poly.append(poly)
        self.poly_count+=1

class poly:
    #This class defines a polygon object
    #each poly contains a shapely polygon object
    #and zero to many traces that represent where layers
    #above rest on the current layer
    def __init__(self,point_str,style,poly_type):
        self.point_str = point_str
        self.shape=Polygon(point_str_to_list(point_str))
        self.style=style
        self.type = poly_type
        self.traces = list()
        self.trace_count = 0
        self.mark_areas = list()
        self.mark_count = 0
        #put in a dummy point as a starter
        self.mark_point = 'dummy'
        #a poly could have many marks if it has multiple polygons above it
        self.mark=list()
        #or have mulitple cutouts if it has multiple polygons below it
        self.cutout=list()

    def add_trace(self, geom):
        #this function adds a shapely geometric object
        #to this polygon
        #each polygon may have zero to many traces
        #the traces represent areas on this polygon
        #where the layer above covers
        self.trace_count+=1
        self.traces.append(geom)
        
    def add_mark_area(self, geom):
        #this function adds a mark area to a geometric object
        #to this polygon
        #each poly may have to many mark areas
        #this mark area represents the portion of the polygon's trace
        #that is covered by a polygon's trace on the layer above
        self.mark_count += 1
        self.mark_areas.append(geom)
        
    def add_mark(self,point_str):
        self.mark.append(point_str)
        
    def add_cutout(self,point_str):
        self.cutout.append(point_str)

    
#create a function to extract the size information from the existing file
def extract_size(line,svg_data):
    width_start = line.find("width=")+7
    width_end = line.find('"',width_start)
    width = line[width_start:width_end]
    svg_data.width = width
    height_start = line.find("height=")+8
    height_end = line.find('"',height_start)
    height = line[height_start:height_end]
    svg_data.height = height
    
    
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
    
def get_mark_areas(layer_collection):
    #this function will go through the layers
    #it will look at the traces on each layer
    #and find a place to put the layer number and orientation marker
    #It is known from previous construction
    #that the trace polygons are areas on each layer that are covered 
    #by the layer above
    #so anything put in that poly will be invisible when fully assembled
    #but to cut alignment holes in the upper layer
    #to see the marks in the lower layer
    #we need to make sure the mark is placed in an area of the lower layer
    #that corresponds to an area that is covered in the upper layer
    #in other words, we can't put the marker in an area on the lower layer
    #that would require cutting a hole in the upper layer
    #that would be visible after assembly
    
    #start by going through the layers
    for i,curr_layer in enumerate(layer_collection.layer):
        #then search each polygon in the current layer
        for curr_poly in curr_layer.poly:
            #check each trace in this polygon
            for curr_trace in curr_poly.traces:
                #if we have a trace in this polygon
                #we need to cycle through all the traces on the layer above
                #which means cycle through each polygon
                #then cycle through its traces
                for check_poly in layer_collection.layer[i+1].poly:
                    #then search through each trace
                    for check_trace in check_poly.traces:
                        mark_area = curr_trace.intersection(check_trace)
                        if mark_area.type == 'Polygon':
                            #only one overlapping area
                            curr_poly.add_mark_area(mark_area)
                        elif mark_area.type == 'MultiPolygon':
                            #in this case, extract each poly separately
                            for part in mark_area:
                                curr_poly.add_mark_area(part)
                            
                        elif mark_area.type == "GeometryCollection":
                            #if it's a geom collection
                            #and len is zero, no issue
                            if len(mark_area) == 0:
                                pass
                            else:
                                print "Error with mark areas.  Geometry Collection Length non-zero"
                        else:
                            print "Trouble with mark area " + mark_area.type
    
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
                    
def draw_mark(lower_poly,upper_poly,test_point,radius):
    lower_poly.mark_point = test_point
    upper_poly.mark_point = test_point
    #get the coordinates for the test point
    cen_x = test_point.bounds[0]
    cen_y = test_point.bounds[1]
    #bottom left corner
    point_str = str(cen_x-radius/2) + ',' + str(cen_y - radius/2) + ' '
    #bottm right corner
    point_str += str(cen_x + radius/2) + ',' + str(cen_y - radius/2) + ' '
    #upper right corner
    point_str += str(cen_x + radius/2) + ',' + str(cen_y + radius/2) + ' '
    #top point
    point_str += str(cen_x) + ',' + str(cen_y + radius) + ' '
    #top_left corner
    point_str += str(cen_x - radius/2) + ',' + str(cen_y + radius/2)
    lower_poly.add_mark(point_str)
    upper_poly.add_cutout(point_str)
    return

    
def check_point(lower_poly,upper_poly,curr_area,test_point,radius):
    #pass in the geometry for testing
    test_circ = test_point.buffer(radius)
    if curr_area.contains(test_circ):
        #in this case, the area around the test point large enough to contain the mark
        #are completely within current mark area
        
        #we have to test to make sure that the mark location on this layer
        #does not overlap the mark on the layer below
        #when a mark gets set, we'll set the mark point
        #on the upper layer at the same point
        #it is initialized as "dummy"
        #so if it is "dummy", there is no mark below it
        #if it is a point, that means there is a mark below it
        #and we need to make sure that the current circle does NOT contain it
        if lower_poly.mark_point == "dummy":
            #in this case, nothing further to check
            #set the upper layer mark point to the current point
            #draw_mark(lower_poly,upper_poly,test_point,radius)
            #once a success is found, exit the for loop
            return True
        else:
            #in this case, there is a mark in the layer below
            #if the point is within two radii of the test point
            #then it's too close
            check_circ = test_point.buffer(2*radius)
            if check_circ.contains(lower_poly.mark_point):
                #in this case, too close do nothing
                pass
            else:
                #in this case, not too close
                #draw the mark
                #draw_mark(lower_poly,upper_poly,test_point,radius)
                return True
    #if all the tests fail, return false, this point won't work
    return False
    
                    
def add_marker(lower_poly,upper_poly):
    #this function will take a polygon object, look at its mark_area
    #and place a pentagonal mark in that area, then a hole in the 
    #corresponding spot in the polygon above
    #The program will find a base point for the marker within the mark area
    #the search pattern will start at the center of the mark area
    #and check to see if there is a radius from the base point
    #that is contained within the mark area
    radius = 2
    check_area = radius*radius*3.1415
    for curr_area in lower_poly.mark_areas:
        #we search through all the mark areas
        #we don't care which one gets marked for a given poly
        #only mark one
        #the test area will be the intersection between the upper poly
        #and the mark area of the lower poly
        test_area = curr_area.intersection(upper_poly.shape)
        #if any mark has an area less than 4*pi, then there's not enough
        #area for it to be marked
        if test_area.area > check_area:
            #the search pattern for finding a mark point
            #start at the centroid
            #if that fails, search on a circle around the centroid
            #increment by one degree (or one radius, whichever is smaller)
            #once the radius exceeds the maximum bounds minus the radius
            #the loop ends in a failure
            #the test point will start at the centroid
            
            
            #the first point is the centroid
            test_point = curr_area.centroid
            #check the centroid first
            point_found = check_point(lower_poly,upper_poly,curr_area,test_point,radius)
            if point_found:
                #if the centroid works
                #draw the mark and return true
                draw_mark(lower_poly,upper_poly,test_point,radius)
                return True
            #if it doesn't work start the search radius
            #start by finding the maximum search radius
            test_bounds = test_area.bounds
            max_bound = 0
            for bound in test_bounds:
                if abs(bound) > max_bound:
                    max_bound = abs(bound)
            
            max_bound = max_bound - 2*radius
            dist = radius
            #get the coordinates for the centroid (currently test_point)
            #which will be the center of the search area
            cen_x = test_point.bounds[0]
            cen_y = test_point.bounds[1]
            #while the search radius is less that the maximum
            while dist < max_bound:
                del_theta = float(radius)/float(dist)
                theta = 0
                while theta < 2*3.1415:
                    #print dist, theta, del_theta
                    #search around the circle
                    test_point = Point(cen_x + dist*math.cos(theta), cen_y + dist*math.sin(theta))
                    if curr_area.contains(test_point):
                        #only check points that are within the current mark area
                        point_found = check_point(lower_poly,upper_poly,curr_area,test_point,radius)
                    else:
                        point_found = False
                    
                    if point_found:
                        #if the test point works, mark and return
                        draw_mark(lower_poly,upper_poly,test_point,radius)
                        return True
                    theta += del_theta
                #if the current circle doesn't work
                #increment distance by radius and repeat
                dist += radius
            
            #if the while loop exits
            #it means we've searched the entire space of the current area
            #and no point worked, that means there are no points on the current
                
    #at this point, all areas have been checked
    #if no possible area can be marked
    #return false
    return False
                    
            
        
 
def read_svg(filepath,svg_data):
    #read in the svg file located at filepath
    #store the data into the structure
    if inputs.verbose:
        print "Reading SVG"
    with open(filepath,'r') as infile:
        for line in infile:
            if line.find('<svg')>=0:
                extract_size(line,svg_data)

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
                svg_data.add_layer(new_layer)

        infile.closed

def add_marker_text_inkscape(text_str,test_point):
    #this function will add marker text centered on the test_point
    #the font data is too large to use as-is
    #set a constant scaling factor here
    text_scale =0.25
    #set the spacing between characters (pixels, relative to the original font size)
    spacing = 3
    #inkscape scaling factor
    #90 ppi/25.4 mm per inch = 3.54331 scaling
    #inkscape inverts y coordinates, so we need to flip the y coordinate
    inkscape_scale = 3.54331
    
    #first, find the total width of the string
    #and build a list of offsets relative to the left edge of the text
    width=0
    offset = list()
    #add up the width of all the characters
    for i,q in enumerate(text_str):
        char_data = font_data[ord(q)-32]
        curr_width= int(char_data.split()[0])
        width += curr_width
        if i == 0:
            #offset for the first character is one half the width of
            #that character
            offset.append(curr_width/2)
        else:
            #offset for every other character is one half the width of
            #the current character, plus one half the width of the last
            #plus the width of the spacing
            offset.append(curr_width/2+last_width/2+spacing)
        #take the current width and set it to the last_width
        last_width=curr_width
    #add width for the spaces between characters
    #n-1 spaces for n characters
    width+=spacing*(len(text_str)-1)
    #get the point data to locate the text
    #the location of the center point needs to be flipped about the y axis
    #and scaled for inkscape
    cen_x = inkscape_scale*test_point.bounds[0]
    cen_y = -inkscape_scale*test_point.bounds[1]
    #each character should be drawn at a position that starts at the cen_x
    #moves to the left by width/2 to reach the start position
    #then moves to the right by its corresponding offset to be spaced correctly
    #the tricky bit is that the cen_x and cen_y coordinates must be scaled and flipped
    #but the data for the font itself shouldn't be, and should remain true to scale only
    
    #create an output string that represents the text to be added to the inkscape svg
    outstring = ""
    for i,q in enumerate(text_str):
        char_data=font_data[ord(q)-32]
        start_pos = char_data.find("M")
        #need to scale the character data
        scaled_data = char_data[start_pos:]
        scaled_data = scaled_data.split()
        for j,item in enumerate(scaled_data):
            if item <> "M" and item <> "L":
                scaled_data[j] = str(text_scale*float(item))
                
        scaled_data = " ".join(scaled_data)
        outstring +='      <path\n'
        outstring +='         transform="translate(' + str(cen_x+text_scale*(-width/2+offset[i]))+','+str(cen_y)+')"\n'
        outstring +='         d="' + scaled_data + '"\n'
        outstring +='         style=' + trace_style + '/>\n'
        
    return outstring
        
def write_to_inkscape(inputs, svg_data):
    with open(inputs.outputfile, 'w') as outfile:
        #writout out the header info
        outfile.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
        outfile.write('<svg\n' + \
                      '   xmlns:dc="http://purl.org/dc/elements/1.1/"\n' + \
                      '   xmlns:cc="http://creativecommons.org/ns#"\n' + \
                      '   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n' + \
                      '   xmlns:svg="http://www.w3.org/2000/svg"\n' + \
                      '   xmlns="http://www.w3.org/2000/svg"\n' + \
                      '   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"\n' + \
                      '   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"\n' + \
                      '   width="' + svg_data.width + '"\n' + \
                      '   height="' + svg_data.height + '"\n' + \
                      '   id="' + inputs.outputfile + '"\n' + \
                      '   version="1.1"\n' + \
                      '   inkscape:version="0.91 r13725"\n' + \
                      '   sodipodi:docname="' + inputs.outputfile + '">\n' + \
                      '  <sodipodi:namedview\n' + \
                      '     pagecolor="#ffffff"\n' + \
                      '     bordercolor="#666666"\n' + \
                      '     borderopacity="1"\n' + \
                      '     objecttolerance="10"\n' + \
                      '     gridtolerance="10"\n' + \
                      '     guidetolerance="10"\n' + \
                      '     inkscape:pageopacity="0"\n' + \
                      '     inkscape:pageshadow="2"\n' + \
                      '     inkscape:window-width="1920"\n' + \
                      '     inkscape:window-height="1005"\n' + \
                      '     id="namedview5887"\n' + \
                      '     showgrid="false"\n' + \
                      '     inkscape:zoom="1.0"\n' + \
                      '     inkscape:cx="58.152"\n' + \
                      '     inkscape:cy="261.96802"\n' + \
                      '     inkscape:window-x="-9"\n' + \
                      '     inkscape:window-y="-9"\n' + \
                      '     inkscape:window-maximized="1"\n' + \
                      '     inkscape:current-layer="layer0" />\n')
        for layer_num, curr_layer in enumerate(svg_data.layer):
            #cycle through each layer
            #start by writing the appropriate intro information for this layer
            layer_str=str(layer_num)
            outfile.write('  <g\n')
            outfile.write('     inkscape:groupmode="layer"\n')
            outfile.write('     id="layer' +layer_str +'"\n')
            outfile.write('     inkscape:label="Layer ' + layer_str+ '">\n')

            #group all polygons in this layer together
            outfile.write('    <g\n')
            outfile.write('       id="poly_group' + layer_str + '">\n')
            for poly_num,curr_poly in enumerate(curr_layer.poly):
                #go through each polygon in the current layer
                #then write the appropriate info to the output
                poly_str=str(poly_num)            
                outfile.write('      <path\n')
                outfile.write('         d="M ' + scale_and_flip(curr_poly.point_str) + ' Z"\n')
                outfile.write('         style=' + curr_poly.style + '/>\n')
                if inputs.traces:
                    for trace_poly in curr_poly.traces:
                        #include all the traces in the same group
                        outfile.write('      <path\n')
                        outfile.write('         d="M ' + scale_and_flip(point_list_to_str(trace_poly.exterior.coords[:])) + ' Z"\n')
                        outfile.write('         style=' + trace_style + '/>\n')
                if inputs.mark_areas:   
                    for mark_area in curr_poly.mark_areas:
                        #includethe mark areas, too
                        outfile.write('      <path\n')
                        outfile.write('         d="M ' + scale_and_flip(point_list_to_str(mark_area.exterior.coords[:])) + ' Z"\n')
                        outfile.write('         style=' + mark_area_style + '/>\n')
                        
                    for curr_mark in curr_poly.mark:
                        outfile.write('      <path\n')
                        outfile.write('         d="M ' + scale_and_flip(curr_mark) + ' Z"\n')
                        outfile.write('         style=' + trace_style + '/>\n')
                    
                    for curr_cutout in curr_poly.cutout:
                        outfile.write('      <path\n')
                        outfile.write('         d="M ' + scale_and_flip(curr_cutout) + ' Z"\n')
                        outfile.write('         style=' + cut_style + '/>\n')
                    if curr_poly.mark_point <> "dummy":    
                        outfile.write(add_marker_text_inkscape(layer_str,curr_poly.mark_point))
                        
            #after writing all the polygons
            #group close the group around them
            outfile.write('    </g>\n')
            #write out the close for the layer
            outfile.write('  </g>\n')
        #after writing all the layers
        #close out the SVG
        outfile.write('</svg>\n')
        outfile.closed 
             
def scale_and_flip(point_str):
    #this function will take a point string
    #and scale and flip it for inkscape
    #by default, inkscape assumes units are in pixels
    #and assumes 90 pixels per inch
    #slicer outputs units in mm
    #90 ppi/25.4 mm per inch = 3.54331 scaling
    #inkscape inverts y coordinates, so we need to flip the y coordinate
    scale = 3.54331
    new_point_str = ""
    while string.find(point_str,",")>=0:
        #as long as a comma is in the string
        #we have at least one more pair of coordinates
        end_position = string.find(point_str,",")
        new_x = scale*float(point_str[:end_position])
        point_str = point_str[end_position+1:]
        #if there is a space in the string, then there are at least two
        if string.find(point_str," ") >= 0:
            end_position = string.find(point_str," ")
            new_y = -scale*float(point_str[:end_position])
            point_str = point_str[end_position+1:]
            new_point_str += str(new_x) + "," + str(new_y) + " "
        else:
            #this is the last coordinate
            new_y = -scale * float(point_str)
            point_str = ""
            new_point_str += str(new_x) + "," + str(new_y)
        
    return new_point_str
    
def write_to_openscad(inputs,svg_data):
    #this function will write the output of the slices to OpenSCAD
    #to allow previewing what the finished shape will look like.
    #Go through each layer in the SVG data
    #draw each polygon from from the layer
    #extrude it by the thickness
    #translate it to the correct height
    outname = inputs.outputfile[:-4] + ".scad"
    print outname
    with open(outname,'w') as outfile:
        for i,curr_layer in enumerate(svg_data.layer): 
            for curr_poly in curr_layer.poly:
                trans_string = "translate([0,0," + str(i*inputs.thickness) + "])\n"
                trans_string += "linear_extrude(height=" + str(inputs.thickness) + ")\n"
                polygon_string = poly_to_openscad(curr_poly.shape)
                outfile.write(trans_string)
                outfile.write(polygon_string)
                outfile.write("\n")
                
            
def poly_to_openscad(shape):
    #take a shapely polygon object
    #and read its exterior coordinates
    #return a formatted string that will contain#
    #the OpenSCAD commands to make the equivalent poly
    polygon_string = "polygon(points=["
    for point in shape.exterior.coords:
        polygon_string += '[' + str(point[0]) + ',' + str(point[1]) + '],'
    #after all the points are added, remove the last comma
    polygon_string = polygon_string[:-1]
    polygon_string += ']);\n'
    return polygon_string
    
def get_args(argv,inputs):
    
    try:
        opts, args = getopt.getopt(argv,"hvi:o:t:r:",
                                   ["ifile=",
                                   "ofile=",
                                   "t1=",
                                   "t2=",
                                   "orient=",
                                   "s1=",
                                   "s2=",
                                   "n1=",
                                   "n2=",
                                   "add-traces",
                                   "verbose"
                                   "mark-areas",
                                   "openscad" ])
    except getopt.GetoptError:
        usage()      
        sys.exit(2)
        
    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputs.inputfile = arg
            print 'Input file is ', inputs.inputfile
        elif opt in ("-o", "--ofile"):
            inputs.outputfile = arg
            print 'Output file is ', inputs.outputfile
        elif opt == '-t':
            inputs.thickness = float(arg)
            print 'Single Thickness is ', str(inputs.thickness)
        elif opt == '--t1':
            inputs.t1 = float(arg)
            print 'First Thickness is ', str(inputs.t1)
        elif opt == '--t2':
            inputs.t2 = float(arg)
            print 'Second Thickness is ', str(inputs.t2)
        elif opt == '-r':
            inputs.euler_angle = extract_angles(arg)
            print 'Rotation is ', inputs.euler_angle
        elif opt == '--orient':
            inputs.orient = float(arg)
            print 'Orientation of second cut is ', inputs.orient
        elif opt == '--s1':
            inputs.space1 = float(arg)
            print 'First spacing is ', str(inputs.space1)
        elif opt == '--s2':
            inputs.space2 = float(arg)
            print 'Second spacing is ', str(inputs.space2)
        elif opt == '--n1':
            inputs.count1 = int(arg)
            print 'First count is ', str(inputs.count1)
        elif opt == '--n2':
            inputs.count2 = int(arg)
            print 'Second count is ', str(inputs.count2)
        elif opt =="--add-traces":
            inputs.traces = True
        elif opt in ("-v", "--verbose"):
            inputs.verbose = True
        elif opt == "--mark-areas":
            inputs.mark_areas = True
        elif opt == "--openscad":
            inputs.openscad = True
        else:
            print "Argument Error"
            
        
        
def check_inputs(inputs):
    #first, check to make sure input file is specified
    if inputs.inputfile == '':
        print "No input STL file specified."
        sys.exit(2)
    #if there are inputs for single slices and double slices
    #then error, because it should be one or the other
    if inputs.thickness <> '' or inputs.euler_angle <> '':
        inputs.single = True
    if inputs.t1 <> '' or \
       inputs.t2 <> '' or \
       inputs.orient <> '' or \
       inputs.space1 <> '' or \
       inputs.space2 <> '' or \
       inputs.count1 <> '' or \
       inputs.count2 <> '':
        inputs.double = True
    if inputs.single and inputs.double:
        if inputs.verbose:
            print "Options for a single cuts and double cuts specified."            
        sys.exit(2)
    #Specify either spacing, or counts, not both
    have_space = False
    have_count = False
    if inputs.space1 <> '' or inputs.space2 <> '':
        have_space = True
    if inputs.count1 <> '' or inputs.count2 <> '':
        have_count = True
    if have_space and have_count:
        if inputs.verbose:
            print "Options specify spacing and counts.  Only once can be specified."
        sys.exit(2)
        
def load_defaults(inputs):
    #if no output file is specified
    #use the input filename as the output file name
    if inputs.outputfile == '':
        end_position = string.find(inputs.inputfile,'.')
        filename = inputs.inputfile[:end_position]
        inputs.outputfile = filename + '.svg'
    #if no values are added
    #assume single cut, in existing z axis
    if inputs.thickness == '' and \
       inputs.t1 == '' and \
       inputs.t2 == '' and \
       inputs.euler_angle == '' and \
       inputs.orient == '' and \
       inputs.space1 == '' and \
       inputs.space2 == '' and \
       inputs.count1 == '' and \
       inputs.count2 == '':
        inputs.thickness = 3.3 #mm default thickness is 1/8" plywood
        inputs.euler_angle = (0,0,0)
        if inputs.verbose:
            print "Default settings for single slice set"
    #if t1 is specified, but not t2, assume they are the same
    if inputs.t1 <> '' and inputs.t2 == '':
        inputs.t2 = inputs.t1
    
       
    #add more default behaviors here
        
    
        
def extract_angles(input_string):
    end_position = string.find(input_string,',')
    first_angle = float(input_string[1:end_position])
    input_string = input_string[end_position+1:]
    end_position = string.find(input_string,',')
    second_angle = float(input_string[:end_position])
    input_string = input_string[end_position+1:]
    third_angle = float(input_string[:-1])
    output_tuple = (first_angle,second_angle,third_angle)
    return output_tuple


def usage():
    print 'staka_vido.py\n'
    print '   -i, --ifile input STL file'
    print '   -o, --ofile output SVG file'
    print '   -t specify the thickness the material in mm'
    print '   --t1 if using two materials for opposite directions,' \
          ' specify the thickness of the first material'
    print '   --t2 if using two materials for opposite directions,' \
          ' specify the thickness of the second material'
    print '   -r specify the euler angle rotation z-x-z (extrinsic) used for rotating the STL'
    print '   --orient specify the angle in degrees for the orientation of the second slices'
    print '   --s1 specify the spacing between the centers of the cuts for the first axis'
    print '   --s2 specify the spacing between the centers of the cuts for the second axis'
    print '   --n1 specify the number of layers for the first axis'
    print '   --n2 specify the number of layers for the second axis'
    print '   --add-traces this option will enable adding traces to layers'
    print '   --verbose this option will enable additional output text'
    print '   --mark-areas this option will draw the mark areas on the SVG for reference'
    print '   --openscad this option will output the geometry into OpenSCAD format for 3D viewing'
    

#if __name__ == "__main__":
#    inputs = input_class()
#    get_args(sys.argv[1:],inputs)
#else:
if True:
    #right now this is used for debugging
    #fix this before release
    inputs = input_class()
    inputs.inputfile = 'yodabust.stl'
    inputs.outputfile = 'yodabust.svg'
    inputs.thickness = 3.3
    inputs.t1 = ''
    inputs.t2 = ''
    inputs.euler_angle = (0,45,0)
    inputs.orient = ''
    inputs.space1 = ''
    inputs.space2 = ''
    inputs.count1 = ''
    inputs.count2 = ''
    inputs.single = False
    inputs.double = False
    inputs.traces = True
    inputs.verbose = True
    inputs.mark_areas = True
    inputs.openscad = True
    
#check inputs for errors
if inputs.verbose:
    print "Checking inputs"
    
check_inputs(inputs)
#load defaults if inputs not specified
if inputs.verbose:
    print "Checking for default values"
load_defaults(inputs)
#prepare the STL by moving it to 
if inputs.verbose:
    print "Preparing input STL file"
inputs.inputfile = stl_prep(inputs.inputfile)

#after inputs are checked
#and defaults are loaded
#and stl file is prepped
#look to see if this program is being used to make
#a figure with single cuts
#or one with double cuts
#pass the inputs to the correct function
#use thickness as a proxy for single cuts
if inputs.thickness <> '':
    if inputs.verbose:
        print "Calling stacker"
    stacker(inputs)
    #create a document to store the data
    stack_doc = svg_data()
    #read in the data from the svg file
    read_svg(inputs.outputfile,stack_doc)
    #always get traces
    for i in range(len(stack_doc.layer)-1):
        get_traces(stack_doc.layer[i+1],stack_doc.layer[i])
    #Mark areas are areas on a polygon that is covered by a polygon
    #that is in turn covered by another polygon
    #in other words, a place on a polygon that has at least two layers
    #above it
    #used in determining where to place any orientation marks
    get_mark_areas(stack_doc)
    #search through the polygons to find where to place the markers 
    #add the markers
    for i in range(len(stack_doc.layer)-2):
        #go through every layer except the last two
        if inputs.verbose:
            print "\nSearching Layer " + str(i) + "====================="
        poly_count = 1
        poly_total = len(stack_doc.layer[i+1].poly)
        for upper_poly in stack_doc.layer[i+1].poly:
            #check each polygon in the upper layer
            #set a boolean bit to see if the marker is found
            marker_added = False
            if inputs.verbose:
                print "Checking Poly " + str(poly_count) + " of " + str(poly_total)
            #check to see if this polygon intersects with the mark area
            #of any polygon on the lower layer
            for lower_poly in stack_doc.layer[i].poly:
                #a polygon may have one or more mark areas
                for curr_mark_area in lower_poly.mark_areas:
                    if curr_mark_area.intersects(upper_poly.shape):
                        #if the upper poly intersects the lower poly's
                        #mark area, then try to add a marker
                        #if it returns true, the marker is added
                        #if it returns false, no marker added
                        marker_added = add_marker(lower_poly,upper_poly)
                    
                    if marker_added:
                        #in this case, a marker has been added to this
                        #upper polygon
                        #do not search more mark areas
                        if inputs.verbose:
                            print "Marker added\n"
                        break
                    
                if marker_added:
                    #in this case, marker has been added to upper poly
                    #do not search more lower polys
                    break
                    
            poly_count+=1
                                   
    write_to_inkscape(inputs,stack_doc)
    if inputs.openscad:
        if inputs.verbose:
            print "Writing OpenSCAD output"
        write_to_openscad(inputs,stack_doc)
else:
    dicer(inputs)

#at this point, the files are sliced into SVG file(s)
#read the SVG file(s) into 
