from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog, colorchooser, messagebox, font
from PIL import Image, ImageFilter, ImageTk, ImageDraw
from math import ceil, floor
from threading import Timer
from imageio import mimsave, imread
from io import BytesIO

#class for images
class image_handler:
    def __init__(self, image: Image):
        self.image = image.convert('RGBA')
    
    def set_image_from_path(self, path: str) -> None:
        self.image = Image.open(path)

    def resize_image(self, scale: int, size: int) -> Image:
        return self.image.resize(((int(self.image.size[0]/size))*size*scale, (int(self.image.size[1]/size))*size*scale), resample = Image.BOX)
    
    def silhouette(self) -> Image:
        x = self.image.size[0]
        inc = 0
        image_copy = self.image.copy()

        for i in self.image.getdata():
            if i[3] != 0:
                image_copy.putpixel((int(inc % x), int(inc / x)), (0, 0, 0, 255))
            else:
                image_copy.putpixel((int(inc % x), int(inc / x)), (0, 0, 0, 0))
            inc+= 1

        return image_copy

    def create_outline(self, scale: int, size: int) -> Image:
        silhouette = self.silhouette()

        sized_outline = silhouette.resize(((int(self.image.size[0]/size))*size*scale, (int(self.image.size[1]/size))*size*scale), resample = Image.BOX)

        bg = Image.new('RGBA', ((int(self.image.size[0]/size))*(size+2)*scale, (int(self.image.size[1]/size))*(size+2)*scale), (0, 0, 0, 0))
        bg.alpha_composite(sized_outline, (scale-1, scale-1))
        bg.alpha_composite(sized_outline, (scale+1, scale-1))
        bg.alpha_composite(sized_outline, (scale+1, scale+1))
        bg.alpha_composite(sized_outline, (scale-1, scale+1))

        return bg

    def drop_shadow(self, scale: int, size: int) -> Image:
        silhouette = self.silhouette()

        sized_image = silhouette.resize(((int(self.image.size[0]/size))*size*scale, (int(self.image.size[1]/size))*size*scale), resample = Image.BOX)

        bg = Image.new('RGBA', ((int(self.image.size[0]/size))*(size+2)*scale, (int(self.image.size[1]/size))*(size+2)*scale), (0, 0, 0, 0))
        bg.alpha_composite(sized_image, (scale, scale))
        bg = bg.filter(ImageFilter.GaussianBlur(radius=scale/2))

        return bg

    def render(self, scale: int, size: int) -> Image:
        img = self.create_outline(scale, size)
        img.alpha_composite(self.drop_shadow(scale, size))
        img.alpha_composite(self.resize_image(scale, size), (scale, scale))
        
        return img.convert('RGBA')

    def show_image(self) -> None:
        self.image.show()

#class for sheets
class sheet_handler:
    def __init__(self, sheet: Image):
        self.sheet = sheet
    
    def sheet_size(self) -> tuple:
        return self.sheet.size
    
    def get_image(self, index: int, size: int, columnspan=0) -> Image:
        length = self.sheet_size()[0]
        row = index % (length/size)
        column = floor(index / (length/size))

        return self.sheet.crop((row*size, column*size, row*size + size + columnspan*size, column*size + size + rowspan*size)).convert('RGBA')

    def close_sheet(self):
        global seek_index
        self.sheet = ''

        seek_index.num = 0
        seek_entry.delete(0, END)
        seek_entry.insert(0, hex(seek_index.num))

        preview_image.grid_remove()
        rendered_image.grid_remove()

        gif_timer.stop()

        for widg in picture_widgets:    widg.state(('disabled',))

#class for seeking
class index:
    def __init__(self, num: int):
        self.num = num
    
    def hex_to_int(self, hex: str) -> None:
        self.num = int(hex[2:], 16)

#timer class
class repeated_timer(object):
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

#tk button commands
def update_previews():
    try:
        update_preview_image()
        update_preview_mask()
    except:
        pass

