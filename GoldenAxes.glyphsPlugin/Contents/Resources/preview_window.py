# encoding: utf-8
from GlyphsApp import *
from AppKit import *
from Foundation import *
import objc
from interpolation_engine import InterpolationEngine

PREF_KEY = "com.goldenaxes.GoldenAxes"
AUTOSAVE_KEY = "com.goldenaxes.GoldenAxes.previewWindow"


class GlyphPreviewView(NSView):
	"""Custom NSView that draws interpolated glyphs with proper advance widths."""

	def initWithFrame_(self, frame):
		self = objc.super(GlyphPreviewView, self).initWithFrame_(frame)
		if self is None:
			return None
		self._layers = []
		self._fontSize = 72.0
		self._upm = 1000.0
		return self

	def isFlipped(self):
		return True

	def setLayers_upm_(self, layers, upm):
		self._layers = layers if layers else []
		self._upm = upm if upm else 1000.0
		self.setNeedsDisplay_(True)

	def setFontSize_(self, size):
		self._fontSize = size
		self.setNeedsDisplay_(True)

	def drawRect_(self, rect):
		# White background
		NSColor.whiteColor().set()
		NSBezierPath.fillRect_(self.bounds())

		if not self._layers:
			return

		scale = self._fontSize / self._upm
		bounds = self.bounds()
		margin = 20.0

		# Lay out lines: wrap when exceeding view width
		viewWidth = bounds.size.width - margin * 2
		lines = []
		currentLine = []
		lineWidth = 0.0

		for layer in self._layers:
			glyphWidth = layer.width * scale
			if currentLine and lineWidth + glyphWidth > viewWidth:
				lines.append((currentLine, lineWidth))
				currentLine = []
				lineWidth = 0.0
			currentLine.append(layer)
			lineWidth += glyphWidth

		if currentLine:
			lines.append((currentLine, lineWidth))

		# Vertical metrics
		ascender = self._upm * 0.8
		lineHeight = self._fontSize * 1.3

		NSGraphicsContext.currentContext().saveGraphicsState()

		NSColor.blackColor().set()

		for lineIdx, (lineLayers, _) in enumerate(lines):
			x = margin
			y = margin + lineIdx * lineHeight + ascender * scale

			for layer in lineLayers:
				transform = NSAffineTransform.transform()
				transform.translateXBy_yBy_(x, y)
				transform.scaleXBy_yBy_(scale, -scale)

				NSGraphicsContext.currentContext().saveGraphicsState()
				transform.concat()

				bezierPath = layer.completeBezierPath
				if bezierPath:
					bezierPath.fill()

				NSGraphicsContext.currentContext().restoreGraphicsState()

				x += layer.width * scale

		NSGraphicsContext.currentContext().restoreGraphicsState()

		# Update minimum content height
		totalHeight = margin * 2 + len(lines) * lineHeight
		if totalHeight > bounds.size.height:
			self.setFrameSize_(NSMakeSize(bounds.size.width, totalHeight))


class PreviewWindowController:
	"""Floating resizable window showing interpolated text."""

	def __init__(self, plugin):
		self.plugin = plugin
		self._buildWindow()
		self.refresh()

	def _buildWindow(self):
		frame = NSMakeRect(200, 200, 600, 300)

		styleMask = (
			NSTitledWindowMask |
			NSClosableWindowMask |
			NSResizableWindowMask |
			NSMiniaturizableWindowMask
		)

		self._nsWindow = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
			frame, styleMask, NSBackingStoreBuffered, False
		)
		self._nsWindow.setTitle_("Interpolation Preview")
		self._nsWindow.setMinSize_(NSMakeSize(300, 150))
		self._nsWindow.setFrameAutosaveName_(AUTOSAVE_KEY)
		self._nsWindow.setLevel_(NSFloatingWindowLevel)
		self._nsWindow.setDelegate_(self._createDelegate())

		# Scroll view wrapping the glyph view
		contentRect = self._nsWindow.contentView().bounds()
		self._scrollView = NSScrollView.alloc().initWithFrame_(contentRect)
		self._scrollView.setHasVerticalScroller_(True)
		self._scrollView.setHasHorizontalScroller_(False)
		self._scrollView.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
		self._scrollView.setDrawsBackground_(False)

		self._glyphView = GlyphPreviewView.alloc().initWithFrame_(contentRect)
		self._glyphView.setAutoresizingMask_(NSViewWidthSizable)
		self._scrollView.setDocumentView_(self._glyphView)

		self._nsWindow.contentView().addSubview_(self._scrollView)
		self._nsWindow.orderFront_(None)

	def _createDelegate(self):
		controller = self
		# Define delegate at module level to avoid repeated class creation
		if not hasattr(PreviewWindowController, '_DelegateClass'):
			class _Delegate(NSObject):
				def windowWillClose_(self, notification):
					if hasattr(self, '_controller') and self._controller:
						self._controller.plugin._previewWindow = None
			PreviewWindowController._DelegateClass = _Delegate

		delegate = PreviewWindowController._DelegateClass.alloc().init()
		delegate._controller = controller
		self._delegateInstance = delegate
		return delegate

	def refresh(self):
		font = Glyphs.font
		if not font or not font.currentTab:
			self._glyphView.setLayers_upm_([], 1000)
			return

		showPreview = Glyphs.defaults.get(f"{PREF_KEY}.showPreview", True)
		if not showPreview:
			self._glyphView.setLayers_upm_([], font.upm)
			return

		# Get text from current tab
		tabLayers = font.currentTab.layers
		if not tabLayers:
			self._glyphView.setLayers_upm_([], font.upm)
			return

		# Read axis values
		axis_values = {}
		for i, axis in enumerate(font.axes):
			aid = axis.axisId if hasattr(axis, 'axisId') else axis.name
			saved = Glyphs.defaults.get(f"{PREF_KEY}.axis.{aid}")
			if saved is not None:
				axis_values[aid] = float(saved)
			else:
				axis_values[aid] = font.masters[0].axes[i]

		# Build interpolated layers with correct widths
		interpLayers = []
		for tabLayer in tabLayers:
			glyph = tabLayer.parent
			if not glyph:
				continue
			interpLayer = InterpolationEngine.interpolate_layer(font, glyph, axis_values)
			if interpLayer:
				interpLayers.append(interpLayer)

		self._glyphView.setLayers_upm_(interpLayers, font.upm)

		# Update font size based on window height
		contentHeight = self._nsWindow.contentView().bounds().size.height
		fontSize = max(24, contentHeight * 0.4)
		self._glyphView.setFontSize_(fontSize)

	@property
	def window(self):
		return self

	def show(self):
		self._nsWindow.orderFront_(None)
		self.refresh()

	def close(self):
		self._nsWindow.orderOut_(None)
		self._nsWindow.setDelegate_(None)
		self._delegateInstance = None
