#! /usr/bin/env python

#Hershey Data processor

from hersheydata import text_data2 as data

#for q in data:
#	test = q.split()
#	print len(test)

with open("output.txt", 'w') as outfile:
	#write file open data
	outfile.write("font_data = [")
	
	for char,q in enumerate(data):
		test = q.split()
		start_point = q.find("M")
		min_offset = test[0]
		max_offset = test[1]
		xmin = 0
		xmax = 0
		for i in range((len(test)-2)/3):
			test_x = int(test[3+3*i])
			#print "Test value is: " + str(test_x)
			if test_x>xmax:
				xmax=test_x
			if test_x<xmin:
				xmin=test_x
		#write out the character width and font data
		outfile.write('"' + str(xmax-xmin) + ' ' + q[start_point:] + '",\n             ')
		
	outfile.write(']')	
		
	

	
	
	
		

