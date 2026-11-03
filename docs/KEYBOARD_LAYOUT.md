# AORUS 15P YD US/ANSI keyboard layout

The reference machine identifies itself through DMI as **AORUS 15P YD**, SKU
**X5LYD**, and exposes Fusion keyboard USB ID **1044:7a3f**. The owner confirmed
a wide horizontal **US/ANSI Enter** key and supplied a front-facing keyboard
image. The physical preview was compared with that image and the official
[AORUS 15P Intel 11th Gen family](https://www.gigabyte.com/Laptop/AORUS-15P--Intel-11th-Gen)
and [Gigabyte keyboard-deck image](https://static.gigabyte.com/StaticFile/Image/Global/b80409615c44a2d8aa0f77321884e694/Product/28107).
The supplied image is used for validation and is not redistributed here.

Physical geometry and LED addressing are separate data. The device descriptor
does not specify the shape, size, or placement of the keys. The LED slots were
checked against the original Windows FusionKeyboard module; the drawing was
then corrected independently against the physical reference.

## Confirmed arrangement

- **101 displayed keys**, with no duplicated keys or invented placements.
- The short top row has **19 keys**: Esc, F1–F12, Pause, Delete, Home, Page Up,
  Page Down, End. Navigation keys are above the numpad, not in its right column.
- The next row ends with Num Lock, `/`, `*`, and `−`.
- Numpad **`+` spans the 7/8/9 and 4/5/6 rows**.
- Numpad **Enter spans the 1/2/3 and bottom rows**.
- Main Enter is horizontal and 2.25 key units wide.
- Up is directly above Down. The bottom Right arrow sits below numpad 1.
- Numpad **0 is single-width**, underneath numpad 2, followed by decimal/delete.
- The bottom-left sequence is Ctrl, Fn, Windows, Alt; the spacebar is followed
  by right Alt, menu, right Ctrl, then the three arrow keys.

The preview uses one 19-unit-wide CSS grid, with quarter-key coordinates and
real row spans. Rows cannot independently stretch or shift the numpad. Its
main keys are approximately square and the function row is shorter. The exact
same geometry is used for theme and saved-profile thumbnails.

Tests check the top-row sequence, key count, widths, row spans, arrow
alignment, and complete grid occupancy without overlaps. Browser checks verify
the rendered `+` span and Up/Down alignment. The physical-unit dimensions are
a proportional reconstruction from the reference image, not a mechanical CAD
measurement. ISO/Japanese layouts still need their own geometry and mapping.
