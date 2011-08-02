"""
Boolean geometry utilities.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def _getAccessibleAttribute(attributeName, xmlElement):
	"""Get the accessible attribute."""
	if attributeName in globalGetAccessibleAttributeSet:
		return getattr(Setting(xmlElement), attributeName, None)
	return None

def getCascadeFloatWithoutSelf(defaultFloat, key, xmlElement):
	"""Get the importRadius."""
	if key in xmlElement.attributeDictionary:
		value = xmlElement.attributeDictionary[key]
		functionName = 'get' + key[0].upper() + key[1 :]
		if functionName in value:
			if xmlElement.parent is None:
				return defaultFloat
			else:
				xmlElement = xmlElement.parent
	return xmlElement.getCascadeFloat(defaultFloat, key)

def getImportRadius(xmlElement):
	"""Get the importRadius."""
	if xmlElement is None:
		return 0.6
	return getCascadeFloatWithoutSelf(1.5 * getLayerThickness(xmlElement), 'importRadius', xmlElement)

def getInteriorOverhangAngle(xmlElement):
	"""Get the interior overhang support angle in degrees."""
	return getCascadeFloatWithoutSelf(30.0, 'interiorOverhangAngle', xmlElement)

def getInteriorOverhangRadians(xmlElement):
	"""Get the interior overhang support angle in radians."""
	return math.radians(getInteriorOverhangAngle(xmlElement))

def getLayerThickness(xmlElement):
	"""Get the layer thickness."""
	if xmlElement is None:
		return 0.4
	return getCascadeFloatWithoutSelf(0.4, 'layerThickness', xmlElement)

def getOverhangSpan(xmlElement):
	"""Get the overhang span."""
	return getCascadeFloatWithoutSelf(2.0 * getLayerThickness(xmlElement), 'overhangSpan', xmlElement)

def getOverhangAngle(xmlElement):
	"""Get the overhang support angle in degrees."""
	return getCascadeFloatWithoutSelf(45.0, 'overhangAngle', xmlElement)

def getOverhangRadians(xmlElement):
	"""Get the overhang support angle in radians."""
	return math.radians(getOverhangAngle(xmlElement))

def getPrecision(xmlElement):
	"""Get the cascade precision."""
	return getCascadeFloatWithoutSelf(0.2 * getLayerThickness(xmlElement), 'precision', xmlElement)

def getSheetThickness(xmlElement):
	"""Get the sheet thickness."""
	return getCascadeFloatWithoutSelf(3.0, 'sheetThickness', xmlElement)

def getTwistPrecision(xmlElement):
	"""Get the twist precision in degrees."""
	return getCascadeFloatWithoutSelf(5.0, 'twistPrecision', xmlElement)

def getTwistPrecisionRadians(xmlElement):
	"""Get the twist precision in radians."""
	return math.radians(getTwistPrecision(xmlElement))


class Setting:
	"""Class to get handle xmlElements in a setting."""
	def __init__(self, xmlElement):
		"""Initialize."""
		self.xmlElement = xmlElement

	def __repr__(self):
		"""Get the string representation of this Setting."""
		return self.xmlElement

	def getImportRadius(self):
		"""Get the importRadius."""
		return getImportRadius(self.xmlElement)

	def getInteriorOverhangAngle(self):
		"""Get the interior overhang support angle in degrees."""
		return getInteriorOverhangAngle(self.xmlElement)

	def getInteriorOverhangRadians(self):
		"""Get the interior overhang support angle in radians."""
		return getInteriorOverhangRadians(self.xmlElement)

	def getLayerThickness(self):
		"""Get the layer thickness."""
		return getLayerThickness(self.xmlElement)

	def getOverhangSpan(self):
		"""Get the overhang span."""
		return getOverhangSpan(self.xmlElement)

	def getOverhangAngle(self):
		"""Get the overhang support angle in degrees."""
		return getOverhangAngle(self.xmlElement)

	def getOverhangRadians(self):
		"""Get the overhang support angle in radians."""
		return getOverhangRadians(self.xmlElement)

	def getPrecision(self):
		"""Get the cascade precision."""
		return getPrecision(self.xmlElement)

	def getSheetThickness(self):
		"""Get the sheet thickness."""
		return getSheetThickness(self.xmlElement)

	def getTwistPrecision(self):
		"""Get the twist precision in degrees."""
		return getTwistPrecision(self.xmlElement)

	def getTwistPrecisionRadians(self):
		"""Get the twist precision in radians."""
		return getTwistPrecisionRadians(self.xmlElement)


globalAccessibleAttributes = 'getImportRadius getInteriorOverhangAngle getInteriorOverhangRadians'.split()
globalAccessibleAttributes += 'getLayerThickness getOverhangSpan getOverhangAngle getOverhangRadians'.split()
globalAccessibleAttributes += 'getPrecision getSheetThickness getTwistPrecision getTwistPrecisionRadians'.split()
globalGetAccessibleAttributeSet = set(globalAccessibleAttributes)
