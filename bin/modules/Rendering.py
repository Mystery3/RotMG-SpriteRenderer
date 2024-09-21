import PIL.Image as Img
import PIL.ImageFilter as ImgF

class Sheet:
    def __init__(self, sheet_image: Img.Image, mask_image: Img.Image = None):
        self.sheet_image = sheet_image.convert('RGBA')
        self.size = sheet_image.size

        if mask_image:
            if mask_image.size != self.size: raise ValueError(f'Mask size, {mask_image.size}, does not match sheet size, {self.size}.')
            self.has_mask = True
            self.mask_image = mask_image.convert('RGBA')
        else:
            self.has_mask = False
            self.mask_image = Img.new('RGBA', self.size, (0, 0, 1, 0)) # blank area loaded if no mask
    
    def get_sprite(self, index: int, width: int, height: int, padding: float = 0) -> tuple[Img.Image, Img.Image]:
        '''
        Returns sprite and matching mask area. If no mask was loaded mask area is blank. Padding expands the region cropped by multiple of the width/height.
        '''
        column_count = self.size[0] // width
        column = index % column_count
        row = index // column_count

        top_left = (int((column - padding) * width), int((row - padding) * height))
        bottom_right = (int((column + 1 + padding) * width), int((row + 1 + padding) * height))

        return self.sheet_image.crop((*top_left, *bottom_right)), self.mask_image.crop((*top_left, *bottom_right))

class Sprite:
    def __init__(self, image: Img.Image):
        self.image = image
        self.size = image.size

    def _silhouette(self, color: tuple[int, int, int]) -> Img.Image:
        mask = self.image.getchannel('A')
        silhouette = Img.new('RGBA', self.image.size, (*color, 0))
        silhouette.paste(Img.new('RGBA', self.image.size, (*color, 255)), mask = mask)

        return silhouette

    def render(self, upscale: int, shadow: bool, outline: bool, shadow_color: tuple[int, int, int], shadow_strength: float, outline_color: tuple[int, int, int], outline_thickness: int) -> Img.Image:
        '''
        returns a rendered sprite with shadow and outline
        '''
        width, height = self.image.size

        base_image = Img.new('RGBA', ((width + 2) * upscale, (height + 2) * upscale), (0, 0, 1, 0))

        if shadow:
            shadow_base_image = Img.new('RGBA', ((width + 2) * upscale, (height + 2) * upscale), (*shadow_color, 0))

            shadow_silhouette = self._silhouette(shadow_color).resize((width * upscale, height * upscale), resample = Img.NEAREST)
            shadow_base_image.paste(shadow_silhouette, (upscale, upscale))
            
            shadow_base_image = shadow_base_image.filter(ImgF.BoxBlur(radius = upscale / 2)).filter(ImgF.BoxBlur(radius = upscale / 2)) # gauss approx that is ~15% faster
            shadow_strength_mask = shadow_base_image.getchannel('A').point(lambda v: 255 if int(v * shadow_strength) > 255 else int(v * shadow_strength), 'L')
            base_image.paste(Img.new('RGBA', shadow_base_image.size, (*shadow_color, 255)), mask = shadow_strength_mask)

        if outline: # outlines thickness shouldn't be more than upscale
            outline_silhouette = self._silhouette(outline_color).resize((width * upscale, height * upscale), resample = Img.NEAREST)

            if outline_thickness:
                offset = outline_thickness
            else:
                offset = upscale // 5 + 1 # looks decent when scaling
            for i in (-1 * offset, offset):
                for j in (-1 * offset, offset):
                    base_image.paste(outline_silhouette, (upscale + i, upscale + j), outline_silhouette)

        sized_image = self.image.resize((width * upscale, height * upscale), resample = Img.NEAREST)

        base_image.paste(sized_image, (upscale, upscale), sized_image.getchannel('A'))

        return base_image

class Mask:
    def __init__(self, mask_image: Img.Image, clothing_texture: Img.Image, accessory_texture: Img.Image):
        self.mask_image = mask_image
        self.size = mask_image.size

        self.clothing_texture = clothing_texture
        self.accessory_texture = accessory_texture
       
    def _silhouette(self) -> Img.Image:
        mask = self.mask_image.getchannel('A')
        silhouette = self.mask_image.copy()
        silhouette.paste(Img.new('RGBA', self.mask_image.size, (0, 0, 0, 255)), mask = mask)

        return silhouette

    def render(self, upscale: int) -> Img.Image:
        '''
        returns a scaled texture to be pasted onto a rendered sprite
        '''
        width, height = self.size
        temp_size = (width * 5, height * 5)

        base_image = Img.new('RGBA', ((width + 2) * 5, (height + 2) * 5), (0, 0, 1, 0))
        clothing_texture_fill = Img.new('RGBA', temp_size, (0, 0, 0, 0))
        accessory_texture_fill = clothing_texture_fill.copy()

        upsized_sillhouette = self._silhouette().resize(temp_size, resample = Img.NEAREST)

        self.clothing_mask = self.mask_image.getchannel('R')
        upsized_clothing_mask = self.clothing_mask.resize(temp_size, resample = Img.NEAREST)
        for x in range(0, upsized_sillhouette.width, self.clothing_texture.size[0]):
            for y in range(0, upsized_sillhouette.height, self.clothing_texture.size[1]):
                clothing_texture_fill.paste(self.clothing_texture, (x, y))

        self.accessory_mask = self.mask_image.getchannel('G')
        upsized_accessory_mask = self.accessory_mask.resize(temp_size, resample = Img.NEAREST)
        for x in range(0, upsized_sillhouette.width, self.accessory_texture.size[0]):
            for y in range(0, upsized_sillhouette.height, self.accessory_texture.size[1]):
                accessory_texture_fill.paste(self.accessory_texture, (x, y))

        upsized_sillhouette.paste(clothing_texture_fill, mask = upsized_clothing_mask)
        upsized_sillhouette.paste(accessory_texture_fill, mask = upsized_accessory_mask)
        
        base_image.paste(upsized_sillhouette, (5, 5))
        base_image = base_image.resize(((width + 2) * upscale, (height + 2) * upscale), resample = Img.NEAREST)

        return base_image

def stitch(width: int, images: list[Img.Image]) -> Img.Image:
    '''
    Input images should all be the same size. Images are placed in the order given.
    '''
    size = images[0].size
    height_factor = (len(images) - 1) // width + 1
    base_image_size = (width * size[0], height_factor * size[1])
    base_image = Img.new('RGBA', base_image_size, (0, 0, 1, 0))

    for i, image in enumerate(images):
        column = i % width
        row = i // width
        base_image.paste(image, (column * size[0], row * size[1]))

    return base_image

def render(sprite: Sprite, mask: Mask, 
           upscale: int, 
           shadow: bool, outline: bool, 
           has_mask: bool,  
           shadow_color: tuple[int, int, int], outline_color: tuple[int, int, int],
           shadow_strength: int, outline_thickness: int) -> Img.Image:
    '''
    produces a final render with all features possible including and mask
    '''
    
    rendered_sprite = sprite.render(upscale, shadow, outline, shadow_color, shadow_strength, outline_color, outline_thickness)

    if has_mask:
        rendered_mask = mask.render(upscale)
        rendered_sprite.paste(rendered_mask, mask = rendered_mask.getchannel('A'))

    return rendered_sprite
