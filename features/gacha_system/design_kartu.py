from PIL import Image, ImageDraw, ImageFont
import os
import json
import random

# Enhanced description system
def generate_enhanced_description(member_name, group_name, rarity):
    """Generate enhanced 3-point description untuk card dengan emoji"""
    
    # Database role dan karakteristik K-pop dengan emoji
    kpop_roles = [
        "🎤 Main Vocalist", "🎵 Lead Vocalist", "🎶 Sub Vocalist",
        "💃 Main Dancer", "🕺 Lead Dancer", "✨ Sub Dancer", 
        "🎤 Main Rapper", "🔥 Lead Rapper", "🎯 Sub Rapper",
        "👑 Visual", "⭐ Face of the Group", "💫 Center",
        "👑 Leader", "🌟 Maknae", "🎭 All-Rounder"
    ]
    
    personality_traits = [
        "✨ Charismatic", "⚡ Energetic", "💎 Elegant", "🥰 Cute", "😎 Cool",
        "🌙 Mysterious", "☀️ Bright", "🌸 Gentle", "🔥 Fierce", "🎈 Playful",
        "👑 Sophisticated", "💖 Charming", "💪 Bold", "🍯 Sweet", "🦋 Confident"
    ]
    
    skills = [
        "🎵 exceptional vocals", "💃 amazing dance skills", "🎤 powerful rap",
        "🎭 stage presence", "📺 variety show talent", "🎬 acting ability",
        "✍️ songwriting skills", "🎨 choreography creation", "🌍 language skills",
        "👗 fashion sense", "👑 leadership qualities", "💕 fan interaction"
    ]
    
    achievements = [
        "📱 viral fancam", "🎵 solo debut", "🎬 acting debut", "📺 variety regular",
        "🌟 brand ambassador", "🏆 award winner", "📈 chart topper", "🌍 international recognition",
        "🤝 collaboration artist", "🔥 trendsetter", "📱 social media star", "🎭 multi-talented"
    ]
    
    # Generate description berdasarkan rarity
    description_points = []
    
    # Point 1: Role/Position (selalu ada)
    roles = random.sample(kpop_roles, min(2, len(kpop_roles)))
    if len(roles) == 2:
        description_points.append(f"{roles[0]} & {roles[1]}")
    else:
        description_points.append(f"{roles[0]}")
    
    # Point 2: Personality/Characteristic
    if rarity in ["SAR", "SR"]:
        # High rarity: lebih detailed
        trait = random.choice(personality_traits)
        skill = random.choice(skills)
        description_points.append(f"{trait} personality with {skill}")
    else:
        # Lower rarity: simple trait
        trait = random.choice(personality_traits)
        description_points.append(f"Known for {trait.lower()} charm")
    
    # Point 3: Achievement/Special (rarity dependent)
    if rarity == "SAR":
        # Ultimate rarity: major achievement
        achievement = random.choice(achievements)
        description_points.append(f"🌟 {achievement.title()} & global icon")
    elif rarity == "SR":
        # Super rare: notable achievement
        achievement = random.choice(achievements)
        description_points.append(f"⭐ Rising star with {achievement}")
    elif rarity == "DR":
        # Double rare: group contribution
        description_points.append(f"💎 Key member of {group_name}")
    else:
        # Common/Rare: basic info
        description_points.append(f"💖 Beloved {group_name} member")
    
    # Format untuk card box
    return "\n".join(description_points)

# Load card template data
def load_card_data():
    """Load card template data from cards_boxes.json"""
    with open("assets/templates/cards_boxes.json", "r") as f:
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
def get_rarity_colors(rarity):
    """Get color scheme berdasarkan rarity"""
    color_schemes = {
        "Common": {
            "text": (255, 255, 255, 255),      # White
            "outline": (0, 0, 0, 255),        # Black
            "glow": None
        },
        "Rare": {
            "text": (100, 200, 255, 255),     # Light Blue
            "outline": (0, 50, 100, 255),     # Dark Blue
            "glow": (100, 200, 255, 80)
        },
        "DR": {
            "text": (255, 215, 0, 255),       # Gold
            "outline": (139, 69, 19, 255),    # Brown
            "glow": (255, 215, 0, 100)
        },
        "SR": {
            "text": (255, 105, 180, 255),     # Hot Pink
            "outline": (139, 0, 139, 255),    # Dark Magenta
            "glow": (255, 105, 180, 120)
        },
        "SAR": {
            "text": (255, 255, 255, 255),     # White
            "outline": (148, 0, 211, 255),    # Dark Violet
            "glow": (255, 20, 147, 150)       # Deep Pink glow
        }
    }
    return color_schemes.get(rarity, color_schemes["Common"])

