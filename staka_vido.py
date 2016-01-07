#! /usr/bin/env python

#take command line inputs, and call appropriate subroutines

import sys
import getopt
import string
from stl_prep import stl_prep
from stacker import stacker
from shapely.geometry import Polygon, LineString


##################################################
#create the styles to be used for objects in inkscape
cut_style = '"fill:#ffffff;stroke:#000000;stroke-opacity:1;stroke-width:0.1;stroke-miterlimit:4;stroke-dasharray:none;fill-opacity:1"'
layer_style = '"stroke-width:0.1;stroke-miterlimit:4;stroke-dasharray:none;stroke:#000000;stroke-opacity:1;fill:#ffffff;fill-opacity:1"'
trace_style = '"fill:none;stroke:#00ffff;stroke-opacity:1;stroke-width:0.1;stroke-miterlimit:4;stroke-dasharray:none;fill-opacity:0"'


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
        self.verbose = False

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

    def add_trace(self, geom):
        #this function adds a shapely geometric object
        #to this polygon
        #each polygon may have zero to many traces
        #the traces represent areas on this polygon
        #where the layer above covers
        self.trace_count+=1
        self.traces.append(geom)
    
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
 
def read_svg(filepath,svg_data):
    #read in the svg file located at filepath
    #store the data into the structure
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
                                   "verbose" ])
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
    

if __name__ == "__main__":
    inputs = input_class()
    get_args(sys.argv[1:],inputs)
    #check inputs for errors
    check_inputs(inputs)
    #load defaults if inputs not specified
    load_defaults(inputs)
    #prepare the STL by moving it to 
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
        stacker(inputs)
        #create a document to store the data
        stack_doc = svg_data()
        #read in the data from the svg file
        read_svg(inputs.outputfile,stack_doc)
        if inputs.traces:
            for i in range(len(stack_doc.layer)-1):
                get_traces(stack_doc.layer[i+1],stack_doc.layer[i])
                
        write_to_inkscape(inputs,stack_doc)
        
    else:
        dicer(inputs)

    #at this point, the files are sliced into SVG file(s)
    #read the SVG file(s) into 
