# RotMG-Sprite-Renderer
A replacement for Tuvior's Tool

# Tutorial
https://imgur.com/a/0LIZ5kd

# Features
- Previewing both sheets and rendering
- Seek feature that allows you to scroll through larger sheets along with manual hex input
- Mask, bg, and shadow toggles
- Custom background color, default is set to discord's bg color
- Clothing and accessory mask options, can select a custom color, select from a list of cloths, or upload your own cloth
- GIFs are previewed before saving
- Dynamic GIF length
- Images that would extend beyond the window are instead displayed in a separate window
- Copying Image to clipboard
- Pasting Image from clipboard as the main or mask sheet (due to clipboard limitations, not all images work, images from Chrome and PAINT.net will work, from discord will not)
- Transparent Background for GIFs (without shadows)
- "Subscribe" Feature that allows changes you make to a file to automatically be rendered
- Shortcuts for opening sheets, rendering, closing sheets, copying, and pasting
   - Control + O prompts you to open a sheet
   - Control + M prompts you to open a mask sheet
   - Control + R renders the sheet
   - Control + / closes the open sheets
   - Control + C copies the first frame of the current render
   - Control + V pastes a sheet into the tool as the main sheet
      - Control + V can paste a cloth texture if the cloth window is open
   - Control + Shift + V pastes a sheet into the tool as the mask sheet
   - Arrow Keys are used for seeking
   - Pressing Enter in any entry field renders
   - Pressing Escape removes focus from an entry field if you are in one

# Modes
All renders have a 1-pixel solid black outline
All modes support masks

- Image Mode
  - Renders the selection as an image
- Whole Sheet
  - Renders each image in the sheet
- Pet or Enemy Mode
  - Creates a GIF of 1 row of a properly formatted animation (https://lh6.googleusercontent.com/QUFc2BtMCO4CppgsHA2r7bjN62jd_RgZ3-1Ow3HV24Jckgtht9ARvK7YbIFFD7Zr0CgbeRqEXMJhV-37sSntmVz0t990pR-FxWeIeem7U-k7nT_mitO6Y1zkNtRNH7bydXiJ1Yg)
- Player Skin Mode
  - Same as Pet or Enemy Mode, but for 3 rows
- Animation Mode
  - Creates a GIF that scrolls through each frame, starting at the index
  - The length of the animation can be specified with the animation length entry. If it is 0 the animation plays until it reaches the end of the sheet.
- Full Overview
  - Renders the first image of each row and arranges them in a 6-column display
- Quick Overview
  - Same as Full Overview, except only renders every 3rd row (for sheets of skins)

# Discord
Join if you have any feedback
https://discord.gg/mdnVtbhuhM
