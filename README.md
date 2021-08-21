# RotMG-Sprite-Renderer

A replacement for Tuvior's Tool

# Features

- Loading sprite sheet and mask sheet
- Previewing both sheets and rendering
- Seek feature that allows you to scroll through larger sheets along with manual hex input
- Custom width and height
- Mask and shadow toggles
- Scale adjustment (1 = each pixel is 1x1, 2 = 2x2, 3 = 3x3, etc)
- GIF speed adjustment
- Animation length adjustment (mainly for taking animations from a larger sheet)
- Custom background color for GIF, default is set to discord's bg color
- Clothing and accessory mask options, can select a custom color, select from a list of cloths, or upload your own cloth
- Modes, various modes, described below
- Ability to render the entire sheet
- Save as a PNG or a GIF
- GIFs are previewed before saving
- Images that would extend beyond the window are instead displayed in a separate window

# Modes
All renders have a 1-pixel solid black outline
All modes support masks

- Image Mode
  - Renders the selection as an image
- Pet or Enemy Mode
  - Creates a GIF of 1 row of a properly formatted animation (https://cdn.discordapp.com/attachments/872906948717195264/873640825492496404/QUFc2BtMCO4CppgsHA2r7bjN62jd_RgZ3-1Ow3HV24Jckgtht9ARvK7YbIFFD7Zr0CgbeRqEXMJhV-37sSntmVz0t990pR-FxWeI.png)
- Player Skin Mode
  - Same as Pet or Enemy Mode, but for 3 rows
- Animation Mode
  - Creates a GIF that scrolls through each frame, starting at the index
  - The length of the animation can be specified with the animation length entry. If it is 0 the animation plays until it reaches the end of the sheet.
- Full Overview
  - Renders the first image of each row and arranges them in a 6-column display
- Quick Overview
  - Same as Full Overview, except only renders every 4th row (for sheets of skins)
