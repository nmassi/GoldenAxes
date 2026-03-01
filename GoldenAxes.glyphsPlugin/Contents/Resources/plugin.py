# encoding: utf-8
from GlyphsApp import *
from GlyphsApp.plugins import *
from AppKit import *
from Foundation import *
import objc

from interpolation_engine import InterpolationEngine
from drawing_utils import (
	PREVIEW_COLOR, EXTRAPOLATION_COLOR,
	draw_filled_path, draw_nodes_for_layer, NODE_COLOR,
	draw_incompatible_emoji,
)
from palette import *  # registers GoldenAxesPalette as secondary plugin


PREF_KEY = "com.goldenaxes.GoldenAxes"


class GoldenAxes(ReporterPlugin):

	@objc.python_method
	def settings(self):
		self.menuName = 'Golden Axes'

	@objc.python_method
	def start(self):
		self._showNodes = bool(Glyphs.defaults.get(f"{PREF_KEY}.showNodes", False))
		self._centerPreview = bool(Glyphs.defaults.get(f"{PREF_KEY}.centerPreview", False))
		self._showEditOverlay = bool(Glyphs.defaults.get(f"{PREF_KEY}.showEditOverlay", True))
		Glyphs.addCallback(self._onUpdate, UPDATEINTERFACE)

	# --- Drawing: Active glyph only (colored overlay) ---

	@objc.python_method
	def background(self, layer):
		font = layer.parent.parent
		if not font or len(font.masters) < 2:
			return

		showPreview = Glyphs.defaults.get(f"{PREF_KEY}.showPreview", True)
		if not showPreview:
			return

		if not self._showEditOverlay:
			return

		self._drawOverlay(layer)

	@objc.python_method
	def _drawOverlay(self, layer):
		font = layer.parent.parent
		glyph = layer.parent

		axis_values = self._readAxisValues(font)
		interpLayer = InterpolationEngine.interpolate_layer(font, glyph, axis_values)

		# None means incompatible (has paths but they don't match across masters)
		if interpLayer is None:
			# Only show skull if the glyph actually has paths (not a space/empty glyph)
			hasPaths = any(len(glyph.layers[m.id].paths) > 0 for m in font.masters)
			if hasPaths:
				scale = self.getScale()
				emojiSize = 48.0 / scale
				centerX = layer.width / 2.0
				master = font.masters[0]
				centerY = (master.ascender + master.descender) / 2.0
				draw_incompatible_emoji(centerX, centerY, emojiSize)
			return

		isExtrap = InterpolationEngine.is_extrapolating(font, axis_values)
		color = EXTRAPOLATION_COLOR if isExtrap else self._readPreviewColor()

		transform = NSAffineTransform.transform()
		if self._centerPreview:
			offset_x = (layer.width - interpLayer.width) / 2.0
			transform.translateXBy_yBy_(offset_x, 0)

		NSGraphicsContext.currentContext().saveGraphicsState()
		transform.concat()

		bezierPath = interpLayer.completeBezierPath
		if bezierPath:
			draw_filled_path(bezierPath, color)

		if self._showNodes:
			scale = self.getScale()
			draw_nodes_for_layer(interpLayer, scale, NODE_COLOR)

		NSGraphicsContext.currentContext().restoreGraphicsState()

	# --- Preview bar: red background for incompatible glyphs (only fires in "live" mode) ---

	def drawBackgroundInPreviewLayer_options_(self, layer, options):
		try:
			font = layer.parent.parent
			if not font or len(font.masters) < 2:
				return
			glyph = layer.parent
			if not glyph:
				return
			if not InterpolationEngine.is_glyph_compatible(glyph):
				hasPaths = any(len(glyph.layers[m.id].paths) > 0 for m in font.masters)
				if hasPaths:
					NSColor.colorWithCalibratedRed_green_blue_alpha_(0.8, 0.15, 0.1, 0.35).set()
					desc = font.masters[0].descender
					asc = font.masters[0].ascender
					NSBezierPath.fillRect_(NSMakeRect(0, desc, layer.width, asc - desc))
		except Exception:
			pass

	# --- Helpers ---

	@objc.python_method
	def _readPreviewColor(self):
		r = Glyphs.defaults.get(f"{PREF_KEY}.color.r")
		if r is not None:
			return (
				float(Glyphs.defaults.get(f"{PREF_KEY}.color.r", 0.0)),
				float(Glyphs.defaults.get(f"{PREF_KEY}.color.g", 0.5)),
				float(Glyphs.defaults.get(f"{PREF_KEY}.color.b", 1.0)),
				float(Glyphs.defaults.get(f"{PREF_KEY}.color.a", 0.4)),
			)
		return PREVIEW_COLOR

	@objc.python_method
	def _readAxisValues(self, font):
		values = {}
		for i, axis in enumerate(font.axes):
			aid = axis.axisId if hasattr(axis, 'axisId') else axis.name
			saved = Glyphs.defaults.get(f"{PREF_KEY}.axis.{aid}")
			if saved is not None:
				values[aid] = float(saved)
			else:
				values[aid] = font.masters[0].axes[i]
		return values

	@objc.python_method
	def _triggerRedraw(self):
		if Glyphs.font and Glyphs.font.currentTab:
			Glyphs.font.currentTab.redraw()

	# --- Context Menu ---

	def conditionalContextMenus(self):
		font = Glyphs.font
		if not font:
			return []

		submenu = NSMenu.alloc().init()
		submenu.setAutoenablesItems_(False)

		overlayTitle = u'\u2713 Show Edit Overlay' if self._showEditOverlay else u'Show Edit Overlay'
		overlayItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(overlayTitle, self.toggleEditOverlay_, u'')
		overlayItem.setTarget_(self)
		submenu.addItem_(overlayItem)

		centerTitle = u'\u2713 Center Preview' if self._centerPreview else u'Center Preview'
		centerItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(centerTitle, self.toggleCenterPreview_, u'')
		centerItem.setTarget_(self)
		centerItem.setEnabled_(self._showEditOverlay)
		submenu.addItem_(centerItem)

		nodesTitle = u'\u2713 Show Nodes' if self._showNodes else u'Show Nodes'
		nodesItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(nodesTitle, self.toggleShowNodes_, u'')
		nodesItem.setTarget_(self)
		nodesItem.setEnabled_(self._showEditOverlay)
		submenu.addItem_(nodesItem)

		submenu.addItem_(NSMenuItem.separatorItem())

		makeItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(u'Make Instance from Current', self.makeInstance_, u'')
		makeItem.setTarget_(self)
		submenu.addItem_(makeItem)

		makeMasterItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(u'Make Master from Current', self.makeMaster_, u'')
		makeMasterItem.setTarget_(self)
		submenu.addItem_(makeMasterItem)

		parentItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(u'Golden Axes', None, u'')
		parentItem.setSubmenu_(submenu)

		return [{'menu': parentItem}]

	def toggleCenterPreview_(self, sender):
		self._centerPreview = not self._centerPreview
		Glyphs.defaults[f"{PREF_KEY}.centerPreview"] = self._centerPreview
		self._triggerRedraw()

	def toggleShowNodes_(self, sender):
		self._showNodes = not self._showNodes
		Glyphs.defaults[f"{PREF_KEY}.showNodes"] = self._showNodes
		self._triggerRedraw()

	def toggleEditOverlay_(self, sender):
		self._showEditOverlay = not bool(self._showEditOverlay)
		Glyphs.defaults[f"{PREF_KEY}.showEditOverlay"] = self._showEditOverlay
		self._triggerRedraw()

	def makeInstance_(self, sender):
		font = Glyphs.font
		if not font:
			return
		axis_values = self._readAxisValues(font)
		newInst = GSInstance()
		newInst.font = font
		for i, axis in enumerate(font.axes):
			aid = axis.axisId if hasattr(axis, 'axisId') else axis.name
			if aid in axis_values:
				newInst.axes[i] = axis_values[aid]
		parts = []
		for i, axis in enumerate(font.axes):
			parts.append(f"{axis.name} {int(round(newInst.axes[i]))}")
		newInst.name = ', '.join(parts)
		font.instances.append(newInst)

	def makeMaster_(self, sender):
		font = Glyphs.font
		if not font:
			return
		axis_values = self._readAxisValues(font)

		# Create a new master with interpolated metrics
		newMaster = GSFontMaster()
		for i, axis in enumerate(font.axes):
			aid = axis.axisId if hasattr(axis, 'axisId') else axis.name
			if aid in axis_values:
				newMaster.axes[i] = axis_values[aid]

		parts = []
		for i, axis in enumerate(font.axes):
			parts.append(f"{axis.name} {int(round(newMaster.axes[i]))}")
		newMaster.name = ', '.join(parts)

		font.masters.append(newMaster)

		# Fill all glyphs with interpolated layers for the new master
		interpFont = InterpolationEngine._get_interpolated_font(font, axis_values)
		if interpFont:
			for glyph in font.glyphs:
				interpGlyph = interpFont.glyphs[glyph.name]
				if interpGlyph and interpGlyph.layers:
					newLayer = glyph.layers[newMaster.id]
					if newLayer:
						sourcLayer = interpGlyph.layers[0]
						newLayer.shapes = sourcLayer.shapes.copy()
						newLayer.width = sourcLayer.width

	# --- Update listener ---

	@objc.python_method
	def _onUpdate(self, sender):
		InterpolationEngine.invalidate_cache()

	# --- Cleanup ---

	@objc.python_method
	def deactivate(self):
		Glyphs.removeCallback(self._onUpdate)
		InterpolationEngine.invalidate_cache()

	@objc.python_method
	def __file__(self):
		return __file__
