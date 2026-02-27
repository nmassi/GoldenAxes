# encoding: utf-8
from GlyphsApp import *
from GlyphsApp.plugins import *
from vanilla import *
from AppKit import *
from Foundation import *
import objc


PREF_KEY = "com.goldenaxes.GoldenAxes"
NOTIFICATION_NAME = "com.goldenaxes.GoldenAxes.valuesChanged"

ROW_HEIGHT = 22
TOOLBAR_HEIGHT = 22
TOP_PADDING = 2
BOTTOM_PADDING = 4
GAP_AFTER_TOOLBAR = 8
PREVIEW_HEIGHT = 160

# Default preview color: blue with 40% opacity
DEFAULT_COLOR = (0.0, 0.5, 1.0, 0.4)

ANIM_FPS = 30.0
ANIM_DURATION = 2.0  # base duration at 1x
SPEED_OPTIONS = [1, 2, 3]


class GlyphPreviewView(NSView):
	"""Draws interpolated glyphs inline in the palette."""

	def initWithFrame_(self, frame):
		self = objc.super(GlyphPreviewView, self).initWithFrame_(frame)
		if self is None:
			return None
		self._layers = []
		self._upm = 1000.0
		self._ascender = 800.0
		self._descender = -200.0
		return self

	def isFlipped(self):
		return True

	def isOpaque(self):
		return True

	def setLayers_upm_ascender_descender_(self, layers, upm, ascender, descender):
		"""Set layers to draw. None entries in the list represent line breaks."""
		self._layers = layers if layers else []
		self._upm = upm if upm else 1000.0
		self._ascender = ascender if ascender else 800.0
		self._descender = descender if descender else -200.0
		self.setNeedsDisplay_(True)

	def drawRect_(self, rect):
		NSColor.whiteColor().set()
		NSBezierPath.fillRect_(self.bounds())

		if not self._layers:
			return

		bounds = self.bounds()
		viewWidth = bounds.size.width
		viewHeight = bounds.size.height
		margin = 6.0

		totalUnitHeight = self._ascender - self._descender
		if totalUnitHeight == 0:
			return

		# Split layers into lines (None = line break)
		lines = []
		currentLine = []
		for layer in self._layers:
			if layer is None:
				lines.append(currentLine)
				currentLine = []
			else:
				currentLine.append(layer)
		if currentLine:
			lines.append(currentLine)

		# Remove empty lines at end
		while lines and not lines[-1]:
			lines.pop()

		if not lines:
			return

		numLines = len(lines)

		# Measure widest line in font units
		lineWidthsUnits = []
		for line in lines:
			w = 0
			for l in line:
				if isinstance(l, tuple) and l[0] == "incompatible":
					w += l[1]
				else:
					w += l.width
			lineWidthsUnits.append(w)

		maxLineWidthUnits = max(lineWidthsUnits) if lineWidthsUnits else 0
		if maxLineWidthUnits == 0:
			return

		availWidth = viewWidth - margin * 2
		availHeight = viewHeight - margin * 2

		# Scale: fit widest line to available width
		scaleByWidth = availWidth / maxLineWidthUnits

		# Scale: fit all lines vertically (with 10% line gap)
		totalVerticalUnits = totalUnitHeight * numLines + totalUnitHeight * 0.1 * max(0, numLines - 1)
		scaleByHeight = availHeight / totalVerticalUnits

		scale = min(scaleByWidth, scaleByHeight)
		lineHeight = totalUnitHeight * scale * 1.1

		# Vertically center all lines
		totalTextHeight = lineHeight * numLines - totalUnitHeight * scale * 0.1
		yStart = margin + (availHeight - totalTextHeight) / 2.0

		NSColor.blackColor().set()

		for lineIdx, lineLayers in enumerate(lines):
			if not lineLayers:
				continue

			# Horizontally center
			lineWidthPx = 0
			for l in lineLayers:
				if isinstance(l, tuple) and l[0] == "incompatible":
					lineWidthPx += l[1] * scale
				else:
					lineWidthPx += l.width * scale
			x = margin + (availWidth - lineWidthPx) / 2.0
			y = yStart + lineIdx * lineHeight + self._ascender * scale

			for layer in lineLayers:
				if isinstance(layer, tuple) and layer[0] == "incompatible":
					# Draw skull emoji for incompatible glyph
					glyphWidth = layer[1]
					emojiSize = totalUnitHeight * scale * 0.5
					attrs = {
						NSFontAttributeName: NSFont.systemFontOfSize_(emojiSize),
					}
					skull = NSAttributedString.alloc().initWithString_attributes_(u"\U0001F480", attrs)
					skullSize = skull.size()
					sx = x + (glyphWidth * scale - skullSize.width) / 2.0
					# Vertically center in the glyph area (flipped coords: y down)
					glyphTop = y - self._ascender * scale
					glyphBottom = y - self._descender * scale
					sy = (glyphTop + glyphBottom) / 2.0 - skullSize.height / 2.0 + emojiSize * 0.15
					skull.drawAtPoint_(NSPoint(sx, sy))
					x += glyphWidth * scale
				else:
					NSGraphicsContext.currentContext().saveGraphicsState()

					transform = NSAffineTransform.transform()
					transform.translateXBy_yBy_(x, y)
					transform.scaleXBy_yBy_(scale, -scale)
					transform.concat()

					bezierPath = layer.completeBezierPath
					if bezierPath:
						bezierPath.fill()

					NSGraphicsContext.currentContext().restoreGraphicsState()

					x += layer.width * scale


