#!/usr/bin/env python3
"""
Card Description System
Modul untuk generate berbagai style deskripsi kartu K-pop
"""

import random

class PokemonStyleDescriptions:
    """Pokemon TCG style description generator"""
    
    def __init__(self):
        # Attack names berdasarkan K-pop themes
        self.attack_names = {
            "Common": [
                "Cute Charm", "Sweet Voice", "Dance Step", "Smile Attack",
                "Fan Service", "Aegyo Beam", "Stage Presence"
            ],
            "Rare": [
                "Visual Strike", "Vocal Power", "Dance Break", "Charisma Burst",
                "Center Position", "Photo Shoot", "Live Performance"
            ],
            "DR": [
                "Main Vocal", "Lead Dance", "Visual Impact", "Rap Battle",
                "Stage Command", "Fan Magnet", "Spotlight Steal"
            ],
            "SR": [
                "Ultimate Visual", "Vocal Mastery", "Dance Domination", "Rap Genius",
                "Stage Takeover", "Heart Breaker", "Global Appeal"
            ],
            "SAR": [
                "Legendary Visual", "Divine Vocals", "Perfect Performance", "Iconic Presence",
                "World Conquest", "Ultimate Bias", "Hall of Fame"
            ]
        }
        
        # Emojis untuk setiap attack type (ASCII safe)
        self.attack_emojis = {
            "Visual": "*", "Vocal": "♪", "Dance": "~", "Rap": "@",
            "Charm": "<3", "Stage": "#", "Global": "O", "Perfect": "^",
            "Ultimate": "*", "Legendary": "!", "Divine": "+", "Iconic": "$"
        }
        
        # Damage ranges berdasarkan rarity
        self.damage_ranges = {
            "Common": (30, 50),
            "Rare": (40, 65),
            "DR": (55, 80),
            "SR": (70, 95),
            "SAR": (85, 120)
        }
        
        # Short descriptions berdasarkan rarity
        self.short_descriptions = {
            "Common": [
                "Trainee dari {group}",
                "Rookie member {group}",
                "Aspiring idol dari {group}",
                "New face of {group}"
            ],
            "Rare": [
                "Rising star dari {group}",
                "Popular member {group}",
                "Talented idol dari {group}",
                "Fan favorite {group}"
            ],
            "DR": [
                "Main member dari {group}",
                "Core performer {group}",
                "Essential part of {group}",
                "Key player {group}"
            ],
            "SR": [
                "Superstar dari {group}",
                "Ace member {group}",
                "Top tier idol dari {group}",
                "Elite performer {group}"
            ],
            "SAR": [
                "Legend dari {group}",
                "Icon of {group}",
                "Ultimate bias dari {group}",
                "Hall of Fame {group}"
            ]
        }
        
        # HP ranges untuk stats system
        self.hp_ranges = {
            "Common": (60, 80),
            "Rare": (80, 100),
            "DR": (100, 120),
            "SR": (120, 150),
            "SAR": (150, 200)
        }
    
    def generate_description(self, member_name, group_name, rarity):
        """
        Generate Pokemon TCG style description
        
        Args:
            member_name: Nama member
            group_name: Nama grup
            rarity: Rarity level
            
        Returns:
            String description format: "Description\nEmoji Attack - DMG"
        """
        
        # Generate components
        description = random.choice(self.short_descriptions.get(rarity, self.short_descriptions["Common"]))
        description = description.format(group=group_name)
        
        attack_name = random.choice(self.attack_names.get(rarity, self.attack_names["Common"]))
        
        # Get emoji based on attack name
        emoji = "*"  # default
        for key, emoji_val in self.attack_emojis.items():
            if key.lower() in attack_name.lower():
                emoji = emoji_val
                break
        
        # Generate damage
        min_dmg, max_dmg = self.damage_ranges.get(rarity, self.damage_ranges["Common"])
        damage = random.randint(min_dmg, max_dmg)
        
        # Format Pokemon style description
        pokemon_desc = f"{description}\n{emoji} {attack_name} - {damage} DMG"
        
        return pokemon_desc
    
    def generate_with_stats(self, member_name, group_name, rarity):
        """
        Generate Pokemon style dengan HP stats
        
        Returns:
            String description dengan HP stats
        """
        
        # Generate base description
        base_desc = self.generate_description(member_name, group_name, rarity)
        
        # Add HP
        min_hp, max_hp = self.hp_ranges.get(rarity, self.hp_ranges["Common"])
        hp = random.randint(min_hp, max_hp)
        
        # Add stats line
        full_desc = f"{base_desc}\nHP: {hp}"
        
        return full_desc

