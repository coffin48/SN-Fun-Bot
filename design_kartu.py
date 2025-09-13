from PIL import Image, ImageDraw, ImageFont
import os
import json
import random

# Load card template data
def load_card_data():
    """Load card template data from cards_boxes.json"""
    with open("cards_boxes.json", "r") as f:
        return json.load(f)

# Fit foto ke dalam box dengan crop proporsional
def fit_photo(foto_path, target_w, target_h):
    """Resize dan crop foto untuk fit ke dalam box"""
    if not os.path.exists(foto_path):
        # Create placeholder jika foto tidak ada
        img = Image.new("RGB", (target_w, target_h), (200, 200, 200))
        draw = ImageDraw.Draw(img)
        draw.text((target_w//2-30, target_h//2-10), "NO PHOTO", fill=(100, 100, 100))
        return img
    
    foto = Image.open(foto_path).convert("RGBA")
    
    # Hitung ratio untuk crop proporsional
    foto_ratio = foto.width / foto.height
    target_ratio = target_w / target_h
    
    if foto_ratio > target_ratio:
        # Foto lebih lebar, fit by height
        new_h = target_h
        new_w = int(new_h * foto_ratio)
    else:
        # Foto lebih tinggi, fit by width
        new_w = target_w
        new_h = int(new_w / foto_ratio)
    
    # Resize foto
    foto_resized = foto.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Crop ke center
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    foto_cropped = foto_resized.crop((left, top, left + target_w, top + target_h))
    
    return foto_cropped

def fit_photo_from_image(pil_image, target_w, target_h):
    """Resize dan crop PIL Image untuk fit ke dalam box"""
    foto = pil_image.convert("RGBA")
    
    # Hitung ratio untuk crop proporsional
    foto_ratio = foto.width / foto.height
    target_ratio = target_w / target_h
    
    if foto_ratio > target_ratio:
        # Foto lebih lebar, fit by height
        new_h = target_h
        new_w = int(new_h * foto_ratio)
    else:
        # Foto lebih tinggi, fit by width
        new_w = target_w
        new_h = int(new_w / foto_ratio)
    
    # Resize foto
    foto_resized = foto.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Crop ke center
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    foto_cropped = foto_resized.crop((left, top, left + target_w, top + target_h))
    
    return foto_cropped

# Draw text dengan auto-fit ke dalam box
def draw_fit_text(draw, text, box, font_path, max_font_size):
    """Draw text yang auto-fit ke dalam box"""
    x, y, w, h = box
    
    # Try to load font
    try:
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, max_font_size)
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    font_size = max_font_size
    
    # Get text dimensions
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    # Scale font down jika teks lebih lebar dari box
    while text_w > w and font_size > 5:
        font_size -= 1
        try:
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    
    # Position text (left-aligned, vertically centered)
    text_x = x
    text_y = y + (h - text_h) // 2
    
    # Draw text dengan outline untuk visibility
    outline_color = (255, 255, 255, 255)  # White outline
    text_color = (0, 0, 0, 255)  # Black text
    
    # Draw outline
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx != 0 or dy != 0:
                draw.text((text_x + dx, text_y + dy), text, font=font, fill=outline_color)
    
    # Draw main text
    draw.text((text_x, text_y), text, font=font, fill=text_color)

# Generate card dengan template system
def generate_card_template(idol_photo, rarity, member_name="", group_name="", description=""):
    """
    Generate card menggunakan template system
    
    Args:
        idol_photo: PIL Image object atau path ke foto
        rarity: String rarity ("Common", "Rare", "DR", "SR", "SAR")
        member_name: Nama member
        group_name: Nama grup (opsional, akan digabung dengan member_name jika ada)
        description: Deskripsi kartu (opsional)
    
    Returns:
        PIL Image object kartu yang sudah jadi
    """
    
    # Load card data
    card_data = load_card_data()
    
    # Filter templates berdasarkan rarity
    available_templates = [key for key, info in card_data.items() if info["rarity"] == rarity]
    
    if not available_templates:
        raise ValueError(f"No templates found for rarity: {rarity}")
    
    # Random pilih template variant
    selected_template = random.choice(available_templates)
    template_info = card_data[selected_template]
    
    # Load template image
    template_folder = "Template"
    template_path = os.path.join(template_folder, f"{selected_template}.png")
    
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found: {template_path}")
    
    # Load template
    template = Image.open(template_path).convert("RGBA")
    canvas = Image.new("RGBA", template.size, (0, 0, 0, 0))
    
    # Get boxes info
    boxes = template_info["boxes"]
    
    # Process foto input
    if isinstance(idol_photo, str):
        # Jika input adalah path
        foto_img = fit_photo(idol_photo, boxes["photo"][2], boxes["photo"][3])
    else:
        # Jika input adalah PIL Image
        foto_img = fit_photo_from_image(idol_photo, boxes["photo"][2], boxes["photo"][3])
    
    # Paste foto ke canvas
    canvas.paste(foto_img, (boxes["photo"][0], boxes["photo"][1]), foto_img)
    
    # Paste template di atas foto
    canvas = Image.alpha_composite(canvas, template)
    
    # Add text
    draw = ImageDraw.Draw(canvas)
    font_path = "Gill Sans/Gill Sans Bold Italic.otf"
    
    # Draw member name
    if member_name:
        display_name = f"{member_name} {group_name}" if group_name else member_name
        draw_fit_text(draw, display_name, boxes["name"], font_path, 20)
    
    # Draw description
    if description:
        draw_fit_text(draw, description, boxes["desc"], font_path, 14)
    elif member_name and group_name:
        # Auto-generate description jika kosong
        auto_desc = f"Member {group_name} yang berbakat"
        draw_fit_text(draw, auto_desc, boxes["desc"], font_path, 14)
    
    return canvas

# Compatibility dengan sistem lama
RARITIES = ["Common", "Rare", "DR", "SR", "SAR"]

# Mapping untuk backward compatibility
RARITY_MAPPING = {
    "Common": "Common",
    "Rare": "Rare", 
    "Epic": "DR",      # Epic -> Double Rare
    "Legendary": "SR",  # Legendary -> Super Rare
    "FullArt": "SAR"   # FullArt -> Special Art Rare
}

def map_old_rarity(old_rarity):
    """Map old rarity system to new rarity system"""
    return RARITY_MAPPING.get(old_rarity, old_rarity)

# Test function
def test_template_system():
    """Test template system dengan sample data"""
    print("Testing Template-Based Card System")
    print("=" * 50)
    
    # Test dengan foto sample
    sample_photo_path = "Databse Foto Idol Kpop/aespa/Karina/aespa_Karina_1.jpg"
    
    for rarity in RARITIES:
        try:
            print(f"Testing {rarity}...")
            card = generate_card_template(
                idol_photo=sample_photo_path,
                rarity=rarity,
                member_name="Karina",
                group_name="aespa",
                description=f"Testing {rarity} card design"
            )
            
            output_filename = f"test_{rarity.lower()}_card.png"
            card.save(output_filename, 'PNG')
            print(f"✅ {rarity} card saved: {output_filename}")
            
        except Exception as e:
            print(f"❌ Error testing {rarity}: {e}")
    
    print("=" * 50)
    print("Template system test completed!")

if __name__ == "__main__":
    test_template_system()
