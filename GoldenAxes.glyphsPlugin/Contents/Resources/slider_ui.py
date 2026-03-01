# encoding: utf-8
from vanilla import *
from GlyphsApp import *
from AppKit import *
import objc
from interpolation_engine import InterpolationEngine


class SliderPanel:
	"""Floating panel with sliders for each font axis."""

	def __init__(self, plugin, font):
		self.plugin = plugin
		self.font = font
		self.sliders = {}
		self.textFields = {}
		self._throttle_timer = None
		self._build_ui(font)

	def _build_ui(self, font):
		axes = InterpolationEngine.get_axes_info(font)
		if not axes:
			return

		rowHeight = 30
		topPadding = 10
		bottomPadding = 10
		height = topPadding + len(axes) * rowHeight + bottomPadding

		self.window = FloatingWindow(
			(320, height),
			"Interpolation Preview",
			minSize=(250, height),
			maxSize=(600, height),
			autosaveName="com.goldenaxes.GoldenAxes.sliders",
			closable=True,
		)
		self.window.bind("close", self._window_closed)

		y = topPadding
		for i, axis in enumerate(axes):
			axisId = axis['id']

			# Axis name label
			label = TextBox(
				(10, y + 2, 60, 17),
				axis['name'],
				sizeStyle='small',
			)
			setattr(self.window, f'label_{i}', label)

			# Slider
			slider = Slider(
				(75, y, -70, 17),
				minValue=axis['min'],
				maxValue=axis['max'],
				value=axis['default'],
				callback=self._slider_callback,
				sizeStyle='small',
			)
			slider._axisId = axisId
			slider._axisIndex = i
			setattr(self.window, f'slider_{i}', slider)
			self.sliders[axisId] = slider

			# Numeric text field
			tf = EditText(
				(-60, y, -10, 19),
				text=str(int(round(axis['default']))),
				callback=self._textfield_callback,
				sizeStyle='small',
			)
			tf._axisId = axisId
			tf._axisIndex = i
			setattr(self.window, f'tf_{i}', tf)
			self.textFields[axisId] = tf

			y += rowHeight

		self.window.open()

	def _slider_callback(self, sender):
		axisId = sender._axisId
		value = sender.get()
		self.textFields[axisId].set(str(int(round(value))))
		self.plugin._axisValues[axisId] = value
		self._throttled_redraw()

	def _textfield_callback(self, sender):
		axisId = sender._axisId
		try:
			value = float(sender.get())
			self.sliders[axisId].set(value)
			self.plugin._axisValues[axisId] = value
			self._throttled_redraw()
		except (ValueError, TypeError):
			pass

	def _throttled_redraw(self):
		"""Throttle redraws to avoid excessive interpolation calls."""
		if self._throttle_timer:
			self._throttle_timer.invalidate()
		InterpolationEngine.invalidate_cache()
		self._throttle_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
			0.016,  # ~60fps
			self.plugin,
			objc.selector(self.plugin._timerRedraw_, signature=b'v@:@'),
			None,
			False,
		)

	def get_values(self):
		"""Return current axis values as dict."""
		return {aid: s.get() for aid, s in self.sliders.items()}

	def set_values(self, values_dict):
		"""Set slider and text field values from dict."""
		for aid, val in values_dict.items():
			if aid in self.sliders:
				self.sliders[aid].set(val)
				self.textFields[aid].set(str(int(round(val))))

	def _window_closed(self, sender):
		"""Called when user closes the window manually."""
		self.plugin._sliderPanel = None
		self.plugin._lastFontId = None

	def close(self):
		"""Close the panel programmatically."""
		if hasattr(self, 'window') and self.window:
			self.window.unbind("close", self._window_closed)
			self.window.close()
