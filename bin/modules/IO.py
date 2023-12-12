from . import Rendering
import PIL.Image as Img
import io, json, win32clipboard

class SheetVar: # var with get/set like tkinter vars
    def __init__(self, sheet: Rendering.Sheet):
        self._sheet = sheet
        self._func = (lambda: None,)

    def get(self) -> Rendering.Sheet:
        return self._sheet
    
    def set(self, sheet: Rendering.Sheet) -> None:
        self._sheet = sheet
        for func in self._func:
            func()

    def trace_add(self, *func: callable) -> None: # emulates a simplified tkvar trace
        self._func = func

class ImgVar: # var with get/set like tkinter vars
    def __init__(self, image: Img.Image):
        self._image = image
        self._func = (lambda: None,)

    def get(self) -> Img.Image:
        return self._image
    
    def set(self, image: Img.Image) -> None:
        self._image = image
        for func in self._func:
            func()

    def trace_add(self, *func: callable) -> None: # emulates a simplified tkvar trace
        self._func = func

class ListVar: # var with get/set like tkinter vars
    def __init__(self, list: list):
        self._list = list
        self._func = (lambda: None,)
        
    def get(self) -> list:
        return self._list
    
    def set(self, list: list) -> None:
        self._list = list
        for func in self._func:
            func()

    def trace_add(self, *func: callable) -> None: # emulates a simplified tkvar trace
        self._func = func

class Config:
    def __init__(self, path: str):
        self.path = path
        self.read()

    def read(self):
        with open(self.path, 'r') as f:
            self.data = json.load(f)
    
    def change(self, keychain: list[any], value):
        '''
        ex: c.write(['Style', 'Dark', 'Frame', 'Height'], 16)
        to change data['Style']['Dark']['Frame']['Height'] to 16
        '''
        buffer = self.data

        for key in keychain[:-1]:
            buffer = buffer[key]

        buffer[keychain[-1]] = value

    def write(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent = 4)

class InfobarAlert:
    func = lambda _: None

    def __init__(self, is_error: bool, exception: Exception, text: str):
        '''
        is_error False = warning
        '''
        self.is_error = is_error
        self.exception = exception
        self.text = text

        InfobarAlert.func(self)
        
    def __bool__(self):
        return bool(self.text)

PNG = win32clipboard.RegisterClipboardFormat('PNG')
TIF = win32clipboard.RegisterClipboardFormat('TIF')
TIFF = win32clipboard.RegisterClipboardFormat('TIFF')

def index_filter(index: str) -> int:
    if not index or index.endswith('0x'):
        return 0
    if index.startswith('0x') or index.startswith('-0x'):
        return int(index, base = 16)
    return int(index)

def length_filter(length: int, index: str, size: tuple[int, int], width: int, height: int, offset: int = 1, overview_override: bool = False) -> int:
    if length == 0:
        if overview_override:
            return 3
        column_count = size[0] // width
        row_count = size[1] // height
        return (column_count * row_count - index_filter(index)) // offset
    else:
        return length

