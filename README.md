# RotMG-Sprite-Renderer
A Windows replacement for Tuvior's Tool

# Features
- Previewing sheets and renders
- Seek feature that allows you to scroll through larger sheets along with manual index input
- Customizable mask, bg, outline, and shadow
- Outline adjusts to upscale
- Cloth options
- Customizable GIF length
- Copying and Pasting Images
- Transparent Background for GIFs (without shadows)
- "Subscribe" feature that allows changes you make to a file to automatically be rendered
- Themes
- Shortcuts for opening sheets, rendering, closing sheets, copying, and pasting
   - Control + 1-8 makes focus jump to buttons throughout the app
   - Control + v pastes a sheet in
   - Control + Shift + v pastes a mask sheet in
   - Control + c copies the render (images only)
   - Control + s saves the current render
   - Control + h sets the index to 0
   - Control + Shift + h resets scrolling in the render back to the top left
   - Control + q clears any alerts
   - Arrow Keys seek through the sheet
   - Control + Arrow Keys scrolls in the render
   - Escape removes focus from any field or button
   - Enter/Return renders with the current settings

# Modes
- Image Mode
  - Renders the selection as an image
  - The length option changes how many images are rendered; the shape of rendered images is not perserved but the number of columns of the original sheet are.
  - A length of 0 renders the whole sheet from the starting index
- Entity Mode
  - Creates a GIF of a row of a properly formatted animation
  - The length option changes how many rows are rendered
  - A length of 0 renders the whole sheet from the starting index
- Animation Mode
  - Creates a GIF that scrolls through each frame, starting at the index
  - The length option changes the amount of frames rendered
  - A length of 0 renders the whole sheet from the starting index
- Overview Mode
  - Renders the first image of every third row and arranges them in a 6-column display
  - The length option changes how many leftmost images after each row are rendered. It should be a value between 1 and 3.
  - A length of 0 renders the same as a length of 3

# Build Instructions (for Windows)
- Have Python >= 3.10
- Have a C compiler (Nuitka will prompt)
- Install all dependencies in requirements.txt (pip install -r requirements.txt)
- Run build.bat
- .del files can be deleted, they are only there so the folders can be archived

# Discord
Join if you have any feedback
https://discord.gg/mdnVtbhuhM
