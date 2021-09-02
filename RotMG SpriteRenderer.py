from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog, colorchooser, messagebox, font, PhotoImage
from PIL import Image, ImageFilter, ImageTk, ImageDraw
from math import ceil, floor
from threading import Timer
from imageio import mimsave, imread
from io import BytesIO
from base64 import b64decode
from datetime import datetime
import win32clipboard

#class for sheets
class sheet_handler:
    def __init__(self, sheet: Image):
        self.sheet = sheet
    
    def sheet_size(self) -> tuple:
        return self.sheet.size
    
    def get_image(self, index: int, x1: int, y1: int) -> Image:
        length = self.sheet_size()[0]
        column = index % (length / x)
        row = floor(index / (length / y / (x / y)))

        return self.sheet.crop((column * x, row * y, column * x + x1, row * y + y1)).convert('RGBA')

    def close_sheet(self):
        self.sheet = None

#class for images
class image_handler:
    def __init__(self, image: Image, mask=None):
        self.image = image.convert('RGBA')
        self.mask = mask

    def silhouette(self) -> Image:
        #create silhouette
        x = self.image.size[0]
        inc = 0

        silhouette = self.image.copy()
        for i in self.image.getdata():
            if i[3] != 0:
                silhouette.putpixel((int(inc % x), int(inc / x)), (0, 0, 0, 255))
            else:
                silhouette.putpixel((int(inc % x), int(inc / x)), (0, 0, 0, 0))
            inc+= 1

        return silhouette

    def render(self, scale: int) -> Image:
        x, y = self.image.size

        #silhouette
        silhouette = self.silhouette()

        #resize silhouette and create bg
        sized_silhouette = silhouette.resize((x*scale, y*scale), resample = Image.BOX)

        if 'selected' in bg_check.state():
            bg = Image.new('RGBA', ((x+2)*scale, (y+2)*scale), bg_var.get())

        else:
            bg = Image.new('RGBA', ((x+2)*scale, (y+2)*scale), (0, 0, 0, 0))        

        #shadow and outline if no mask
        if self.mask == None:
            if 'selected' in shadow_check.state():
                bg.alpha_composite(sized_silhouette, (scale, scale))
                bg = bg.filter(ImageFilter.GaussianBlur(radius=scale/2))

            for i in (-1, 1):
                for j in (-1, 1):    bg.alpha_composite(sized_silhouette, (scale+i, scale+j))

        #final image
        bg.alpha_composite(self.image.resize((x*scale, y*scale), resample=Image.BOX), (scale, scale))
        
        return bg.convert('RGBA')
    
    def render_mask(self, scale: int, clothing_texture: Image, accessory_texture: Image) -> Image:
        #initial render to paste onto
        base = self.render(4)

        #size grabbing
        base_x, base_y = base.size
        x, y = self.image.size

        #creating a texture image to cut from (clothing)
        clothing_texture = clothing_texture.convert('RGBA')
        clothing_texture_size = clothing_texture.size[0]
        clothing_texture_filled = Image.new('RGBA', (base_x, base_y), (0, 0, 0, 0))
        for i in range(4, base_x, clothing_texture_size):
            for j in range(4, base_y, clothing_texture_size):
                clothing_texture_filled.alpha_composite(clothing_texture, (i, base_y - j - clothing_texture_size))

        #creating a texture image to cut from (accessory)
        accessory_texture = accessory_texture.convert('RGBA')
        accessory_texture_size = accessory_texture.size[0]
        accessory_texture_filled = Image.new('RGBA', (base_x, base_y), (0, 0, 0, 0))
        for i in range(4, base_x, accessory_texture_size):
            for j in range(4, base_y, accessory_texture_size):
                accessory_texture_filled.alpha_composite(accessory_texture, (i, base_y - j - accessory_texture_size))

        #reading mask, saving intensity and position of red and green pixels
        inc = 0
        primaries, secondaries = [], []
        for i in self.mask.getdata():
            if i[0] != 0:
                primaries.append((i[0], int(inc % x), int(inc / x)))
            elif i[1] != 0:
                secondaries.append((i[1], int(inc % x), int(inc / x)))
            inc+= 1

        #according to previous step, cut from texture image to paste onto base image, then paste transparent layer for brightness adjust
        for i in primaries:
            cropped = clothing_texture_filled.crop((i[1] * 4 + 4, i[2] * 4 + 4, i[1] * 4 + 2 * 4, i[2] * 4 + 2 * 4))
            base.alpha_composite(cropped, (i[1] * 4 + 4, i[2] * 4 + 4))

            obscure = Image.new('RGBA', (4, 4), (0, 0, 0, 255 - i[0]))
            base.alpha_composite(obscure, (i[1] * 4 + 4, i[2] * 4 + 4))

        for i in secondaries:
            cropped = accessory_texture_filled.crop((i[1] * 4 + 4, i[2] * 4 + 4, i[1] * 4 + 2 * 4, i[2] * 4 + 2 * 4))
            base.alpha_composite(cropped, (i[1] * 4 + 4, i[2] * 4 + 4))

            obscure = Image.new('RGBA', (4, 4), (0, 0, 0, 255 - i[0]))
            base.alpha_composite(obscure, (i[1] * 4 + 4, i[2] * 4 + 4))

        #create shadow
        silhouette = self.silhouette().resize((x * scale, y * scale), resample=Image.BOX)
        bg = Image.new('RGBA', (int(base_x * (scale / 4)), int(base_y * (scale / 4))), (0, 0, 0, 0))

        if 'selected' in shadow_check.state():
            bg.alpha_composite(silhouette, (scale, scale))
            bg = bg.filter(ImageFilter.GaussianBlur(radius=scale/2))

        #outline
        for i in (-1, 1):
            for j in (-1, 1):    bg.alpha_composite(silhouette, (scale+i, scale+j))

        #drop resized base onto shadow
        base = base.resize((int(base_x * (scale / 4)), int(base_y * (scale / 4))), resample=Image.BOX)
        bg.alpha_composite(base, (0, 0))

        return bg

#class for seeking
class index:
    def __init__(self, num: int):
        self.num = num
    
    def set_num(self, num: int):
        self.num = num

    def hex_to_int(self, hex: str) -> None:
        self.num = int(hex[2:], 16)

#class for gif driving
class repeated_timer:
    def __init__(self, interval, function):
        self._timer = None
        self.interval = interval
        self.function = function
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function()

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.setDaemon(True)
            self._timer.start()
            self.is_running = True

    def stop(self):
        global frame
        self._timer.cancel()
        self.is_running = False
        frame = 0

