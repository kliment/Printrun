#!/usr/bin/python
#Interactive RepRap e axis calibration program
#(C) Nathan Zadoks 2011
#Licensed under CC-BY-SA or GPLv2 and higher - Pick your poison.
t= 60			#Time to wait for extrusion
n=100			#Default length to extrude
m=  0			#User-entered measured extrusion length
k=300			#Default amount of steps per mm
port='/dev/ttyUSB0'	#Default serial port to connect to printer

try:
	from printdummy import printcore
except ImportError:
	from printcore import printcore
import time,getopt,sys,os

def float_input(prompt=''):
	import sys
	f=None
	while f==None:
		s=raw_input(prompt)
		try:
			f=float(s)
		except ValueError:
			sys.stderr.write("Not a valid floating-point number.\n")
			sys.stderr.flush()
	return f
def wait(t,m=''):
	import time,sys
	sys.stdout.write(m+'['+(' '*t)+']\r'+m+'[')
	sys.stdout.flush()
	for i in range(t):
		for s in ['|\b','/\b','-\b','\\\b','|']:
			sys.stdout.write(s)
			sys.stdout.flush()
			time.sleep(1.0/5)
	print

if not os.path.exists(port):
	port=0

#Parse options
help="""
%s [ -l DISTANCE ] [ -s STEPS ] [ -p PORT ]
	-l	--length	Length of filament to extrude for each calibration step (default: %d mm)
	-s	--steps		Initial amount of steps to use (default: %d steps)
	-p	--port		Serial port the printer is connected to (default: %s)
	-h	--help		This cruft.
"""[1:-1]%(sys.argv[0],n,k,port if port else 'auto')
try:
	opts,args=getopt.getopt(sys.argv[1:],"hl:s:p:",["help","length=","steps=","port="])
except getopt.GetoptError,err:
	print str(err)
	print help
	sys.exit(2)
for o,a in opts:
	if o in ('-h','--help'):
		print help
		sys.exit()
	elif o in ('-l','--length'):
		n=float(a)
	elif o in ('-s','--steps'):
		k=int(a)

#Show initial parameters
print "Initial parameters"
print "Steps per mm:    %3d steps"%k
print "Length extruded: %3d mm"%n
print 
print "Serial port:     %s"%(port if port else 'auto')

#Connect to printer
print "Connecting to printer..",
p=printcore(port,115200)
print "connected."

#Calibration loop
while n!=m:
	p.send_now("G92 E0")			#Reset e axis
	p.send_now("G1 E%d F100"%int(n))	#Extrude length of filament
	wait(t,'Extruding.. ')
	m=float_input("How many millimeters of filament were extruded? ")
	if n!=m:
		k=(n/m)*k
		p.send_now("M92 E%d"%int(round(k)))	#Set new step count
		print "Steps per mm:    %3d steps"%k	#Tell user
print 'Calibration completed.'	#Yay!
p.disconnect()