def create_gradient_text(draw, text, position, font, start_color, end_color, width):
    """Create gradient text effect"""
    # Create temporary image for gradient
    temp_img = Image.new("RGBA", (width, font.size), (0, 0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    
    # Draw text on temp image
    temp_draw.text((0, 0), text, font=font, fill=(255, 255, 255, 255))
    
    # Create gradient overlay
    for x in range(width):
        ratio = x / width if width > 0 else 0
        r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
        g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
        b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
        
        # Apply gradient to each column
        for y in range(font.size):
            pixel = temp_img.getpixel((x, y))
            if pixel[3] > 0:  # If pixel is not transparent
                temp_img.putpixel((x, y), (r, g, b, pixel[3]))
    
    return temp_img

def draw_enhanced_text(draw, text, box, font_path, max_font_size, rarity, is_title=False):
    """Draw text dengan enhanced styling berdasarkan rarity"""
    x, y, w, h = box
    
    # Load font dengan fallback
    try:
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, max_font_size)
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    font_size = max_font_size
    
    # Auto-fit font size
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
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
    
    # Position text
    text_x = x + (w - text_w) // 2 if is_title else x  # Center for titles
    text_y = y + (h - text_h) // 2
    
    # Get rarity colors
    colors = get_rarity_colors(rarity)
    
    # Draw glow effect untuk rarity tinggi
    if colors["glow"] and rarity in ["DR", "SR", "SAR"]:
        glow_size = 3 if rarity == "SAR" else 2
        for dx in range(-glow_size, glow_size + 1):
            for dy in range(-glow_size, glow_size + 1):
                if dx != 0 or dy != 0:
                    distance = (dx**2 + dy**2)**0.5
                    if distance <= glow_size:
                        alpha = int(colors["glow"][3] * (1 - distance/glow_size))
                        glow_color = (*colors["glow"][:3], alpha)
                        draw.text((text_x + dx, text_y + dy), text, font=font, fill=glow_color)
    
    # Draw outline (multi-layer untuk rarity tinggi)
    outline_layers = 2 if rarity in ["SR", "SAR"] else 1
    for layer in range(outline_layers, 0, -1):
        for dx in range(-layer, layer + 1):
            for dy in range(-layer, layer + 1):
                if dx != 0 or dy != 0:
                    outline_alpha = 255 // layer
                    outline_color = (*colors["outline"][:3], outline_alpha)
                    draw.text((text_x + dx, text_y + dy), text, font=font, fill=outline_color)
    
    # Draw main text
    if rarity == "SAR" and is_title:
        # Gradient text untuk SAR titles
        gradient_start = (255, 215, 0)  # Gold
        gradient_end = (255, 20, 147)   # Deep Pink
        gradient_img = create_gradient_text(draw, text, (text_x, text_y), font, gradient_start, gradient_end, text_w)
        # Note: Untuk implementasi penuh gradient, perlu composite ke image utama
        draw.text((text_x, text_y), text, font=font, fill=colors["text"])
    else:
        draw.text((text_x, text_y), text, font=font, fill=colors["text"])

# Backward compatibility
def draw_fit_text(draw, text, box, font_path, max_font_size):
    """Draw text yang auto-fit ke dalam box (legacy function)"""
    draw_enhanced_text(draw, text, box, font_path, max_font_size, "Common", False)

# Generate card dengan template system
def generate_card_template(idol_photo, rarity, member_name="", group_name="", description=""):
    """
    Generate card menggunakan template system dengan enhanced description
    
    Args:
        idol_photo: PIL Image object atau path ke foto
        rarity: String rarity ("Common", "Rare", "DR", "SR", "SAR")
        member_name: Nama member
        group_name: Nama grup (opsional, akan digabung dengan member_name jika ada)
        description: Deskripsi kartu (opsional, jika kosong akan generate otomatis)
    
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
    
    # Load template image - fallback to old design system if template not found
    template_folder = "assets/templates"
    template_path = os.path.join(template_folder, f"{selected_template}.png")
    
    if not os.path.exists(template_path):
        # Fallback to old design system
        print(f"Template file not found: {template_path}, using fallback design system")
        from features.gacha_system.design_kartu_old import generate_card_template as old_generate_card
        return old_generate_card(idol_photo, rarity, member_name, group_name, description)
    
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
    font_path = "assets/fonts/Gill Sans Bold Italic.otf"
    
    # Draw member name dengan enhanced styling
    if member_name:
        # Prepare text content
        name_text = f"{member_name} • {group_name}" if group_name else member_name
        draw_enhanced_text(draw, name_text, boxes["name"], font_path, 20, rarity, is_title=True)
    
    # Use provided description or generate enhanced description dengan emoji
    if not description:
        description = generate_enhanced_description(member_name, group_name, rarity)
    draw_enhanced_text(draw, description, boxes["desc"], font_path, 14, rarity, is_title=False)
    
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
