from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import os
from IPython.display import display
import math
import random

# --- Ukuran kartu ---
CARD_W, CARD_H = 350, 540
BORDER_WIDTH = 15
BG_MARGIN = 5
ART_MARGIN = 15
TEXT_HEIGHT = 50  # area untuk teks rarity di bawah art

# --- Area background & art ---
BG_XY = (BORDER_WIDTH + BG_MARGIN, BORDER_WIDTH + BG_MARGIN)
BG_W, BG_H = CARD_W - 2*(BORDER_WIDTH + BG_MARGIN), CARD_H - 2*(BORDER_WIDTH + BG_MARGIN) - TEXT_HEIGHT
ART_XY = (BG_XY[0]+ART_MARGIN, BG_XY[1]+ART_MARGIN)
ART_W, ART_H = BG_W - 2*ART_MARGIN, BG_H - 2*ART_MARGIN

# --- File foto sample ---
sample_photo_path = "/content/aespa_Giselle_1.jpg"
idol_photo_original = Image.open(sample_photo_path).convert("RGBA")

# --- Folder output ---
output_folder = "templates_final_safe_ruby_textpos"
rarities = ["Common","Rare","Epic","Legendary","FullArt"]
variations_per_rarity = 2
os.makedirs(output_folder, exist_ok=True)

# --- Load font Gill Sans Bold Italic ---
font_path = "/content/Font/Gill Sans Bold Italic.otf"
font_size = 24
font = ImageFont.truetype(font_path, font_size)

# --- Resize cover tanpa padding ---
def resize_cover(img, target_w, target_h):
    w,h = img.size
    scale = max(target_w/w, target_h/h)
    new_w, new_h = int(w*scale), int(h*scale)
    img_resized = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w)//2
    top = (new_h - target_h)//2
    return img_resized.crop((left, top, left+target_w, top+target_h))

# --- Gradient border ---
def draw_gradient_border(draw, xy, width, colors):
    left, top, right, bottom = xy
    for i in range(width):
        t = i/width
        r = int(colors[0][0]*(1-t)+colors[1][0]*t)
        g = int(colors[0][1]*(1-t)+colors[1][1]*t)
        b = int(colors[0][2]*(1-t)+colors[1][2]*t)
        draw.rectangle([left+i, top+i, right-i-1, bottom-i-1], outline=(r,g,b))

# --- Rectangular radial spotlight background ---
def draw_rectangular_radial_bg(template, bbox, center_color, edge_color):
    left, top, right, bottom = bbox
    w, h = right-left, bottom-top
    cx, cy = w/2, h/2
    for y in range(h):
        for x in range(w):
            dx = (x - cx)/(w/2)
            dy = (y - cy)/(h/2)
            dist = min(math.sqrt(dx*dx + dy*dy),1.0)
            color = tuple(int(center_color[i]*(1-dist) + edge_color[i]*dist) for i in range(3))
            template.putpixel((left+x, top+y), color + (255,))
    return template

# --- Full Art holo rainbow overlay (tipis) ---
def add_fullart_holo(img):
    w,h = img.size
    overlay = Image.new("RGBA",(w,h),(0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    colors = [(255,0,0,30),(255,127,0,30),(255,255,0,30),(0,255,0,30),
              (0,0,255,30),(75,0,130,30),(148,0,211,30)]
    stripe_h = h // len(colors)
    for i,color in enumerate(colors):
        draw.rectangle([0,i*stripe_h,w,(i+1)*stripe_h], fill=color)
    overlay = overlay.filter(ImageFilter.GaussianBlur(5))
    return Image.alpha_composite(img.convert("RGBA"), overlay)

# --- Sparkling holo overlay (lebih sedikit & elegan) ---
def add_sparkles(img, count=60):
    w,h = img.size
    sparkle_layer = Image.new("RGBA", (w,h),(0,0,0,0))
    draw = ImageDraw.Draw(sparkle_layer)
    for _ in range(count):
        x = random.randint(0,w-1)
        y = random.randint(0,h-1)
        size = random.randint(1,2)
        alpha = random.randint(80,150)
        draw.ellipse([x,y,x+size,y+size], fill=(255,255,255,alpha))
    return Image.alpha_composite(img, sparkle_layer)

# --- Gabungkan holo + sparkle ---
def add_fullart_final(img):
    img = add_fullart_holo(img)
    img = add_sparkles(img, count=60)
    return img

# --- Gradient & background colors per rarity (Legendary = merah ruby) ---
rarity_gradients = {
    "Common": [(180,180,180),(220,220,220)],
    "Rare": [(50,150,255),(100,200,255)],
    "Epic": [(180,0,255),(220,50,255)],
    "Legendary": [(204,0,0),(255,100,100)]  # merah ruby
}
bg_colors = {
    "Common": [(200,200,200),(150,150,150)],
    "Rare": [(80,180,255),(30,100,255)],
    "Epic": [(200,50,255),(120,0,200)],
    "Legendary": [(255,180,180),(150,0,0)]  # merah ruby
}

all_images = []

for rarity in rarities:
    folder_rarity = os.path.join(output_folder, rarity)
    os.makedirs(folder_rarity, exist_ok=True)
    
    for i in range(variations_per_rarity):
        if rarity != "FullArt":
            template = Image.new("RGBA",(CARD_W,CARD_H),(255,255,255,255))
            draw = ImageDraw.Draw(template)
            
            # Gradient border
            draw_gradient_border(draw,[0,0,CARD_W,CARD_H],BORDER_WIDTH,rarity_gradients[rarity])
            
            # Background termasuk area teks rarity
            template = draw_rectangular_radial_bg(template,
                                                  [BG_XY[0], BG_XY[1], BG_XY[0]+BG_W, BG_XY[1]+BG_H+TEXT_HEIGHT],
                                                  bg_colors[rarity][0], bg_colors[rarity][1])
            
            # Paste area art
            idol_photo = resize_cover(idol_photo_original, ART_W, ART_H)
            template.paste(idol_photo, ART_XY, idol_photo)
            
            # --- Tulis teks rarity ---
            if rarity in ["Common", "Rare"]:
                # Bawah kiri
                text_x = ART_XY[0] + 5
                text_y = ART_XY[1] + ART_H + 5
            else:
                # Atas kanan
                bbox = font.getbbox(rarity)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                text_x = CARD_W - text_w - 10
                text_y = 10
            
            draw.text((text_x, text_y), rarity, fill=(255,255,255), font=font)
            
        else:
            # Full Art: holo + sparkle overlay
            template = resize_cover(idol_photo_original, CARD_W, CARD_H)
            template = template.convert("RGBA")
            template = add_fullart_final(template)
        
        filename = f"{rarity}_{i+1}.png"
        template.save(os.path.join(folder_rarity,filename))
        all_images.append(template)

# --- Preview horizontal ---
total_width = CARD_W*len(all_images)
horizontal_strip = Image.new("RGBA",(total_width,CARD_H),(255,255,255,255))
for idx,img in enumerate(all_images):
    horizontal_strip.paste(img,(CARD_W*idx,0))
display(horizontal_strip)
print("✅ Semua rarity selesai: Legendary merah ruby, border gradient, background + teks, area art, Full Art holo tipis + sparkle siap dengan teks C & R bawah kiri!")
