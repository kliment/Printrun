"""
Boolean geometry copy.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities import euclidean


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return CopyDerivation(xmlElement)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	processXMLElementByDerivation(None, xmlElement)

def processXMLElementByDerivation(derivation, xmlElement):
	"""Process the xml element by derivation."""
	if derivation is None:
		derivation = CopyDerivation(xmlElement)
	if derivation.target is None:
		print('Warning, copy could not get target for:')
		print(xmlElement)
		return
	del xmlElement.attributeDictionary['target']
	copyMatrix = matrix.getBranchMatrixSetXMLElement(xmlElement)
	targetMatrix = matrix.getBranchMatrixSetXMLElement(derivation.target)
	targetDictionaryCopy = derivation.target.attributeDictionary.copy()
	evaluate.removeIdentifiersFromDictionary(targetDictionaryCopy)
	targetDictionaryCopy.update(xmlElement.attributeDictionary)
	xmlElement.attributeDictionary = targetDictionaryCopy
	euclidean.removeTrueFromDictionary(xmlElement.attributeDictionary, 'visible')
	xmlElement.className = derivation.target.className
	derivation.target.copyXMLChildren(xmlElement.getIDSuffix(), xmlElement)
	xmlElement.getXMLProcessor().processXMLElement(xmlElement)
	if copyMatrix is not None and targetMatrix is not None:
		xmlElement.xmlObject.matrix4X4 = copyMatrix.getSelfTimesOther(targetMatrix.tetragrid)


class CopyDerivation:
	"""Class to hold copy variables."""
	def __init__(self, xmlElement):
		"""Set defaults."""
		self.target = evaluate.getXMLElementByKey('target', xmlElement)

	def __repr__(self):
		"""Get the string representation of this CopyDerivation."""
		return str(self.__dict__)