class EnhancedDescriptions:
    """Enhanced 3-point bullet description system"""
    
    def __init__(self):
        # Member description database
        self.member_descriptions = {
            "Karina": {
                "roles": ["Leader", "Main Rapper", "Visual", "Face of the Group"],
                "traits": ["Charismatic", "Mysterious", "Fierce", "Sweet"],
                "achievements": ["Viral Fancam", "Chart Topper", "Acting Debut", "Global Icon"]
            },
            "Winter": {
                "roles": ["Main Vocalist", "Lead Dancer", "Visual", "Center"],
                "traits": ["Bright", "Confident", "Gentle", "Playful"],
                "achievements": ["Rising Star", "Award Winner", "Solo Debut", "International Recognition"]
            }
            # Add more members as needed
        }
        
        # Default roles, traits, achievements by rarity
        self.default_data = {
            "Common": {
                "roles": ["Sub Vocalist", "Sub Dancer", "Trainee", "Rookie"],
                "traits": ["Cheerful", "Energetic", "Cute", "Friendly"],
                "achievements": ["Debut Stage", "First Win", "Fan Meeting", "Music Show"]
            },
            "Rare": {
                "roles": ["Lead Vocalist", "Lead Dancer", "Visual", "Rapper"],
                "traits": ["Talented", "Charming", "Skilled", "Popular"],
                "achievements": ["Chart Success", "Award Nominee", "Variety Show", "Collaboration"]
            },
            "DR": {
                "roles": ["Main Vocalist", "Main Dancer", "Lead Rapper", "Center"],
                "traits": ["Exceptional", "Charismatic", "Versatile", "Professional"],
                "achievements": ["Top Charts", "Music Awards", "Solo Activities", "International Fame"]
            },
            "SR": {
                "roles": ["Ace", "All-rounder", "Face of Group", "Main Position"],
                "traits": ["Outstanding", "Captivating", "Multi-talented", "Inspiring"],
                "achievements": ["Major Awards", "Global Recognition", "Brand Ambassador", "Acting Career"]
            },
            "SAR": {
                "roles": ["Legend", "Icon", "Ultimate Bias", "Hall of Fame"],
                "traits": ["Legendary", "Iconic", "Phenomenal", "Transcendent"],
                "achievements": ["Industry Legend", "Cultural Impact", "Global Superstar", "Timeless Icon"]
            }
        }
    
    def generate_description(self, member_name, group_name, rarity):
        """
        Generate enhanced 3-point bullet description
        
        Returns:
            String dengan format:
            • Role & Position
            • Personality trait with detail
            • Achievement & status
        """
        
        # Get member-specific data or use defaults
        if member_name in self.member_descriptions:
            data = self.member_descriptions[member_name]
        else:
            data = self.default_data.get(rarity, self.default_data["Common"])
        
        # Select components
        role = random.choice(data["roles"])
        trait = random.choice(data["traits"])
        achievement = random.choice(data["achievements"])
        
        # Format based on rarity (different detail levels)
        if rarity == "SAR":
            role_line = f"• {role} & {random.choice(data['roles'])}"
            trait_line = f"• {trait} personality with {random.choice(['stage presence', 'fan interaction', 'leadership qualities'])}"
            achievement_line = f"• {achievement} & global icon"
        elif rarity == "SR":
            role_line = f"• {role} & {random.choice(['Visual', 'Center', 'Ace'])}"
            trait_line = f"• {trait} personality with {random.choice(['powerful vocals', 'exceptional dance', 'stage charisma'])}"
            achievement_line = f"• {achievement} with {random.choice(['award winner', 'chart success', 'international recognition'])}"
        elif rarity == "DR":
            role_line = f"• {role} & {random.choice(['Sub Vocalist', 'Sub Dancer', 'Lead Position'])}"
            trait_line = f"• Known for {trait.lower()} charm"
            achievement_line = f"• Key member of {group_name}"
        else:  # Rare, Common
            role_line = f"• {role} & {random.choice(['Sub Dancer', 'Sub Vocalist', 'Trainee'])}"
            trait_line = f"• Known for {trait.lower()} charm"
            achievement_line = f"• Beloved {group_name} member"
        
        return f"{role_line}\n{trait_line}\n{achievement_line}"

# Factory function untuk mudah digunakan
def generate_card_description(member_name, group_name, rarity, style="pokemon"):
    """
    Factory function untuk generate description
    
    Args:
        member_name: Nama member
        group_name: Nama grup  
        rarity: Rarity level
        style: "pokemon" atau "enhanced"
        
    Returns:
        String description
    """
    
    if style == "pokemon":
        generator = PokemonStyleDescriptions()
        return generator.generate_description(member_name, group_name, rarity)
    elif style == "pokemon_stats":
        generator = PokemonStyleDescriptions()
        return generator.generate_with_stats(member_name, group_name, rarity)
    elif style == "enhanced":
        generator = EnhancedDescriptions()
        return generator.generate_description(member_name, group_name, rarity)
    else:
        # Default to pokemon style
        generator = PokemonStyleDescriptions()
        return generator.generate_description(member_name, group_name, rarity)
