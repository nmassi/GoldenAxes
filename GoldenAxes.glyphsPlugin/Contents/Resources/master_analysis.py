# encoding: utf-8
from AppKit import *
from Foundation import *


MASTER_COLORS = [
	(1.0, 0.2, 0.2, 0.7),   # Red
	(0.2, 0.6, 1.0, 0.7),   # Blue
	(0.2, 0.8, 0.3, 0.7),   # Green
	(1.0, 0.7, 0.1, 0.7),   # Yellow
	(0.8, 0.3, 0.8, 0.7),   # Purple
	(1.0, 0.5, 0.2, 0.7),   # Orange
	(0.4, 0.8, 0.8, 0.7),   # Cyan
	(0.7, 0.5, 0.3, 0.7),   # Brown
]


def get_master_color(index):
	"""Return RGBA tuple for a master by index."""
	return MASTER_COLORS[index % len(MASTER_COLORS)]


def draw_involvement_bars(font, involvements, origin_x, origin_y, total_width, scale):
	"""Draw horizontal bars showing master involvement percentages.

	Args:
		font: GSFont
		involvements: dict {masterId: coefficient}
		origin_x, origin_y: position in view coordinates
		total_width: max bar width
		scale: current view scale
	"""
	if not involvements:
		return

	barHeight = 14.0 / scale
	padding = 3.0 / scale
	fontSize = 10.0 / scale
	y = origin_y

	for i, master in enumerate(font.masters):
		coeff = involvements.get(master.id, 0)
		if coeff <= 0.001:
			continue

		color = get_master_color(i)
		r, g, b, a = color

		# Draw bar background (subtle)
		bgRect = NSMakeRect(origin_x, y, total_width, barHeight)
		NSColor.colorWithCalibratedRed_green_blue_alpha_(0.85, 0.85, 0.85, 0.3).set()
		NSBezierPath.fillRect_(bgRect)

		# Draw filled portion
		barRect = NSMakeRect(origin_x, y, total_width * coeff, barHeight)
		NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a).set()
		NSBezierPath.fillRect_(barRect)

		# Draw label
		label = f"{master.name}: {round(coeff * 100)}%"
		attrs = {
			NSFontAttributeName: NSFont.systemFontOfSize_(fontSize),
			NSForegroundColorAttributeName: NSColor.colorWithCalibratedRed_green_blue_alpha_(0.1, 0.1, 0.1, 0.9),
		}
		nsStr = NSAttributedString.alloc().initWithString_attributes_(label, attrs)
		nsStr.drawAtPoint_(NSMakePoint(origin_x + 4.0 / scale, y + 1.0 / scale))

		y += barHeight + padding
