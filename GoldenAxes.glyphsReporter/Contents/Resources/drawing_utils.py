# encoding: utf-8
from GlyphsApp import *
from AppKit import *
from Foundation import *


# Preview colors
PREVIEW_COLOR = (0.0, 0.5, 1.0, 0.4)       # Blue semi-transparent
EXTRAPOLATION_COLOR = (0.5, 0.5, 0.5, 0.3)  # Gray semi-transparent
NODE_COLOR = (0.0, 0.4, 0.9, 0.6)           # Blue for nodes
NODE_RADIUS = 6.0


def make_color(r, g, b, a):
	"""Create and return an NSColor."""
	return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)


def draw_filled_path(bezierPath, color_tuple):
	"""Fill a bezier path with the given RGBA color."""
	make_color(*color_tuple).set()
	bezierPath.fill()


def draw_stroked_path(bezierPath, color_tuple, lineWidth=1.0):
	"""Stroke a bezier path with the given RGBA color and line width."""
	make_color(*color_tuple).set()
	bezierPath.setLineWidth_(lineWidth)
	bezierPath.stroke()


def draw_node(x, y, radius, scale, color_tuple=NODE_COLOR):
	"""Draw a small circle at (x, y) representing a node."""
	r = radius / scale
	rect = NSMakeRect(x - r, y - r, r * 2, r * 2)
	path = NSBezierPath.bezierPathWithOvalInRect_(rect)
	make_color(*color_tuple).set()
	path.fill()


def draw_nodes_for_layer(layer, scale, color_tuple=NODE_COLOR):
	"""Draw all on-curve nodes of a layer."""
	for path in layer.paths:
		for node in path.nodes:
			if node.type != OFFCURVE:
				draw_node(node.x, node.y, NODE_RADIUS, scale, color_tuple)


def draw_rect_filled(rect, color_tuple):
	"""Fill a rectangle with the given color."""
	make_color(*color_tuple).set()
	NSBezierPath.fillRect_(rect)