def speed_filter(speeds_string: str, length: int) -> list[int]:
    speeds = [int(e.strip()) if e.strip().isnumeric() else 500 for e in speeds_string.split(',')] # yikes!
    speeds = [500 if speed == 0 else speed for speed in speeds]
    speeds = speeds * (length // len(speeds) + 1) # this has some undefined behavior but it still works
    return speeds[:length]

def load_sheet(path: str) -> tuple[Rendering.Sheet, str]:
    sheet = Rendering.Sheet(Rendering.Img.open(path))
    return (sheet, path)
    
def load_mask(path: str, sheet: Rendering.Sheet) -> tuple[Rendering.Sheet, str]:
    sheet = Rendering.Sheet(sheet.sheet_image, Img.open(path))
    return (sheet, path)

def render(mode: str, *args, **kwargs) -> list[Img.Image]:
    '''
    modes: Image, Entity, Animation, Overview

    args: sheet, index, length, width, height, upscale, shadow, outline,
          has_bg, bg_color, has_mask, clothing_texture, accessory_texture,
          shadow_strength, shadow_color, outline_thickness, outline_color

    a function that maps modes to render functions for i/o
    '''
    if mode == 'Image':
        return r_image(*args, **kwargs)
    if mode == 'Entity':
        return r_entity(*args, **kwargs)
    if mode == 'Animation':
        return r_animation(*args, **kwargs)
    if mode == 'Overview':
        return r_overview(*args, **kwargs)

def r_image(sheet: Rendering.Sheet, index: str, # str in case hex conversion needed
           length: int, # length in image mode is how many consecutive images to render
           width: int, height: int,
           upscale: int, 
           shadow: bool, outline: bool, 
           shadow_color: tuple[int, int, int], outline_color: tuple[int, int, int],
           has_bg: bool = False, bg_color: str = '',
           has_mask: bool = False, clothing_texture: Img.Image = None, accessory_texture: Img.Image = None, 
           shadow_strength: float = 1.0, outline_thickness: int = None) -> list[Img.Image]:
    
    f_index = index_filter(index) # filtered index
    f_length = length_filter(length, index, sheet.size, width, height) # filtered length, if 0, length set to entire sheet
    rendered_images = []

    for i in range(f_length):
        sprite, mask = sheet.get_sprite(f_index + i, width, height)
        sprite, mask = Rendering.Sprite(sprite), Rendering.Mask(mask, clothing_texture, accessory_texture)
        rendered_images.append(Rendering.render(sprite, mask, upscale, shadow, outline, has_mask, shadow_color, outline_color, shadow_strength, outline_thickness))

    column_count = sheet.size[0] // width
    stitch_width = (column_count if len(rendered_images) > column_count else len(rendered_images))

    final = Rendering.stitch(stitch_width, rendered_images)
    if has_bg:
        bg = Img.new('RGBA', final.size, bg_color)
        final = Img.alpha_composite(bg, final)

    return [final,]

def r_entity(sheet: Rendering.Sheet, index: str, # str in case hex conversion needed
             length: int, # length in entity mode corresponds to the number of rows rendered
             width: int, height: int,
             upscale: int, 
             shadow: bool, outline: bool, 
             shadow_color: tuple[int, int, int], outline_color: tuple[int, int, int],
             has_bg: bool = False, bg_color: str = '',
             has_mask: bool = False, clothing_texture: Img.Image = None, accessory_texture: Img.Image = None, 
             shadow_strength: float = 1.0, outline_thickness: int = None) -> list[Img.Image]:
    
    f_index = index_filter(index) # filtered index
    f_length = length_filter(length, index, sheet.size, width, height, offset = 7) # filtered length, if 0, length set to entire sheet, divided by 7 for entity mode if full sheet
    frame0, frame1 = [], []

    for i in range(f_length):
        row0, row1 = [], []
        second_walk = False
        
        # still
        sprite0, mask0 = sheet.get_sprite(f_index + i * 7, width, height)
        sprite0, mask0 = Rendering.Sprite(sprite0), Rendering.Mask(mask0, clothing_texture, accessory_texture)
        
        still = Rendering.render(sprite0, mask0, upscale, shadow, outline, has_mask, shadow_color, outline_color, shadow_strength, outline_thickness)
        row0.append(still)
        row1.append(still)

        # walk 1
        sprite1, mask1 = sheet.get_sprite(f_index + 1 + i * 7, width, height)
        sprite1, mask1 = Rendering.Sprite(sprite1), Rendering.Mask(mask1, clothing_texture, accessory_texture)
        row0.append(Rendering.render(sprite1, mask1, upscale, shadow, outline, has_mask, shadow_color, outline_color, shadow_strength, outline_thickness))

        # walk 2
        sprite2, mask2 = sheet.get_sprite(f_index + 2 + i * 7, width, height)
        for value in sprite2.getdata(): # some sprite sheets omit the walk 2, implying that it's the same as walk 1
            if value[3] != 0:
                second_walk = True
                break
        if second_walk:
            sprite2, mask2 = Rendering.Sprite(sprite2), Rendering.Mask(mask2, clothing_texture, accessory_texture)
            row1.append(Rendering.render(sprite2, mask2, upscale, shadow, outline, has_mask, shadow_color, outline_color, shadow_strength, outline_thickness))
        else:
            row1.append(row0[1])

        # attack 1
        sprite3, mask3 = sheet.get_sprite(f_index + 4 + i * 7, width, height)
        sprite3, mask3 = Rendering.Sprite(sprite3), Rendering.Mask(mask3, clothing_texture, accessory_texture)
        row0.append(Rendering.render(sprite3, mask3, upscale, shadow, outline, has_mask, shadow_color, outline_color, shadow_strength, outline_thickness))

        # attack 2
        sprite4_0, mask4_0 = sheet.get_sprite(f_index + 5 + i * 7, width, height)
        sprite4_1, mask4_1 = sheet.get_sprite(f_index + 6 + i * 7, width, height)
        sprite4, mask4 = Rendering.Sprite(Rendering.stitch(2, [sprite4_0, sprite4_1])), Rendering.Mask(Rendering.stitch(2, [mask4_0, mask4_1]), clothing_texture, accessory_texture)
        
        rendered_image = Rendering.render(sprite4, mask4, upscale, shadow, outline, has_mask, shadow_color, outline_color, shadow_strength, outline_thickness)
        row1.append(rendered_image)

        frame0.append(Rendering.stitch(4, row0))
        frame1.append(Rendering.stitch(4, row1))

    frame0 = Rendering.stitch(1, frame0)
    frame1 = Rendering.stitch(1, frame1)

    if has_bg:
        bg = Img.new('RGBA', frame0.size, bg_color)
        frame0 = Img.alpha_composite(bg, frame0)
        frame1 = Img.alpha_composite(bg, frame1)

    return [frame0, frame1]

def r_animation(sheet: Rendering.Sheet, index: str, # str in case hex conversion needed
                length: int, # length in animation mode corresponds to how many frames are animated
                width: int, height: int,
                upscale: int, 
                shadow: bool, outline: bool, 
                shadow_color: tuple[int, int, int], outline_color: tuple[int, int, int],
                has_bg: bool = False, bg_color: str = '',
                has_mask: bool = False, clothing_texture: Img.Image = None, accessory_texture: Img.Image = None, 
                shadow_strength: float = 1.0, outline_thickness: int = None) -> list[Img.Image]:
    
    f_index = index_filter(index) # filtered index
    f_length = length_filter(length, index, sheet.size, width, height) # filtered length, if 0, length set to entire sheet
    rendered_images = []

    bg = False

    for i in range(f_length):
        sprite, mask = sheet.get_sprite(f_index + i, width, height)
        sprite, mask = Rendering.Sprite(sprite), Rendering.Mask(mask, clothing_texture, accessory_texture)
        render = Rendering.render(sprite, mask, upscale, shadow, outline, has_mask, shadow_color, outline_color, shadow_strength, outline_thickness)
        
        if has_bg:
            if not bg:
                bg = Img.new('RGBA', render.size, bg_color)
            render = Img.alpha_composite(bg, render)

        rendered_images.append(render)

    return rendered_images

def r_overview(sheet: Rendering.Sheet, index: str, # str in case hex conversion needed
                length: int, # length in overview mode corresponds to how many frames are captured (front, side, back). for sheets of enemies use length 3
                width: int, height: int,
                upscale: int, 
                shadow: bool, outline: bool, 
                shadow_color: tuple[int, int, int], outline_color: tuple[int, int, int],
                has_bg: bool = False, bg_color: str = '',
                has_mask: bool = False, clothing_texture: Img.Image = None, accessory_texture: Img.Image = None, 
                shadow_strength: float = 1.0, outline_thickness: int = None) -> list[Img.Image]:
    
    f_index = index_filter(index) # filtered index
    f_length = length_filter(length, index, sheet.size, width, height, overview_override = True) # filtered length, if 0, length set to entire sheet, length should be a number from 1 to 3
    sheet_length = length_filter(0, '0', sheet.size, width, height, offset = 7)
    rendered_images = []

    for i in range(sheet_length):
        for j in range(f_length):
            sprite, mask = sheet.get_sprite(f_index + i * 21 + j * 7, width, height)
            sprite, mask = Rendering.Sprite(sprite), Rendering.Mask(mask, clothing_texture, accessory_texture)
            rendered_images.append(Rendering.render(sprite, mask, upscale, shadow, outline, has_mask, shadow_color, outline_color, shadow_strength, outline_thickness))

    final = Rendering.stitch(6, rendered_images)
    if has_bg:
        bg = Img.new('RGBA', final.size, bg_color)
        final = Img.alpha_composite(bg, final)

    return [final,]

def alpha_filter(image: Img.Image) -> Img.Image:
    base = Img.new('RGBA', image.size, (0, 0, 0, 1)) # tk has speed issues with 0 alpha
    base.paste(image, (0, 0), image.getchannel('A').point(lambda v: v > 0, '1')) # this effectively replaces all 0 alpha values with 1
    return base

def save(path: str, mode: str, rendered_images: list[Img.Image], gif_durations: list[int], has_bg: bool):
    '''
    DO NOT USE THIS COLOR IN GIFS
    (0, 0, 1) or #000001
    '''
    if mode == 'Image' or mode == 'Overview':
        rendered_images[0].save(path, 'PNG')
    if mode == 'Entity' or mode == 'Animation':
        if has_bg:
            rendered_images[0].save(path, 'GIF', save_all = True, append_images = rendered_images[1:], duration = gif_durations, loop = 0, disposal = 2)
        else:
            rendered_images[0].save(path, 'GIF', save_all = True, append_images = rendered_images[1:], transparency = 0, duration = gif_durations, loop = 0, disposal = 2)

def copy(images: list[Img.Image]) -> None:
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()

    png_buffer, tif_buffer, bmp_buffer = io.BytesIO(), io.BytesIO(), io.BytesIO()

    images[0].save(png_buffer, 'PNG')
    images[0].save(tif_buffer, 'TIFF')
    images[0].save(bmp_buffer, 'BMP') # loses transparency; just-in-case format

    win32clipboard.SetClipboardData(PNG, png_buffer.getvalue())
    win32clipboard.SetClipboardData(TIF, tif_buffer.getvalue())
    win32clipboard.SetClipboardData(TIFF, tif_buffer.getvalue())
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, bmp_buffer.getvalue()[14:])
    win32clipboard.SetClipboardData(win32clipboard.CF_DIBV5, bmp_buffer.getvalue()[14:])
    
    win32clipboard.CloseClipboard()
    
def make_validate(tk_root, allowed_chars: str, test_functions: list[callable], alert_function: callable) -> callable:
    def validate(event_type: str, change: str, new: str, name: str):
        root = tk_root
        chars = allowed_chars
        tests = test_functions
        alert = alert_function

        match event_type:
            case 'key':
                if new == '': # allow empty string to retype something
                    return True
                
                if change not in chars:
                    alert(InfobarAlert(False, None, f'Bad Input {new}'))
                    return False
                
                for test in tests:
                    try: # if one test works the string is valid
                        test(new)
                        return True
                    except:
                        pass
                else:
                    alert(InfobarAlert(False, None, f'Bad Input {new}'))

                return False

            case 'focusout':
                if new == '':
                    root.setvar(root.nametowidget(name)['textvariable'], '1') # would love to set it to something else but I wouldn't like to make this an object
                return True

            case _:
                return True

    return validate
