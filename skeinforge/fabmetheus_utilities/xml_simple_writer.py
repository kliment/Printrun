"""
XML tag writer utilities.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

import cStringIO


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addBeginEndInnerXMLTag( attributeDictionary, className, depth, innerText, output, text=''):
	"""Add the begin and end xml tag and the inner text if any."""
	if len( innerText ) > 0:
		addBeginXMLTag( attributeDictionary, className, depth, output, text )
		output.write( innerText )
		addEndXMLTag( className, depth, output )
	else:
		addClosedXMLTag( attributeDictionary, className, depth, output, text )

def addBeginXMLTag( attributeDictionary, className, depth, output, text=''):
	"""Add the begin xml tag."""
	depthStart = '\t' * depth
	output.write('%s<%s%s>%s\n' % ( depthStart, className, getAttributeDictionaryString(attributeDictionary), text ) )

def addClosedXMLTag( attributeDictionary, className, depth, output, text=''):
	"""Add the closed xml tag."""
	depthStart = '\t' * depth
	attributeDictionaryString = getAttributeDictionaryString(attributeDictionary)
	if len(text) > 0:
		output.write('%s<%s%s >%s</%s>\n' % ( depthStart, className, attributeDictionaryString, text, className ) )
	else:
		output.write('%s<%s%s />\n' % ( depthStart, className, attributeDictionaryString ) )

def addEndXMLTag( className, depth, output ):
	"""Add the end xml tag."""
	depthStart = '\t' * depth
	output.write('%s</%s>\n' % ( depthStart, className ) )

def addXMLFromLoopComplexZ( attributeDictionary, depth, loop, output, z ):
	"""Add xml from loop."""
	addBeginXMLTag( attributeDictionary, 'path', depth, output )
	for pointComplexIndex in xrange(len(loop)):
		pointComplex = loop[ pointComplexIndex ]
		addXMLFromXYZ( depth + 1, pointComplexIndex, output, pointComplex.real, pointComplex.imag, z )
	addEndXMLTag('path', depth, output )

def addXMLFromObjects( depth, objects, output ):
	"""Add xml from objects."""
	for object in objects:
		object.addXML(depth, output)

def addXMLFromVertexes( depth, output, vertexes ):
	"""Add xml from loop."""
	for vertexIndex in xrange(len(vertexes)):
		vertex = vertexes[vertexIndex]
		addXMLFromXYZ( depth + 1, vertexIndex, output, vertex.x, vertex.y, vertex.z )

def addXMLFromXYZ( depth, index, output, x, y, z ):
	"""Add xml from x, y & z."""
	attributeDictionary = { 'index' : str( index ) }
	if x != 0.0:
		attributeDictionary['x'] = str(x)
	if y != 0.0:
		attributeDictionary['y'] = str(y)
	if z != 0.0:
		attributeDictionary['z'] = str(z)
	addClosedXMLTag( attributeDictionary, 'vertex', depth, output )

def compareAttributeKeyAscending(key, otherKey):
	"""Get comparison in order to sort attribute keys in ascending order, with the id key first and name second."""
	if key == 'id':
		return - 1
	if otherKey == 'id':
		return 1
	if key == 'name':
		return - 1
	if otherKey == 'name':
		return 1
	if key < otherKey:
		return - 1
	return int(key > otherKey)

def getAttributeDictionaryString(attributeDictionary):
	"""Add the closed xml tag."""
	attributeDictionaryString = ''
	attributeDictionaryKeys = attributeDictionary.keys()
	attributeDictionaryKeys.sort( compareAttributeKeyAscending )
	for attributeDictionaryKey in attributeDictionaryKeys:
		valueString = str(attributeDictionary[attributeDictionaryKey])
		if "'" in valueString:
			attributeDictionaryString += ' %s="%s"' % (attributeDictionaryKey, valueString)
		else:
			attributeDictionaryString += " %s='%s'" % (attributeDictionaryKey, valueString)
	return attributeDictionaryString

def getBeforeRootOutput(xmlParser):
	"""Get the output before the root and the root xml."""
	output = cStringIO.StringIO()
	output.write(xmlParser.beforeRoot)
	xmlParser.getRoot().addXML(0, output)
	return output.getvalue()

def getBeginGeometryXMLOutput(xmlElement=None):
	"""Get the beginning of the string representation of this boolean geometry object info."""
	output = getBeginXMLOutput()
	attributeDictionary = {}
	if xmlElement is not None:
		root = xmlElement.getRoot()
		attributeDictionary = root.attributeDictionary
#	attributeDictionary['version'] = '10.11.30'
	addBeginXMLTag( attributeDictionary, 'fabmetheus', 0, output )
	return output

def getBeginXMLOutput():
	"""Get the beginning of the string representation of this object info."""
	output = cStringIO.StringIO()
	output.write("<?xml version='1.0' ?>\n")
	return output

def getDictionaryWithoutList( dictionary, withoutList ):
	"""Get the dictionary without the keys in the list."""
	dictionaryWithoutList = {}
	for key in dictionary:
		if key not in withoutList:
			dictionaryWithoutList[key] = dictionary[key]
	return dictionaryWithoutList

def getEndGeometryXMLString(output):
	"""Get the string representation of this object info."""
	addEndXMLTag('fabmetheus', 0, output )
	return output.getvalue()