def update_preview_image():
    global pic
    previewed_image = sheet.get_image(seek_index.num, size, columnspan=columnspan)
    previewed_image = previewed_image.convert('RGBA').resize(
        (int(previewed_image.size[0]*75/size), int(previewed_image.size[1]*75/size)), #size is 75 times the size divided by size (size is constant while keeping image dimensions)
        resample = Image.BOX)
    pic = ImageTk.PhotoImage(previewed_image)
    preview_image.config(image=pic)

def update_preview_mask():
    global premask
    previewed_mask = mask_sheet.get_image(seek_index.num, size, columnspan=columnspan)
    previewed_mask = previewed_mask.convert('RGBA').resize(
        (int(previewed_mask.size[0]*75/size), int(previewed_mask.size[1]*75/size)), #size is 75 times the size divided by size (size is constant while keeping image dimensions)
        resample = Image.BOX)
    premask = ImageTk.PhotoImage(previewed_mask)
    preview_mask.config(image=premask)

def update_index_frame_from_button(increment: int):
    if seek_index.num + increment > -1:    seek_index.num = seek_index.num + increment

    seek_entry.delete(0, END)
    seek_entry.insert(0, hex(seek_index.num))

    update_previews()

def update_index_frame_from_entry(event):
    if int(seek_entry.get()[2:], 16) > -1:    seek_index.hex_to_int(seek_entry.get())

    update_previews()

def open_sheet():
    global sheet, seek_index, has_mask, mask_sheet
    mask_sheet = sheet_handler('')
    has_mask = False

    opened_file = filedialog.askopenfilename()
    try:
        sheet = sheet_handler(Image.open(opened_file))
    except:
        messagebox.showwarning('Warning', 'No sheet opened.')
        return
    
    seek_index.num = 0
    seek_entry.delete(0, END)
    seek_entry.insert(0, hex(seek_index.num))

    preview_image.grid(row=1, column=0)
    preview_mask.grid_remove()
    rendered_image.grid(row=1, column=1, rowspan=3, sticky='nw')

    for widg in picture_widgets:    widg.state(('!disabled',))

    update_index_frame_from_entry(None)
    render()

def open_mask():
    global mask_sheet, seek_index, has_mask
    opened_file = filedialog.askopenfilename()
    try:
        mask_sheet = sheet_handler(Image.open(opened_file))
    except:
        messagebox.showwarning('Warning', 'No sheet opened.')
        return
    has_mask = True

    seek_index.num = 0
    seek_entry.delete(0, END)
    seek_entry.insert(0, hex(seek_index.num))

    preview_mask.grid(row=3, column=0)
    rendered_image.grid(row=1, column=1, rowspan=3, sticky='nw')

    for widg in picture_widgets:    widg.state(('!disabled',))

    update_index_frame_from_entry(None)
    render()

def close_sheets():
    global has_mask
    try:
        has_mask = False
        sheet.close_sheet()
        mask_sheet.close_sheet()
        preview_mask.grid_remove()
    except:
        gif_timer.stop()

def update_size(new_size):
    global size
    size = sizes[new_size]

    seek_index.num = 0
    seek_entry.delete(0, END)
    seek_entry.insert(0, hex(seek_index.num))

    update_previews()

def bg_color_chooser():
    global bg_color_image, bg_color_label
    if (new_color := colorchooser.askcolor(bg_var.get())[1]) != None:
        bg_var.set(new_color)

    bg_color_image = ImageTk.PhotoImage(Image.new('RGB', (20, 20), bg_var.get()))
    bg_color_label.config(image=bg_color_image)

def mask_clothing_chooser():
    global mask_clothing_image, mask_clothing_label
    if (new_color := colorchooser.askcolor(mask_clothing_var.get())[1]) != None:
        mask_clothing_var.set(new_color)

    mask_clothing_image = ImageTk.PhotoImage(Image.new('RGB', (20, 20), mask_clothing_var.get()))
    mask_clothing_label.config(image=mask_clothing_image)

