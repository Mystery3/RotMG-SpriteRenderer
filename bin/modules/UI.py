import tkinter as tk
import tkinter.colorchooser as tkcolor
import tkinter.filedialog as tkfile
import tkinter.font as tkfont
import tkinter.ttk as ttk
import tkinter.messagebox as tkmb
import tktooltip as tktt # shoutout this

import PIL.Image as Img
import PIL.ImageTk as ImgTk
import PIL.ImageGrab as ImgGr

import os.path, pickle, traceback

from . import Rendering, IO

class IndexWidget(ttk.Frame):
    def __init__(self, *args, index: tk.StringVar, sheet: IO.SheetVar, width: tk.StringVar, **kwargs):
        ttk.Frame.__init__(self, *args, **kwargs)

        self._index = index
        self._sheet = sheet
        self._width = width
        
        self._Eentry = ttk.Entry(self, textvariable = self._index, style = 'index.TEntry')
        self._Eentry.grid(row = 1, column = 1)

        self._Bup = ttk.Button(self, command = self._up, text = '🡅', style = 'index.TButton')
        self._Bup.grid(row = 0, column = 1)

        self._Bleft = ttk.Button(self, command = self._left, text = '🡄', style = 'index.TButton')
        self._Bleft.grid(row = 1, column = 0)

        self._Bright = ttk.Button(self, command = self._right, text = '🡆', style = 'index.TButton')
        self._Bright.grid(row = 1, column = 2)

        self._Bdown = ttk.Button(self, command = self._down, text = '🡇', style = 'index.TButton')
        self._Bdown.grid(row = 2, column = 1)

    def _change_index(self, delta: int) -> None:
        old_index = self._index.get()
        new_index = IO.index_filter(old_index) + delta

        if old_index.startswith('0x') or old_index.startswith('-0x'):
            self._index.set(hex(new_index))
        else:
            self._index.set(str(new_index))

    def _up(self) -> None:
        delta = -1 * (self._sheet.get().size[0] // int(self._width.get()))
        self._change_index(delta)

    def _left(self) -> None:
        self._change_index(-1)

    def _right(self) -> None:
        self._change_index(1)

    def _down(self) -> None:
        delta = self._sheet.get().size[0] // int(self._width.get())
        self._change_index(delta)

class DropDown(ttk.Button):
    def __init__(self, *args, up_text: str = 'Show More', up_image: tk.PhotoImage = None, 
                              down_text: str = 'Show Less', down_image: tk.PhotoImage = None, default = False, **kwargs):
        ttk.Button.__init__(self, *args, command = self.toggle, **kwargs)
        
        self.widgets = []
        self._dropped = default
        self._state_map = {
            False: {'text': up_text, 'image': up_image},
            True: {'text': down_text, 'image': down_image}
        }

        self._update()

    def _update(self):
        self.configure(**self._state_map[self._dropped])

        for widget in self.widgets:
            if self._dropped:
                widget.grid()
            else:
                widget.grid_remove()

    def add(self, widget: tk.Widget):
        self.widgets.append(widget)
        self._update()

    def remove(self, widget: tk.Widget):
        self.widgets.remove(widget)
        self._update()

    def toggle(self):
        self._dropped = self._dropped ^ True
        self._update()

class ColorPicker(ttk.Button):
    def __init__(self, *args, color_var: tk.StringVar, hex: bool = True, **kwargs):
        ttk.Button.__init__(self, *args, command = self._choose, compound = tk.LEFT, **kwargs)

        self._color_var = color_var
        self._hex = hex
        
        self._update()

    def _choose(self) -> None:
        new_color = tkcolor.askcolor(self._color_var.get())[self._hex]

        if new_color:
            self._color_var.set(new_color)
        
        self._update()

    def _update(self) -> None:
        self._image = ImgTk.PhotoImage(Img.new('RGB', (27, 27), self._color_var.get()))

        self.configure(image = self._image)

class ScrollableFrame(ttk.Frame):
    '''
    Place widgets in the contained Frame.
    height is a required parameter
    '''
    canvas_style = {}

    def __init__(self, *args, **kwargs):
        ttk.Frame.__init__(self, *args, **kwargs)
        height = kwargs['height']
    
        self.Canvas = tk.Canvas(self, height = height, **self.canvas_style)
        self.Canvas.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)

        self._SBscrollbar = ttk.Scrollbar(self, orient = tk.VERTICAL, command = self.Canvas.yview)
        self.Canvas.configure(yscrollcommand = self._SBscrollbar.set)
        self._SBscrollbar.place(relx = 1, rely = 0, width = 14, relheight = 1, anchor = tk.NE)
        
        self.Frame = ttk.Frame(self.Canvas)
        self.Canvas.create_window((0, 0), anchor = tk.NW, window = self.Frame)
        
        self.Frame.bind('<Configure>', lambda _: self.Canvas.configure(scrollregion = self.Canvas.bbox('all')))
        self.Frame.bind('<Configure>', lambda _: self.Canvas.configure(width = self.Canvas.bbox('all')[2]), True)
        self.Frame.bind('<Configure>', lambda _: self.configure(width = self.Canvas.bbox('all')[2] + 17), True)
        self.Canvas.bind('<MouseWheel>', lambda event: self.Canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units'))

class TextilePicker(ttk.Button):
    def __init__(self, *args, image_var: IO.ImgVar, textiles: dict[int, list[Img.Image]], icon_set: dict[str, Img.Image], config: IO.Config, **kwargs): 
        ttk.Button.__init__(self, *args, command = self._choose, compound = tk.LEFT, **kwargs)

        self._image_var = image_var
        self._textile = textiles

        self._image = ImgTk.PhotoImage(self._image_var.get().resize((27, 27), resample = Img.BOX)) 
        self._image_big = ImgTk.PhotoImage(self._image_var.get().resize((100, 100), resample = Img.BOX))

        self._Ipalette = ImgTk.PhotoImage(icon_set['palette'])
        self._Ifolder = ImgTk.PhotoImage(icon_set['folder'])

        self.config = config

        self.configure(image = self._image)

    def _choose(self) -> None:
        self._TLwindow = tk.Toplevel(self, name = str(self.winfo_name())) # named for uniqueness, only 1 can be open
        self._TLwindow.title(self['text'])
        self._TLwindow.focus_set()

        height = 250

        self._Fmain = ttk.Frame(self._TLwindow)
        self._Fmain.pack(expand = True, fill = tk.BOTH)

        self._NBnotebook = ttk.Notebook(self._Fmain)
        self._NBnotebook.enable_traversal()
        self._NBnotebook.grid(row = 0, column = 0, rowspan = 2)

        self._Lchoose_image = ttk.Label(self._Fmain, image = self._image_big) 
        self._Lchoose_image.grid(row = 0, column = 1, sticky = tk.S)

        self._Fbuttons = ttk.Frame(self._Fmain)
        self._Fbuttons.grid(row = 1, column = 1, padx = 20, pady = 20)

        self._Bchoose_color = ttk.Button(self._Fbuttons, text = 'Choose Color', command = self._set_color, image = self._Ipalette, compound = tk.LEFT)
        self._Bchoose_color.grid(row = 0, column = 0)
        self._TTchoose_color = tktt.ToolTip(self._Bchoose_color, 
                        'Ctrl + 1. Up/Down to scroll.',
                        0.5, False, 100)

        self._Bload_cloth = ttk.Button(self._Fbuttons, text = 'Load Cloth', command = self._set_file, image = self._Ifolder, compound = tk.LEFT)
        self._Bload_cloth.grid(row = 1, column = 0)
        self._TTload_cloth = tktt.ToolTip(self._Bload_cloth, 
                        'Ctrl + o',
                        0.5, False, 100)

        self._frames = {}  # keep a reference to frames, images
        self._buttons = {} # and buttons to avoid garbage collection
        self._images = {}
        self._tk_images = {}

        for size, images in self._textile.items():
            self._frames[size] = ScrollableFrame(self._NBnotebook, height = height)
            self._buttons[size] = [None] * len(images)
            self._images[size] = [None] * len(images)
            self._tk_images[size] = [None] * len(images)

            self._frames[size].Frame.configure(style = 'graphic.TFrame')

            for i, image in enumerate(images):
                self._images[size][i] = image
                self._tk_images[size][i] = ImgTk.PhotoImage(image.resize((35, 35), resample = Img.BOX))

                self._buttons[size][i] = ttk.Button(self._frames[size].Frame,
                                                    image = self._tk_images[size][i],
                                                    command = lambda image = image,: self._set(image)) # image = image to avoid for loop silly business
                self._buttons[size][i].grid(row = i // 8, column = i % 8)

            self._NBnotebook.add(self._frames[size], text = f'{size}x{size}')

        self._TLwindow.bind('<MouseWheel>', # lol vvv
                            lambda event: self._TLwindow.nametowidget(self._NBnotebook.select()).Canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units'))
        
        self._TLwindow.bind('<Up>', lambda _: self._TLwindow.nametowidget(self._NBnotebook.select()).Canvas.yview_scroll((-1), 'units'))
        self._TLwindow.bind('<Down>', lambda _: self._TLwindow.nametowidget(self._NBnotebook.select()).Canvas.yview_scroll((1), 'units'))

        self._TLwindow.bind('<Control-1>', self._Bchoose_color.focus_set)
        self._TLwindow.bind('<Control-v>', self._set_paste)

    def _set(self, image: Img.Image) -> None:
        self._image_var.set(image.convert('RGBA'))
        
        self._image = ImgTk.PhotoImage(self._image_var.get().resize((27, 27), resample = Img.BOX))
        self._image_big = ImgTk.PhotoImage(self._image_var.get().resize((100, 100), resample = Img.BOX))

        self.configure(image = self._image)
        self._Lchoose_image.configure(image = self._image_big)

    def _set_color(self) -> None:
        new_color = tkcolor.askcolor()[1]

        if new_color:
            self._set(Img.new('RGBA', (10, 10), new_color))

        self._TLwindow.focus()

    def _set_file(self) -> None:
        path = tkfile.askopenfilename(initialdir = self.config.data['textiles_dir'], filetypes = (('Image (png, tiff, tif, jpeg, jpg)', ('*.png', '*.tiff', '*.tif', '*.jpeg', '*.jpg')),))

        if path:
            try:
                self._set(Img.open(path))
            except Exception as e:
                IO.InfobarAlert(True, e, 'Error opening textile file.')

        self._TLwindow.focus()

    def _set_paste(self, event = None) -> None:
        image = ImgGr.grabclipboard()

        if image:
            self._set(image)
        else:
            IO.InfobarAlert(False, None, 'Paste Failed.')

class SelectPreview(ttk.Frame):
    def __init__(self, *args, sheet: IO.SheetVar, index: tk.StringVar, width: tk.StringVar, height: tk.StringVar, 
                 text: str, img_padding: int, outline: Img.Image, mask = False, **kwargs):
        ttk.Frame.__init__(self, *args, style = 'graphic.TFrame', **kwargs)
    
        self._sheet = sheet
        self._index = index
        self._width = width
        self._height = height
        self._text = text
        self._img_padding = img_padding
        self._outline_template = outline
        self._mask = mask # bool
        self._last_size = 0

        self._Limage = ttk.Label(self, style = 'graphic.TLabel')
        self._Limage.place(relx = 0.5, rely = 0.5, anchor = tk.CENTER)

        self._Ltext = ttk.Label(self, text = self._text, style = 'graphic.TLabel')
        self._Ltext.place(x = 10, y = 5)

    def _update(self, e = None) -> None:
        if self._last_size == 0:
            self.bind('<Configure>', lambda e: self._update(e))

        if e != None: # called by size change or external?
            if self._last_size == self.winfo_height():
                return
            self._last_size = self.winfo_height()
        
        index = IO.index_filter(self._index.get()) 
        width = int(self._width.get())
        height = int(self._height.get())

        size = (self.winfo_height() - self._Ltext.winfo_height(),) * 2        
        image = self._sheet.get().get_sprite(index, width, height, padding = self._img_padding)[self._mask]

        if size[0] < 5: # for startup
            image = image.resize((5, 5), resample = Img.BOX)
        else:
            image = image.resize(size, resample = Img.BOX)
            scale_factor = size[0] // (2 * self._img_padding + 1)
            outline = self._outline_template.resize((scale_factor,) * 2, resample = Img.BOX)
            image.alpha_composite(outline, (size[0] // 2 - scale_factor // 2,) * 2) # basing off of factor and padding inconsistent since sprite sizes inconsistent, this works better

        self._preview = ImgTk.PhotoImage(IO.alpha_filter(image))
        #self._preview = ImgTk.PhotoImage(image) #slight visual downgrade but better performance
        self._Limage.configure(image = self._preview)

class RenderOutput(ttk.Frame):
    canvas_style = {}

    def __init__(self, *args, rendered_images: IO.ListVar, speeds: tk.StringVar, mode: tk.StringVar, **kwargs):
        ttk.Frame.__init__(self, *args, style = 'graphic.TFrame', **kwargs)

        self._rendered_images = rendered_images
        self._speeds = speeds
        self._mode = mode

        self._current_frame = 0
        self._last_running = 'hi'

        self._Cimage = tk.Canvas(self, width = 100, height = 100, **self.canvas_style)
        self._Cimage.grid(row = 0, column = 0, rowspan = 2)

        self._Ltext = ttk.Label(self, text = 'Render', style = 'graphic.TLabel')
        self._Ltext.grid(row = 0, column = 0, padx = 10, pady = 5, sticky = tk.NW)

        self._SBv_scrollbar = ttk.Scrollbar(self, orient = tk.VERTICAL, command = self._Cimage.yview, style = 'graphic.Vertical.TScrollbar')
        self._SBv_scrollbar.grid(row = 0, column = 1, rowspan = 2, sticky = 'nse') # no tk var for nse :(
        
        self._SBh_scrollbar = ttk.Scrollbar(self, orient = tk.HORIZONTAL, command = self._Cimage.xview, style = 'graphic.Horizontal.TScrollbar')
        self._SBh_scrollbar.grid(row = 2, column = 0, columnspan = 2, sticky = 'sew') # no tk var for sew :(

        self._Cimage.configure(xscrollcommand = self._SBh_scrollbar.set, yscrollcommand = self._SBv_scrollbar.set)

        self.bind('<Configure>', lambda _: self._Cimage.configure(width = self.winfo_width() - self._SBv_scrollbar.winfo_width(), 
                                                                  height = self.winfo_height() - self._SBh_scrollbar.winfo_height()))# - self._Ltext.winfo_height() - 10))
        self._Cimage.bind('<MouseWheel>', lambda event: self._Cimage.yview_scroll(int(-1 * (event.delta / 120)), 'units'))
        self._Cimage.bind('<Shift-MouseWheel>', lambda event: self._Cimage.xview_scroll(int(-1 * (event.delta / 120)), 'units'))

    def reset_view(self) -> None:
        self._Cimage.xview('moveto', 0)
        self._Cimage.yview('moveto', 0)

    def _place_image(self, image: ImgTk.PhotoImage) -> None:
        self._Cimage.configure(scrollregion = (0, -self._Ltext.winfo_height() - 10, image.width(), image.height()))

        self._Cimage.delete('all')
        self._Cimage.create_image(0, 0, image = image, anchor = tk.NW)

    def _update(self) -> None:
        self._Cimage.after_cancel(self._last_running)
        
        self._current_frame = 0

        self._filtered_render = IO.alpha_filter(self._rendered_images.get()[0]) # much faster even for large images
        self._current_render = ImgTk.PhotoImage(self._filtered_render)

        self._place_image(self._current_render)
        
        if self._mode.get().strip() in ('Entity', 'Animation'):
            self._length = len(self._rendered_images.get())
            self._intervals = IO.speed_filter(self._speeds.get(), self._length)

            self._last_running = self._Cimage.after(self._intervals[0], self._next_frame)
    
    def _next_frame(self) -> None:
        self._current_frame+= 1

        if self._current_frame == len(self._rendered_images.get()):
            self._current_frame = 0

        self._current_render = ImgTk.PhotoImage(self._rendered_images.get()[self._current_frame])
        self._place_image(self._current_render)

        self._last_running = self._Cimage.after(self._intervals[self._current_frame], self._next_frame)

class InfoBar(ttk.Frame):
    def __init__(self, *args, sheet: IO.SheetVar, sheet_name: tk.StringVar, mask_name: tk.StringVar, config: IO.Config, 
                 settings_image: ImgTk.PhotoImage, warning_image: ImgTk.PhotoImage, error_image: ImgTk.PhotoImage, **kwargs):
        ttk.Frame.__init__(self, *args, style = 'infobar.TFrame', **kwargs)

        self.settings = None

        self._sheet = sheet
        self._sheet_name = sheet_name
        self._mask_name = mask_name
        self._config = config
        self._settings_image = settings_image
        self._warning_image = warning_image
        self._error_image = error_image

        self._sheet_info = tk.StringVar(self, value = '')
        self._exception_info = tk.StringVar(self, value = '')

        self._Lsheet_info = ttk.Label(self, textvariable = self._sheet_info, style = 'infobar.TLabel')
        self._Lsheet_info.pack(side = tk.LEFT, padx = 10) # not sure why grid didn't work even with columnconfigure

        self._Bexception_info = ttk.Button(self, compound = tk.LEFT, textvariable = self._exception_info, command = self.clear_alert, style = 'alert.TButton')
        self._Bexception_info.pack(side = tk.LEFT, expand = True, fill = 'both')

        self._Bsettings = ttk.Button(self, image = self._settings_image, command = self._open_settings, style = 'settings.TButton')
        self._Bsettings.pack(side = tk.RIGHT)

        self._update()
        self.clear_alert()

    def _update(self) -> None:
        if self._sheet_name.get():
            sheet_name = self._sheet_name.get().rpartition('/')[2]
            size = f'{self._sheet.get().size[0]}x{self._sheet.get().size[1]}  |  ' # pipe added as separator
        else:
            sheet_name = ''
            size = ''

        if self._mask_name.get():
            mask_name = f', {self._mask_name.get().rpartition("/")[2]}' # comma added here as separator; can use 2 pairs of ' in 3.12
        else:
            mask_name = ''

        self._sheet_info.set(size + sheet_name + mask_name)

    def show_alert(self, alert: IO.InfobarAlert) -> None:
        self._exception_info.set(' ' + alert.text)
        if alert.is_error:
            self._Bexception_info.configure(image = self._error_image)
        else:
            self._Bexception_info.configure(image = self._warning_image)

    def clear_alert(self) -> None:
        self._exception_info.set('')
        self._Bexception_info.configure(image = '')
        self.master.focus_set()

    def _open_settings(self) -> None:
        self.settings = Settings(self, name = 'settings', config = self._config) # named for uniqueness, only 1 can be open

class Settings(tk.Toplevel):
    restart_func = lambda: None
    menu_style = None
    font = None

    def __init__(self, *args, config: IO.Config, **kwargs):
        tk.Toplevel.__init__(self, *args, **kwargs)
        self.title('Settings')
        self.focus_set()

        self._config = config

        self._Vstyletype = tk.StringVar(self, self._config.data['styletype'])
        self._Vfontsize = tk.IntVar(self, self._config.data['fontsize'])
        self._Vpadding = tk.IntVar(self, self._config.data['padding'])
        self._Vautorender = tk.BooleanVar(self, self._config.data['autorender'])
        self._Vshow_tooltips = tk.BooleanVar(self, self._config.data['show_tooltips'])
        self._Vsheets_dir = tk.StringVar(self, self._config.data['sheets_dir'])
        self._Vrenders_dir = tk.StringVar(self, self._config.data['renders_dir'])
        self._Vtextiles_dir = tk.StringVar(self, self._config.data['textiles_dir'])

        self._Iblank = ImgTk.PhotoImage(Img.new('RGBA', (27, 27), (0, 0, 0, 1)))

        self._Fmain = ttk.Frame(self)
        self._Fmain.pack(expand = True, fill = tk.BOTH)

        self._Foptions = ttk.Frame(self._Fmain)
        self._Foptions.grid(row = 0, column = 0, padx = 10, pady = 10, sticky = tk.W)

        self._OMstyletype = ttk.OptionMenu(self._Foptions, self._Vstyletype, self._Vstyletype.get(), 'Dark', 'Light', 'Custom 1', 'Custom 2', 'Custom 3', 'Custom 4')
        self._OMstyletype.configure(compound = tk.CENTER, image = self._Iblank, width = 14)
        self._OMstyletype['menu'].configure(font = self.font, **self.menu_style)
        self._OMstyletype.grid(row = 0, column = 0, sticky = tk.W)

        self._Lstyletype = ttk.Label(self._Foptions, text = ' Style')
        self._Lstyletype.grid(row = 0, column = 1, sticky = tk.W)

        self._SBfontsize = ttk.Spinbox(self._Foptions, textvariable = self._Vfontsize, width = 3, font = tkfont.nametofont('TkDefaultFont'),
                                       validate = 'key', validatecommand = lambda *_: False,
                                       from_ = 5, to = 20, increment = 1)
        self._SBfontsize.grid(row = 1, column = 0, sticky = tk.NSEW)

        self._Lfontsize = ttk.Label(self._Foptions, text = ' Fontsize')
        self._Lfontsize.grid(row = 1, column = 1, sticky = tk.W)

        self._SBpadding = ttk.Spinbox(self._Foptions, textvariable = self._Vpadding, width = 3, font = tkfont.nametofont('TkDefaultFont'), 
                                       validate = 'key', validatecommand = lambda *_: False,
                                       from_ = 0, to = 10, increment = 1)
        self._SBpadding.grid(row = 2, column = 0, sticky = tk.NSEW)

        self._Lpadding = ttk.Label(self._Foptions, text = ' Padding')
        self._Lpadding.grid(row = 2, column = 1, sticky = tk.W)
        self._TTpadding = tktt.ToolTip(self._Lpadding,
                                          'How many sprites around the targeted sprite are shown in sheet and mask previews.',
                                          0.5, False, 100)

        self._Cautorender = ttk.Checkbutton(self._Foptions, text = 'Autorender', variable = self._Vautorender)
        self._Cautorender.grid(row = 3, column = 0, columnspan = 2, sticky = tk.W)
        self._TTautorender = tktt.ToolTip(self._Cautorender,
                                          'Automatically renders when an option is changed. Not recommended if you plan to render large sheets.',
                                          0.5, False, 100)

        self._Cshow_tooltips = ttk.Checkbutton(self._Foptions, text = 'Show Tooltips', variable = self._Vshow_tooltips)
        self._Cshow_tooltips.grid(row = 4, column = 0, columnspan = 2, sticky = tk.W)

        # generates functions for changing default dirs
        def _change_dir_command(var: tk.StringVar) -> callable:
            def f() -> None:
                directory = tkfile.askdirectory(initialdir = var.get(), mustexist = True)
                if directory == '': return
                var.set(directory)
            return f
        
        self._Bchange_sheets_dir = ttk.Button(self._Foptions, text = 'Sheets Default Directory', width = 25,
                                               command = _change_dir_command(self._Vsheets_dir))
        self._Bchange_sheets_dir.grid(row = 5, column = 0, columnspan = 3, sticky = tk.W)
        self._TTchange_sheets_dir = tktt.ToolTip(self._Bchange_sheets_dir,
                                          'Change default directory for searching for sheets.',
                                          0.5, False, 100)

        self._Bclear_sheets_dir = ttk.Button(self._Foptions, text = 'Clear', width = 6,
                                              command = lambda: self._Vsheets_dir.set(''))
        self._Bclear_sheets_dir.grid(row = 5, column = 3, sticky = tk.W)
        self._TTclear_sheets_dir = tktt.ToolTip(self._Bclear_sheets_dir,
                                          'Clear this option to have no default, the last folder accessed will be the default.',
                                          0.5, False, 100)

        self._Lsheets_dir = ttk.Label(self._Foptions, textvariable = self._Vsheets_dir)
        self._Lsheets_dir.grid(row = 5, column = 4, padx = 10, sticky = tk.W)

        self._Bchange_renders_dir = ttk.Button(self._Foptions, text = 'Renders Default Directory', width = 25,
                                               command = _change_dir_command(self._Vrenders_dir))
        self._Bchange_renders_dir.grid(row = 6, column = 0, columnspan = 3, sticky = tk.W)
        self._TTchange_renders_dir = tktt.ToolTip(self._Bchange_renders_dir,
                                          'Change default directory for saving renders.',
                                          0.5, False, 100)

        self._Bclear_renders_dir = ttk.Button(self._Foptions, text = 'Clear', width = 6,
                                              command = lambda: self._Vrenders_dir.set(''))
        self._Bclear_renders_dir.grid(row = 6, column = 3, sticky = tk.W)
        self._TTclear_renders_dir = tktt.ToolTip(self._Bclear_renders_dir,
                                          'Clear this option to have no default, the last folder accessed will be the default.',
                                          0.5, False, 100)
        
        self._Lrenders_dir = ttk.Label(self._Foptions, textvariable = self._Vrenders_dir)
        self._Lrenders_dir.grid(row = 6, column = 4, padx = 10, sticky = tk.W)

        self._Bchange_textiles_dir = ttk.Button(self._Foptions, text = 'Textiles Default Directory', width = 25,
                                               command = _change_dir_command(self._Vtextiles_dir))
        self._Bchange_textiles_dir.grid(row = 7, column = 0, columnspan = 3, sticky = tk.W)
        self._TTchange_textiles_dir = tktt.ToolTip(self._Bchange_textiles_dir,
                                          'Change default directory for searching for textiles.',
                                          0.5, False, 100)

        self._Bclear_textiles_dir = ttk.Button(self._Foptions, text = 'Clear', width = 6,
                                              command = lambda: self._Vtextiles_dir.set(''))
        self._Bclear_textiles_dir.grid(row = 7, column = 3, sticky = tk.W)
        self._TTclear_textiles_dir = tktt.ToolTip(self._Bclear_textiles_dir,
                                          'Clear this option to have no default, the last folder accessed will be the default.',
                                          0.5, False, 100)
        
        self._Lrenders_dir = ttk.Label(self._Foptions, textvariable = self._Vtextiles_dir)
        self._Lrenders_dir.grid(row = 7, column = 4, padx = 10, sticky = tk.W)

        self._Fbuttons = ttk.Frame(self._Fmain)
        self._Fbuttons.grid(row = 1, column = 0, padx = 10, sticky = tk.W)

        self._Bapply = ttk.Button(self._Fbuttons, text = 'Apply Settings', command = self.apply, style = 'apply.TButton')
        self._Bapply.grid(row = 0, column = 0)

        self._Bapply_restart = ttk.Button(self._Fbuttons, text = 'Apply Settings and Restart', command = self.apply_restart, style = 'apply.TButton')
        self._Bapply_restart.grid(row = 1, column = 0)

        self._SFb_end = ttk.Frame(self._Fmain, height = 10)
        self._SFb_end.grid(row = 2, column = 0)

    def _set(self, keychain: list[any], var: tk.Variable) -> None:
        try:
            self._config.change(keychain, var.get())
        except tk.TclError: # when var empty or invalid, change not applied, maybe redundant
            pass

    def apply(self) -> None:
        self._set(['styletype'], self._Vstyletype)
        self._set(['fontsize'], self._Vfontsize)
        self._set(['padding'], self._Vpadding)
        self._set(['autorender'], self._Vautorender)
        self._set(['show_tooltips'], self._Vshow_tooltips)
        self._set(['sheets_dir'], self._Vsheets_dir)
        self._set(['renders_dir'], self._Vrenders_dir)
        self._set(['textiles_dir'], self._Vtextiles_dir)

        try:
            self._config.write()
        except Exception as e:
            IO.InfobarAlert(True, e, f'Error writing to config.json: {e}')

    def apply_restart(self) -> None:
        self.apply()
        Settings.restart_func()

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('RotMG Sprite Renderer')

        try:
            self.root.iconbitmap(default = './bin/favicon.ico')

        except Exception as e:
            self._alert(IO.InfobarAlert(False, e, '')) # text is empty so infobar isn't accessed

        self.root.focus_set()
        
        try:
            self.config = IO.Config('./bin/config.json')

        except Exception as e:
            self._alert(IO.InfobarAlert(True, e, '')) # text is empty so infobar isn't accessed
            tkmb.showerror('Bad Config', f'Error opening config; try reinstalling config.json: {e}')
            raise ValueError      
          
        try:
            with open('./bin/images.pickle', 'rb') as f:
                self._image_set = pickle.load(f)

        except Exception as e:
            self._alert(IO.InfobarAlert(True, e, '')) # text is empty so infobar isn't accessed
            tkmb.showerror('Bad Images File', f'Error opening images; try reinstalling images.pickle: {e}')
            raise ValueError


        # STYLE
        try:
            self._style = ttk.Style(self.root)
            self._style.theme_use('clam')

            self._font = tkfont.nametofont('TkDefaultFont')
            self._font.configure(size = self.config.data['fontsize'])

            self._style_config = self.config.data['style'][self.config.data['styletype']]

            for widget_style, kwargs in self._style_config['configure'].items():
                self._style.configure(widget_style, **kwargs)

            for widget_style, kwargs in self._style_config['map'].items():
                self._style.map(widget_style, **kwargs)
            
            RenderOutput.canvas_style = self._style_config['render_canvas'] # boo no ttk canvas
            ScrollableFrame.canvas_style = self._style_config['textile_canvas'] # boo no ttk canvas
            Settings.menu_style = self._style_config['menu'] # boo no ttk menu
            self._menu_style = self._style_config['menu'] # boo no ttk menu
            
            self._style.configure('TCheckbutton', indicatorsize = self.config.data['fontsize'])
            self._style.configure('TSpinbox', arrowsize = 3 + self.config.data['fontsize'])
            Settings.font = self._font

            self._icon_set = self._image_set['icons'][self._style_config['icon_set']]

        except KeyError as e:
            self._alert(IO.InfobarAlert(True, e, '')) # text is empty so infobar isn't accessed
            tkmb.showerror('Style Key Error', f'Likely missing key from the style config: {e}')
            raise KeyError
        
        except Exception as e:
            self._alert(IO.InfobarAlert(True, e, '')) # text is empty so infobar isn't accessed
            tkmb.showerror('Style Error', f'Unknown error reading style config: {e}')
            raise ValueError
        # /STYLE


        # ICONS
        self._Ifolder = ImgTk.PhotoImage(self._icon_set['folder'])
        self._Isubscribe = ImgTk.PhotoImage(self._icon_set['subscribe'])
        self._Iunsubscribe = ImgTk.PhotoImage(self._icon_set['unsubscribe'])
        self._Idown = ImgTk.PhotoImage(self._icon_set['down'])
        self._Iup = ImgTk.PhotoImage(self._icon_set['up'])
        self._Irender = ImgTk.PhotoImage(self._icon_set['render'])
        self._Isave = ImgTk.PhotoImage(self._icon_set['save'])
        self._Isettings = ImgTk.PhotoImage(self._icon_set['settings'])

        self._Iwarning = ImgTk.PhotoImage(self._image_set['warning'])
        self._Ierror = ImgTk.PhotoImage(self._image_set['error'])

        self._Iblank = ImgTk.PhotoImage(Img.new('RGBA', (27, 27), (0, 0, 0, 1)))
        # /ICONS


        # VARS
        self._sub_sheet_last = 'none'
        self._sub_sheet_mtime = 0
        self._sub_mask_last = 'none'
        self._sub_mask_mtime = 0

        self._Vsheet = IO.SheetVar(Rendering.Sheet(Img.new('RGBA', (8, 8), (0, 0, 1, 0))))
        self._Vsheet_name = tk.StringVar(self.root)
        self._Vmask_sheet_name = tk.StringVar(self.root)

        self._Vindex = tk.StringVar(self.root, '0')
        self._Vwidth = tk.StringVar(self.root, '8')
        self._Vheight = tk.StringVar(self.root, '8')
        self._Vhas_bg = tk.BooleanVar(self.root, False)
        self._Vhas_mask = tk.BooleanVar(self.root, False)
        self._Vhas_shadows = tk.BooleanVar(self.root, True)
        self._Vhas_outline = tk.BooleanVar(self.root, True)

        self._Vscale = tk.StringVar(self.root, '5')
        self._Vlength = tk.StringVar(self.root, '1')
        self._Vshadow_strength = tk.StringVar(self.root, '0.7')
        self._Voutline_thickness = tk.StringVar(self.root, '1')
        self._Vspeed = tk.StringVar(self.root, '500')
        self._Vbg_color = tk.StringVar(self.root, '#36393e')
        self._Vshadow_color = IO.ListVar((0, 0, 0))
        self._Voutline_color = IO.ListVar((0, 0, 0))
        self._Vclothing_textile = IO.ImgVar(Img.new('RGB', (10, 10), '#ff0000'))
        self._Vaccessory_textile = IO.ImgVar(Img.new('RGB', (10, 10), '#00ff00'))

        self._Vmode = tk.StringVar(self.root, ' Image')

        self._Vrendered_images = IO.ListVar([])
        # /VARS


        # VALIDATE COMMANDS
        self._validate_int = self.root.register(IO.make_validate(self.root, '0123456789', [lambda v: int(v)], self._alert))
        self._validate_index = self.root.register(IO.make_validate(self.root, '0123456789x', [lambda v: IO.index_filter(v)], self._alert))
        self._validate_float = self.root.register(IO.make_validate(self.root, '0123456789.', [lambda v: float(v)], self._alert))
        self._validate_speed = self.root.register(IO.make_validate(self.root, '0123456789, ', [lambda v: IO.speed_filter(v, 1)], self._alert))
        # /VALIDATE COMMANDS


        # OPTIONS
        self._Foptions = ttk.Frame(self.root, padding = 20)
        self._Foptions.grid(row = 0, column = 0, sticky = tk.NS)

        #### LOAD BUTTONS
        self._Fload_buttons = ttk.Frame(self._Foptions)
        self._Fload_buttons.grid(row = 0, column = 0)

        self._Bload = ttk.Button(self._Fload_buttons, text = ' Load Sheet', command = self._load_sheet, 
                                 compound = tk.LEFT, image = self._Ifolder)
        self._Bload.grid(row = 0, column = 0)

        self._Bsub = ttk.Button(self._Fload_buttons, command = self._sub_sheet, image = self._Isubscribe)
        self._Bsub.grid(row = 0, column = 1)

        self._Bsub_clear = ttk.Button(self._Fload_buttons, command = self._unsub_sheet, image = self._Iunsubscribe)
        self._Bsub_clear.state(('disabled',))
        self._Bsub_clear.grid(row = 0, column = 2)

        self._Bload_mask = ttk.Button(self._Fload_buttons, text = ' Load Mask', command = self._load_mask, 
                                      compound = tk.LEFT, image = self._Ifolder)
        self._Bload_mask.grid(row = 1, column = 0)

        self._Bsub_mask = ttk.Button(self._Fload_buttons, command = self._sub_mask, image = self._Isubscribe)
        self._Bsub_mask.grid(row = 1, column = 1)

        self._Bsub_mask_clear = ttk.Button(self._Fload_buttons, command = self._unsub_mask, image = self._Iunsubscribe)
        self._Bsub_mask_clear.state(('disabled',))
        self._Bsub_mask_clear.grid(row = 1, column = 2)
        #### /LOAD BUTTONS

        #### SPACER
        self._SFload_ro1 = ttk.Frame(self._Foptions, height = 20)
        self._SFload_ro1.grid(row = 1, column = 0)
        #### /SPACER

        #### RENDER OPTIONS 1 (index, width, height, bg, mask, shadows, outline)
        self._Frender_options_1 = ttk.Frame(self._Foptions)
        self._Frender_options_1.grid(row = 2, column = 0)
        
        self._IWindex = IndexWidget(self._Frender_options_1, index = self._Vindex, sheet = self._Vsheet, width = self._Vwidth)
        self._IWindex._Eentry.configure(validate = 'all', validatecommand = (self._validate_index, '%V', '%S', '%P', '%W'), 
                                        font = self._font, width = 5, justify = 'center')
        self._IWindex.grid(row = 0, column = 0, rowspan = 7)

        #### SPACER
        self._SFiw_ro1 = ttk.Frame(self._Frender_options_1, width = 20)
        self._SFiw_ro1.grid(row = 0, column = 1, rowspan = 7)
        #### /SPACER

        self._Ewidth = ttk.Entry(self._Frender_options_1, textvariable = self._Vwidth,
                                 validate = 'all', validatecommand = (self._validate_int, '%V', '%S', '%P', '%W'),
                                 font = self._font, width = 4, justify = 'center')
        self._Ewidth.grid(row = 0, column = 2, sticky = tk.W)

        self._Lwidth = ttk.Label(self._Frender_options_1, text = ' Width')
        self._Lwidth.grid(row = 0, column = 3, sticky = tk.W)

        self._Eheight = ttk.Entry(self._Frender_options_1, textvariable = self._Vheight,
                                  validate = 'all', validatecommand = (self._validate_int, '%V', '%S', '%P', '%W'),
                                  font = self._font, width = 4, justify = 'center')
        self._Eheight.grid(row = 1, column = 2, sticky = tk.W)

        self._Lheight = ttk.Label(self._Frender_options_1, text = ' Height', width = 14) # align width and height labels left
        self._Lheight.grid(row = 1, column = 3, sticky = tk.W)

        #### SPACER
        self._SFe_c = ttk.Frame(self._Frender_options_1, height = 10)
        self._SFe_c.grid(row = 2, column = 2)
        #### /SPACER

        self._Cbg = ttk.Checkbutton(self._Frender_options_1, text = ' Render Background', variable = self._Vhas_bg)
        self._Cbg.grid(row = 3, column = 2, columnspan = 2, sticky = tk.EW)

        self._Cmask = ttk.Checkbutton(self._Frender_options_1, text = ' Render Mask', variable = self._Vhas_mask)
        self._Cmask.grid(row = 4, column = 2, columnspan = 2, sticky = tk.EW)

        self._Cshadows = ttk.Checkbutton(self._Frender_options_1, text = ' Render Shadows', variable = self._Vhas_shadows)
        self._Cshadows.grid(row = 5, column = 2, columnspan = 2, sticky = tk.EW)

        self._Coutline = ttk.Checkbutton(self._Frender_options_1, text = ' Render Outline', variable = self._Vhas_outline)
        self._Coutline.grid(row = 6, column = 2, columnspan = 2, sticky = tk.EW)
        #### /RENDER OPTIONS 1 (index, width, height, bg, mask, shadows, outline)

        #### SPACER
        self._SFro1_ro2 = ttk.Frame(self._Foptions, height = 16)
        self._SFro1_ro2.grid(row = 3, column = 0)
        #### /SPACER

        #### RENDER OPTIONS 2 (scale, length, shadow strength, outline thickness, speed, bg color, outline color, shadow color, clothing, accessory)
        self._Frender_options_2 = ttk.Frame(self._Foptions)
        self._Frender_options_2.grid(row = 4, column = 0)

        ####### LABEL-ENTRIES
        self._Flabel_entries = ttk.Frame(self._Frender_options_2)
        self._Flabel_entries.grid(row = 0, column = 0)

        self._Lscale = ttk.Label(self._Flabel_entries, text = 'Scale ')
        self._Lscale.grid(row = 0, column = 0, sticky = tk.E)

        self._Escale = ttk.Entry(self._Flabel_entries, textvariable = self._Vscale,
                                 validate = 'all', validatecommand = (self._validate_int, '%V', '%S', '%P', '%W'),
                                 font = self._font, width = 3, justify = 'center')
        self._Escale.grid(row = 0, column = 1, sticky = tk.W)

        self._Lshadow_strength = ttk.Label(self._Flabel_entries, text = 'Shadow Strength ')
        self._Lshadow_strength.grid(row = 0, column = 3, sticky = tk.E)

        self._Eshadow_strength = ttk.Entry(self._Flabel_entries, textvariable = self._Vshadow_strength,
                                           validate = 'all', validatecommand = (self._validate_float, '%V', '%S', '%P', '%W'),
                                           font = self._font, width = 3, justify = 'center')
        self._Eshadow_strength.grid(row = 0, column = 4, sticky = tk.W)

        ####### SPACER
        self._SFel_el = ttk.Frame(self._Flabel_entries, width = 20)
        self._SFel_el.grid(row = 0, column = 2)
        ####### /SPACER

        self._Llength = ttk.Label(self._Flabel_entries, text = 'Length ')
        self._Llength.grid(row = 1, column = 0, sticky = tk.E)

        self._Elength = ttk.Entry(self._Flabel_entries, textvariable = self._Vlength,
                                  validate = 'all', validatecommand = (self._validate_int, '%V', '%S', '%P', '%W'),
                                  font = self._font, width = 3, justify = 'center')
        self._Elength.grid(row = 1, column = 1, sticky = tk.W)

        self._Loutline_thickness = ttk.Label(self._Flabel_entries, text = 'Outline Thickness ')
        self._Loutline_thickness.grid(row = 1, column = 3, sticky = tk.E)

        self._Eoutline_thickness = ttk.Entry(self._Flabel_entries, textvariable = self._Voutline_thickness,
                                             validate = 'all', validatecommand = (self._validate_int, '%V', '%S', '%P', '%W'),
                                             font = self._font, width = 3, justify = 'center')
        self._Eoutline_thickness.grid(row = 1, column = 4, sticky = tk.W)

        ####### SPACER
        self._SFel_speed = ttk.Frame(self._Flabel_entries, height = 10)
        self._SFel_speed.grid(row = 2, column = 0)
        ####### /SPACER

        self._Lspeed = ttk.Label(self._Flabel_entries, text = 'GIF Speed ')
        self._Lspeed.grid(row = 3, column = 0, sticky = tk.E)

        self._Espeed = ttk.Entry(self._Flabel_entries, textvariable = self._Vspeed,
                                 validate = 'all', validatecommand = (self._validate_speed, '%V', '%S', '%P', '%W'),
                                 font = self._font, justify = 'center')
        self._Espeed.grid(row = 3, column = 1, columnspan = 4, sticky = tk.EW)
        ####### /LABEL-ENTRIES


        #### SPACER
        self._SFro2_co = ttk.Frame(self._Frender_options_2, height = 20)
        self._SFro2_co.grid(row = 1, column = 0)
        #### /SPACER


        ####### COLOR AND TEXTILE OPTIONS
        self._Fcolor_textile_options = ttk.Frame(self._Frender_options_2)
        self._Fcolor_textile_options.grid(row = 2, column = 0)

        self._CPbg_color = ColorPicker(self._Fcolor_textile_options, text = ' Background Color', color_var = self._Vbg_color)
        self._CPbg_color.grid(row = 0, column = 0)

        self._DDcolor_textile = DropDown(self._Fcolor_textile_options, up_image = self._Idown, up_text = '',
                                         down_image = self._Iup, down_text = '', # whoops, kinda hard to change 
                                         compound = tk.LEFT, style = 'dropdown.TButton')
        self._DDcolor_textile.grid(row = 0, column = 1)

        ####### SPACER  
        self._SFbg_co = ttk.Frame(self._Fcolor_textile_options, height = 10)
        self._SFbg_co.grid(row = 1, column = 0)
        self._DDcolor_textile.add(self._SFbg_co)
        ####### /SPACER

        self._CPshadow_color = ColorPicker(self._Fcolor_textile_options, text = ' Shadow Color', color_var = self._Vshadow_color, hex = False)
        self._CPshadow_color.grid(row = 2, column = 0)
        self._DDcolor_textile.add(self._CPshadow_color)

        self._CPoutline_color = ColorPicker(self._Fcolor_textile_options, text = ' Outline Color', color_var = self._Voutline_color, hex = False)
        self._CPoutline_color.grid(row = 2, column = 1)
        self._DDcolor_textile.add(self._CPoutline_color)

        self._TPclothing = TextilePicker(self._Fcolor_textile_options, text = ' Clothing Texture', image_var = self._Vclothing_textile,
                                         textiles = self._image_set['textiles'], icon_set = self._icon_set, config = self.config)
        self._TPclothing.grid(row = 3, column = 0)
        self._DDcolor_textile.add(self._TPclothing)

        self._TPaccessory = TextilePicker(self._Fcolor_textile_options, text = ' Accessory Texture', image_var = self._Vaccessory_textile, 
                                          textiles = self._image_set['textiles'], icon_set = self._icon_set, config = self.config)
        self._TPaccessory.grid(row = 3, column = 1)
        self._DDcolor_textile.add(self._TPaccessory)
        ####### /COLOR AND TEXTILE OPTIONS


        #### /RENDER OPTIONS 2 (scale, length, shadow strength, outline thickness, speed, bg color, outline color, shadow color, clothing, accessory)

        # SPACER
        self._SFro2_o = ttk.Frame(self._Foptions, height = 20)
        self._SFro2_o.grid(row = 5, column = 0)
        # /SPACER

        self._OMmode = ttk.OptionMenu(self._Foptions, self._Vmode, ' Image', ' Image', ' Entity', ' Animation', ' Overview')
        self._OMmode.configure(compound = tk.CENTER, image = self._Iblank)
        self._OMmode['menu'].configure(font = self._font, **self._menu_style)
        self._OMmode.grid(row = 6, column = 0)

        #### SPACER
        self._SFo_o = ttk.Frame(self._Foptions, height = 20)
        self._SFo_o.grid(row = 7, column = 0)
        # /SPACER

        self._Brender = ttk.Button(self._Foptions, text = ' Render', command = self._update, compound = tk.LEFT, image = self._Irender)
        self._Brender.grid(row = 8, column = 0)

        self._Bsave = ttk.Button(self._Foptions, text = ' Save', command = self._save, compound = tk.LEFT, image = self._Isave)
        self._Bsave.grid(row = 9, column = 0)
        # /OPTIONS


        # GRAPHICS
        self._Fgraphics = ttk.Frame(self.root)
        self._Fgraphics.grid(row = 0, column = 1, sticky = tk.NSEW)

        self._SPpreview = SelectPreview(self._Fgraphics, 
                                        sheet = self._Vsheet, index = self._Vindex, width = self._Vwidth, height = self._Vheight,
                                        text = 'Selection', img_padding = self.config.data['padding'], outline = self._image_set['outline'])
        self._SPpreview.place(relx = 0, rely = 0, relwidth = 0.38, relheight = 0.5)

        self._SPpreview_mask = SelectPreview(self._Fgraphics, 
                                             sheet = self._Vsheet, index = self._Vindex, width = self._Vwidth, height = self._Vheight,
                                             text = 'Mask', img_padding = self.config.data['padding'], outline = self._image_set['outline'], mask = True)
        self._SPpreview_mask.place(relx = 0, rely = 0.5, relwidth = 0.38, relheight = 0.5)
    
        self._ROoutput = RenderOutput(self._Fgraphics, rendered_images = self._Vrendered_images, speeds = self._Vspeed, mode = self._Vmode)
        self._ROoutput.place(relx = 0.38, rely = 0, relwidth = 0.62, relheight = 1)

        # SEPARATORS
        self._SFo_g = ttk.Frame(self._Fgraphics, style = 'separator.TFrame')
        self._SFo_g.place(x = 0, rely = 0, width = 2, relheight = 1, anchor = tk.NW)

        self._SFsp_spm = ttk.Frame(self._Fgraphics, style = 'separator.TFrame')
        self._SFsp_spm.place(relx = 0, rely = 0.5, relwidth = 0.38, height = 2, anchor = tk.W)

        self._SFsp_ro = ttk.Frame(self._Fgraphics, style = 'separator.TFrame')
        self._SFsp_ro.place(relx = 0.38, rely = 0, width = 2, relheight = 1, anchor = tk.N)
        # SEPARATORS

        # /GRAPHICS


        # INFOBAR
        self._IBinfo_bar = InfoBar(self.root, config = self.config,
                                  sheet = self._Vsheet, sheet_name = self._Vsheet_name, mask_name = self._Vmask_sheet_name,
                                  settings_image = self._Isettings, warning_image = self._Iwarning, error_image = self._Ierror, height = 30)
        self._IBinfo_bar.grid(row = 1, column = 0, columnspan = 2, sticky = tk.EW) # no tk variable for SEW :(
        
        Settings.restart_func = self._restart
        IO.InfobarAlert.func = self._alert
        # /INFOBAR


        # TOOLTIPS
        try:
            self.config.data['show_tooltips']
        except KeyError as e:
            self._alert(IO.InfobarAlert(True, e, '')) # text is empty so infobar isn't accessed
            tkmb.showerror('Key Error', f'Missing "show_tooltips": {e}')
            raise KeyError

        if self.config.data['show_tooltips']:
            self._TTload = tktt.ToolTip(self._Bload, 'Ctrl + o, Ctrl + v pastes sheet from clipboard, use Ctrl + 1-8 to navigate quickly', 0.5, False, 100)
            self._TTload_mask = tktt.ToolTip(self._Bload_mask, 'Ctrl + Shift + o, Ctrl + Shift + v pastes mask from clipboard', 0.5, False, 100)
            self._TTindex = tktt.ToolTip(self._IWindex._Eentry, 'Arrow Keys, Ctrl + h to set to 0. Can also use hex values here. Use Esc to exit any Entry', 0.5, False, 100)
            self._TTsave = tktt.ToolTip(self._Bsave, 'Ctrl + s, Ctrl + c to copy render', 0.5, False, 100)
            self._TTrender = tktt.ToolTip(self._Brender, 'Enter/Return', 0.5, False, 100)
            self._TToutput = tktt.ToolTip(self._ROoutput, 'Ctrl + Arrow Keys to scroll, Ctrl + Shift + h to reset scroll', 0.5, False, 100)
            
            self._TTsub = tktt.ToolTip(self._Bsub, 
                                    'Subscribe to changes to this file. When the saved file is changed, a new render will be generated automatically.',
                                    0.5, False, 100)
            self._TTsub_mask = tktt.ToolTip(self._Bsub_mask, 
                                    'Subscribe to changes to this file. When the saved file is changed, a new render will be generated automatically.',
                                    0.5, False, 100)
            self._TTscale = tktt.ToolTip(self._Lscale, 
                                    '1 pixel in the sheet will be equal to this many pixels in the render.',
                                    0.5, False, 100)
            self._TTlength = tktt.ToolTip(self._Llength, 
                                    'Has different behaviors depending on mode. Use length 0 to render the whole sheet starting at the index.\n\nImage: how many images after the current one to render\nEntity: how many rows to render\nAnimation: how many images after the current one to render\nOverview: how many images from each skin group to render (use 3 for enemies)',
                                    0.5, False, 100)
            self._TTshadow_strength = tktt.ToolTip(self._Lshadow_strength, 
                                    'After blurring, the alpha channel of the shadow is multiplied by this value (can be a decimal).',
                                    0.5, False, 100)
            self._TToutline_thickness = tktt.ToolTip(self._Loutline_thickness, 
                                    'How many pixels of outline there are. 0 in this field will automatically assign an outline thickness 1/5 the scale.',
                                    0.5, False, 100)
            self._TTspeed = tktt.ToolTip(self._Lspeed, 
                                    'In ms, the duration between frames. This can be a list of values separated by commas. If there are more frames than durations the durations will be looped over.',
                                    0.5, False, 100)
            self._TTalert = tktt.ToolTip(self._IBinfo_bar._Bexception_info, 
                                    'Ctrl + q to clear. Errors and warnings appear here. Errors are also stored in the "bin/error.log" file.',
                                    0.5, False, 100)
        # /TOOLTIPS


        # WEIGHT
        self.root.columnconfigure(1, weight = 1)
        self.root.rowconfigure(0, weight = 1)
        # /WEIGHT


        # VAR TRACES (has to be after widget definitions to avoid errors)
        self._Vsheet.trace_add(self._update, self._update_previews)
        self._Vsheet_name.trace_add('write', lambda *_: self._IBinfo_bar._update())
        self._Vmask_sheet_name.trace_add('write', lambda *_: self._IBinfo_bar._update())

        self._Vindex.trace_add('write', lambda *_: self._update_previews()) # previews should stay relevant
        self._Vwidth.trace_add('write', lambda *_: self._update_previews())
        self._Vheight.trace_add('write', lambda *_: self._update_previews())

        try:
            self.config.data['autorender']
        except KeyError as e:
            self._alert(IO.InfobarAlert(True, e, '')) # text is empty so infobar isn't accessed
            tkmb.showerror('Key Error', f'Missing "autorender": {e}')
            raise KeyError

        if self.config.data['autorender']:
            self._Vindex.trace_add('write', lambda *_: self._update())
            self._Vwidth.trace_add('write', lambda *_: self._update())
            self._Vheight.trace_add('write', lambda *_: self._update())
            self._Vhas_bg.trace_add('write', lambda *_: self._update())
            self._Vhas_mask.trace_add('write', lambda *_: self._update())
            self._Vhas_shadows.trace_add('write', lambda *_: self._update())
            self._Vhas_outline.trace_add('write', lambda *_: self._update())

            self._Vscale.trace_add('write', lambda *_: self._update())
            self._Vlength.trace_add('write', lambda *_: self._update())
            self._Vshadow_strength.trace_add('write', lambda *_: self._update())
            self._Voutline_thickness.trace_add('write', lambda *_: self._update())
            self._Vspeed.trace_add('write', lambda *_: self._ROoutput._update()) # no need to rerender
            self._Vbg_color.trace_add('write', lambda *_: self._update())
            self._Vshadow_color.trace_add('write', lambda *_: self._update())
            self._Voutline_color.trace_add('write', lambda *_: self._update())
            self._Vclothing_textile.trace_add(self._update)
            self._Vaccessory_textile.trace_add(self._update)

            self._Vmode.trace_add('write', lambda *_: self._update())
        # /VAR TRACES


        # BINDS
        self.root.bind('<Control-Key-1>', lambda _: self._Bload.focus_set())
        self.root.bind('<Control-Key-2>', lambda _: self._IWindex._Eentry.focus_set())
        self.root.bind('<Control-Key-3>', lambda _: self._Ewidth.focus_set())
        self.root.bind('<Control-Key-4>', lambda _: self._Cbg.focus_set())
        self.root.bind('<Control-Key-5>', lambda _: self._Escale.focus_set())
        self.root.bind('<Control-Key-6>', lambda _: self._CPbg_color.focus_set())
        self.root.bind('<Control-Key-7>', lambda _: self._OMmode.focus_set())
        self.root.bind('<Control-Key-8>', lambda _: self._IBinfo_bar._Bexception_info.focus_set())
        
        self.root.bind('<Control-v>', lambda _: self._entry_protect(self._paste_sheet))
        self.root.bind('<Control-V>', lambda _: self._entry_protect(self._paste_mask))
        self.root.bind('<Control-c>', lambda _: self._entry_protect(self._copy))

        self.root.bind('<Control-o>', lambda _: self._load_sheet())
        self.root.bind('<Control-O>', lambda _: self._load_mask())

        self.root.bind('<Control-s>', lambda _: self._save())

        self.root.bind('<Control-h>', lambda _: self._Vindex.set('0'))
        self.root.bind('<Control-H>', lambda _: self._ROoutput.reset_view())

        self.root.bind('<Control-q>', lambda _: self._IBinfo_bar.clear_alert())

        self.root.bind('<Up>', lambda _: self._IWindex._up())
        self.root.bind('<Up>', lambda _: self.root.focus_set(), True) # lose focus on up arrow too
        self.root.bind('<Left>', lambda _: self._entry_protect(self._IWindex._left))
        self.root.bind('<Right>', lambda _: self._entry_protect(self._IWindex._right))
        self.root.bind('<Down>', lambda _: self._IWindex._down())
        self.root.bind('<Down>', lambda _: self.root.focus_set(), True) # lose focus on down arrow too

        self.root.bind('<Control-Up>', lambda _: self._ROoutput._Cimage.yview_scroll(-1, 'units'))
        self.root.bind('<Control-Up>', lambda _: self.root.focus_set(), True) # lose focus on up arrow too
        self.root.bind('<Control-Left>', lambda _: self._entry_protect(self._ROoutput._Cimage.xview_scroll, -1, 'units'))
        self.root.bind('<Control-Right>', lambda _: self._entry_protect(self._ROoutput._Cimage.xview_scroll, 1, 'units'))
        self.root.bind('<Control-Down>', lambda _: self._ROoutput._Cimage.yview_scroll(1, 'units'))
        self.root.bind('<Control-Down>', lambda _: self.root.focus_set(), True) # lose focus on down arrow too

        self.root.bind('<Escape>', lambda _: self.root.focus_set())
        self.root.bind_all('<Button-1>', lambda e: e.widget.focus_set())

        self.root.bind('<Return>', lambda _: self._update())
        self.root.bind('<Return>', lambda _: self.root.focus_set(), True)
        # /BINDS


        self._update()
        self._update_previews()
        self.root.mainloop()

    def _update(self) -> None:
        try:
            self._render()
            self._ROoutput._update()
        except ValueError as e: # these will throw a ValueError when a field is cleared to nothing
            pass # handled by validation
        except ZeroDivisionError as e: # edge case where width is wider than sheet
            IO.InfobarAlert(True, e, 'Width greater than sheet width.')
        except Exception as e: # other cases
            IO.InfobarAlert(True, e, f'Unknown Error: {e}')

    def _update_previews(self) -> None:
        try:
            self._SPpreview._update()
            self._SPpreview_mask._update()
        except ValueError as e: # these will throw a ValueError when a field is cleared to nothing
            pass # handled by validation
        except ZeroDivisionError as e: # edge case where width is wider than sheet
            IO.InfobarAlert(True, e, 'Width greater than sheet width.')
        except Exception as e: # other cases
            IO.InfobarAlert(True, e, f'Unknown Error: {e}')

    def _entry_protect(self, func: callable, *args, **kwargs) -> None:
        if 'entry' not in str(self.root.focus_get()):
            func(*args, **kwargs)

    def _load_sheet(self) -> None:
        path = tkfile.askopenfilename(initialdir = self.config.data['sheets_dir'], filetypes = (('Image (png, tiff, tif)', ('*.png', '*.tiff', '*.tif')),))
        if path:
            try:
                loaded = IO.load_sheet(path)
            except Exception as e:
                IO.InfobarAlert(True, e, f'Couldn\'t open sheet file: {e}')
                return
            
            self._Vindex.set('0')
            self._Vsheet.set(loaded[0])
            self._Vsheet_name.set(loaded[1])

            self._ROoutput.reset_view()
            self._unsub_sheet()
            self._unsub_mask()

    def _sub_sheet(self) -> None:
        path = self._Vsheet_name.get()

        if path:
            self._Bsub.state(('disabled',))
            self._Bsub_clear.state(('!disabled',))
            self.root.after(1000, self._refresh_sheet)

    def _refresh_sheet(self) -> None:
        path = self._Vsheet_name.get()

        try:
            mtime = os.path.getmtime(path)
        except OSError as e: # if file stops being available
            self._unsub_sheet()
            IO.InfobarAlert(True, e, f'Subscription to {path} lost.')
            return

        if self._sub_sheet_mtime != mtime:
            self._sub_sheet_mtime = mtime

            loaded = IO.load_sheet(path)
            self._Vsheet.set(loaded[0])
            self._Vsheet_name.set(loaded[1]) # in case of size change

        self._sub_sheet_last = self.root.after(1000, self._refresh_sheet)

    def _unsub_sheet(self) -> None:
        self._Bsub.state(('!disabled',))
        self._Bsub_clear.state(('disabled',))
        self.root.after_cancel(self._sub_sheet_last)

    def _paste_sheet(self) -> None:
        image = ImgGr.grabclipboard()
        if image:
            sheet = Rendering.Sheet(image)
            self._Vindex.set('0')
            self._Vsheet.set(sheet)
            self._Vsheet_name.set('Pasted Sheet')

            self._ROoutput.reset_view()
            self._unsub_sheet()
            self._unsub_mask()
        else:
            IO.InfobarAlert(False, None, 'Paste Failed.')

    def _load_mask(self) -> None:
        path = tkfile.askopenfilename(initialdir = self.config.data['sheets_dir'], filetypes = (('Image (png, tiff, tif)', ('*.png', '*.tiff', '*.tif')),))
        if path:
            try:
                loaded = IO.load_mask(path, self._Vsheet.get())
            except Exception as e:
                IO.InfobarAlert(True, e, f'Couldn\'t open mask file: {e}')
                return
            
            self._Vsheet.set(loaded[0])
            self._Vmask_sheet_name.set(loaded[1])

            self._unsub_mask()

    def _sub_mask(self) -> None:
        path = self._Vmask_sheet_name.get()

        if path:
            self._Bsub_mask.state(('disabled',))
            self._Bsub_mask_clear.state(('!disabled',))
            self.root.after(1000, self._refresh_mask)

    def _refresh_mask(self) -> None:
        path = self._Vmask_sheet_name.get()

        try:
            mtime = os.path.getmtime(path)
        except OSError as e: # if file stops being available
            self._unsub_mask()
            IO.InfobarAlert(True, e, f'Subscription to {path} lost.')
            return

        if self._sub_mask_mtime != mtime:
            self._sub_mask_mtime = mtime

            loaded = IO.load_mask(path, self._Vsheet.get())
            self._Vsheet.set(loaded[0])

        self._sub_mask_last = self.root.after(1000, self._refresh_mask)

    def _unsub_mask(self) -> None:
        self._Bsub_mask.state(('!disabled',))
        self._Bsub_mask_clear.state(('disabled',))
        self.root.after_cancel(self._sub_mask_last)

    def _paste_mask(self) -> None:
        image = ImgGr.grabclipboard()
        if image:
            sheet = Rendering.Sheet(self._Vsheet.get().sheet_image, image)
            self._Vsheet.set(sheet)
            self._Vmask_sheet_name.set('Pasted Mask')

            self._unsub_mask()
        else:
            IO.InfobarAlert(False, None, 'Paste Failed')

    def _render(self) -> None:
        mode = self._Vmode.get().strip()
        kwargs = {
            'sheet': self._Vsheet.get(),
            'index': self._Vindex.get(),
            'length': int(self._Vlength.get()),
            'width': int(self._Vwidth.get()),
            'height': int(self._Vheight.get()),
            'upscale': int(self._Vscale.get()),
            'shadow': self._Vhas_shadows.get(),
            'shadow_color': self._Vshadow_color.get(),
            'outline': self._Vhas_outline.get(),
            'outline_color': self._Voutline_color.get(),
            'has_bg': self._Vhas_bg.get(),
            'bg_color': self._Vbg_color.get(),
            'has_mask': self._Vhas_mask.get(),
            'clothing_texture': self._Vclothing_textile.get(),
            'accessory_texture': self._Vaccessory_textile.get(),
            'shadow_strength': float(self._Vshadow_strength.get()),
            'outline_thickness': int(self._Voutline_thickness.get())
        }

        render = IO.render(mode, **kwargs)
        self._Vrendered_images.set(render)

    def _save(self) -> None:
        mode = self._Vmode.get().strip()

        if mode == 'Image' or mode == 'Overview':
            filetype = 'png'

        if mode == 'Entity' or mode == 'Animation':
            filetype = 'gif'
        
        path = tkfile.asksaveasfilename(initialdir = self.config.data['renders_dir'], filetypes = ((filetype.upper(), f'*.{filetype}'),))
        
        if path:
            try:
                IO.save(path.removesuffix(f'.{filetype}') + f'.{filetype}',
                        mode,
                        self._Vrendered_images.get(),
                        IO.speed_filter(self._Vspeed.get(), len(self._Vrendered_images.get())),
                        self._Vhas_bg.get())
            except OSError as e:
                IO.InfobarAlert(True, e, f'Couldn\'t save file, OS Error: {e}')
            except Exception as e:
                IO.InfobarAlert(True, e, f'Couldn\'t save file: {e}')
        
    def _copy(self) -> None:
        IO.copy(self._Vrendered_images.get())

    def _alert(self, alert: IO.InfobarAlert) -> None:
        if alert.exception != None:
            with open('./bin/error.log', 'a') as f:
                traceback.print_exception(alert.exception, file = f)
                f.write('\n\n-----------------------------------------------------------------------------------------------------\n\n\n')

        if alert:
            self._IBinfo_bar.show_alert(alert)

    def _restart(self) -> None:
        self.root.destroy()
        self.__init__()
        self.root.mainloop()