class AnimationHelper(NSObject):

	def initWithPalette_index_(self, palette, index):
		self = objc.super(AnimationHelper, self).init()
		if self is None:
			return None
		self._palette = palette
		self._index = index
		return self

	def tick_(self, timer):
		try:
			self._palette._animTick(self._index)
		except Exception:
			timer.invalidate()


class GoldenAxesPalette(PalettePlugin):

	@objc.python_method
	def settings(self):
		self.name = Glyphs.localize({'en': 'Golden Axes'})

		width = 150
		# Start with space for 1 axis row; will be rebuilt dynamically
		initialAxes = 1
		controlsHeight = TOP_PADDING + TOOLBAR_HEIGHT + GAP_AFTER_TOOLBAR + initialAxes * ROW_HEIGHT
		height = controlsHeight + PREVIEW_HEIGHT + BOTTOM_PADDING

		self.paletteView = Window((width, height))
		self.paletteView.group = Group((0, 0, width, height))

		# Toolbar row: pill toggle + color well
		showPref = Glyphs.defaults.get(f"{PREF_KEY}.showPreview", True)
		initialSegment = 0 if showPref else 1
		self.paletteView.group.toggle = SegmentedButton(
			(6, TOP_PADDING, 60, TOOLBAR_HEIGHT),
			[dict(title="On", width=28), dict(title="Off", width=28)],
			callback=self._toggle_preview,
			sizeStyle='mini',
		)
		self.paletteView.group.toggle.set(initialSegment)

		# Color well
		savedColor = self._loadColor()
		nsColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(*savedColor)
		self.paletteView.group.colorWell = ColorWell(
			(72, TOP_PADDING + 2, 28, 18),
			color=nsColor,
			callback=self._color_changed,
		)

		# Speed selector
		savedSpeed = Glyphs.defaults.get(f"{PREF_KEY}.animSpeed", 0)
		self.paletteView.group.speed = SegmentedButton(
			(-72, TOP_PADDING, 68, TOOLBAR_HEIGHT),
			[dict(title=f"{s}x", width=20) for s in SPEED_OPTIONS],
			callback=self._speed_changed,
			sizeStyle='mini',
		)
		self.paletteView.group.speed.set(savedSpeed if savedSpeed is not None else 0)
		self._speedMultiplier = SPEED_OPTIONS[int(savedSpeed) if savedSpeed is not None else 0]

		# Preview area (positioned dynamically in _setupAxes)
		self.paletteView.group.previewWrapper = Group(
			(4, TOP_PADDING + TOOLBAR_HEIGHT + GAP_AFTER_TOOLBAR + ROW_HEIGHT + 4, -4, PREVIEW_HEIGHT)
		)
		wrapperNS = self.paletteView.group.previewWrapper.getNSView()

		self._previewView = GlyphPreviewView.alloc().initWithFrame_(
			NSMakeRect(0, 0, width - 8, PREVIEW_HEIGHT)
		)
		self._previewView.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
		wrapperNS.addSubview_(self._previewView)

		self.dialog = self.paletteView.group.getNSView()
		self._currentAxes = []
		self._axisRows = []  # list of dicts with vanilla widgets per axis
		self._numAxisRows = 0
		self._font = None
		self._animations = {}

	@objc.python_method
	def start(self):
		Glyphs.addCallback(self.update, UPDATEINTERFACE)

	def minHeight(self):
		n = len(self._currentAxes) if self._currentAxes else 1
		return TOP_PADDING + TOOLBAR_HEIGHT + GAP_AFTER_TOOLBAR + n * ROW_HEIGHT + PREVIEW_HEIGHT + BOTTOM_PADDING + 4

	def maxHeight(self):
		n = len(self._currentAxes) if self._currentAxes else 1
		return TOP_PADDING + TOOLBAR_HEIGHT + GAP_AFTER_TOOLBAR + n * ROW_HEIGHT + PREVIEW_HEIGHT + BOTTOM_PADDING + 4

	@objc.python_method
	def update(self, sender):
		font = Glyphs.font
		if not font or len(font.masters) < 2:
			return

		if font != self._font:
			self._stopAllAnimations()
			self._font = font
			self._setupAxes(font)

		self._refreshPreview()

	@objc.python_method
	def _ensureAxisRows(self, count):
		"""Create or remove axis rows so we have exactly `count` rows."""
		# Add rows if needed
		while self._numAxisRows < count:
			i = self._numAxisRows
			sliderTop = TOP_PADDING + TOOLBAR_HEIGHT + GAP_AFTER_TOOLBAR
			y = sliderTop + i * ROW_HEIGHT
			attrSuffix = f'_{i}'

			label = TextBox(
				(6, y + 3, 46, 14),
				"",
				sizeStyle='mini',
			)
			setattr(self.paletteView.group, f'label{attrSuffix}', label)

			btn = SquareButton(
				(52, y + 1, 15, 15),
				u"\u25B6",
				callback=self._play_callback,
				sizeStyle='mini',
			)
			btn._axisIndex = i
			btn._axisId = None
			btn._playing = False
			setattr(self.paletteView.group, f'play{attrSuffix}', btn)

			slider = Slider(
				(70, y + 1, -40, 15),
				minValue=0,
				maxValue=1000,
				value=0,
				callback=self._slider_callback,
				sizeStyle='mini',
			)
			slider._axisIndex = i
			slider._axisId = None
			setattr(self.paletteView.group, f'slider{attrSuffix}', slider)

			tf = EditText(
				(-38, y, -4, 17),
				text="",
				callback=self._textfield_callback,
				sizeStyle='mini',
			)
			tf._axisIndex = i
			tf._axisId = None
			setattr(self.paletteView.group, f'tf{attrSuffix}', tf)

			self._axisRows.append({
				'label': label,
				'btn': btn,
				'slider': slider,
				'tf': tf,
			})
			self._numAxisRows += 1

		# Hide extra rows
		for i in range(count, self._numAxisRows):
			row = self._axisRows[i]
			row['label'].show(False)
			row['btn'].show(False)
			row['slider'].show(False)
			row['tf'].show(False)

	@objc.python_method
	def _setupAxes(self, font):
		self._currentAxes = []
		numAxes = len(font.axes)

		self._ensureAxisRows(numAxes)

		for i in range(numAxes):
			row = self._axisRows[i]
			axis = font.axes[i]
			axisId = axis.axisId if hasattr(axis, 'axisId') else axis.name
			values = [m.axes[i] for m in font.masters]
			minVal = min(values)
			maxVal = max(values)

			savedKey = f"{PREF_KEY}.axis.{axisId}"
			saved = Glyphs.defaults.get(savedKey)
			current = saved if saved is not None else font.masters[0].axes[i]

			row['label'].set(axis.name)
			row['slider'].setMinValue(minVal)
			row['slider'].setMaxValue(maxVal)
			row['slider'].set(current)
			row['slider']._axisId = axisId
			row['tf']._axisId = axisId
			row['tf'].set(str(int(round(current))))
			row['btn']._axisId = axisId
			row['btn']._playing = False
			row['btn'].setTitle(u"\u25B6")

			Glyphs.defaults[savedKey] = current

			self._currentAxes.append({
				'id': axisId,
				'name': axis.name,
				'min': minVal,
				'max': maxVal,
			})

			row['label'].show(True)
			row['slider'].show(True)
			row['tf'].show(True)
			row['btn'].show(True)

		# Reposition preview below axis rows
		sliderTop = TOP_PADDING + TOOLBAR_HEIGHT + GAP_AFTER_TOOLBAR
		previewTop = sliderTop + numAxes * ROW_HEIGHT + 4
		previewWrapper = self.paletteView.group.previewWrapper
		previewWrapper.setPosSize((4, previewTop, -4, PREVIEW_HEIGHT))

	# --- Preview ---

	@objc.python_method
	def _refreshPreview(self):
		font = Glyphs.font
		if not font or not font.currentTab:
			self._previewView.setLayers_upm_ascender_descender_([], 1000, 800, -200)
			return

		showPreview = Glyphs.defaults.get(f"{PREF_KEY}.showPreview", True)
		if not showPreview:
			self._previewView.setLayers_upm_ascender_descender_([], font.upm, font.masters[0].ascender, font.masters[0].descender)
			return

		tabLayers = font.currentTab.layers
		if not tabLayers:
			self._previewView.setLayers_upm_ascender_descender_([], font.upm, font.masters[0].ascender, font.masters[0].descender)
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

		# Get interpolated font once
		from interpolation_engine import InterpolationEngine
		interpFont = InterpolationEngine._get_interpolated_font(font, axis_values)
		if not interpFont:
			self._previewView.setLayers_upm_ascender_descender_([], font.upm, font.masters[0].ascender, font.masters[0].descender)
			return

		interpLayers = []
		for tabLayer in tabLayers:
			# Detect newline (GSControlLayer with newline char)
			if isinstance(tabLayer, GSControlLayer):
				if tabLayer.parent is None or (hasattr(tabLayer, 'name') and tabLayer.name == 'newline'):
					interpLayers.append(None)  # line break marker
				# Check unicode for newline (10 = \n)
				try:
					if tabLayer.parent and tabLayer.parent.unicode == '000A':
						interpLayers.append(None)
				except:
					pass
				continue

			glyph = tabLayer.parent
			if not glyph:
				continue
			if not InterpolationEngine.is_glyph_compatible(glyph):
				interpLayers.append(("incompatible", tabLayer.width))
				continue
			interpGlyph = interpFont.glyphs[glyph.name]
			if interpGlyph and interpGlyph.layers:
				interpLayer = interpGlyph.layers[0]
				bp = interpLayer.completeBezierPath
				if bp and not bp.isEmpty():
					interpLayers.append(interpLayer)
				else:
					interpLayers.append(("incompatible", tabLayer.width))
			else:
				interpLayers.append(("incompatible", tabLayer.width))

		self._previewView.setLayers_upm_ascender_descender_(
			interpLayers, font.upm,
			font.masters[0].ascender, font.masters[0].descender
		)

	# --- Show/Hide Preview + Color ---

	@objc.python_method
	def _toggle_preview(self, sender):
		segment = sender.get()
		isOn = (segment == 0)
		Glyphs.defaults[f"{PREF_KEY}.showPreview"] = isOn
		if not isOn:
			self._stopAllAnimations()
		self._triggerRedraw()

	@objc.python_method
	def _color_changed(self, sender):
		nsColor = sender.get()
		nsColor = nsColor.colorUsingColorSpaceName_(NSCalibratedRGBColorSpace)
		if nsColor:
			r = nsColor.redComponent()
			g = nsColor.greenComponent()
			b = nsColor.blueComponent()
			a = nsColor.alphaComponent()
			Glyphs.defaults[f"{PREF_KEY}.color.r"] = r
			Glyphs.defaults[f"{PREF_KEY}.color.g"] = g
			Glyphs.defaults[f"{PREF_KEY}.color.b"] = b
			Glyphs.defaults[f"{PREF_KEY}.color.a"] = a
			self._triggerRedraw()

	@objc.python_method
	def _loadColor(self):
		r = Glyphs.defaults.get(f"{PREF_KEY}.color.r")
		if r is not None:
			return (
				float(Glyphs.defaults.get(f"{PREF_KEY}.color.r", DEFAULT_COLOR[0])),
				float(Glyphs.defaults.get(f"{PREF_KEY}.color.g", DEFAULT_COLOR[1])),
				float(Glyphs.defaults.get(f"{PREF_KEY}.color.b", DEFAULT_COLOR[2])),
				float(Glyphs.defaults.get(f"{PREF_KEY}.color.a", DEFAULT_COLOR[3])),
			)
		return DEFAULT_COLOR

	@objc.python_method
	def _speed_changed(self, sender):
		idx = sender.get()
		self._speedMultiplier = SPEED_OPTIONS[idx]
		Glyphs.defaults[f"{PREF_KEY}.animSpeed"] = idx
		for animIdx, anim in self._animations.items():
			row = self._axisRows[animIdx]
			minVal = row['slider'].getNSSlider().minValue()
			maxVal = row['slider'].getNSSlider().maxValue()
			axisRange = maxVal - minVal
			anim['step'] = (axisRange / (ANIM_DURATION * ANIM_FPS)) * self._speedMultiplier

	# --- Slider / TextField ---

	@objc.python_method
	def _slider_callback(self, sender):
		axisId = sender._axisId
		if not axisId:
			return
		value = sender.get()
		idx = sender._axisIndex

		if idx in self._animations:
			self._stopAnimation(idx)

		row = self._axisRows[idx]
		row['tf'].set(str(int(round(value))))
		Glyphs.defaults[f"{PREF_KEY}.axis.{axisId}"] = value
		self._triggerRedraw()

	@objc.python_method
	def _textfield_callback(self, sender):
		axisId = sender._axisId
		if not axisId:
			return
		try:
			value = float(sender.get())
		except (ValueError, TypeError):
			return

		idx = sender._axisIndex

		if idx in self._animations:
			self._stopAnimation(idx)

		row = self._axisRows[idx]
		row['slider'].set(value)
		Glyphs.defaults[f"{PREF_KEY}.axis.{axisId}"] = value
		self._triggerRedraw()

	# --- Play / Pause ---

	@objc.python_method
	def _play_callback(self, sender):
		idx = sender._axisIndex
		if sender._playing:
			self._stopAnimation(idx)
		else:
			if not Glyphs.defaults.get(f"{PREF_KEY}.showPreview", True):
				Glyphs.defaults[f"{PREF_KEY}.showPreview"] = True
				self.paletteView.group.toggle.set(0)
			self._startAnimation(idx)

	@objc.python_method
	def _startAnimation(self, idx):
		row = self._axisRows[idx]
		btn = row['btn']
		slider = row['slider']

		btn._playing = True
		btn.setTitle(u"\u275A\u275A")

		minVal = slider.getNSSlider().minValue()
		maxVal = slider.getNSSlider().maxValue()
		axisRange = maxVal - minVal
		if axisRange == 0:
			return

		step = (axisRange / (ANIM_DURATION * ANIM_FPS)) * self._speedMultiplier

		current = slider.get()
		direction = 1 if current <= (minVal + maxVal) / 2.0 else -1

		self._animations[idx] = {
			'timer': None,
			'direction': direction,
			'step': step,
		}

		helper = AnimationHelper.alloc().initWithPalette_index_(self, idx)
		timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
			1.0 / ANIM_FPS,
			helper,
			b'tick:',
			None,
			True,
		)
		self._animations[idx]['timer'] = timer
		self._animations[idx]['helper'] = helper

	@objc.python_method
	def _stopAnimation(self, idx):
		row = self._axisRows[idx]
		row['btn']._playing = False
		row['btn'].setTitle(u"\u25B6")

		anim = self._animations.pop(idx, None)
		if anim and anim['timer']:
			anim['timer'].invalidate()

	@objc.python_method
	def _stopAllAnimations(self):
		for idx in list(self._animations.keys()):
			self._stopAnimation(idx)

	@objc.python_method
	def _animTick(self, idx):
		anim = self._animations.get(idx)
		if not anim:
			return

		direction = anim['direction']
		step = anim['step']

		row = self._axisRows[idx]
		slider = row['slider']
		tf = row['tf']
		axisId = slider._axisId

		minVal = slider.getNSSlider().minValue()
		maxVal = slider.getNSSlider().maxValue()

		current = slider.get() + step * direction

		if current >= maxVal:
			current = maxVal
			anim['direction'] = -1
		elif current <= minVal:
			current = minVal
			anim['direction'] = 1

		slider.set(current)
		tf.set(str(int(round(current))))
		Glyphs.defaults[f"{PREF_KEY}.axis.{axisId}"] = current

		self._refreshPreview()

		NSNotificationCenter.defaultCenter().postNotificationName_object_(
			NOTIFICATION_NAME, None
		)
		if Glyphs.font and Glyphs.font.currentTab:
			Glyphs.font.currentTab.redraw()

	# --- Misc ---

	@objc.python_method
	def _triggerRedraw(self):
		self._refreshPreview()
		NSNotificationCenter.defaultCenter().postNotificationName_object_(
			NOTIFICATION_NAME, None
		)
		if Glyphs.font and Glyphs.font.currentTab:
			Glyphs.font.currentTab.redraw()

	@objc.python_method
	def __del__(self):
		self._stopAllAnimations()
		Glyphs.removeCallback(self.update)

	@objc.python_method
	def __file__(self):
		return __file__
