# encoding: utf-8
from GlyphsApp import *
from AppKit import *


class InterpolationEngine:
	"""Interpolation engine that generates interpolated layers for arbitrary axis values."""

	_cache_axis_key = None
	_cache_font = None

	@staticmethod
	def get_axes_info(font):
		"""Return info for all font axes.
		Returns: [{'id', 'name', 'tag', 'min', 'max', 'default', 'masterValues'}, ...]
		"""
		axes_info = []
		for axis in font.axes:
			idx = list(font.axes).index(axis)
			values = [m.axes[idx] for m in font.masters]
			axes_info.append({
				'id': axis.axisId if hasattr(axis, 'axisId') else axis.name,
				'name': axis.name,
				'tag': axis.axisTag,
				'min': min(values),
				'max': max(values),
				'default': values[0],
				'masterValues': values,
			})
		return axes_info

	@staticmethod
	def _get_interpolated_font(font, axis_values):
		"""Get or create cached interpolated font for given axis values."""
		axis_key = tuple(sorted(axis_values.items()))
		if axis_key == InterpolationEngine._cache_axis_key and InterpolationEngine._cache_font:
			return InterpolationEngine._cache_font

		try:
			tempInstance = GSInstance()
			tempInstance.font = font

			for i, axis in enumerate(font.axes):
				axis_id = axis.axisId if hasattr(axis, 'axisId') else axis.name
				if axis_id in axis_values:
					tempInstance.axes[i] = axis_values[axis_id]
				else:
					tempInstance.axes[i] = font.masters[0].axes[i]

			tempInstance.updateInterpolationValues()

			interpolatedFont = tempInstance.interpolatedFont
			if interpolatedFont:
				InterpolationEngine._cache_axis_key = axis_key
				InterpolationEngine._cache_font = interpolatedFont
				return interpolatedFont

		except Exception as e:
			print(f"GoldenAxes Error: {e}")
			import traceback
			traceback.print_exc()

		return None

	@staticmethod
	def interpolate_layer(font, glyph, axis_values):
		"""Interpolate a glyph at arbitrary design-space coordinates.
		Returns an interpolated GSLayer or None.
		"""
		interpolatedFont = InterpolationEngine._get_interpolated_font(font, axis_values)
		if not interpolatedFont:
			return None

		interpGlyph = interpolatedFont.glyphs[glyph.name]
		if interpGlyph and interpGlyph.layers:
			return interpGlyph.layers[0]

		return None

	@staticmethod
	def calculate_master_involvement(font, axis_values):
		"""Calculate the involvement percentage of each master.
		Returns dict {masterId: coefficient} where coefficient is 0.0-1.0.
		"""
		try:
			tempInstance = GSInstance()
			tempInstance.font = font

			for i, axis in enumerate(font.axes):
				axis_id = axis.axisId if hasattr(axis, 'axisId') else axis.name
				if axis_id in axis_values:
					tempInstance.axes[i] = axis_values[axis_id]
				else:
					tempInstance.axes[i] = font.masters[0].axes[i]

			tempInstance.updateInterpolationValues()
			return dict(tempInstance.instanceInterpolations)
		except Exception as e:
			print(f"GoldenAxes MasterInvolvement Error: {e}")
			return {}

	@staticmethod
	def is_extrapolating(font, axis_values):
		"""Detect if any axis value is outside the master range."""
		for i, axis in enumerate(font.axes):
			axis_id = axis.axisId if hasattr(axis, 'axisId') else axis.name
			if axis_id in axis_values:
				values = [m.axes[i] for m in font.masters]
				if axis_values[axis_id] < min(values) or axis_values[axis_id] > max(values):
					return True
		return False

	@staticmethod
	def invalidate_cache():
		"""Clear the interpolation cache."""
		InterpolationEngine._cache_axis_key = None
		InterpolationEngine._cache_font = None
