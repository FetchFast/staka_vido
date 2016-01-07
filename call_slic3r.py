#! /usr/bin/env python

#this function will call slic3r and return an svg file

import platform
import subprocess
import string

def call_slic3r(inputs):
    #set slicer options from inputs
    options = list()
    #output an svg file
    options.append("--export-svg")
    #pass in the output name
    options.append("--output-filename-format")
    options.append(inputs.outputfile)
    #the nozzle diameter needs to be at least the size of the material thickness
    options.append("--nozzle-diameter")
    options.append(str(inputs.thickness))
    #no infill
    options.append("--fill-density")
    options.append("0%")
    #first layer height is one-half the thickness
    options.append("--first-layer-height")
    options.append(str(inputs.thickness/2))
    #remaining layres all at thickness
    options.append("--layer-height")
    options.append(str(inputs.thickness))
    #force only one perimeter
    options.append("--perimeters")
    options.append("1")
    #force no skits
    options.append("--skirts")
    options.append("0")
    #put print center at origin
    options.append("--print-center")
    options.append("0,0")
    #after all options are added, the file name should be appended
    options.append(inputs.inputfile)
    
    
    #in windows call slic3r-console
    #in linux, call slic3r
    #first, find platform
    test_plat = platform.platform()
    if string.find(test_plat,"Windows")>=0:
        #in this case, found windows
        slic3r_command = list()
        slic3r_command.append('slic3r-console')
        for opt in options:
            slic3r_command.append(opt)
            
        if inputs.verbose:
			for command in slic3r_command:
				print command
        subprocess.call(slic3r_command)

    elif string.find(test_plat,"Linux")>=0:
        #in this case, found windows
        slic3r_command = list()
        slic3r_command.append('slic3r')
        for opt in options:
            slic3r_command.append(opt)
        if inputs.verbose:
			for command in slic3r_command:
				print command
        
        subprocess.call(slic3r_command)

    else:
        print "Platform not implemented."
        sys.exit()
        