def mask_accessory_chooser():
    global mask_accessory_image, mask_accessory_label
    if (new_color := colorchooser.askcolor(mask_accessory_var.get())[1]) != None:
        mask_accessory_var.set(new_color)

    mask_accessory_image = ImageTk.PhotoImage(Image.new('RGB', (20, 20), mask_accessory_var.get()))
    mask_accessory_label.config(image=mask_accessory_image)

def update_mode(new_mode):
    global columnspan, rowspan, mode
    if modes[new_mode][0] == 'png':
        mode = 0
        rowspan = 0
        columnspan = 0
    elif modes[new_mode][0] == 'gif':
        mode = 1
        rowspan = modes[new_mode][1]
        columnspan = 6
    elif  modes[new_mode][0] == 'ani':
        mode = 2
        rowspan = 0
        columnspan = 0
    elif  modes[new_mode][0] == 'over':
        mode = 3
        rowspan = 0
        columnspan = 0

    update_previews()

def update_render_image():
    global rendered_display, gif_frame, too_large
    gif_timer.stop()
    rendered_image.delete('all')

    if rendered_images[0].size[0] > (int(width/2.4)) or rendered_images[0].size[1] > (int(height/1.35)): #800x800 on 1080p
        rendered_images[0].show()
        gif_timer.stop()

        too_large = Image.new('RGBA', (300, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(too_large)
        draw.text((0, 0), 'Image too large for preview', '#d6d7d8')
        too_large = ImageTk.PhotoImage(too_large)

        rendered_image.config(width=300, height=100)
        rendered_image.create_image(0, 0, image=too_large, anchor=NW)
    else:
        if modes[mode_var.get()][0] == 'png' or modes[mode_var.get()][0] == 'over':
            rendered_image.config(width=rendered_images[0].size[0], height=rendered_images[0].size[1])
            rendered_display = ImageTk.PhotoImage(rendered_images[0])
            rendered_image.create_image(0, 0, image=rendered_display, anchor=NW)

        else:
            rendered_image.config(width=rendered_images[0].size[0], height=rendered_images[0].size[1])
            gif_frame = ImageTk.PhotoImage(rendered_images[1])
            rendered_image.create_image(0, 0, image=gif_frame, anchor=NW)

            gif_timer.interval = float(gif_speed_entry.get()) / 1000
            gif_timer.start()

def update_render_gif():
    global frame, gif_frame

    rendered_image.delete('all')
    gif_frame = ImageTk.PhotoImage(rendered_images[frame])
    rendered_image.create_image(0, 0, image=gif_frame, anchor=NW)
    if frame == len(rendered_images)-1:    frame = 0
    else:    frame+= 1

def save_as_image():
    if (file_path := filedialog.asksaveasfilename(confirmoverwrite = True, initialfile = 'sprite.png', filetypes = [('PNG', '*.png')]).rstrip('.png') + '.png') == '.png':
        return messagebox.showerror('Error', 'File not saved, invalid path.')
    try:
        rendered_images[0].save(file_path, 'PNG')
    except Exception as e:
        return messagebox.showerror('Error', 'File not saved, no render: {}'.format(str(e)))

def save_as_gif():
    if (file_path := filedialog.asksaveasfilename(confirmoverwrite = True, initialfile = 'sprite.gif', filetypes = [('GIF', '*.gif')]).rstrip('.gif') + '.gif') == '.gif':
        return messagebox.showerror('Error', 'File not saved, invalid path.')
    try:
        mimsave(file_path, frames, format='GIF', duration=float(gif_speed_entry.get()) / 1000)
    except Exception as e:
        return messagebox.showerror('Error', 'File not saved, no render: {}'.format(str(e)))

def mask_handler(image: Image) -> Image:
    masked = image.copy()
    x = masked.size[0]
    inc = 0
    for pxl in masked.getdata():
        if pxl[3] != 0:
            if pxl[0] != 0:
                masked.putpixel((int(inc % x), int(inc / x)), 
                (int(int(mask_clothing_var.get()[1:3], 16)*pxl[0]/255), int(int(mask_clothing_var.get()[3:5], 16)*pxl[0]/255), int(int(mask_clothing_var.get()[5:7], 16)*pxl[0]/255), 255))
            if pxl[1] != 0:
                masked.putpixel((int(inc % x), int(inc / x)), 
                (int(int(mask_accessory_var.get()[1:3], 16)*pxl[1]/255), int(int(mask_accessory_var.get()[3:5], 16)*pxl[1]/255), int(int(mask_accessory_var.get()[5:7], 16)*pxl[1]/255), 255))
        inc+= 1
    return masked

#rendering functions
def render():
    try:
        gif_timer.stop()
        if mode == 1:    render_gif(modes[mode_var.get()][1])
        elif mode == 2:    render_animation(animation_length_entry.get())
        elif mode == 3:    render_overview(modes[mode_var.get()][1])
        else:    render_image()
    except Exception as e:
        messagebox.showerror('Error', 'Rendering error: ' + str(e))

    update_render_image()

def render_image():
    global rendered
    if not has_mask:
        rendered_images.clear()

        rendered = image_handler(sheet.get_image(seek_index.num, size, columnspan=columnspan))
        rendered = rendered.render(int(scale_entry.get()), size)

        rendered_images.append(rendered)
    else:
        rendered_images.clear()

        start_image = sheet.get_image(seek_index.num, size, columnspan=columnspan)
        mask = mask_handler(mask_sheet.get_image(seek_index.num, size, columnspan=columnspan))
        start_image.alpha_composite(mask)

        start_image = image_handler(start_image)
        rendered = start_image.render(int(scale_entry.get()), size)

        rendered_images.append(rendered)

def render_gif(rows):
    global rendered_images, frames
    rendered_images.clear()
    rows+= 1
    scale = int(scale_entry.get())
    gif_base = Image.new('RGBA', (4*(size+2)*scale, rows*(size+2)*scale), bg_var.get())
    gif_images = [gif_base.copy()] + [gif_base.copy()]
    sheet_sample = sheet.get_image(seek_index.num, size, columnspan=columnspan)

    if not has_mask:
        for row in range(rows):
            second_walk = False

            #still frame
            still_image = image_handler(sheet_sample.crop((0*size, row*size, 0*size+size, row*size+size))).render(scale, size)
            gif_images[0].alpha_composite(still_image, (0*(size+2)*scale, row*(size+2)*scale))
            gif_images[1].alpha_composite(still_image, (0*(size+2)*scale, row*(size+2)*scale))

            #first walk frame
            walk_one = image_handler(sheet_sample.crop((1*size, row*size, 1*size+size, row*size+size))).render(scale, size)
            gif_images[0].alpha_composite(walk_one, (1*(size+2)*scale, row*(size+2)*scale))

            #second walk frame (check if exists as well)
            walk_two = image_handler(sheet_sample.crop((2*size, row*size, 2*size+size, row*size+size)))
            for i in walk_two.image.convert('RGBA').getdata():
                if i[3] != 0:    second_walk = True
            walk_two = walk_two.render(scale, size)
            if second_walk:    gif_images[1].alpha_composite(walk_two, (1*(size+2)*scale, row*(size+2)*scale))
            else:    gif_images[1].alpha_composite(walk_one, (1*(size+2)*scale, row*(size+2)*scale))

            #first attack frame
            attack_one = image_handler(sheet_sample.crop((4*size, row*size, 4*size+size, row*size+size))).render(scale, size)
            gif_images[0].alpha_composite(attack_one, (2*(size+2)*scale, row*(size+2)*scale))

            #final attack frame
            attack_combo = Image.new('RGBA', (2*size, size), (0, 0, 0, 0))
            attack_two_one = sheet_sample.crop((5*size, row*size, 5*size+size, row*size+size))
            attack_combo.alpha_composite(attack_two_one, (0*size, 0))
            attack_two_two = sheet_sample.crop((6*size, row*size, 6*size+size, row*size+size))
            attack_combo.alpha_composite(attack_two_two, (1*size, 0))
            attack_combo = image_handler(attack_combo).render(scale, size)
            gif_images[1].alpha_composite(attack_combo, (2*(size+2)*scale, row*(size+2)*scale))

    else:
        mask_sample = mask_sheet.get_image(seek_index.num, size, columnspan=columnspan)
        for row in range(rows):
            second_walk = False

            #still frame
            still_initial = sheet_sample.crop((0*size, row*size, 0*size+size, row*size+size))
            still_mask = mask_handler(mask_sample.crop((0*size, row*size, 0*size+size, row*size+size)))
            still_initial.alpha_composite(still_mask, (0, 0))

            still_image = image_handler(still_initial).render(scale, size)
            gif_images[0].alpha_composite(still_image, (0*(size+2)*scale, row*(size+2)*scale))
            gif_images[1].alpha_composite(still_image, (0*(size+2)*scale, row*(size+2)*scale))

            #first walk frame
            walk_one_initial = sheet_sample.crop((1*size, row*size, 1*size+size, row*size+size))
            walk_one_mask = mask_handler(mask_sample.crop((1*size, row*size, 1*size+size, row*size+size)))
            walk_one_initial.alpha_composite(walk_one_mask, (0, 0))

            walk_one = image_handler(walk_one_initial).render(scale, size)
            gif_images[0].alpha_composite(walk_one, (1*(size+2)*scale, row*(size+2)*scale))

            #second walk frame (check if exists as well)
            walk_two_initial = sheet_sample.crop((2*size, row*size, 2*size+size, row*size+size))
            walk_two_mask = mask_handler(mask_sample.crop((2*size, row*size, 2*size+size, row*size+size)))
            walk_two_initial.alpha_composite(walk_two_mask, (0, 0))

            walk_two = image_handler(walk_two_initial)
            for i in walk_two.image.convert('RGBA').getdata():
                if i[3] != 0:    second_walk = True
            walk_two = walk_two.render(scale, size)
            if second_walk:    gif_images[1].alpha_composite(walk_two, (1*(size+2)*scale, row*(size+2)*scale))
            else:    gif_images[1].alpha_composite(walk_one, (1*(size+2)*scale, row*(size+2)*scale))

            #first attack frame
            attack_one_initial = sheet_sample.crop((4*size, row*size, 4*size+size, row*size+size))
            attack_one_mask = mask_handler(mask_sample.crop((4*size, row*size, 4*size+size, row*size+size)))
            attack_one_initial.alpha_composite(attack_one_mask, (0, 0))

            attack_one = image_handler(attack_one_initial).render(scale, size)
            gif_images[0].alpha_composite(attack_one, (2*(size+2)*scale, row*(size+2)*scale))

            #final attack frame
            attack_combo = Image.new('RGBA', (2*size, size), (0, 0, 0, 0))

            attack_two_one_initial = sheet_sample.crop((5*size, row*size, 5*size+size, row*size+size))
            attack_two_one_mask = mask_handler(mask_sample.crop((5*size, row*size, 5*size+size, row*size+size)))
            attack_two_one_initial.alpha_composite(attack_two_one_mask, (0*size, 0))

            attack_combo.alpha_composite(attack_two_one_initial, (0*size, 0))

            attack_two_two_initial = sheet_sample.crop((6*size, row*size, 6*size+size, row*size+size))
            attack_two_two_mask = mask_handler(mask_sample.crop((6*size, row*size, 6*size+size, row*size+size)))
            attack_two_two_initial.alpha_composite(attack_two_two_mask, (1*size, 0))

            attack_combo.alpha_composite(attack_two_two_initial, (1*size, 0))

            attack_combo = image_handler(attack_combo).render(scale, size)

            gif_images[1].alpha_composite(attack_combo, (2*(size+2)*scale, row*(size+2)*scale))

    rendered_images = gif_images.copy()
    frames = []

    frame = 0
    for img in gif_images:
        buffer = BytesIO()

        img = rendered_images[frame].convert('RGB')
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
        length = int(sheet.sheet_size()[0]/size) * int(sheet.sheet_size()[1]/size)
    
    animation_base = Image.new('RGBA', ((size+2)*scale, (size+2)*scale), bg_var.get())
    for garb in range(length):
        animation_frames.append(animation_base.copy())

    if not has_mask:
        for i in range(len(animation_frames)):
            frame_image = image_handler(sheet.get_image(start_index+i, size, columnspan=0))
            animation_frames[i].alpha_composite(frame_image.render(scale, size), (0, 0))
    else:
        for i in range(len(animation_frames)):
            frame_initial = sheet.get_image(start_index+i, size, columnspan=0)
            frame_mask = mask_handler(mask_sheet.get_image(start_index+i, size, columnspan=0))
            frame_initial.alpha_composite(frame_mask, (0, 0))

            frame_image = image_handler(frame_initial).render(scale, size)
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
    rows = int(sheet.sheet_size()[1]/size)

    nonempty_rows = []
    for i in range(rows):
        for pxl in sheet.get_image(i*(sheet.sheet_size()[0]/size), size, columnspan=0).convert('RGBA').getdata():
            if pxl[3] != 0:
                nonempty_rows.append(i)
                break

    maxcolumns = 6
    if len(nonempty_rows) < 6:    maxcolumns = len(nonempty_rows)

    image_base = Image.new('RGBA', ((size+2)*scale*maxcolumns, ceil(len(nonempty_rows)/maxcolumns/skip)*(size+2)*scale))

    if skip != 1:
        nonempty_rows = nonempty_rows[::3]

    row, column = 0, 0
    if not has_mask:
        for i in range(len(nonempty_rows)):
            next_image = image_handler(sheet.get_image(nonempty_rows[i]*(sheet.sheet_size()[0]/size), size, columnspan=0)).render(scale, size)
            image_base.alpha_composite(next_image, ((size+2)*scale*column, (size+2)*scale*row))

            if column == 5:
                column = 0
                row+= 1
            else:
                column+= 1
    else:
        for i in range(len(nonempty_rows)):
            inital_image = sheet.get_image(nonempty_rows[i]*(sheet.sheet_size()[0]/size), size, columnspan=0)
            mask = mask_handler(mask_sheet.get_image(nonempty_rows[i]*(sheet.sheet_size()[0]/size), size, columnspan=0))
            inital_image.alpha_composite(mask, (0, 0))

            next_image = image_handler(inital_image).render(scale, size)
            image_base.alpha_composite(next_image, ((size+2)*scale*column, (size+2)*scale*row))

            if column == 5:
                column = 0
                row+= 1
            else:
                column+= 1    

    rendered_images.append(image_base)

def render_whole():
    global rendered_images, too_large
    if modes[mode_var.get()][0] != 'png':    return messagebox.showerror('Error', 'Must be in image mode to render whole sheet.')

    rendered_images.clear()
    rendered_image.delete('all')
    scale = int(scale_entry.get())

    whole_sheet_render = Image.new('RGBA', (int(sheet.sheet_size()[0]/size)*(size+2)*scale, int(sheet.sheet_size()[1]/size)*(size+2)*scale), (0, 0, 0, 0))
    sheet_length = int(sheet.sheet_size()[0]/size) * int(sheet.sheet_size()[1]/size)
    sheet_width = int(sheet.sheet_size()[0])

    if not has_mask:
        for i in range(sheet_length):
            row = int(i % (sheet_width/size))
            column = floor(i / (sheet_width/size))

            next_image = image_handler(sheet.get_image(i, size, columnspan=0)).render(scale, size)
            whole_sheet_render.alpha_composite(next_image, ((size+2)*scale*row, (size+2)*scale*column))
    else:
        for i in range(sheet_length-1):
            row = int(i % (sheet_width/size))
            column = floor(i / (sheet_width/size))

            initial_image = sheet.get_image(i, size, columnspan=0)
            mask = mask_handler(mask_sheet.get_image(i, size, columnspan=0))
            initial_image.alpha_composite(mask, (0, 0))

            next_image = image_handler(initial_image).render(scale, size)
            whole_sheet_render.alpha_composite(next_image, ((size+2)*scale*row, (size+2)*scale*column))

    rendered_images.append(whole_sheet_render)
    update_render_image()

if __name__ == '__main__':
    #window setup
    window = Tk()
    window.title('Sprite Renderer')

    #compatibility sizing
    width = window.winfo_screenwidth()
    height = window.winfo_screenheight()

    window.geometry('{}x{}'.format(int(width*0.859), int(height*0.6296))) #1650x680 on 1080p

    #vars
    sheet = sheet_handler('')
    mask_sheet = sheet_handler('')
    sizes = {'8x8': 8, '16x16': 16, '32x32': 32, '64x64': 64}
    modes = {'Image Mode': ('png',), 'Pet or Enemy Mode': ('gif', 0), 'Player Skin Mode': ('gif', 2), 'Animation Mode': ('ani',), 'Full Overview': ('over', 1), 'Quick Skin Overview': ('over', 3)}
    mode = 0
    size, columnspan, rowspan = 8, 0, 0
    rendered_images, picture_widgets = [], set()
    has_mask = False

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
        insertcolor='#d6d7d8')

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

    ##################################################################################################################################
    #seeking
    seek_index = index(0)
    index_frame = Frame(sidebar)

    seek_up = Button(index_frame, text='🡅', command=lambda: update_index_frame_from_button(-ceil(sheet.sheet_size()[0]/size)), style='seek.TButton')
    seek_up.grid(row=0, column=1)
    picture_widgets.add(seek_up)

    seek_left = Button(index_frame, text='🡄', command=lambda: update_index_frame_from_button(-1), style='seek.TButton')
    seek_left.grid(row=1, column=0)
    picture_widgets.add(seek_left)

    seek_entry = Entry(index_frame, justify='center', width=6, font=default_font)
    seek_entry.insert(0, hex(seek_index.num))
    seek_entry.bind('<Return>', update_index_frame_from_entry)
    seek_entry.grid(row=1, column=1, ipady=int(height/180)) #6 on 1080p
    picture_widgets.add(seek_entry)

    seek_right = Button(index_frame, text='🡆', command=lambda: update_index_frame_from_button(1), style='seek.TButton')
    seek_right.grid(row=1, column=2)
    picture_widgets.add(seek_right)

    seek_down = Button(index_frame, text='🡇', command=lambda: update_index_frame_from_button(ceil(sheet.sheet_size()[0]/size)), style='seek.TButton')
    seek_down.grid(row=2, column=1)
    picture_widgets.add(seek_down)

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

    bg_picker = Button(bg_color_frame, text='Choose Background (GIF)', command=bg_color_chooser)
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

    mask_clothing_var = StringVar(window, '#ff0000')

    mask_clothing_image = ImageTk.PhotoImage(Image.new('RGB', (int(height/54), int(height/54)), mask_clothing_var.get())) #20x20 on 1080p
    mask_clothing_label = Label(mask_clothing_frame, image=mask_clothing_image)
    mask_clothing_label.grid(row=0, column=0, sticky='e')
    picture_widgets.add(mask_clothing_label)

    bg_picker = Button(mask_clothing_frame, text='Choose Clothing (Mask)', command=mask_clothing_chooser)
    bg_picker.grid(row=0, column=1, sticky='we')
    picture_widgets.add(bg_picker)

    mask_clothing_frame.grid(row=0, column=0)
    
    #mask accessory
    mask_accessory_frame = Frame(mask_colors)

    mask_accessory_var = StringVar(window, '#00ff00')

    mask_accessory_image = ImageTk.PhotoImage(Image.new('RGB', (int(height/54), int(height/54)), mask_accessory_var.get())) #20x20 on 1080p
    mask_accessory_label = Label(mask_accessory_frame, image=mask_accessory_image)
    mask_accessory_label.grid(row=0, column=0, sticky='e')
    picture_widgets.add(mask_accessory_label)

    mask_accessory_picker = Button(mask_accessory_frame, text='Choose Accessory (Mask)', command=mask_accessory_chooser)
    mask_accessory_picker.grid(row=0, column=1, sticky='we')
    picture_widgets.add(mask_accessory_picker)

    mask_accessory_frame.grid(row=1, column=0)
    
    mask_colors.grid(row=1, column=0, sticky='we')

    ##################################################################################################################################
    #option menus
    option_menus_frame = Frame(sidebar)

    #size options
    size_list = OptionMenu(option_menus_frame, (size_var := StringVar(window, '8x8')), None, *sizes.keys(), command=update_size)
    size_list['menu'].configure(bg='#36393e', fg='#d6d7d8')
    size_list.grid(row=0, column=0, sticky='we')
    picture_widgets.add(size_list)

    #mode option
    mode_list = OptionMenu(option_menus_frame, (mode_var := StringVar(window, 'Image Mode')), None, *modes.keys(), command=update_mode)
    mode_list['menu'].configure(bg='#36393e', fg='#d6d7d8')
    mode_list.grid(row=1,column=0, sticky='we')
    picture_widgets.add(mode_list)

    ##################################################################################################################################
    #render and save buttons
    finish_buttons = Frame(sidebar)

    #render
    render_button = Button(finish_buttons, text='Render', command=render, width=20)
    render_button.grid(row=0, column=0, sticky='we')
    picture_widgets.add(render_button)

    #render whole sheet
    render_whole_button = Button(finish_buttons, text='Render Whole Sheet', command=render_whole)
    render_whole_button.grid(row=1, column=0, sticky='we')
    picture_widgets.add(render_whole_button)

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
    separator_two = Frame(sidebar, style='separator.TFrame')
    separator_two.grid(row=0, column=1, rowspan=6, sticky='ns', ipadx=1, padx=int(height/54))

    ##################################################################################################################################
    #sidebar grid
    sheet_buttons.grid(row=0, column=0)
    index_frame.grid(row=1, column=0, pady=int(height/54)) #20 on 1080p
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

    preview_image = Label(main_content)
    preview_image.grid(row=1, column=0, sticky='nw')

    #mask preview
    preview_mask_label = Label(main_content, text='Mask:')
    preview_mask_label.grid(row=2, column=0, sticky='nw', pady=int(height/108)) #10 on 1080p

    preview_mask = Label(main_content)
    preview_mask.grid(row=3, column=0, sticky='nw')

    #rendered
    rendered_label = Label(main_content, text='Rendered:')
    rendered_label.grid(row=0, column=1, sticky='nw', pady=int(height/108)) #10 on 1080p

    rendered_image = Canvas(main_content, height=0, width=0, relief=FLAT, background='#36393e', highlightthickness=0)
    rendered_image.grid(row=1, column=1, rowspan=3, sticky='nw')

    main_content.grid(row=0, column=1, sticky='nw')

    ##################################################################################################################################
    #disable widgets
    for widg in picture_widgets:    widg.state(('disabled',))

    ##################################################################################################################################
    #timer for gif previews
    gif_timer = repeated_timer(0.5, update_render_gif)
    gif_timer.stop()
    frame = 0

    window.mainloop()