from PIL import Image, ImageDraw, ImageFont
import os
import json
import random

# Enhanced description system
def generate_enhanced_description(member_name, group_name, rarity):
    """Generate simple bullet-point description untuk kartu gacha"""
    
    # Simple traits berdasarkan rarity
    rarity_traits = {
        "Common": ["ROOKIE IDOL", "FRESH TALENT", "NEW STAR"],
        "Rare": ["RISING STAR", "POPULAR IDOL", "TALENTED MEMBER"],
        "DR": ["MAIN VOCALIST", "LEAD DANCER", "VISUAL QUEEN"],
        "SR": ["ACE MEMBER", "ALL-ROUNDER", "CENTER IDOL"],
        "SAR": ["LEGEND IDOL", "ICON GODDESS", "ULTIMATE STAR"]
    }
    
    # Power/Stats untuk gaming feel
    power_stats = {
        "Common": ["CHARM 45", "TALENT 50", "POPULARITY 40"],
        "Rare": ["CHARM 65", "TALENT 70", "POPULARITY 60"],
        "DR": ["CHARM 80", "TALENT 85", "POPULARITY 75"],
        "SR": ["CHARM 90", "TALENT 95", "POPULARITY 85"],
        "SAR": ["CHARM 99", "TALENT 99", "POPULARITY 99"]
    }
    
    # Generate 2 simple points
    description_points = []
    
    # Point 1: Role/Title
    import random
    role = random.choice(rarity_traits.get(rarity, ["MEMBER"]))
    description_points.append(f"- {role}")
    
    # Point 2: Power stat
    stat = random.choice(power_stats.get(rarity, ["POWER 50"]))
    description_points.append(f"- {stat}")
    
    return "\n".join(description_points)

# Load card template data
def load_card_data():
    """Load card template data from cards_boxes.json"""
    with open("assets/templates/cards_boxes.json", "r") as f:
        return json.load(f)

# Fit foto ke dalam box dengan crop proporsional
def detect_and_crop_padding(image, padding_threshold=10):
    """Detect dan crop padding/whitespace dari foto"""
    import numpy as np
    
    # Convert ke array untuk analisis
    img_array = np.array(image)
    
    # Detect edges berdasarkan variance
    # Hitung variance untuk setiap row dan column
    if len(img_array.shape) == 3:  # RGB/RGBA
        gray = np.mean(img_array[:, :, :3], axis=2)
    else:  # Grayscale
        gray = img_array
    
    # Hitung variance untuk detect content area
    row_variance = np.var(gray, axis=1)
    col_variance = np.var(gray, axis=0)
    
    # Find content boundaries
    content_rows = np.where(row_variance > padding_threshold)[0]
    content_cols = np.where(col_variance > padding_threshold)[0]
    
    if len(content_rows) == 0 or len(content_cols) == 0:
        # Jika tidak ada content terdeteksi, return original
        return image
    
    # Crop ke content area
    top = max(0, content_rows[0] - 5)  # Small margin
    bottom = min(image.height, content_rows[-1] + 5)
    left = max(0, content_cols[0] - 5)
    right = min(image.width, content_cols[-1] + 5)
    
    return image.crop((left, top, right, bottom))

