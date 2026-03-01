# encoding: utf-8
from GlyphsApp import *
from GlyphsApp.plugins import *
from vanilla import *
from AppKit import *
from Foundation import *
import objc

from interpolation_engine import InterpolationEngine

PREF_KEY = "com.goldenaxes.GoldenAxes"
NOTIFICATION_NAME = "com.goldenaxes.GoldenAxes.valuesChanged"

ROW_HEIGHT = 22
TOOLBAR_HEIGHT = 22
TOP_PADDING = 10
BOTTOM_PADDING = 4
GAP_AFTER_TOOLBAR = 8

# Default preview color: blue with 40% opacity
DEFAULT_COLOR = (0.0, 0.5, 1.0, 0.4)

ANIM_FPS = 30.0
ANIM_DURATION = 2.0  # base duration at 1x
SPEED_OPTIONS = [1, 2, 3]

PREVIEW_INSTANCE_NAME = "Golden Axes"


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
		initialAxes = 1
		height = TOP_PADDING + TOOLBAR_HEIGHT + GAP_AFTER_TOOLBAR + initialAxes * ROW_HEIGHT + BOTTOM_PADDING

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

		self.dialog = self.paletteView.group.getNSView()
		self._currentAxes = []
		self._axisRows = []
		self._numAxisRows = 0
		self._font = None
		self._animations = {}

	@objc.python_method
	def start(self):
		Glyphs.addCallback(self.update, UPDATEINTERFACE)

	def minHeight(self):
		n = len(self._currentAxes) if self._currentAxes else 1
		return TOP_PADDING + TOOLBAR_HEIGHT + GAP_AFTER_TOOLBAR + n * ROW_HEIGHT + BOTTOM_PADDING

	def maxHeight(self):
		return self.minHeight()

	@objc.python_method
	def update(self, sender):
		font = Glyphs.font
		if not font or len(font.masters) < 2:
			return

		if font != self._font:
			self._stopAllAnimations()
			self._font = font
			self._setupAxes(font)

	@objc.python_method
	def _ensureAxisRows(self, count):
		"""Create or remove axis rows so we have exactly `count` rows."""
		while self._numAxisRows < count:
			i = self._numAxisRows
			sliderTop = TOP_PADDING + TOOLBAR_HEIGHT + GAP_AFTER_TOOLBAR
			y = sliderTop + i * ROW_HEIGHT
			attrSuffix = f'_{i}'

			label = TextBox(
				(6, y + 2, 46, 16),
				"",
				sizeStyle='small',
			)
			setattr(self.paletteView.group, f'label{attrSuffix}', label)

			btn = Button(
				(52, y - 2, 20, TOOLBAR_HEIGHT),
				u"\u25B6",
				callback=self._play_callback,
				sizeStyle='small',
			)
			btn._axisIndex = i
			btn._axisId = None
			btn._playing = False
			setattr(self.paletteView.group, f'play{attrSuffix}', btn)

			slider = Slider(
				(76, y + 1, -46, 15),
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
				(-38, y, -4, 19),
				text="",
				callback=self._textfield_callback,
				sizeStyle='small',
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

		# Update the Auto Layout height constraint on the dialog view
		self._updateSidebarHeight()

		self._updatePreviewInstance()

	# --- Show/Hide + Color ---

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

		NSNotificationCenter.defaultCenter().postNotificationName_object_(
			NOTIFICATION_NAME, None
		)
		self._updatePreviewInstance()
		if Glyphs.font and Glyphs.font.currentTab:
			Glyphs.font.currentTab.redraw()

	# --- Sidebar Height ---

	@objc.python_method
	def _updateSidebarHeight(self):
		newHeight = self.minHeight()
		dialogView = self.dialog
		parent = dialogView.superview()
		if not parent:
			return
		for c in parent.constraints():
			if c.firstItem() == dialogView and 'height' in str(c).lower():
				c.setConstant_(newHeight)
				parent.layoutSubtreeIfNeeded()
				return

	# --- Preview Instance Management ---

	@objc.python_method
	def _findPreviewInstance(self, font):
		for inst in font.instances:
			if inst.name == PREVIEW_INSTANCE_NAME:
				return inst
		return None

	@objc.python_method
	def _updatePreviewInstance(self):
		font = Glyphs.font
		if not font or len(font.masters) < 2:
			return

		inst = self._findPreviewInstance(font)
		if inst is None:
			inst = GSInstance()
			inst.name = PREVIEW_INSTANCE_NAME
			font.instances.append(inst)

		for i, axis in enumerate(font.axes):
			axisId = axis.axisId if hasattr(axis, 'axisId') else axis.name
			saved = Glyphs.defaults.get(f"{PREF_KEY}.axis.{axisId}")
			if saved is not None:
				inst.axes[i] = float(saved)
			else:
				inst.axes[i] = font.masters[0].axes[i]

		# Select instance or "live" mode depending on glyph compatibility
		tab = font.currentTab
		if tab:
			try:
				layer = tab.layers[tab.layersCursor]
				glyph = layer.parent if layer else None
				if glyph and not InterpolationEngine.is_glyph_compatible(glyph):
					tab.previewInstances = "live"
				else:
					tab.previewInstances = inst
			except Exception:
				tab.previewInstances = inst

	@objc.python_method
	def _removePreviewInstance(self):
		font = Glyphs.font
		if not font:
			return
		inst = self._findPreviewInstance(font)
		if inst:
			font.instances.remove(inst)

	# --- Misc ---

	@objc.python_method
	def _triggerRedraw(self):
		NSNotificationCenter.defaultCenter().postNotificationName_object_(
			NOTIFICATION_NAME, None
		)
		self._updatePreviewInstance()
		if Glyphs.font and Glyphs.font.currentTab:
			Glyphs.font.currentTab.redraw()

	@objc.python_method
	def __del__(self):
		self._stopAllAnimations()
		self._removePreviewInstance()
		Glyphs.removeCallback(self.update)

	@objc.python_method
	def __file__(self):
		return __file__
