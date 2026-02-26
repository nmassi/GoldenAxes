# Golden Axes

![Golden Axes](assets/GoldenAxes.png)

Live interpolation preview for GlyphsApp. Explore your variable font's design space in real time &mdash; scrub through axes, animate, and preview text without exporting.

---

## Installation

## Getting Started

1. Open a font with **2 or more masters**
2. Activate the reporter: **View > Golden Axes**
3. Open the palette from the right sidebar

---

## Palette

The Golden Axes palette sits in the right sidebar with three sections:

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

### Inline Preview

A live text preview below the sliders. It renders whatever you have typed in the current Edit View tab at the selected axis values.

- Text scales automatically to fit the preview area
- Centered horizontally and vertically
- Line breaks from the Edit View are preserved
- Uses the font's real ascender and descender values

---

## Edit View Overlay

When editing a glyph, Golden Axes draws a colored interpolation overlay on top of the current master outline. This lets you compare the interpolated result against the master you are working on.

- Color is set from the palette's color well
- Overlay turns gray when extrapolating beyond the master range

---

## Right-Click Menu

Right-click in the Edit View to open the **Golden Axes** submenu:

| Option                         | Description                                                                              |
| ------------------------------ | ---------------------------------------------------------------------------------------- |
| **Center Preview**             | Center the overlay when its width differs from the current master                        |
| **Show Nodes**                 | Display on-curve nodes of the interpolated outline                                       |
| **Make Instance from Current** | Add a new instance to Font Info at the current axis position                             |
| **Make Master from Current**   | Add a new master at the current axis position with interpolated outlines for every glyph |

---

## Requirements

- GlyphsApp 3 (build 3062+)
- A font with 2 or more masters

MIT — [nico.works](https://nico.works)