def fit_photo(foto_path, target_w, target_h):
    """Enhanced resize dan crop foto untuk fit ke dalam box dengan padding detection"""
    if not os.path.exists(foto_path):
        # Create placeholder jika foto tidak ada
        img = Image.new("RGB", (target_w, target_h), (200, 200, 200))
        draw = ImageDraw.Draw(img)
        draw.text((target_w//2-30, target_h//2-10), "NO PHOTO", fill=(100, 100, 100))
        return img
    
    foto = Image.open(foto_path).convert("RGBA")
    
    # Step 1: Detect dan crop padding/whitespace
    try:
        foto = detect_and_crop_padding(foto)
    except Exception as e:
        print(f"Padding detection failed: {e}, using original image")
    
    # Step 2: Handle landscape/portrait orientation intelligently
    foto_ratio = foto.width / foto.height
    target_ratio = target_w / target_h
    
    # Enhanced scaling untuk better fit
    if foto_ratio > target_ratio:
        # Foto lebih lebar (landscape), prioritas fit width dengan smart crop
        new_w = target_w
        new_h = int(new_w / foto_ratio)
        
        # Jika hasil terlalu kecil, fit by height instead
        if new_h < target_h * 0.8:  # Threshold 80%
            new_h = target_h
            new_w = int(new_h * foto_ratio)
    else:
        # Foto lebih tinggi (portrait), prioritas fit height
        new_h = target_h
        new_w = int(new_h * foto_ratio)
        
        # Jika hasil terlalu kecil, fit by width instead
        if new_w < target_w * 0.8:  # Threshold 80%
            new_w = target_w
            new_h = int(new_w / foto_ratio)
    
    # Resize foto dengan high quality
    foto_resized = foto.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Smart crop ke center dengan bias ke atas untuk portrait
    left = max(0, (new_w - target_w) // 2)
    
    # Untuk portrait, bias crop ke atas (wajah biasanya di atas)
    if foto_ratio < 1:  # Portrait
        top = max(0, int((new_h - target_h) * 0.3))  # 30% dari atas
    else:  # Landscape
        top = max(0, (new_h - target_h) // 2)  # Center
    
    # Ensure crop bounds are valid
    left = min(left, new_w - target_w)
    top = min(top, new_h - target_h)
    
    foto_cropped = foto_resized.crop((left, top, left + target_w, top + target_h))
    
    return foto_cropped

def fit_photo_from_image(pil_image, target_w, target_h):
    """Enhanced resize dan crop PIL Image untuk fit ke dalam box dengan padding detection"""
    foto = pil_image.convert("RGBA")
    
    # Step 1: Detect dan crop padding/whitespace
    try:
        foto = detect_and_crop_padding(foto)
    except Exception as e:
        print(f"Padding detection failed: {e}, using original image")
    
    # Step 2: Handle landscape/portrait orientation intelligently
    foto_ratio = foto.width / foto.height
    target_ratio = target_w / target_h
    
    # Enhanced scaling untuk better fit
    if foto_ratio > target_ratio:
        # Foto lebih lebar (landscape), prioritas fit width dengan smart crop
        new_w = target_w
        new_h = int(new_w / foto_ratio)
        
        # Jika hasil terlalu kecil, fit by height instead
        if new_h < target_h * 0.8:  # Threshold 80%
            new_h = target_h
            new_w = int(new_h * foto_ratio)
    else:
        # Foto lebih tinggi (portrait), prioritas fit height
        new_h = target_h
        new_w = int(new_h * foto_ratio)
        
        # Jika hasil terlalu kecil, fit by width instead
        if new_w < target_w * 0.8:  # Threshold 80%
            new_w = target_w
            new_h = int(new_w / foto_ratio)
    
    # Resize foto dengan high quality
    foto_resized = foto.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Smart crop ke center dengan bias ke atas untuk portrait
    left = max(0, (new_w - target_w) // 2)
    
    # Untuk portrait, bias crop ke atas (wajah biasanya di atas)
    if foto_ratio < 1:  # Portrait
        top = max(0, int((new_h - target_h) * 0.3))  # 30% dari atas
    else:  # Landscape
        top = max(0, (new_h - target_h) // 2)  # Center
    
    # Ensure crop bounds are valid
    left = min(left, new_w - target_w)
    top = min(top, new_h - target_h)
    
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

def get_emoji_font(size):
    """Get emoji-compatible font dengan fallback untuk GitHub/Railway deployment"""
    emoji_fonts = [
        # GitHub/Railway deployment paths - prioritas utama
        "assets/fonts/NotoColorEmoji-Regular.ttf",
        "assets/fonts/Noto_Color_Emoji/NotoColorEmoji-Regular.ttf",
        # System fallbacks dengan priority order
        "C:/Windows/Fonts/seguiemj.ttf",  # Windows Segoe UI Emoji
        "C:/Windows/Fonts/NotoColorEmoji.ttf",  # Windows Noto Color Emoji
        "C:/Windows/Fonts/segoeui.ttf",  # Windows Segoe UI (basic emoji)
        "/System/Library/Fonts/Apple Color Emoji.ttc",  # macOS
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",  # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux fallback
    ]
    
    for font_path in emoji_fonts:
        try:
            if os.path.exists(font_path):
                print(f"Loading emoji font: {font_path}")
                return ImageFont.truetype(font_path, size)
        except Exception as e:
            print(f"Failed to load emoji font {font_path}: {e}")
            continue
    
    print("Warning: No emoji font found, using default")
    return ImageFont.load_default()

def get_main_font(size, font_preference="montserrat"):
    """Get main text font dengan preference dan fallback"""
    if font_preference.lower() == "montserrat":
        main_fonts = [
            "assets/fonts/Montserrat-Bold.ttf",
            "assets/fonts/Montserrat-SemiBold.ttf", 
            "assets/fonts/Montserrat-Medium.ttf",
            "assets/fonts/Montserrat-Regular.ttf"
        ]
    elif font_preference.lower() == "noto":
        main_fonts = [
            "assets/fonts/NotoSans-Bold.ttf",
            "assets/fonts/NotoSans-SemiBold.ttf",
            "assets/fonts/NotoSans-Medium.ttf", 
            "assets/fonts/NotoSans-Regular.ttf"
        ]
    else:
        # Fallback ke Gill Sans atau default
        main_fonts = [
            "assets/fonts/Gill Sans Bold Italic.otf",
            "assets/fonts/Montserrat-Bold.ttf",
            "assets/fonts/NotoSans-Bold.ttf"
        ]
    
    for font_path in main_fonts:
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except:
            continue
    
    return ImageFont.load_default()

def split_text_and_emoji(text):
    """Split text menjadi bagian text biasa dan emoji"""
    import re
    
    # Enhanced regex untuk detect emoji dengan coverage lebih luas
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
        "\U00002600-\U000026FF"  # miscellaneous symbols
        "\U0000FE00-\U0000FE0F"  # variation selectors
        "\U0001F004\U0001F0CF"   # mahjong, playing cards
        "]+", flags=re.UNICODE
    )
    
    parts = []
    last_end = 0
    
    for match in emoji_pattern.finditer(text):
        # Add text before emoji
        if match.start() > last_end:
            parts.append({
                'type': 'text',
                'content': text[last_end:match.start()]
            })
        
        # Add emoji
        parts.append({
            'type': 'emoji',
            'content': match.group()
        })
        
        last_end = match.end()
    
    # Add remaining text
    if last_end < len(text):
        parts.append({
            'type': 'text',
            'content': text[last_end:]
        })
    
    return parts

def draw_enhanced_text(draw, text, box, max_font_size, rarity, is_title=False, font_preference="montserrat"):
    """Draw text dengan enhanced styling dan emoji support"""
    x, y, w, h = box
    
    # Load main font dengan preference system
    main_font = get_main_font(max_font_size, font_preference)
    
    # Load emoji font
    emoji_font = get_emoji_font(max_font_size)
    
    font_size = max_font_size
    
    # Split text into parts (text dan emoji)
    text_parts = split_text_and_emoji(text)
    
    # Auto-fit font size berdasarkan total width
    while font_size > 5:
        try:
            main_font = get_main_font(font_size, font_preference)
            emoji_font = get_emoji_font(font_size)
        except:
            main_font = ImageFont.load_default()
            emoji_font = ImageFont.load_default()
        
        # Calculate total width
        total_width = 0
        max_height = 0
        
        for part in text_parts:
            font_to_use = emoji_font if part['type'] == 'emoji' else main_font
            bbox = draw.textbbox((0, 0), part['content'], font=font_to_use)
            part_w = bbox[2] - bbox[0]
            part_h = bbox[3] - bbox[1]
            total_width += part_w
            max_height = max(max_height, part_h)
        
        if total_width <= w:
            break
        
        font_size -= 1
    
    # Position text - Left align untuk semua text
    text_x = x + 3  # Left alignment dengan padding 3px untuk semua text
    text_y = y + (h - max_height) // 2
    
    # Get rarity colors
    colors = get_rarity_colors(rarity)
    
    # Draw each part dengan styling
    current_x = text_x
    
    for part in text_parts:
        font_to_use = emoji_font if part['type'] == 'emoji' else main_font
        part_content = part['content']
        
        # Skip empty parts
        if not part_content.strip():
            continue
        
        # Get part dimensions
        bbox = draw.textbbox((0, 0), part_content, font=font_to_use)
        part_w = bbox[2] - bbox[0]
        part_h = bbox[3] - bbox[1]
        
        # Adjust Y position for this part
        part_y = text_y + (max_height - part_h) // 2
        
        # Apply styling hanya untuk text, tidak untuk emoji
        if part['type'] == 'text':
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
                                draw.text((current_x + dx, part_y + dy), part_content, font=font_to_use, fill=glow_color)
            
            # Draw outline (multi-layer untuk rarity tinggi)
            outline_layers = 2 if rarity in ["SR", "SAR"] else 1
            for layer in range(outline_layers, 0, -1):
                for dx in range(-layer, layer + 1):
                    for dy in range(-layer, layer + 1):
                        if dx != 0 or dy != 0:
                            outline_alpha = 255 // layer
                            outline_color = (*colors["outline"][:3], outline_alpha)
                            draw.text((current_x + dx, part_y + dy), part_content, font=font_to_use, fill=outline_color)
            
            # Draw main text
            draw.text((current_x, part_y), part_content, font=font_to_use, fill=colors["text"])
        else:
            # Draw emoji dengan enhanced error handling
            try:
                # Debug: print emoji yang akan di-render
                print(f"Rendering emoji: '{part_content}' with font: {font_to_use}")
                
                # Coba render emoji dengan font emoji
                draw.text((current_x, part_y), part_content, font=font_to_use, fill=(255, 255, 255, 255))
                print(f"Emoji rendered successfully: {part_content}")
            except Exception as e:
                # Enhanced fallback dengan multiple attempts
                print(f"Emoji rendering failed: {e}, trying fallback methods")
                
                # Try with main font first
                try:
                    draw.text((current_x, part_y), part_content, font=main_font, fill=colors["text"])
                    print(f"Emoji rendered with main font: {part_content}")
                except Exception as e2:
                    # Ultimate fallback - render as text placeholder
                    print(f"All emoji rendering failed: {e2}, using placeholder")
                    placeholder = "[emoji]"
                    draw.text((current_x, part_y), placeholder, font=main_font, fill=colors["text"])
        
        # Move to next position
        current_x += part_w

# Backward compatibility
def draw_fit_text(draw, text, box, font_path, max_font_size):
    """Draw text yang auto-fit ke dalam box (legacy function)"""
    draw_enhanced_text(draw, text, box, max_font_size, "Common", False)

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
    template_path = f"assets/templates/{selected_template}.png"
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")
    
    # Load template dan convert ke RGB untuk mobile compatibility
    card = Image.open(template_path).convert("RGB")
    
    # Get boxes info
    boxes = template_info["boxes"]
    
    # Process foto input
    if isinstance(idol_photo, str):
        # Jika input adalah path
        foto_img = fit_photo(idol_photo, boxes["photo"][2], boxes["photo"][3])
    else:
        # Jika input adalah PIL Image
        foto_img = fit_photo_from_image(idol_photo, boxes["photo"][2], boxes["photo"][3])
    
    # Paste foto ke card (RGB mode)
    if foto_img.mode == 'RGBA':
        # Convert foto ke RGB dengan white background untuk mobile compatibility
        rgb_foto = Image.new('RGB', foto_img.size, (255, 255, 255))
        rgb_foto.paste(foto_img, mask=foto_img.split()[-1])
        foto_img = rgb_foto
    
    card.paste(foto_img, (boxes["photo"][0], boxes["photo"][1]))
    
    # Add text
    draw = ImageDraw.Draw(card)
    
    # Draw member name dengan enhanced styling menggunakan Montserrat
    if member_name:
        # Prepare text content
        name_text = f"{member_name} • {group_name}" if group_name else member_name
        draw_enhanced_text(draw, name_text, boxes["name"], 20, rarity, is_title=True, font_preference="montserrat")
    
    # Use provided description or generate enhanced description dengan emoji
    if not description:
        description = generate_enhanced_description(member_name, group_name, rarity)
    
    # Render description dengan emoji support menggunakan Noto Sans
    draw_enhanced_text(draw, description, boxes["desc"], 14, rarity, is_title=False, font_preference="noto")
    
    return card

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
