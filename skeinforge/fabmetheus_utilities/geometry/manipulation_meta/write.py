"""
Boolean geometry write.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
import os

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return WriteDerivation(xmlElement)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	processXMLElementByDerivation(None, xmlElement)

def processXMLElementByDerivation(derivation, xmlElement):
	"""Process the xml element by derivation."""
	if derivation is None:
		derivation = WriteDerivation(xmlElement)
	if len(derivation.targets) < 1:
		print('Warning, processXMLElement in write could not get targets for:')
		print(xmlElement)
		return
	fileNames = []
	for target in derivation.targets:
		writeXMLElement(derivation, fileNames, target)

def writeXMLElement(derivation, fileNames, target):
	"""Write a quantity of the target."""
	xmlObject = target.xmlObject
	if xmlObject is None:
		print('Warning, writeTarget in write could not get xmlObject for:')
		print(target)
		print(derivation.xmlElement)
		return
	parserDirectory = os.path.dirname(derivation.xmlElement.getRoot().parser.fileName)
	absoluteFolderDirectory = os.path.abspath(os.path.join(parserDirectory, derivation.folderName))
	if '/models' not in absoluteFolderDirectory:
		print('Warning, models/ was not in the absolute file path, so for security nothing will be done for:')
		print(derivation.xmlElement)
		print('For which the absolute folder path is:')
		print(absoluteFolderDirectory)
		print('The write tool can only write a file which has models/ in the file path.')
		print('To write the file, move the file into a folder called model/ or a subfolder which is inside the model folder tree.')
		return
	quantity = evaluate.getEvaluatedInt(1, 'quantity', target)
	for itemIndex in xrange(quantity):
		writeXMLObject(absoluteFolderDirectory, derivation, fileNames, target, xmlObject)

def writeXMLObject(absoluteFolderDirectory, derivation, fileNames, target, xmlObject):
	"""Write one instance of the xmlObject."""
	extension = evaluate.getEvaluatedString(xmlObject.getFabricationExtension(), 'extension', derivation.xmlElement)
	fileNameRoot = derivation.fileName
	if fileNameRoot == '':
		fileNameRoot = evaluate.getEvaluatedString('', 'name', target)
		fileNameRoot = evaluate.getEvaluatedString(fileNameRoot, 'id', target)
		fileNameRoot += derivation.suffix
	fileName = '%s.%s' % (fileNameRoot, extension)
	suffixIndex = 2
	while fileName in fileNames:
		fileName = '%s_%s.%s' % (fileNameRoot, suffixIndex, extension)
		suffixIndex += 1
	absoluteFileName = os.path.join(absoluteFolderDirectory, fileName)
	fileNames.append(fileName)
	archive.makeDirectory(absoluteFolderDirectory)
	if not derivation.writeMatrix:
		xmlObject.matrix4X4 = matrix.Matrix()
	print('The write tool generated the file:')
	print(absoluteFileName)
	archive.writeFileText(absoluteFileName, xmlObject.getFabricationText(derivation.addLayerTemplate))


class WriteDerivation:
	"""Class to hold write variables."""
	def __init__(self, xmlElement):
		"""Set defaults."""
		self.addLayerTemplate = evaluate.getEvaluatedBoolean(False, 'addLayerTemplate', xmlElement)
		self.fileName = evaluate.getEvaluatedString('', 'file', xmlElement)
		self.folderName = evaluate.getEvaluatedString('', 'folder', xmlElement)
		self.suffix = evaluate.getEvaluatedString('', 'suffix', xmlElement)
		self.targets = evaluate.getXMLElementsByKey('target', xmlElement)
		self.writeMatrix = evaluate.getEvaluatedBoolean(True, 'writeMatrix', xmlElement)
		self.xmlElement = xmlElement

	def __repr__(self):
		"""Get the string representation of this WriteDerivation."""
		return str(self.__dict__)
