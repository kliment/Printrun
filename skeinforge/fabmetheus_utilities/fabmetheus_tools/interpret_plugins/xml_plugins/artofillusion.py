"""
This page is in the table of contents.
The xml.py script is an import translator plugin to get a carving from an Art of Illusion xml file.

An import plugin is a script in the interpret_plugins folder which has the function getCarving.  It is meant to be run from the interpret tool.  To ensure that the plugin works on platforms which do not handle file capitalization properly, give the plugin a lower case name.

The getCarving function takes the file name of an xml file and returns the carving.

An xml file can be exported from Art of Illusion by going to the "File" menu, then going into the "Export" menu item, then picking the XML choice.  This will bring up the XML file chooser window, choose a place to save the file then click "OK".  Leave the "compressFile" checkbox unchecked.  All the objects from the scene will be exported, this plugin will ignore the light and camera.  If you want to fabricate more than one object at a time, you can have multiple objects in the Art of Illusion scene and they will all be carved, then fabricated together.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_tools import face
from fabmetheus_utilities.geometry.geometry_utilities import boolean_geometry
from fabmetheus_utilities.geometry.geometry_utilities import boolean_solid
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.geometry.solids import cube
from fabmetheus_utilities.geometry.solids import cylinder
from fabmetheus_utilities.geometry.solids import group
from fabmetheus_utilities.geometry.solids import sphere
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCarvingFromParser( xmlParser ):
	"""Get the carving for the parser."""
	booleanGeometry = boolean_geometry.BooleanGeometry()
	artOfIllusionElement = xmlParser.getRoot()
	artOfIllusionElement.xmlObject = booleanGeometry
	euclidean.removeElementsFromDictionary( artOfIllusionElement.attributeDictionary, ['fileversion', 'xmlns:bf'] )
	sceneElement = artOfIllusionElement.getFirstChildWithClassName('Scene')
	xmlElements = sceneElement.getFirstChildWithClassName('objects').getChildrenWithClassName('bf:Elem')
	for xmlElement in xmlElements:
		processXMLElement( booleanGeometry.archivableObjects, artOfIllusionElement, xmlElement )
	return booleanGeometry

def getCarvableObject(globalObject, object, xmlElement):
	"""Get new carvable object info."""
	object.xmlObject = globalObject()
	object.xmlObject.xmlElement = object
	object.attributeDictionary['id'] = xmlElement.getFirstChildWithClassName('name').text
	coords = xmlElement.getFirstChildWithClassName('coords')
	transformXMLElement = getTransformXMLElement(coords, 'transformFrom')
	if len(transformXMLElement.attributeDictionary) < 16:
		transformXMLElement = getTransformXMLElement(coords, 'transformTo')
	matrix.setXMLElementDictionaryMatrix(object.xmlObject.matrix4X4.getFromXMLElement('', transformXMLElement), object)
	return object.xmlObject

def getTransformXMLElement( coords, transformName ):
	"""Get the transform attributes."""
	transformXMLElement = coords.getFirstChildWithClassName( transformName )
	if len( transformXMLElement.attributeDictionary ) < 16:
		if 'bf:ref' in transformXMLElement.attributeDictionary:
			idReference = transformXMLElement.attributeDictionary['bf:ref']
			return coords.getRoot().getSubChildWithID( idReference )
	return transformXMLElement

def processXMLElement( archivableObjects, parent, xmlElement ):
	"""Add the object info if it is carvable."""
	if xmlElement is None:
		return
	object = xmlElement.getFirstChildWithClassName('object')
	if 'bf:type' not in object.attributeDictionary:
		return
	shapeType = object.attributeDictionary['bf:type']
	if shapeType not in globalCarvableClassObjectTable:
		return
	carvableClassObject = globalCarvableClassObjectTable[ shapeType ]
	archivableObject = getCarvableObject( carvableClassObject, object, xmlElement )
	archivableObject.xmlElement.attributeDictionary['visible'] = xmlElement.attributeDictionary['visible']
	archivableObject.setToArtOfIllusionDictionary()
	archivableObject.xmlElement.parent = parent
	archivableObjects.append(archivableObject)

def removeListArtOfIllusionFromDictionary( dictionary, scrubKeys ):
	"""Remove the list and art of illusion keys from the dictionary."""
	euclidean.removeElementsFromDictionary( dictionary, ['bf:id', 'bf:type'] )
	euclidean.removeElementsFromDictionary( dictionary, scrubKeys )


class BooleanSolid( boolean_solid.BooleanSolid ):
	"""An Art of Illusion CSG object info."""
	def setToArtOfIllusionDictionary(self):
		"""Set the shape of this carvable object info."""
		processXMLElement( self.archivableObjects, self.xmlElement, self.xmlElement.getFirstChildWithClassName('obj1') )
		processXMLElement( self.archivableObjects, self.xmlElement, self.xmlElement.getFirstChildWithClassName('obj2') )
		operationString = self.xmlElement.attributeDictionary['operation']
		self.operationFunction = { '0': self.getUnion, '1': self.getIntersection, '2': self.getDifference, '3': self.getDifference }[ operationString ]
		if operationString == '3':
			self.archivableObjects.reverse()
		removeListArtOfIllusionFromDictionary( self.xmlElement.attributeDictionary, ['operation'] )


class Cube( cube.Cube ):
	"""An Art of Illusion Cube object."""
	def setToArtOfIllusionDictionary(self):
		"""Set the shape of this carvable object info."""
		self.inradius = Vector3(
			float( self.xmlElement.attributeDictionary['halfx'] ),
			float( self.xmlElement.attributeDictionary['halfy'] ),
			float( self.xmlElement.attributeDictionary['halfz'] ) )
		self.xmlElement.attributeDictionary['inradius.x'] = self.xmlElement.attributeDictionary['halfx']
		self.xmlElement.attributeDictionary['inradius.y'] = self.xmlElement.attributeDictionary['halfy']
		self.xmlElement.attributeDictionary['inradius.z'] = self.xmlElement.attributeDictionary['halfz']
		removeListArtOfIllusionFromDictionary( self.xmlElement.attributeDictionary, ['halfx', 'halfy', 'halfz'] )
		self.createShape()


class Cylinder(cylinder.Cylinder):
	"""An Art of Illusion Cylinder object."""
	def setToArtOfIllusionDictionary(self):
		"""Set the shape of this carvable object info."""
		self.inradius = Vector3()
		self.inradius.x = float(self.xmlElement.attributeDictionary['rx'])
		self.inradius.y = float(self.xmlElement.attributeDictionary['rz'])
		self.inradius.z = float(self.xmlElement.attributeDictionary['height'])
		self.topOverBottom = float(self.xmlElement.attributeDictionary['ratio'])
		self.xmlElement.attributeDictionary['radius.x'] = self.xmlElement.attributeDictionary['rx']
		self.xmlElement.attributeDictionary['radius.y'] = self.xmlElement.attributeDictionary['rz']
		self.xmlElement.attributeDictionary['topOverBottom'] = self.xmlElement.attributeDictionary['ratio']
		xmlObject = self.xmlElement.xmlObject
		xmlObject.matrix4X4 = xmlObject.matrix4X4.getOtherTimesSelf(matrix.getDiagonalSwitchedTetragrid(90.0, [0, 2]))
		removeListArtOfIllusionFromDictionary(self.xmlElement.attributeDictionary, ['rx', 'rz', 'ratio'])
		self.createShape()


class Group( group.Group ):
	"""An Art of Illusion Group object."""
	def setToArtOfIllusionDictionary(self):
		"""Set the shape of this group."""
		childrenElement = self.xmlElement.parent.getFirstChildWithClassName('children')
		children = childrenElement.getChildrenWithClassName('bf:Elem')
		for child in children:
			processXMLElement( self.archivableObjects, self.xmlElement, child )
		removeListArtOfIllusionFromDictionary( self.xmlElement.attributeDictionary, [] )


class Sphere( sphere.Sphere ):
	"""An Art of Illusion Sphere object."""
	def setToArtOfIllusionDictionary(self):
		"""Set the shape of this carvable object."""
		self.radius = Vector3(
			float( self.xmlElement.attributeDictionary['rx'] ),
			float( self.xmlElement.attributeDictionary['ry'] ),
			float( self.xmlElement.attributeDictionary['rz'] ) )
		self.xmlElement.attributeDictionary['radius.x'] = self.xmlElement.attributeDictionary['rx']
		self.xmlElement.attributeDictionary['radius.y'] = self.xmlElement.attributeDictionary['ry']
		self.xmlElement.attributeDictionary['radius.z'] = self.xmlElement.attributeDictionary['rz']
		removeListArtOfIllusionFromDictionary( self.xmlElement.attributeDictionary, ['rx', 'ry', 'rz'] )
		self.createShape()


class TriangleMesh(triangle_mesh.TriangleMesh):
	"""An Art of Illusion triangle mesh object."""
	def setToArtOfIllusionDictionary(self):
		"""Set the shape of this carvable object info."""
		vertexElement = self.xmlElement.getFirstChildWithClassName('vertex')
		vertexPointElements = vertexElement.getChildrenWithClassName('bf:Elem')
		for vertexPointElement in vertexPointElements:
			coordinateElement = vertexPointElement.getFirstChildWithClassName('r')
			vertex = Vector3( float( coordinateElement.attributeDictionary['x'] ), float( coordinateElement.attributeDictionary['y'] ), float( coordinateElement.attributeDictionary['z'] ) )
			self.vertexes.append(vertex)
		edgeElement = self.xmlElement.getFirstChildWithClassName('edge')
		edgeSubelements = edgeElement.getChildrenWithClassName('bf:Elem')
		for edgeSubelementIndex in xrange( len( edgeSubelements ) ):
			edgeSubelement = edgeSubelements[ edgeSubelementIndex ]
			vertexIndexes = [ int( edgeSubelement.attributeDictionary['v1'] ), int( edgeSubelement.attributeDictionary['v2'] ) ]
			edge = face.Edge().getFromVertexIndexes( edgeSubelementIndex, vertexIndexes )
			self.edges.append( edge )
		faceElement = self.xmlElement.getFirstChildWithClassName('face')
		faceSubelements = faceElement.getChildrenWithClassName('bf:Elem')
		for faceSubelementIndex in xrange( len( faceSubelements ) ):
			faceSubelement = faceSubelements[ faceSubelementIndex ]
			edgeIndexes = [ int( faceSubelement.attributeDictionary['e1'] ), int( faceSubelement.attributeDictionary['e2'] ), int( faceSubelement.attributeDictionary['e3'] ) ]
			self.faces.append( face.Face().getFromEdgeIndexes( edgeIndexes, self.edges, faceSubelementIndex ) )
		removeListArtOfIllusionFromDictionary( self.xmlElement.attributeDictionary, ['closed', 'smoothingMethod'] )


globalCarvableClassObjectTable = { 'CSGObject' : BooleanSolid, 'Cube' : Cube, 'Cylinder' : Cylinder, 'artofillusion.object.NullObject' : Group, 'Sphere' : Sphere, 'TriangleMesh' : TriangleMesh }