#class for image previewing
class preview_image:
    def __init__(self, label: Label):
        self.label = label
    
    def update_image(self, image: Image):
        sized_image = image.convert('RGBA').resize((int(image.size[0] * 50 / x), int(image.size[1] * 50 / y)), resample = Image.BOX) #size is 50 times the size divided by size (size is constant while keeping image dimensions)
        sized_image.alpha_composite(Image.open(BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x006\x00\x00\x006\x08\x06\x00\x00\x00\x8cEj\xdd\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f\x0b\xfca\x05\x00\x00\x00\tpHYs\x00\x00\x0e\xc3\x00\x00\x0e\xc3\x01\xc7o\xa8d\x00\x00\x00\xf9IDAThC\xed\xdaM\x0e\x820\x14\x04\xe0\xa2;\xe3\x92\x0bx\xffCi\xbc\x83\xae\xfc{SZ\x84\x94\x12\xbb1\xbeq\xbe\x80\xd6R\x0b\x13*4\x86\xee\x19\x82-\xa5..\xa5\xd6\xf6\xb0\xf4\x9d\x95\xfeo\xf6\xb6\xb5\xf5\x14+\x12k|H\xc5\x99\xd47\xda\xeem\xedQ\x07?\x15\xcc\x1a\xa1\xee1|\x9a\xab\xf5_;\x9e\xb8\xa1\xba\xd1\t;\xf8\xde\xd6]*\x0fy\xc6\x02\t\x0brA\x9eM\xfa\xcc\xe4\x8a\x97\xf17V\x1b\xc3\xde\xe4<""2E{\xb9g\xbcAG\x08v\x1e\x8a4b\x1e\xea3F\x89\xfa\xe2qG\x81\xc8;\x8fE\xa48[\x19[\x1e\x11\xf9"M\x82\xbdQ0o\x14LDD\\\xb3\x89\xd51\xcf\xaf\x18\xe4<\xbaA{\xa3`\xdeh\xae("\xf2\x17\xf4\xbf\xa27\xb4\xc1\xc6\xa18U\x1b\x96Kmam\x187\xf6\xdf\xf4<p\xb6\xb8\x8f\xc6\x1d\x17m\xa1\xd6\x1e>\xed\xdf\x1a\xa1\xae\xe9y\xe0\xac\xdcG\x08/\xd1\xcc_\x8a\x96-Ty\x00\x00\x00\x00IEND\xaeB`\x82')), (48, 48))
        photo_image = ImageTk.PhotoImage(sized_image)

        self.label.config(image=photo_image)

        self.photo_image = photo_image

#class for color and cloth picking
class color_picker:
    def __init__(self, image: Image, image_label: Label, title: str):
        self.image = image
        self.image_label = image_label
        self.title = title
    
    def set_image(self, img: Image):
        self.image = img
        display_image_one = ImageTk.PhotoImage(self.image.resize((int(height/54), int(height/54)), resample=Image.BOX))
        self.image_label.config(image=display_image_one)

        display_image_two = ImageTk.PhotoImage(self.image.resize((60, 60), resample=Image.BOX))
        self.color_preview.config(image=display_image_two)

        #replacement for global definition
        self.display_image_one = display_image_one
        self.display_image_two = display_image_two

        render()

    def choose_color(self):
        if (new_color := colorchooser.askcolor('#ffffff')[1]) != None:
            self.set_image(Image.new('RGBA', (10, 10), new_color))

    def choose_cloth(self):
        b64_cloths = [b'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAF0lEQVR4nGP8//8/AzGAiShVowqpphAA1RIDEZR7aoQAAAAASUVORK5CYII=', b'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKAQMAAAC3/F3+AAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAZQTFRFTU1NmZmZBC4lqQAAABFJREFUeJxjCHVgWNXAgIMEAH9TCLzkBdSkAAAAAElFTkSuQmCC', b'iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFAgMAAADwAc52AAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAlQTFRFNQlPbBOgAwugaLCN6gAAABdJREFUeJxjkGJg8HBgWOjA0NLAIMYAABKbAp7dfVT4AAAAAElFTkSuQmCC', b'iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAMAAAC6sdbXAAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAD9QTFRFc3NzOTNHR0YvPUc6MUk4OEJHKzgwNFxwTUQXQEcvMVFgP0c7Y3ppVkodZmhzMywqZmBePU9/RztDRzdAOjQwPoOYmwAAACZJREFUeJxjYGBkYmZhYGVj5+BkYODi5uFl4ODjF2BnEBTiEBYBAAmYAOrM5quqAAAAAElFTkSuQmCC', b'iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFBAMAAAB/QTvWAAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAA9QTFRFWysLWzMLWyAIwZM5updm18AGKQAAABhJREFUeJxjYAACQUEBBiUlBQYTEwcQBgAL4wHnJ4dSPwAAAABJRU5ErkJggg==', b'iVBORw0KGgoAAAANSUhEUgAAAAQAAAAEAgMAAADUn3btAAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAlQTFRFAAAAADx4b0MXUjUhKAAAABBJREFUeJxjEGJoYVBk8AAAA8UBAGPzOUIAAAAASUVORK5CYII=', b'iVBORw0KGgoAAAANSUhEUgAAAAQAAAAEBAMAAABb34NNAAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAA9QTFRFa1szhGkfJ0VMFltmtQAA3Gvk0AAAABRJREFUeJxjYGBgEBRkUFZmcHEBAAMSAPGtRs5jAAAAAElFTkSuQmCC', b'iVBORw0KGgoAAAANSUhEUgAAAAQAAAAEAQMAAACTPww9AAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAZQTFRFAAAA999rySy9mgAAAA5JREFUeJxjYAACBQYGAABoACEO48ZHAAAAAElFTkSuQmCC', b'iVBORw0KGgoAAAANSUhEUgAAAAQAAAAEAQMAAACTPww9AAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAZQTFRFb23LAAAAnCveuwAAAAxJREFUeJxjCGAAQwAFCAFBQtVWSQAAAABJRU5ErkJggg==', b'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKAgMAAADwXCcuAAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAxQTFRFAH7T29v/ADx4AGnTEzcLwwAAACZJREFUeJxjEFtQwMC6QoDBMYsBjEFssQUODFGNDAxZLAJgDGQDAKK4B5//az36AAAAAElFTkSuQmCC', b'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKBAMAAAB/HNKOAAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAABVQTFRF88RJ/+5Z1IY9Ym6MdI2zo73ZQkhmAKnDwgAAADNJREFUeJxjYBQEAgYhExcXIwZhF0dXZxDpAiQNGAWNGYTNEtOApLGhMYI0A5JCxsbGRgD7ZgjJpOI9/gAAAABJRU5ErkJggg==', b'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKBAMAAAB/HNKOAAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAABJQTFRFgi8gwRkZwVxVWSAWc3Nzt8GFcgbo6gAAAB5JREFUeJxjYGAQFFRiwCSNjRkYXFBIFxclpVBkEgCGYAZyLymKYAAAAABJRU5ErkJggg==', b'iVBORw0KGgoAAAANSUhEUgAAAAkAAAAJAgMAAACd/+6DAAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAxQTFRFAAAAIJv/uf+z////rxwV9QAAACVJREFUeJxjYBBgYFAoYWBgEHBgAAEWDgYGWRDNCCTYHRgYGRkAH9ABbLrxs9EAAAAASUVORK5CYII=', b'iVBORw0KGgoAAAANSUhEUgAAAAkAAAAJBAMAAAASvxsjAAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAABVQTFRFPxgA////RFB+KztbZXqgAP//n7rMfQkbcwAAADNJREFUeJxjYBAUYGBgYFRSAJFGSiAOk4oDkGQIcUoAsllcgKQCg0oCAxMDQxoDA0gBAwBhggPsOHDfnwAAAABJRU5ErkJggg==', b'iVBORw0KGgoAAAANSUhEUgAAAAkAAAAJAQMAAADaX5RTAAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAZQTFRFMKTy////CGt/CgAAABtJREFUeJxjYGBgYGZgYG8AISBIYGD4AEYMDAAjMwNSwdMtOQAAAABJRU5ErkJggg==', b'iVBORw0KGgoAAAANSUhEUgAAAAkAAAAJBAMAAAASvxsjAAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAABVQTFRFAAD/lgD03h0d/64M/+oMDP9IYf/ncdl+vQAAAC5JREFUeJxjYFR2TWBgEDIJY2BgADEFGIBMRgUGIFPIgAHIVHZgADJNAhgYEEoBubgG5YKCELsAAAAASUVORK5CYII=', b'iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFAQMAAAC3obSmAAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAZQTFRFAAB4////C1IXrgAAABJJREFUeJxjMGCQYOhgOMCQAAAHqgHxkZYmYgAAAABJRU5ErkJggg==', b'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKBAMAAAB/HNKOAAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAABVQTFRFGcTqoB5qhxlZkRtg3bgjwSSAADsQE5sPfQAAADdJREFUeJxjYIACQRChaCziwMCqJOzIwMAaJGIswMAQpCgMJEOVFBkYElJDVRkY2BhYA0AkEAAAfS4EsT2ccyoAAAAASUVORK5CYII=', b'iVBORw0KGgoAAAANSUhEUgAAAAQAAAAEAQMAAACTPww9AAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAZQTFRF/9voAAAArE01nAAAAA5JREFUeJxjYGD4wADEAAWoAeH1ZN1mAAAAAElFTkSuQmCC', b'iVBORw0KGgoAAAANSUhEUgAAAAQAAAAEAQMAAACTPww9AAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAZQTFRFAAAAAQB4+nsq9gAAAAxJREFUeJxjSGAAQwAGCAGBFZY4EAAAAABJRU5ErkJggg==', b'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKAQMAAAC3/F3+AAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAZQTFRFAAAAYf+LBTy/AgAAAB9JREFUeJxjCGlgiGlgAILbDgyeYHTSAcS928AQ0gAAZgkHGDG1EzEAAAAASUVORK5CYII=']
        button_images, actual_images = [], []

        try:    self.chooser.destroy()
        except:    pass

        self.chooser = Toplevel()
        self.chooser.wm_iconphoto(True, icon)
        self.chooser.geometry('266x115')
        self.chooser.configure(bg='#36393e')
        for i in range(len(b64_cloths)):
            button_images.append(ImageTk.PhotoImage(Image.open(BytesIO(b64decode(b64_cloths[i]))).resize((20, 20))))
            actual_images.append(Image.open(BytesIO(b64decode(b64_cloths[i]))))

            button = Button(self.chooser, image=button_images[i], command=lambda i=i: self.set_image(actual_images[i]))
            button.grid(row=int(i / 7), column=i % 7)

        #replacement for global definition
        self.button_images = button_images
        self.actual_images = actual_images

    def upload_cloth(self):
        try:
            image = Image.open(filedialog.askopenfilename())
            self.set_image(image)
        except Exception as e:
            messagebox.showwarning('Warning', 'No Cloth Uploaded: ' + str(e))

    def upload_from_clipboard(self):
        win32clipboard.OpenClipboard()
        #check if png format available
        if win32clipboard.IsClipboardFormatAvailable(png_format):
            data = BytesIO(win32clipboard.GetClipboardData(png_format))
            image = Image.open(data)
        #check if dibv5 format available
        elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIBV5):
            data = BytesIO(win32clipboard.GetClipboardData(win32clipboard.CF_DIBV5))
            messagebox.showwarning('Warning', 'Possible malformed cloth due to invalid format.')
            image = Image.open(data)
        #check if dib format available
        elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
            data = BytesIO(win32clipboard.GetClipboardData(win32clipboard.CF_DIB))
            messagebox.showwarning('Warning', 'Possible malformed cloth due to invalid format.')
            image = Image.open(data)
        #no valid formats
        else:
            win32clipboard.CloseClipboard()
            return messagebox.showerror('Error', 'Unable to get image from clipboard.')
        win32clipboard.CloseClipboard()

        self.set_image(image)

    def generate(self):
        try:    self.selection_window.destroy()
        except:    pass

        self.selection_window = Toplevel()
        self.selection_window.wm_iconphoto(True, icon)
        self.selection_window.title(self.title)
        self.selection_window.geometry('233x98')
        self.selection_window.configure(bg='#36393e')
        self.selection_window.bind('<Control-v>', lambda _: self.upload_from_clipboard())

        #image label for previews
        color_preview_image = ImageTk.PhotoImage(self.image.resize((60, 60), resample=Image.BOX))

        color_preview = Label(self.selection_window, image=color_preview_image)
        color_preview.grid(row=0, column=0)

        #main buttons
        buttons = Frame(self.selection_window)

        choose_color = Button(buttons, text='Choose Color', command=self.choose_color)
        choose_color.grid(row=0, column=0)

        choose_cloth = Button(buttons, text='Choose Cloth', command=self.choose_cloth)
        choose_cloth.grid(row=1, column=0)

        upload_cloth = Button(buttons, text='Upload Cloth', command=self.upload_cloth)
        upload_cloth.grid(row=2, column=0)

        buttons.grid(row=0, column=1)

        #replacement for global definition
        self.color_preview_image = color_preview_image
        self.color_preview = color_preview

#tk button commands
def update_previews():
    columnspan, rowspan = 1, 1
    if mode[0] == 'gif':
        columnspan = 7
        rowspan = mode[1]

    length = sheet.sheet_size()[0]
    column = seek_index.num % (length / x)
    row = floor(seek_index.num / (length / y / (x / y)))

    previewed_sheet = sheet.sheet.crop((column * x - x, row * y - y, column * x + (x * columnspan) + x, row * y + (y * rowspan) + y)).convert('RGBA')
    preview_sheet_sample.update_image(previewed_sheet)

    if mask_sheet.sheet != None:
        previewed_mask = mask_sheet.sheet.crop((column * x - x, row * y - y, column * x + (x * columnspan) + x, row * y + (y * rowspan) + y)).convert('RGBA')
        preview_mask_sample.update_image(previewed_mask)
    else:
        preview_mask_sample.update_image(Image.new('RGBA', (5, 5), (0, 0, 0, 0)))

def update_index_frame_from_button(increment: int):
    if seek_index.num + increment > -1:    seek_index.set_num(seek_index.num + increment)

    seek_entry.delete(0, END)
    seek_entry.insert(0, hex(seek_index.num))

    update_previews()
    render()

def update_index_frame_from_entry(event):
    try:
        if int(seek_entry.get()[2:], 16) > -1:    seek_index.hex_to_int(seek_entry.get())
    except:
        return messagebox.showerror('Error', 'Invalid Index')


    update_previews()
    render()

def open_sheet(clipboard=False):
    global sheet, opened_file

    if clipboard == False:
        opened_file = filedialog.askopenfilename()
        try:
            sheet = sheet_handler(Image.open(opened_file))
        except:
            return messagebox.showwarning('Warning', 'No sheet opened.')

    else:
        #exit if entry has focus
        if 'entry' in str(window.focus_get()):
            return

        win32clipboard.OpenClipboard()
        #check if png format available (only one that supports transparent bg)
        if win32clipboard.IsClipboardFormatAvailable(png_format):
            data = BytesIO(win32clipboard.GetClipboardData(png_format))
            image = Image.open(data)
        #check if dibv5 format available
        elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIBV5):
            messagebox.showwarning('Warning', 'Incorrect clipboard format, Pasted image will have a black background.')
            data = BytesIO(win32clipboard.GetClipboardData(win32clipboard.CF_DIBV5))
            image = Image.open(data)
        #check if dib format available
        elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
            messagebox.showwarning('Warning', 'Incorrect clipboard format, Pasted image will have a black background.')
            data = BytesIO(win32clipboard.GetClipboardData(win32clipboard.CF_DIB))
            image = Image.open(data)
        #no valid formats
        else:
            win32clipboard.CloseClipboard()
            return messagebox.showerror('Error', 'Unable to get image from clipboard.')
        win32clipboard.CloseClipboard()

        opened_file = 'unknown.png'
        sheet = sheet_handler(image)

    mask_sheet.close_sheet()
    mask_check.state(('disabled', '!selected'))

    seek_index.set_num(0)
    seek_entry.delete(0, END)
    seek_entry.insert(0, hex(seek_index.num))

    for widg in picture_widgets:    widg.state(('!disabled',))

    update_index_frame_from_entry(None)
    update_previews()
    render()

def open_mask(clipboard=False):
    global mask_sheet

    if clipboard == False:
        opened_file = filedialog.askopenfilename()
        try:
            mask_sheet = sheet_handler(Image.open(opened_file))
        except:
            return messagebox.showwarning('Warning', 'No sheet opened.')
    else:
        #exit if entry has focus or main sheet not loaded
        if 'entry' in str(window.focus_get()) or sheet.sheet == None:
            return

        win32clipboard.OpenClipboard()
        #check if png format available (only one that supports transparent bg)
        if win32clipboard.IsClipboardFormatAvailable(png_format):
            data = BytesIO(win32clipboard.GetClipboardData(png_format))
            image = Image.open(data)
        #check if dibv5 format available
        elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIBV5):
            messagebox.showwarning('Warning', 'Incorrect clipboard format, Pasted image will have a black background.')
            data = BytesIO(win32clipboard.GetClipboardData(win32clipboard.CF_DIBV5))
            image = Image.open(data)
        #check if dib format available
        elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
            messagebox.showwarning('Warning', 'Incorrect clipboard format, Pasted image will have a black background.')
            data = BytesIO(win32clipboard.GetClipboardData(win32clipboard.CF_DIB))
            image = Image.open(data)
        #no valid formats
        else:
            win32clipboard.CloseClipboard()
            return messagebox.showerror('Error', 'Unable to get image from clipboard.')
        win32clipboard.CloseClipboard()

        mask_sheet = sheet_handler(image) 

    seek_index.set_num(0)
    seek_entry.delete(0, END)
    seek_entry.insert(0, hex(seek_index.num))

    for widg in picture_widgets:    widg.state(('!disabled',))
    mask_check.state(('!disabled',))

    update_index_frame_from_entry(None)
    update_previews()
    render()

def close_sheets():
    seek_index.set_num(0)
    seek_entry.delete(0, END)
    seek_entry.insert(0, hex(seek_index.num))

    mask_check.state(('disabled', '!selected'))
    for widg in picture_widgets:    widg.state(('disabled',))

    sheet.close_sheet()
    mask_sheet.close_sheet()

    _image = Image.new('RGBA', (5, 5), (0, 0, 0, 0))
    preview_sheet_sample.update_image(_image)
    preview_mask_sample.update_image(_image)
    rendered_image.delete('all')

    gif_timer.stop()

def bg_color_chooser():
    global bg_color_image
    if (new_color := colorchooser.askcolor(bg_var.get())[1]) != None:
        bg_var.set(new_color)

    bg_color_image = ImageTk.PhotoImage(Image.new('RGB', (20, 20), bg_var.get()))
    bg_color_label.config(image=bg_color_image)

    render()

def update_mode(new_mode):
    global mode
    mode = modes[new_mode]
    render()

def update_render_image():
    global rendered_display, gif_frame, too_large, oversize_preview, oversize_preview_image
    gif_timer.stop()
    rendered_image.delete('all')

    if rendered_images[0].size[0] > (int(width/2.4)) or rendered_images[0].size[1] > (int(height/1.35)): #800x800 on 1080p
        #too large canvas
        try:    oversize_preview.destroy()
        except: pass

        window.focus_set()

        oversize_preview = Toplevel()
        oversize_preview.title('Render Preview')
        oversize_preview.geometry('{}x{}'.format(int(width/2.353), int(height/1.319))) #815x815 on 1080p
        oversize_preview.configure(bg='#36393e')

        oversize_preview_image = ImageTk.PhotoImage(rendered_images[0])
        oversize_canvas = Canvas(oversize_preview, bg='#36393e', relief=FLAT, highlightthickness=0, width=int(width/2.39), height=int(height/1.34), scrollregion=(0, 0, rendered_images[0].size[0], rendered_images[0].size[1])) #815x815 on 1080p
        oversize_canvas.create_image(0, 0, image=oversize_preview_image, anchor=NW)
        oversize_canvas.grid(row=0, column=0)

        vert_scroll = Scrollbar(oversize_preview, orient=VERTICAL, command=oversize_canvas.yview)
        vert_scroll.grid(row=0, column=1, sticky='ns')

        horiz_scroll = Scrollbar(oversize_preview, orient=HORIZONTAL, command=oversize_canvas.xview)
        horiz_scroll.grid(row=1, column=0, sticky='ew')

        oversize_canvas.config(xscrollcommand=horiz_scroll.set, yscrollcommand=vert_scroll.set)

        gif_timer.stop()

        too_large = Image.new('RGBA', (300, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(too_large)
        draw.text((0, 0), 'Image too large for preview', '#d6d7d8')
        too_large = ImageTk.PhotoImage(too_large)

        rendered_image.config(width=300, height=100)
        rendered_image.create_image(0, 0, image=too_large, anchor=NW)

    else:
        if modes[mode_var.get()][0] == 'png' or modes[mode_var.get()][0] == 'over' or modes[mode_var.get()][0] == 'whl':
            rendered_image.config(width=rendered_images[0].size[0], height=rendered_images[0].size[1])
            rendered_display = ImageTk.PhotoImage(rendered_images[0])
            rendered_image.create_image(0, 0, image=rendered_display, anchor=NW)

        else:
            rendered_image.config(width=rendered_images[0].size[0], height=rendered_images[0].size[1])
            gif_frame = ImageTk.PhotoImage(rendered_images[1])
            rendered_image.create_image(0, 0, image=gif_frame, anchor=NW)

            gif_timer.interval = float(gif_speed_entry.get()) / 1000 - (float(gif_speed_entry.get()) / 10000)
            gif_timer.start()

def update_render_gif():
    global frame, gif_frame

    rendered_image.delete('all')
    gif_frame = ImageTk.PhotoImage(rendered_images[frame])
    rendered_image.create_image(0, 0, image=gif_frame, anchor=NW)
    if frame == len(rendered_images)-1:    frame = 0
    else:    frame+= 1

def save_as_image():
    if (file_path := filedialog.asksaveasfilename(confirmoverwrite = True, initialfile = '{}-{}-{}.png'.format(opened_file.rpartition('/')[2].rstrip('png').rstrip('.'), mode[0], datetime.now().strftime('%H%M%S')), filetypes = [('PNG', '*.png')]).rstrip('.png') + '.png') == '.png':
        return messagebox.showerror('Error', 'File not saved, invalid path.')
    try:
        rendered_images[0].save(file_path, 'PNG')
    except Exception as e:
        return messagebox.showerror('Error', 'File not saved, no render: {}'.format(str(e)))

def save_as_gif():
    #exit if wrong mode or invalid file path
    if not (mode[0] == 'gif' or mode[0] == 'ani'):
        return messagebox.showerror('Error', 'Wrong mode.')

    if (file_path := filedialog.asksaveasfilename(confirmoverwrite = True, initialfile = '{}-{}-{}.gif'.format(opened_file.rpartition('/')[2].rstrip('png').rstrip('.'), mode[0], datetime.now().strftime('%H%M%S')), filetypes = [('GIF', '*.gif')]).rstrip('.gif') + '.gif') == '.gif':
        return messagebox.showerror('Error', 'File not saved, invalid path.')

    try:
        gif_bytes = BytesIO()

        if 'selected' in bg_check.state():
            mimsave(gif_bytes, frames, format='GIF', duration=float(gif_speed_entry.get()) / 1000)

        else:
            temp_rendered_images = []

            #modify each black pixel in every other frame to be slightly off-black so PIL optimization doesnt mess the gif up
            for i in range(len(rendered_images)):
                if i % 2 == 0:
                    temp_image = rendered_images[i]
                    temp_rendered_images.append(temp_image.copy())

                else:
                    temp_image = rendered_images[i].copy()
                    inc = 0
                    for pxl in temp_image.getdata():
                            if pxl[0:3] == (0, 0, 0):    temp_image.putpixel((int(inc % temp_image.size[0]), int(inc / temp_image.size[0])), (0, 0, 1))
                            inc+= 1

                    temp_rendered_images.append(temp_image.copy())

            temp_rendered_images[0].save(gif_bytes, 'GIF', loop=0, append_images=temp_rendered_images[1:], save_all=True, include_color_table=True, optimize=False, duration=int(gif_speed_entry.get()))

            buffer = gif_bytes.getbuffer()
            graphic_control_indexes, palette_indexes, transparent_indexes = [], [], []

            #look for graphic control extension
            for i in range(781, len(buffer) - 20):
                if hex(buffer[i]) + hex(buffer[i + 1]) + hex(buffer[i + 2]) == '0x210xf90x4':
                    graphic_control_indexes.append(i)
                    palette_indexes.append(i + 37)

            #look for the bg color in each palette
            for i in palette_indexes:
                for j in range(i, len(buffer))[::3]:
                    if int(bg_var.get()[1:3], 16) == buffer[j] and int(bg_var.get()[3:5], 16) == buffer[j + 1] and int(bg_var.get()[5:7], 16) == buffer[j + 2]:
                        transparent_indexes.append(int((j - i) / 3))
                        break

            for i in range(len(graphic_control_indexes)):
                buffer[graphic_control_indexes[i] + 3] = buffer[graphic_control_indexes[i] + 3] + 1 + 8 #+1 for transparent color flag and +8 for disposal method 2
                buffer[graphic_control_indexes[i] + 6] = transparent_indexes[i]

        with open(file_path, 'wb') as file:
            file.write(gif_bytes.getvalue())

    except Exception as e:
        return messagebox.showerror('Error', 'File not saved, no render: {}'.format(str(e)))

def send_image_to_clipboard():
    if 'entry' in str(window.focus_get()):
        return

    if len(rendered_images) == 0:
        messagebox.showerror('Error', 'Nothing rendered yet.')
        return

    if mode[0] == 'gif' or mode[0] == 'ani':
        messagebox.showwarning('Error', 'GIFs cannot be copied to the clipboard, only the first frame is copied.')

    bmp_buffer, png_buffer = BytesIO(), BytesIO()
    rendered_images[0].convert('RGBA').save(bmp_buffer, 'BMP')
    rendered_images[0].convert('RGBA').save(png_buffer, 'PNG')

    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, bmp_buffer.getvalue()[14:])
    win32clipboard.SetClipboardData(png_format, png_buffer.getvalue())
    win32clipboard.CloseClipboard()

#rendering functions
def render():
    global x, y
    try:    win32clipboard.CloseClipboard()
    except:    pass

    try:
        x = int(width_entry.get())
        y = int(height_entry.get())
    except:
        messagebox.showerror('Error', 'Invalid width/height.')

    try:
        gif_timer.stop()
        if mode[0] == 'gif':    render_gif(modes[mode_var.get()][1])
        elif mode[0] == 'ani':    render_animation(animation_length_entry.get())
        elif mode[0] == 'over':    render_overview(modes[mode_var.get()][1])
        elif mode[0] == 'whl':    render_whole()
        else:    render_image()
    except Exception as e:
        messagebox.showerror('Error', 'Rendering error: ' + str(e))

    update_previews()
    update_render_image()

def render_image():
    global rendered
    scale = int(scale_entry.get())
    if not 'selected' in mask_check.state():
        rendered_images.clear()

        rendered = image_handler(sheet.get_image(seek_index.num, x, y))
        rendered = rendered.render(scale)

        rendered_images.append(rendered)
    else:
        rendered_images.clear()

        start_image = image_handler(sheet.get_image(seek_index.num, x, y), mask=mask_sheet.get_image(seek_index.num, x, y))
        rendered = start_image.render_mask(scale, mask_clothing_handler.image, mask_accessory_handler.image)

        rendered_images.append(rendered)

def render_gif(rows):
    global rendered_images, frames
    rendered_images.clear()
    scale = int(scale_entry.get())

    if 'selected' in bg_check.state():
        gif_base = Image.new('RGBA', (4 * (x + 2) * scale, rows * (y + 2) * scale), bg_var.get())
    else:
        gif_base = Image.new('RGBA', (4 * (x + 2) * scale, rows * (y + 2) * scale), (int(bg_var.get()[1:3], 16), int(bg_var.get()[3:5], 16), int(bg_var.get()[5:7], 16), 0))

    gif_images = [gif_base.copy()] + [gif_base.copy()]
    sheet_sample = sheet.get_image(seek_index.num, x * 7, y * rows)

    if not 'selected' in mask_check.state():
        for row in range(rows):
            second_walk = False

            #still frame
            still_image = image_handler(sheet_sample.crop((0 * x, row * y, 0 * x + x, row * y + y))).render(scale)
            gif_images[0].alpha_composite(still_image, (0 * (x + 2) * scale, row * (y + 2) * scale))
            gif_images[1].alpha_composite(still_image, (0 * (x + 2) * scale, row * (y + 2) * scale))

            #first walk frame
            walk_one = image_handler(sheet_sample.crop((1 * x, row * y, 1 * x + x, row * y + y))).render(scale)
            gif_images[0].alpha_composite(walk_one, (1 * (x + 2) * scale, row * (y + 2) * scale))

            #second walk frame (check if exists as well)
            walk_two = image_handler(sheet_sample.crop((2 * x, row * y, 2 * x + x, row * y + y)))
            for i in walk_two.image.convert('RGBA').getdata():
                if i[3] != 0:    second_walk = True
            walk_two = walk_two.render(scale)
            if second_walk:    gif_images[1].alpha_composite(walk_two, (1 * (x + 2) * scale, row * (y + 2) * scale))
            else:    gif_images[1].alpha_composite(walk_one, (1 * (x + 2) * scale, row * (y + 2) * scale))

            #first attack frame
            attack_one = image_handler(sheet_sample.crop((4 * x, row * y, 4 * x + x, row * y + y))).render(scale)
            gif_images[0].alpha_composite(attack_one, (2 * (x + 2) * scale, row * (y + 2) * scale))

            #final attack frame
            attack_two = image_handler(sheet_sample.crop((5 * x, row * y, 6 * x + x, row * y + y))).render(scale)
            gif_images[1].alpha_composite(attack_two, (2 * (x + 2) * scale, row * (y + 2) * scale))

    else:
        mask_sample = mask_sheet.get_image(seek_index.num, x * 7, y * rows)
        for row in range(rows):
            second_walk = False

            #still frame
            still_image = image_handler(sheet_sample.crop((0 * x, row * y, 0 * x + x, row * y + y)), mask=mask_sample.crop((0 * x, row * y, 0 * x + x, row * y + y))).render_mask(scale, mask_clothing_handler.image, mask_accessory_handler.image)
            gif_images[0].alpha_composite(still_image, (0 * (x + 2) * scale, row * (y + 2) * scale))
            gif_images[1].alpha_composite(still_image, (0 * (x + 2) * scale, row * (y + 2) * scale))

            #first walk frame
            walk_one = image_handler(sheet_sample.crop((1 * x, row * y, 1 * x + x, row * y + y)), mask=mask_sample.crop((1 * x, row * y, 1 * x + x, row * y + y))).render_mask(scale, mask_clothing_handler.image, mask_accessory_handler.image)
            gif_images[0].alpha_composite(walk_one, (1 * (x + 2) * scale, row * (y + 2) * scale))

            #second walk frame (check if exists as well)
            walk_two = image_handler(sheet_sample.crop((2 * x, row * y, 2 * x + x, row * y + y)), mask=mask_sample.crop((2 * x, row * y, 2 * x + x, row * y + y)))
            for i in walk_two.image.convert('RGBA').getdata():
                if i[3] != 0:    second_walk = True
            walk_two = walk_two.render_mask(scale, mask_clothing_handler.image, mask_accessory_handler.image)
            if second_walk:    gif_images[1].alpha_composite(walk_two, (1 * (x + 2) * scale, row * (y + 2) * scale))
            else:    gif_images[1].alpha_composite(walk_one, (1 * (x + 2) * scale, row * (y + 2) * scale))

            #first attack frame
            attack_one = image_handler(sheet_sample.crop((4 * x, row * y, 4 * x + x, row * y + y)), mask=mask_sample.crop((4 * x, row * y, 4 * x + x, row * y + y))).render_mask(scale, mask_clothing_handler.image, mask_accessory_handler.image)
            gif_images[0].alpha_composite(attack_one, (2 * (x + 2) * scale, row * (y + 2) * scale))

            #final attack frame
            attack_two = image_handler(sheet_sample.crop((5 * x, row * y, 6 * x + x, row * y + y)), mask=mask_sample.crop((5 * x, row * y, 6 * x + x, row * y + y))).render_mask(scale, mask_clothing_handler.image, mask_accessory_handler.image)
            gif_images[1].alpha_composite(attack_two, (2 * (x + 2) * scale, row * (y + 2) * scale))

    rendered_images = gif_images.copy()
    frames = []

    frame = 0
    for img in gif_images:
        buffer = BytesIO()

        img = rendered_images[frame].convert('RGBA')
        img.save(buffer, 'PNG')

        frames.append(imread(buffer.getvalue(), format='PNG-PIL'))
        frame+= 1

def render_animation(length):
    global rendered_images, frames
    rendered_images.clear()
    length = int(length)
    scale = int(scale_entry.get())
    start_index = seek_index.num
    animation_frames, frames = [], []

    if length == 0:
        length = int(sheet.sheet_size()[0] / x) * int(sheet.sheet_size()[1] / y)
    
    if 'selected' in bg_check.state():
        animation_base = Image.new('RGBA', ((x + 2) * scale, (y + 2) * scale), bg_var.get())
    else:
        animation_base = Image.new('RGBA', ((x + 2) * scale, (y + 2) * scale), (int(bg_var.get()[1:3], 16), int(bg_var.get()[3:5], 16), int(bg_var.get()[5:7], 16), 0))
    
    for garb in range(length):
        animation_frames.append(animation_base.copy())

    if not 'selected' in mask_check.state():
        for i in range(len(animation_frames)):
            frame_image = image_handler(sheet.get_image(start_index + i, x, y)).render(scale)
            animation_frames[i].alpha_composite(frame_image, (0, 0))
    else:
        for i in range(len(animation_frames)):
            frame_image = image_handler(sheet.get_image(start_index + i, x, y), mask=mask_sheet.get_image(start_index + i, x, y)).render_mask(scale, mask_clothing_handler.image, mask_accessory_handler.image)
            animation_frames[i].alpha_composite(frame_image, (0, 0))

    rendered_images = animation_frames.copy()

    frame = 0
    for img in animation_frames:
        buffer = BytesIO()

        img = rendered_images[frame].convert('RGB')
        img.save(buffer, 'PNG')

        frames.append(imread(buffer.getvalue(), format='PNG-PIL'))
        frame+= 1

def render_overview(skip):
    global rendered_images
    rendered_images.clear()
    scale = int(scale_entry.get())
    rows = int(sheet.sheet_size()[1]/y)

    nonempty_rows = []
    for i in range(rows):
        for pxl in sheet.get_image(i * (sheet.sheet_size()[0] / x), x, y).convert('RGBA').getdata():
            if pxl[3] != 0:
                nonempty_rows.append(i)
                break

    maxcolumns = 6
    if len(nonempty_rows) < 6:    maxcolumns = len(nonempty_rows)

    image_base = Image.new('RGBA', ((x + 2) * scale * maxcolumns, ceil(len(nonempty_rows) / maxcolumns / skip) * (y + 2) * scale))

    if skip != 1:
        nonempty_rows = nonempty_rows[::3]

    row, column = 0, 0
    if not 'selected' in mask_check.state():
        for i in range(len(nonempty_rows)):
            next_image = image_handler(sheet.get_image(nonempty_rows[i] * (sheet.sheet_size()[0] / x), x, y)).render(scale)
            image_base.alpha_composite(next_image, ((x + 2) * scale * column, (y + 2) * scale * row))

            if column == 5:
                column = 0
                row+= 1
            else:
                column+= 1
    else:
        for i in range(len(nonempty_rows)):
            next_image = image_handler(sheet.get_image(nonempty_rows[i] * (sheet.sheet_size()[0] / x), x, y), mask=mask_sheet.get_image(nonempty_rows[i] * (sheet.sheet_size()[0] / x), x, y)).render_mask(scale, mask_clothing_handler.image, mask_accessory_handler.image)
            image_base.alpha_composite(next_image, ((x + 2) * scale * column, (y + 2) * scale * row))

            if column == 5:
                column = 0
                row+= 1
            else:
                column+= 1    

    rendered_images.append(image_base)

def render_whole():
    global rendered_images

    rendered_images.clear()
    rendered_image.delete('all')
    scale = int(scale_entry.get())

    whole_sheet_render = Image.new('RGBA', (int(sheet.sheet_size()[0] / x) * (x + 2)*scale, int(sheet.sheet_size()[1] / y) * (y + 2) * scale), (0, 0, 0, 0))
    sheet_length = int(sheet.sheet_size()[0] / x) * int(sheet.sheet_size()[1] / y)
    sheet_width = int(sheet.sheet_size()[0])

    if not 'selected' in mask_check.state():
        for i in range(sheet_length):
            row = int(i % (sheet_width / x))
            column = floor(i / (sheet_width / x))

            next_image = image_handler(sheet.get_image(i, x, y)).render(scale)
            whole_sheet_render.alpha_composite(next_image, ((x + 2) * scale * row, (y + 2) * scale * column))
    else:
        for i in range(sheet_length-1):
            row = int(i % (sheet_width / x))
            column = floor(i / (sheet_width / x))

            next_image = image_handler(sheet.get_image(i, x, y), mask=mask_sheet.get_image(i, x, y)).render_mask(scale, mask_clothing_handler.image, mask_accessory_handler.image)
            whole_sheet_render.alpha_composite(next_image, ((x + 2) * scale * row, (y + 2) * scale * column))

    rendered_images.append(whole_sheet_render)

if __name__ == '__main__':
    #window setup
    window = Tk()
    window.title('Sprite Renderer')

    #icon setup
    icon = PhotoImage(data=b64decode(b'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'))
    window.wm_iconphoto(True, icon)

    #compatibility sizing
    width = window.winfo_screenwidth()
    height = window.winfo_screenheight()

    window.geometry('{}x{}'.format(int(width*0.859), int(height*0.6))) #1650x648 on 1080p

    #for clipboard action
    png_format = win32clipboard.RegisterClipboardFormat('PNG')

    #vars
    sheet = sheet_handler(None)
    mask_sheet = sheet_handler(None)
    modes = {'Image Mode': ('png',), 'Whole Sheet': ('whl',), 'Pet or Enemy Mode': ('gif', 1), 'Player Skin Mode': ('gif', 3), 'Animation Mode': ('ani',), 'Full Overview': ('over', 1), 'Quick Overview': ('over', 3)}
    mode = ('png',)
    rendered_images, picture_widgets = [], set()
    x, y = 8, 8

    ##################################################################################################################################
    #style options
    window.configure(bg='#36393e')

    default_font = font.nametofont('TkDefaultFont')
    default_font.config(size=int(height/120)) #9 on 1080p

    style = Style(window)
    style.theme_use('clam')
    style.configure('.',
        background='#36393e',
        fieldbackground='#36393e',
        foreground='#d6d7d8',
        borderwidth=3,
        bordercolor='#292b2f',
        lightcolor='#292b2f',
        darkcolor='#292b2f',
        insertcolor='#d6d7d8',
        gripcount=10,
        troughcolor='#45494f')

    style.configure('separator.TFrame',
        background='#292b2f')

    style.configure('TMenubutton',
        width=22)

    style.configure('TButton',
        width=25)
    
    style.configure('seek.TButton',
        width=4)

    style.map('.', foreground=[('disabled', '#6f7278')])
    style.map('TButton', background=[('active', '#292b2f')])
    style.map('TMenubutton', background=[('disabled', '#36393e'), ('active', '#292b2f')])
    style.map('TLabel', background=[('disabled', '#36393e')])
    style.map('TCheckbutton', background=[('disabled', '#36393e')])
    style.map('Vertical.TScrollbar', background=[('active', '#45494f')])
    style.map('Horizontal.TScrollbar', background=[('active', '#45494f')])

    ##################################################################################################################################
    #binds
    window.bind('<Control-v>', lambda _: open_sheet(clipboard=True)) #lowercase v (no shift)
    window.bind('<Control-V>', lambda _: open_mask(clipboard=True)) #uppercase v (with shift)
    window.bind('<Control-c>', lambda _: send_image_to_clipboard())

    window.bind('<Control-o>', lambda _: open_sheet())
    window.bind('<Control-m>', lambda _: open_mask())

    window.bind('<Control-r>', lambda _: render())
    window.bind('<Control-/>', lambda _: close_sheets())

    window.bind('<Up>', lambda _: (update_index_frame_from_button(-ceil(sheet.sheet_size()[0] / x)) if sheet.sheet != None and 'entry' not in str(window.focus_get()) else ''))
    window.bind('<Left>', lambda _: (update_index_frame_from_button(-1) if sheet.sheet != None and 'entry' not in str(window.focus_get()) else ''))
    window.bind('<Right>', lambda _: (update_index_frame_from_button(1) if sheet.sheet != None and 'entry' not in str(window.focus_get()) else ''))
    window.bind('<Down>', lambda _: (update_index_frame_from_button(ceil(sheet.sheet_size()[0] / x)) if sheet.sheet != None and 'entry' not in str(window.focus_get()) else ''))

    ##################################################################################################################################
    #sidebar
    sidebar = Frame(window)

    ##################################################################################################################################
    #sidebar sheet buttons
    sheet_buttons = Frame(sidebar)

    #file select
    file_select_button = Button(sheet_buttons, text='Load Sheet', command=open_sheet, width=20)
    file_select_button.grid(row=0, column=0, sticky='we')

    #file select
    mask_select_button = Button(sheet_buttons, text='Load Mask Sheet', command=open_mask)
    mask_select_button.grid(row=1, column=0, sticky='we')
    picture_widgets.add(mask_select_button)

    #clear sheet
    clear_sheet_button = Button(sheet_buttons, text='Clear Sheet', command=close_sheets)
    clear_sheet_button.grid(row=2, column=0, sticky='we')
    picture_widgets.add(clear_sheet_button)

    ##################################################################################################################################
    #seeking, size, mask toggle (et al as in and others)
    seek_index = index(0)

    seek_et_al_frame = Frame(sidebar)

    index_frame = Frame(seek_et_al_frame)

    seek_up = Button(index_frame, text='🡅', command=lambda: update_index_frame_from_button(-ceil(sheet.sheet_size()[0] / x)), style='seek.TButton')
    seek_up.grid(row=0, column=1)
    picture_widgets.add(seek_up)

    seek_left = Button(index_frame, text='🡄', command=lambda: update_index_frame_from_button(-1), style='seek.TButton')
    seek_left.grid(row=1, column=0)
    picture_widgets.add(seek_left)

    seek_entry = Entry(index_frame, justify='center', width=6, font=default_font)
    seek_entry.insert(0, hex(seek_index.num))
    seek_entry.bind('<Return>', update_index_frame_from_entry)
    seek_entry.bind('<FocusOut>', update_index_frame_from_entry)
    seek_entry.grid(row=1, column=1, ipady=int(height/180)) #6 on 1080p
    picture_widgets.add(seek_entry)

    seek_right = Button(index_frame, text='🡆', command=lambda: update_index_frame_from_button(1), style='seek.TButton')
    seek_right.grid(row=1, column=2)
    picture_widgets.add(seek_right)

    seek_down = Button(index_frame, text='🡇', command=lambda: update_index_frame_from_button(ceil(sheet.sheet_size()[0] / x)), style='seek.TButton')
    seek_down.grid(row=2, column=1)
    picture_widgets.add(seek_down)

    index_frame.grid(row=0, column=0, padx=int(height/54)) #20 on 1080p

    et_al_frame = Frame(seek_et_al_frame)

    width_entry = Entry(et_al_frame, width=10, justify='center')
    width_entry.insert(0, '8')
    width_entry.bind('<Return>', lambda _:render())
    width_entry.grid(row=0, column=0)
    picture_widgets.add(width_entry)

    width_label = Label(et_al_frame, text='Width')
    width_label.grid(row=0, column=1, sticky='w')
    picture_widgets.add(width_label)

    height_entry = Entry(et_al_frame, width=10, justify='center')
    height_entry.insert(0, '8')
    height_entry.bind('<Return>', lambda _:render())
    height_entry.grid(row=1, column=0)
    picture_widgets.add(height_entry)

    height_label = Label(et_al_frame, text='Height')
    height_label.grid(row=1, column=1, sticky='w')
    picture_widgets.add(height_label)

    check_size_spacer = Frame(et_al_frame)
    check_size_spacer.grid(row=2, column=0, columnspan=2, ipady=5)

    mask_check = Checkbutton(et_al_frame, text='Render Mask', command=render)
    mask_check.state(('disabled',))
    mask_check.grid(row=3, column=0, columnspan=2, sticky='w')

    bg_check = Checkbutton(et_al_frame, text='Render BG', command=render)
    bg_check.grid(row=4, column=0, columnspan=2, sticky='w')
    picture_widgets.add(bg_check)

    shadow_check = Checkbutton(et_al_frame, text='Render Shadows', command=render)
    shadow_check.grid(row=5, column=0, columnspan=2, sticky='w')
    picture_widgets.add(shadow_check)

    et_al_frame.grid(row=0, column=1, padx=int(height/54)) #20 on 1080p

    ##################################################################################################################################
    #entries
    entries_frame = Frame(sidebar)

    #scale
    scale_frame= Frame(entries_frame)

    scale_label = Label(scale_frame, text='Scale:')
    scale_label.grid(row=0, column=0)
    picture_widgets.add(scale_label)

    scale_entry = Entry(scale_frame, justify='center', font=default_font)
    scale_entry.insert(0, '5')
    scale_entry.bind('<Return>', lambda _:render())
    scale_entry.grid(row=0, column=1, sticky='we', ipadx =int(height/18)) #60 on 1080p
    picture_widgets.add(scale_entry)

    scale_frame.grid(row=0, column=0, sticky='we')

    #gif speed
    gif_speed_frame= Frame(entries_frame)

    gif_speed_label = Label(gif_speed_frame, text='GIF Speed (ms): ')
    gif_speed_label.grid(row=0, column=0)
    picture_widgets.add(gif_speed_label)

    gif_speed_entry = Entry(gif_speed_frame, justify='center', font=default_font)
    gif_speed_entry.insert(0, '500')
    gif_speed_entry.bind('<Return>', lambda _:render())
    gif_speed_entry.grid(row=0, column=1, sticky='we', ipadx=int(height/31.765)) #34 on 1080p
    picture_widgets.add(gif_speed_entry)

    gif_speed_frame.grid(row=1, column=0, sticky='we')

    #animation length
    animation_length_frame = Frame(entries_frame)

    animation_length_label = Label(animation_length_frame, text='Animation Length:')
    animation_length_label.grid(row=0, column=0, padx=1)
    picture_widgets.add(animation_length_label)

    animation_length_entry = Entry(animation_length_frame, justify='center', font=default_font)
    animation_length_entry.insert(0, '0')
    animation_length_entry.bind('<Return>', lambda _:render())
    animation_length_entry.grid(row=0, column=1, sticky='we', ipadx=int(height/43.2)) #25 on 1080p
    picture_widgets.add(animation_length_entry)

    animation_length_frame.grid(row=2, column=0, sticky='we')

    ##################################################################################################################################
    #color pickers
    color_pickers_frame = Frame(sidebar)

    #bg color (for gifs)
    bg_color_frame = Frame(color_pickers_frame)

    bg_var = StringVar(window, '#36393e')

    bg_color_image = ImageTk.PhotoImage(Image.new('RGB', (int(height/54), int(height/54)), bg_var.get())) #20x20 on 1080p
    bg_color_label = Label(bg_color_frame, image=bg_color_image)
    bg_color_label.grid(row=0, column=0, sticky='e')
    picture_widgets.add(bg_color_label)

    bg_picker = Button(bg_color_frame, text='Choose Background', command=bg_color_chooser)
    bg_picker.grid(row=0, column=1, sticky='we')
    picture_widgets.add(bg_picker)

    bg_color_frame.grid(row=0, column=0)

    #spacer
    spacer = Frame(bg_color_frame)
    spacer.grid(row=0, column=2, padx=int(height/90)) #12 on 1080p

    #mask frame
    mask_colors = Frame(color_pickers_frame)

    #mask clothing
    mask_clothing_frame = Frame(mask_colors)

    mask_clothing_preview = ImageTk.PhotoImage(Image.new('RGB', (int(height/54), int(height/54)), '#ff0000')) #20x20 on 1080p
    mask_clothing_label = Label(mask_clothing_frame, image=mask_clothing_preview)
    mask_clothing_label.grid(row=0, column=0, sticky='e')
    picture_widgets.add(mask_clothing_label)

    mask_clothing_image = Image.new('RGB', (int(height/54), int(height/54)), '#ff0000')
    mask_clothing_handler = color_picker(mask_clothing_image, mask_clothing_label, 'Mask Clothing Color')

    mask_clothing_picker = Button(mask_clothing_frame, text='Choose Clothing (Mask)', command=mask_clothing_handler.generate)
    mask_clothing_picker.grid(row=0, column=1, sticky='we')
    picture_widgets.add(mask_clothing_picker)

    mask_clothing_frame.grid(row=0, column=0)
    
    #mask accessory
    mask_accessory_frame = Frame(mask_colors)

    mask_accessory_preview = ImageTk.PhotoImage(Image.new('RGB', (int(height/54), int(height/54)), '#00ff00')) #20x20 on 1080p
    mask_accessory_label = Label(mask_accessory_frame, image=mask_accessory_preview)
    mask_accessory_label.grid(row=0, column=0, sticky='e')
    picture_widgets.add(mask_accessory_label)

    mask_accessory_image = Image.new('RGB', (int(height/54), int(height/54)), '#00ff00')
    mask_accessory_handler = color_picker(mask_accessory_image, mask_accessory_label, 'Mask Clothing Color')

    mask_accessory_picker = Button(mask_accessory_frame, text='Choose Clothing (Mask)', command=mask_accessory_handler.generate)
    mask_accessory_picker.grid(row=0, column=1, sticky='we')
    picture_widgets.add(mask_accessory_picker)

    mask_accessory_frame.grid(row=1, column=0)

    mask_colors.grid(row=1, column=0, sticky='we')

    ##################################################################################################################################
    #option menus
    option_menus_frame = Frame(sidebar)

    #mode option
    mode_list = OptionMenu(option_menus_frame, (mode_var := StringVar(window, 'Image Mode')), None, *modes.keys(), command=update_mode)
    mode_list['menu'].configure(bg='#36393e', fg='#d6d7d8')
    mode_list.grid(row=0,column=0, sticky='we')
    picture_widgets.add(mode_list)

    ##################################################################################################################################
    #render and save buttons
    finish_buttons = Frame(sidebar)

    #render
    render_button = Button(finish_buttons, text='Render', command=render, width=20)
    render_button.grid(row=0, column=0, sticky='we')
    picture_widgets.add(render_button)

    #copy to clipboard
    #clipboard_button = Button(finish_buttons, text='Copy to Clipboard', command=send_image_to_clipboard)
    #clipboard_button.grid(row=1, column=0, sticky='we')
    #picture_widgets.add(clipboard_button)

    #saves first frame if multiple
    save_image_button = Button(finish_buttons, text='Save PNG', command=save_as_image)
    save_image_button.grid(row=2, column=0, sticky='we')
    picture_widgets.add(save_image_button)

    #saves as gif for animation and gif modes
    save_gif_button = Button(finish_buttons, text='Save GIF', command=save_as_gif)
    save_gif_button.grid(row=3, column=0, sticky='we')
    picture_widgets.add(save_gif_button)

    ##################################################################################################################################
    #separator
    separator_one = Frame(sidebar, style='separator.TFrame')
    separator_one.grid(row=0, column=1, rowspan=6, sticky='ns', ipadx=1, padx=int(height/54))

    ##################################################################################################################################
    #sidebar grid
    sheet_buttons.grid(row=0, column=0)
    seek_et_al_frame.grid(row=1, column=0, pady=int(height/54)) #20 on 1080p
    entries_frame.grid(row=2, column=0)
    color_pickers_frame.grid(row=3, column=0, pady=int(height/54)) #20 on 1080p
    option_menus_frame.grid(row=4, column=0)
    finish_buttons.grid(row=5, column=0, pady=int(height/54)) #20 on 1080p
    sidebar.grid(row=0, column=0, sticky='nw', padx=int(height/108), pady=int(height/108)) #10x10 on 1080p

    ##################################################################################################################################
    #main content
    main_content = Frame(window)

    #preview
    preview_label = Label(main_content, text='Preview:')
    preview_label.grid(row=0, column=0, sticky='nw', pady=int(height/108)) #10 on 1080p

    preview_image_label = Label(main_content)
    preview_image_label.grid(row=1, column=0, sticky='nw')

    preview_sheet_sample = preview_image(preview_image_label)

    #mask preview
    preview_mask_label = Label(main_content, text='Mask:')
    preview_mask_label.grid(row=2, column=0, sticky='nw', pady=int(height/108)) #10 on 1080p

    preview_mask_image_label = Label(main_content)
    preview_mask_image_label.grid(row=3, column=0, sticky='nw')

    preview_mask_sample = preview_image(preview_mask_image_label)

    #separator
    separator_two = Frame(main_content, style='separator.TFrame')
    separator_two.grid(row=0, column=1, rowspan=4, sticky='ns', ipadx=1, padx=int(height/43.2)) #25 on 1080p

    #rendered
    rendered_label = Label(main_content, text='Rendered:')
    rendered_label.grid(row=0, column=2, sticky='nw', pady=int(height/108)) #10 on 1080p

    rendered_image = Canvas(main_content, height=0, width=0, relief=FLAT, background='#36393e', highlightthickness=0)
    rendered_image.grid(row=1, column=2, rowspan=3, sticky='nw')

    main_content.grid(row=0, column=1, sticky='nw')

    ##################################################################################################################################
    #info bar
    #info_frame = Frame(window, style='separator.TFrame')
    #info_frame.grid(row=1, column=0, columnspan=100, sticky='sew', ipady=20, ipadx=1000)

    ##################################################################################################################################
    #disable widgets
    for widg in picture_widgets:    widg.state(('disabled',))

    ##################################################################################################################################
    #timer for gif previews
    gif_timer = repeated_timer(0.5, update_render_gif)
    gif_timer.stop()
    frame = 0

    window.mainloop()
    try:    win32clipboard.CloseClipboard()
    except:    pass
