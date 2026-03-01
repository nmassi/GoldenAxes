# Golden Axes

Live interpolation preview for GlyphsApp. Explore your variable font's design space in real time &mdash; scrub through axes, animate, and preview text without exporting.

## Installation

1. Download or clone this repository
2. Double-click **GoldenAxes.glyphsPlugin** to install (includes both reporter and palette)
3. Restart GlyphsApp

## Getting Started

1. Open a font with **2 or more masters**
2. Activate the reporter: **View > Golden Axes**
3. Open the palette from the right sidebar

---

## Palette

The Golden Axes palette sits in the right sidebar with controls and axis sliders.

### Controls

- **On / Off** &mdash; toggle the interpolation preview
- **Color well** &mdash; choose the overlay color used in Edit View
- **1x / 2x / 3x** &mdash; animation speed multiplier

### Axis Sliders

One row per axis defined in your font &mdash; no limit on the number of axes. Each row includes:

- **Axis name**
- **Play / Pause** &mdash; animates between the axis minimum and maximum
- **Slider** &mdash; drag to scrub through the design space
- **Value field** &mdash; type an exact number

Multiple axes can animate simultaneously.

### Preview Bar

The bottom preview bar shows the interpolated text at the current axis values. Golden Axes manages a hidden instance that keeps the preview in sync with the sliders. Incompatible glyphs fall back to "live" mode and are highlighted with a red background.

---

## Edit View Overlay

When editing a glyph, Golden Axes draws a colored interpolation overlay on top of the current master outline. This lets you compare the interpolated result against the master you are working on.

- Color is set from the palette's color well
- Overlay turns gray when extrapolating beyond the master range
- Incompatible glyphs display a skull emoji centered in the glyph area

---

## Right-Click Menu

Right-click in the Edit View to open the **Golden Axes** submenu:

| Option                         | Description                                                                              |
| ------------------------------ | ---------------------------------------------------------------------------------------- |
| **Show Edit Overlay**          | Toggle the colored interpolation overlay in Edit View                                    |
| **Center Preview**             | Center the overlay when its width differs from the current master                        |
| **Show Nodes**                 | Display on-curve nodes of the interpolated outline                                       |
| **Make Instance from Current** | Add a new instance to Font Info at the current axis position                             |
| **Make Master from Current**   | Add a new master at the current axis position with interpolated outlines for every glyph |

*Center Preview* and *Show Nodes* are disabled when the edit overlay is off.

---

## Requirements

- GlyphsApp 3 (build 3062+)
- A font with 2 or more masters

MIT — [nico.works](https://nico.works)
