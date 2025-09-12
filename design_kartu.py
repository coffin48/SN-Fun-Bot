from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import math
import random

# --- Ukuran kartu ---
CARD_W, CARD_H = 350, 540
BORDER_WIDTH = 15
BG_MARGIN = 5
ART_MARGIN = 15
TEXT_HEIGHT = 50  # area untuk teks rarity di bawah art
HEADER_HEIGHT = 40  # area untuk nama member dan grup di atas
DESC_HEIGHT = 60   # area untuk deskripsi di bawah foto

# --- Area background & art ---
BG_XY = (BORDER_WIDTH + BG_MARGIN, BORDER_WIDTH + BG_MARGIN)
BG_W, BG_H = CARD_W - 2*(BORDER_WIDTH + BG_MARGIN), CARD_H - 2*(BORDER_WIDTH + BG_MARGIN) - TEXT_HEIGHT
# Area foto dengan space untuk header dan deskripsi
ART_XY = (BG_XY[0]+ART_MARGIN, BG_XY[1]+ART_MARGIN+HEADER_HEIGHT)
ART_W, ART_H = BG_W - 2*ART_MARGIN, BG_H - 2*ART_MARGIN - HEADER_HEIGHT - DESC_HEIGHT

# --- Rarity list ---
RARITIES = ["Common","Rare","Epic","Legendary","FullArt"]

# --- Font configuration ---
FONT_PATH = "Gill Sans/Gill Sans Bold Italic.otf"
FONT_SIZE = 24
FONT_SIZE_SMALL = 16  # untuk nama member dan deskripsi
FONT_SIZE_TINY = 12   # untuk grup dan detail kecil

def get_font(size=FONT_SIZE):
    """Load font dengan error handling dan custom size"""
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        # Fallback ke default font jika font tidak ditemukan
        return ImageFont.load_default()

def get_small_font():
    """Get font untuk teks kecil"""
    return get_font(FONT_SIZE_SMALL)

def get_tiny_font():
    """Get font untuk teks sangat kecil"""
    return get_font(FONT_SIZE_TINY)

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
RARITY_GRADIENTS = {
    "Common": [(180,180,180),(220,220,220)],
    "Rare": [(50,150,255),(100,200,255)],
    "Epic": [(180,0,255),(220,50,255)],
    "Legendary": [(204,0,0),(255,100,100)],  # merah ruby
    "FullArt": [(255,215,0),(255,255,0)]     # gold untuk FullArt
}

BG_COLORS = {
    "Common": [(200,200,200),(150,150,150)],
    "Rare": [(80,180,255),(30,100,255)],
    "Epic": [(200,50,255),(120,0,200)],
    "Legendary": [(255,180,180),(150,0,0)],  # merah ruby
    "FullArt": [(255,248,220),(255,215,0)]   # gold untuk FullArt
}

def generate_card_template(idol_photo, rarity, member_name="Member", group_name="Group", description=""):
    """
    Generate template kartu berdasarkan rarity dengan info member seperti Pokemon TCG
    
    Args:
        idol_photo: PIL Image object foto idol
        rarity: String rarity ("Common", "Rare", "Epic", "Legendary", "FullArt")
        member_name: Nama member untuk ditampilkan di kartu
        group_name: Nama grup untuk ditampilkan di kartu
        description: Deskripsi singkat member (opsional)
        
    Returns:
        PIL Image object template kartu
    """
    font = get_font()
    small_font = get_small_font()
    tiny_font = get_tiny_font()
    
    # Generate default description jika kosong
    if not description:
        descriptions = [
            f"Main vocalist dari {group_name}",
            f"Lead dancer yang energik",
            f"Visual member dengan pesona unik",
            f"Rapper berbakat dari {group_name}",
            f"Maknae yang menggemaskan",
            f"Leader yang karismatik",
            f"All-rounder member {group_name}"
        ]
        description = random.choice(descriptions)
    
    if rarity != "FullArt":
        template = Image.new("RGBA",(CARD_W,CARD_H),(255,255,255,255))
        draw = ImageDraw.Draw(template)
        
        # Gradient border
        draw_gradient_border(draw,[0,0,CARD_W,CARD_H],BORDER_WIDTH,RARITY_GRADIENTS[rarity])
        
        # Background termasuk area teks rarity
        template = draw_rectangular_radial_bg(template,
                                              [BG_XY[0], BG_XY[1], BG_XY[0]+BG_W, BG_XY[1]+BG_H+TEXT_HEIGHT],
                                              BG_COLORS[rarity][0], BG_COLORS[rarity][1])
        
        # --- Header: Nama Member dan Grup (atas kiri) ---
        header_x = BG_XY[0] + 10
        header_y = BG_XY[1] + 5
        
        # Nama member (lebih besar)
        draw.text((header_x, header_y), member_name, fill=(255,255,255), font=small_font)
        
        # Nama grup (lebih kecil, di bawah nama member)
        group_y = header_y + 20
        draw.text((header_x, group_y), group_name, fill=(200,200,200), font=tiny_font)
        
        # Paste area art
        idol_photo_resized = resize_cover(idol_photo, ART_W, ART_H)
        template.paste(idol_photo_resized, ART_XY, idol_photo_resized)
        
        # --- Deskripsi di bawah foto ---
        desc_x = ART_XY[0] + 5
        desc_y = ART_XY[1] + ART_H + 5
        
        # Wrap text untuk deskripsi panjang
        max_width = ART_W - 10
        wrapped_desc = wrap_text(description, tiny_font, max_width)
        
        line_height = 14
        for i, line in enumerate(wrapped_desc[:3]):  # Maksimal 3 baris
            draw.text((desc_x, desc_y + i * line_height), line, fill=(220,220,220), font=tiny_font)
        
        # --- Tulis teks rarity ---
        if rarity in ["Common", "Rare"]:
            # Bawah kanan (pindah dari kiri)
            bbox = font.getbbox(rarity)
            text_w = bbox[2] - bbox[0]
            text_x = CARD_W - text_w - 15
            text_y = CARD_H - 35
        else:
            # Atas kanan
            bbox = font.getbbox(rarity)
            text_w = bbox[2] - bbox[0]
            text_x = CARD_W - text_w - 10
            text_y = 10
        
        draw.text((text_x, text_y), rarity, fill=(255,255,255), font=font)
        
    else:
        # Full Art: holo + sparkle overlay dengan teks minimal tanpa background
        template = resize_cover(idol_photo, CARD_W, CARD_H)
        template = template.convert("RGBA")
        template = add_fullart_final(template)
        
        # Tambah teks langsung di atas foto tanpa background overlay
        draw = ImageDraw.Draw(template)
        
        # Nama member di atas kiri dengan outline untuk visibility
        text_x, text_y = 15, 10
        # Text outline untuk visibility di atas foto
        for adj in range(-1, 2):
            for adj2 in range(-1, 2):
                draw.text((text_x+adj, text_y+adj2), member_name, fill=(0,0,0), font=small_font)
        draw.text((text_x, text_y), member_name, fill=(255,255,255), font=small_font)
        
        # Nama grup di bawah nama member dengan outline
        group_y = text_y + 22
        for adj in range(-1, 2):
            for adj2 in range(-1, 2):
                draw.text((text_x+adj, group_y+adj2), group_name, fill=(0,0,0), font=tiny_font)
        draw.text((text_x, group_y), group_name, fill=(220,220,220), font=tiny_font)
    
    return template

def wrap_text(text, font, max_width):
    """Wrap text untuk fit dalam width tertentu"""
    words = text.split(' ')
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = font.getbbox(test_line)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)  # Word terlalu panjang, paksa masuk
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines
