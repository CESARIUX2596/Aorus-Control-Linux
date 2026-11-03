# Themes and palette inspiration

Lumen 1.1 includes **30 presets**, triple the original ten. Colors are embedded
locally; the app does not fetch palettes, fonts, or theme assets at runtime.
All presets have distinct device output. Patterns describe real per-key RGB
data, not just different thumbnail art.

## Gaming: contrast by key role

Gaming backgrounds are scaled independently of the main brightness. For FPS
patterns, WASD and arrow keys use the movement color at full intensity; nearby
action keys, number keys, Shift, Ctrl, Space, and Esc use a separate color at
55%. Other keys, including the function row, use the base color multiplied by
**Background glow**, initially 0–8% depending on the preset. A value of 0%
switches those background keys off. These are RGB scaling values, not measured
photometric brightness ratios.

| Theme | Layout |
| --- | --- |
| Night runner | Mint movement, pink actions, faint navy background |
| Toxic bloom | Lime movement, magenta actions, faint green background |
| FPS tactical | Amber movement, cyan actions, faint blue background |
| Spellbook | Magenta QWER spells; cyan D/F and number keys; faint purple background |
| Redline | Red movement, white actions, faint red background |
| Stealth ops | White movement, blue actions, unlit background |

Existing saved `wasd` profiles gain the new dim-background behavior with an 8%
default if they do not yet have that field. Their chosen colors, painted keys,
brightness, and other settings are retained. Custom per-key paint overrides
the pattern intentionally, including on background keys.

## Palette-inspired designs

These are original keyboard arrangements inspired by the named palettes;
they are not official ports or endorsements. No source code, artwork, fonts,
or logos from the palette projects are bundled.

| Lumen theme | Selected colors | Primary palette reference |
| --- | --- | --- |
| Dracula | Purple `#bd93f9`, pink `#ff79c6`, green `#50fa7b`; horizontal bands | [Dracula Classic specification](https://draculatheme.com/spec) |
| Catppuccin | Mocha lavender `#b4befe`, mauve `#cba6f7`, peach `#fab387`; gradient | [Catppuccin palette](https://catppuccin.com/palette/) |
| Tokyo night | Storm blue `#7aa2f7`, magenta `#bb9af7`, cyan `#7dcfff`; zones | [Tokyo Night Storm palette](https://github.com/folke/tokyonight.nvim/blob/main/lua/tokyonight/colors/storm.lua) |
| Nord frost | `#5e81ac`, `#88c0d0`, `#8fbcbb`; gradient | [Nord colors and palettes](https://www.nordtheme.com/docs/colors-and-palettes/) |
| Solarized | Cyan `#2aa198`, yellow `#b58900`, blue `#268bd2`; zones | [Ethan Schoonover's Solarized](https://ethanschoonover.com/solarized/) |
| Gruvbox | Yellow `#fabd2f`, orange `#fe8019`, green `#b8bb26`; bands | [Gruvbox palette definitions](https://github.com/morhetz/gruvbox/blob/master/colors/gruvbox.vim) |
| Rosé pine | Rose `#ebbcba`, iris `#c4a7e7`, foam `#9ccfd8`; bands | [Rosé Pine palette](https://rosepinetheme.com/palette/), [reference definitions](https://github.com/rose-pine/neovim/blob/main/lua/rose-pine/palette.lua) |

Palette references were checked on November 3, 2026. The translation to LED
layouts is Lumen's own design. Screens and physical keyboard LEDs have
different color responses, so a palette's appearance will vary on hardware.

## Other designs

- **Gradients:** Aurora, Synthwave, Golden hour, Glacier, Ember, Ocean current.
- **Patterns:** Cyberpunk and Miami vice zones; Sakura and Pixel arcade
  checker keys; Lava flow and Zen garden bands; Digital rain static scattered
  lights; Prism spectrum.
- **Minimal:** Soft focus warm white.
- **Animated:** Deep breath and Color drift, running in the keyboard firmware.

Digital rain is a static per-key texture, not a software-driven animation.
Animated previews are illustrative. Static/custom theme cards and profile
thumbnails use the backend's exact rendered colors and key positions, including
paint overrides and background dimming. Dark main-preview key legends stay
readable in neutral gray while their glow still represents the actual RGB.
