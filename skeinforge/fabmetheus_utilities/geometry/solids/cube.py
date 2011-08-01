"""
Boolean geometry cube.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addCube(faces, inradius, vertexes, xmlElement):
	"""Add cube by inradius."""
	square = [
		complex(-inradius.x, -inradius.y),
		complex(inradius.x, -inradius.y),
		complex(inradius.x, inradius.y),
		complex(-inradius.x, inradius.y)]
	bottomTopSquare = triangle_mesh.getAddIndexedLoops(square, vertexes, [-inradius.z, inradius.z])
	triangle_mesh.addPillarByLoops(faces, bottomTopSquare)

def getGeometryOutput(inradius, xmlElement):
	"""Get cube triangle mesh by inradius."""
	faces = []
	vertexes = []
	addCube(faces, inradius, vertexes, xmlElement)
	return {'trianglemesh' : {'vertex' : vertexes, 'face' : faces}}

def processXMLElement(xmlElement):
	"""Process the xml element."""
	evaluate.processArchivable(Cube, xmlElement)


class Cube(triangle_mesh.TriangleMesh):
	"""A cube object."""
	def addXMLSection(self, depth, output):
		"""Add the xml section for this object."""
		pass

	def createShape(self):
		"""Create the shape."""
		addCube(self.faces, self.inradius, self.vertexes, self.xmlElement)

	def setToXMLElement(self, xmlElement):
		"""Set to xmlElement."""
		attributeDictionary = xmlElement.attributeDictionary
		self.inradius = evaluate.getVector3ByPrefixes(['demisize', 'inradius'], Vector3(1.0, 1.0, 1.0), xmlElement)
		self.inradius = evaluate.getVector3ByMultiplierPrefix(2.0, 'size', self.inradius, xmlElement)
		self.xmlElement = xmlElement
		attributeDictionary['inradius.x'] = self.inradius.x
		attributeDictionary['inradius.y'] = self.inradius.y
		attributeDictionary['inradius.z'] = self.inradius.z
		if 'inradius' in attributeDictionary:
			del attributeDictionary['inradius']
		self.createShape()
		self.liftByMinimumZ(-self.inradius.z)
		solid.processArchiveRemoveSolid(self.getGeometryOutput(), xmlElement)
