#!/usr/bin/env python3
"""
Mental Omega Arsenal - Comprehensive Unit Database Application (Layout 2)
A single-file application for browsing Mental Omega mod units, structures, and support powers.
Features always-on-top overlay, grid-based navigation, search, and unit comparison.
"""

import tkinter as tk
from tkinter import ttk, font, messagebox
import json
import base64
import os
import sys
from io import BytesIO
from PIL import Image, ImageTk
import re
from typing import Dict, List, Optional, Tuple, Any
import pickle
from dataclasses import dataclass
from pathlib import Path

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

VERSION = "1.0.0"
APP_TITLE = "Mental Omega Arsenal"
DEFAULT_WINDOW_SIZE = (1000, 700)
MIN_WINDOW_SIZE = (800, 600)
COMPARISON_WINDOW_WIDTH = 1400

# Faction hierarchy structure
FACTION_HIERARCHY = {
    "Allied Nations": {
        "icon": "Allicon",
        "subfactions": {
            "United States": {"icon": "USAicon"},
            "European Alliance": {"icon": "EAicon"},
            "Pacific Front": {"icon": "PFicon"}
        }
    },
    "Soviet Union": {
        "icon": "Sovicon",
        "subfactions": {
            "Russia": {"icon": "Russiaicon"},
            "Latin Confederation": {"icon": "Confederationicon"},
            "China": {"icon": "Chinaicon"}
        }
    },
    "Epsilon Army": {
        "icon": "Yuricon",
        "subfactions": {
            "PsiCorps": {"icon": "PCicon"},
            "Scorpion Cell": {"icon": "SCicon"},
            "Epsilon Headquarters": {"icon": "HQicon"}
        }
    },
    "Foehn Revolt": {
        "icon": "Foeicon",
        "subfactions": {
            "Haihead": {"icon": "HHicon"},
            "Last Bastion": {"icon": "LBicon"},
            "Wings of Coronia": {"icon": "WCicon"}
        }
    }
}

# Unit categories
UNIT_CATEGORIES = ["Structures", "Defenses", "Infantry", "Vehicles", "Aircraft", "Support powers"]

# Default theme colors
DEFAULT_THEME = {
    "bg": "#1e1e1e",
    "fg": "#ffffff",
    "select_bg": "#404040",
    "select_fg": "#ffffff",
    "button_bg": "#2d2d2d",
    "button_fg": "#ffffff",
    "button_active_bg": "#505050",
    "title_bg": "#2d2d30",
    "title_fg": "#ffffff",
    "border": "#3c3c3c",
    "accent": "#007acc",
    "hover": "#505050"
}

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class UnitData:
    """Data class for unit information"""
    name: str
    faction: str
    subfaction: str
    category: str
    infobox_data: Dict[str, Any]
    icon_filename: str
    icon_url: str
    article_tables: Optional[List[Dict]] = None

@dataclass
class SearchItem:
    """Data class for search results"""
    name: str
    faction: str
    subfaction: str
    category: str
    unit_data: UnitData

# =============================================================================
# DATA MANAGER
# =============================================================================

class DataManager:
    """Manages all unit data and search functionality"""
    
    def __init__(self):
        self.units: Dict[str, UnitData] = {}
        self.search_index: List[SearchItem] = []
        self.faction_units: Dict[str, Dict[str, Dict[str, List[UnitData]]]] = {}
        self._load_data()
    
    def _load_data(self):
        """Load and process all unit data from the sterilized data box"""
        data_path = Path("sterilized data box")
        
        if not data_path.exists():
            messagebox.showerror("Data Error", f"Data directory not found: {data_path}")
            return
        
        # Initialize faction structure
        for faction in FACTION_HIERARCHY:
            self.faction_units[faction] = {}
            for subfaction in FACTION_HIERARCHY[faction]["subfactions"]:
                self.faction_units[faction][subfaction] = {}
                for category in UNIT_CATEGORIES:
                    self.faction_units[faction][subfaction][category] = []
        
        # Load units from file system
        self._load_units_from_directory(data_path)
        
        # Build search index
        self._build_search_index()
    
    def _load_units_from_directory(self, base_path: Path):
        """Load units from the directory structure"""
        for faction_name, faction_data in FACTION_HIERARCHY.items():
            # Try different faction directory name variants
            faction_variants = [
                faction_name,  # Try with spaces first
                faction_name.replace(" ", "_"),
                faction_name.replace(" ", "")
            ]
            
            faction_dir = None
            for variant in faction_variants:
                potential_dir = base_path / variant
                if potential_dir.exists():
                    faction_dir = potential_dir
                    break
            
            if not faction_dir:
                print(f"Faction directory not found: {faction_name}")
                continue
                
            print(f"Loading faction: {faction_name} from {faction_dir}")
            
            # Load base faction units using a temporary subfaction name
            temp_subfaction = "_base_faction_"
            
            # Initialize temporary subfaction structure
            self.faction_units[faction_name][temp_subfaction] = {}
            for category in UNIT_CATEGORIES:
                self.faction_units[faction_name][temp_subfaction][category] = []
            
            self._load_category_units(faction_dir, faction_name, temp_subfaction)
            
            # Store base faction units to be inherited by all subfactions
            base_faction_units = {}
            for category in UNIT_CATEGORIES:
                base_faction_units[category] = self.faction_units[faction_name][temp_subfaction][category].copy()
            
            # Remove the temporary subfaction after copying
            del self.faction_units[faction_name][temp_subfaction]
            
            # Load subfaction-specific units
            for subfaction_name in faction_data["subfactions"]:
                # Try multiple possible subfaction directory names
                subfaction_variants = [
                    subfaction_name,  # Try with spaces first
                    subfaction_name.replace(" ", "_"),
                    subfaction_name.replace(" ", ""),
                    subfaction_name.split()[0] if " " in subfaction_name else subfaction_name
                ]
                
                subfaction_dir = None
                for variant in subfaction_variants:
                    potential_dir = faction_dir / "subfaction" / variant
                    if potential_dir.exists():
                        subfaction_dir = potential_dir
                        break
                
                if subfaction_dir:
                    print(f"Loading subfaction: {subfaction_name} from {subfaction_dir}")
                    self._load_category_units(subfaction_dir, faction_name, subfaction_name)
                    
                    # Add base faction units to subfaction (inheritance)
                    for category, units in base_faction_units.items():
                        self.faction_units[faction_name][subfaction_name][category].extend(units)
                    
                    # Remove duplicates and sort
                    for category in UNIT_CATEGORIES:
                        seen = set()
                        unique_units = []
                        for unit in self.faction_units[faction_name][subfaction_name][category]:
                            if unit.name not in seen:
                                seen.add(unit.name)
                                unique_units.append(unit)
                        self.faction_units[faction_name][subfaction_name][category] = sorted(unique_units, key=lambda u: u.name)
                        
                else:
                    print(f"Subfaction directory not found for {subfaction_name}")
                    
                    # Even if subfaction directory doesn't exist, inherit base faction units
                    for category, units in base_faction_units.items():
                        self.faction_units[faction_name][subfaction_name][category].extend(units)
    
    def _load_category_units(self, directory: Path, faction: str, subfaction: str):
        """Load units from a specific directory"""
        for category in UNIT_CATEGORIES:
            category_dir = directory / category.replace(" ", "_")
            if not category_dir.exists():
                continue
                
            units_loaded = 0
            for json_file in category_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    unit = UnitData(
                        name=data.get("unit_name", json_file.stem),
                        faction=faction,
                        subfaction=subfaction,
                        category=category,
                        infobox_data=data.get("infobox_data", {}),
                        icon_filename=data.get("icon_filename", ""),
                        icon_url=data.get("icon_url", ""),
                        article_tables=data.get("article_tables", [])
                    )
                    
                    # Store unit
                    unit_key = f"{faction}_{subfaction}_{category}_{unit.name}"
                    self.units[unit_key] = unit
                    
                    # Add to faction structure with safety checks
                    if faction in self.faction_units:
                        if subfaction in self.faction_units[faction]:
                            if category in self.faction_units[faction][subfaction]:
                                self.faction_units[faction][subfaction][category].append(unit)
                                units_loaded += 1
                            else:
                                print(f"Category {category} not found for {faction}/{subfaction}")
                        else:
                            print(f"Subfaction {subfaction} not found for {faction}")
                    else:
                        print(f"Faction {faction} not found in faction_units")
                    
                except json.JSONDecodeError as e:
                    print(f"JSON decode error in {json_file}: {e}")
                except KeyError as e:
                    print(f"KeyError in {json_file}: {e}")
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")
                    import traceback
                    traceback.print_exc()
            
            if units_loaded > 0:
                print(f"Loaded {units_loaded} {category} for {subfaction}")
    
    def _build_search_index(self):
        """Build search index for fast autocomplete"""
        self.search_index = []
        for unit in self.units.values():
            search_item = SearchItem(
                name=unit.name,
                faction=unit.faction,
                subfaction=unit.subfaction,
                category=unit.category,
                unit_data=unit
            )
            self.search_index.append(search_item)
        
        # Sort by name for alphabetical display
        self.search_index.sort(key=lambda x: x.name.lower())
    
    def search_units(self, query: str) -> List[SearchItem]:
        """Search units by name, faction, or category"""
        if not query:
            return []
        
        query = query.lower()
        results = []
        
        for item in self.search_index:
            if (query in item.name.lower() or 
                query in item.faction.lower() or 
                query in item.subfaction.lower() or
                query in item.category.lower()):
                results.append(item)
        
        return results
    
    def get_units_for_path(self, faction: str, subfaction: str = None, category: str = None) -> List[UnitData]:
        """Get units for a specific navigation path"""
        if faction not in self.faction_units:
            return []
        
        if subfaction is None:
            # Return all units for faction
            all_units = []
            for sub in self.faction_units[faction].values():
                for cat in sub.values():
                    all_units.extend(cat)
            return all_units
        
        if subfaction not in self.faction_units[faction]:
            return []
        
        if category is None:
            # Return all units for subfaction
            all_units = []
            for cat in self.faction_units[faction][subfaction].values():
                all_units.extend(cat)
            return all_units
        
        if category not in self.faction_units[faction][subfaction]:
            return []
        
        return self.faction_units[faction][subfaction][category]

# =============================================================================
# THEME MANAGER
# =============================================================================

class ThemeManager:
    """Manages application themes and appearance"""
    
    def __init__(self):
        self.current_theme = DEFAULT_THEME.copy()
        self.custom_settings = {
            "opacity": 0.9,
            "font_family": "Segoe UI",
            "font_size": 10,
            "font_weight": "normal",
            "icon_scale": 1.0,
            "ui_scale": 1.0,  # Global UI scaling factor
            "bold_text": False  # Bold text toggle
        }
        self.load_settings()
    
    def load_settings(self):
        """Load settings from file"""
        try:
            settings_file = Path("mental_omega_settings.json")
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    self.current_theme.update(settings.get("theme", {}))
                    self.custom_settings.update(settings.get("custom", {}))
        except Exception:
            pass  # Use defaults if loading fails
    
    def save_settings(self):
        """Save settings to file"""
        try:
            settings = {
                "theme": self.current_theme,
                "custom": self.custom_settings
            }
            with open("mental_omega_settings.json", 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception:
            pass
    
    def get_font(self, size_delta: int = 0, weight: str = None) -> font.Font:
        """Get configured font with UI scaling applied"""
        family = self.custom_settings["font_family"]
        base_size = self.custom_settings["font_size"] + size_delta
        
        # Apply UI scaling to font size
        ui_scale = self.custom_settings.get("ui_scale", 1.0)
        size = int(base_size * ui_scale)
        
        if weight is None:
            weight = "bold" if self.custom_settings.get("bold_text", False) else self.custom_settings["font_weight"]
        
        return font.Font(family=family, size=size, weight=weight)
    
    def get_scaled_size(self, base_size: int) -> int:
        """Get a size value scaled by the UI scale factor"""
        ui_scale = self.custom_settings.get("ui_scale", 1.0)
        return int(base_size * ui_scale)
    
    def get_scaled_padding(self, base_padding: int) -> int:
        """Get padding value scaled by the UI scale factor"""
        ui_scale = self.custom_settings.get("ui_scale", 1.0)
        return max(1, int(base_padding * ui_scale))
    
    def apply_theme(self, widget: tk.Widget):
        """Apply theme to a widget"""
        try:
            widget.configure(bg=self.current_theme["bg"])
            if hasattr(widget, 'configure'):
                if isinstance(widget, (tk.Label, tk.Button)):
                    widget.configure(fg=self.current_theme["fg"])
                elif isinstance(widget, tk.Entry):
                    widget.configure(
                        fg=self.current_theme["fg"],
                        insertbackground=self.current_theme["fg"],
                        selectbackground=self.current_theme["select_bg"],
                        selectforeground=self.current_theme["select_fg"]
                    )
        except:
            pass  # Ignore theme application errors

# =============================================================================
# ICON MANAGER
# =============================================================================

class IconManager:
    """Manages loading and caching of icons"""
    
    def __init__(self, theme_manager: ThemeManager):
        self.theme_manager = theme_manager
        self.icon_cache: Dict[str, ImageTk.PhotoImage] = {}
        self.base_path = Path("sterilized data box")
    
    def get_icon(self, icon_path: str, size: Tuple[int, int] = (32, 32)) -> Optional[ImageTk.PhotoImage]:
        """Get icon with caching and scaling applied"""
        # Apply UI scaling to base size
        ui_scale = self.theme_manager.custom_settings.get("ui_scale", 1.0)
        scaled_size = (int(size[0] * ui_scale), int(size[1] * ui_scale))
        
        # Apply icon scale (for unit icons specifically)
        icon_scale = self.theme_manager.custom_settings["icon_scale"]
        final_size = (int(scaled_size[0] * icon_scale), int(scaled_size[1] * icon_scale))
        
        cache_key = f"{icon_path}_{final_size[0]}x{final_size[1]}"
        
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
        
        # Try to load icon
        full_path = self.base_path / icon_path
        if not full_path.exists():
            return None
        
        try:
            # Load and resize image
            image = Image.open(full_path)
            image = image.resize(final_size, Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image)
            self.icon_cache[cache_key] = photo
            return photo
            
        except Exception as e:
            print(f"Error loading icon {icon_path}: {e}")
            return None
    
    def get_faction_icon(self, faction: str, size: Tuple[int, int] = (32, 32)) -> Optional[ImageTk.PhotoImage]:
        """Get faction icon"""
        if faction in FACTION_HIERARCHY:
            icon_name = FACTION_HIERARCHY[faction]["icon"]
            return self.get_icon(f"{icon_name}.webp", size)
        return None

# =============================================================================
# CUSTOM WIDGETS
# =============================================================================

class HelpTip(tk.Frame):
    """A circular help tip widget that shows contextual information when clicked"""
    
    def __init__(self, parent, tip_text: str, theme_manager: ThemeManager, **kwargs):
        super().__init__(parent, **kwargs)
        self.tip_text = tip_text
        self.theme_manager = theme_manager
        self.popup = None
        
        # Create circular button with "!" inside
        self.button = tk.Canvas(
            self,
            width=self.theme_manager.get_scaled_size(20),
            height=self.theme_manager.get_scaled_size(20),
            bg=DEFAULT_THEME["bg"],
            highlightthickness=0,
            cursor="hand2"
        )
        self.button.pack()
        
        # Draw circle and "!"
        self.draw_icon()
        
        # Bind click event
        self.button.bind("<Button-1>", self.show_popup)
        self.bind("<Button-1>", self.show_popup)
    
    def draw_icon(self):
        """Draw the circular icon with "!" inside"""
        self.button.delete("all")
        
        size = self.theme_manager.get_scaled_size(20)
        radius = size // 2 - 2
        
        # Draw circle
        self.button.create_oval(
            2, 2, size-2, size-2,
            fill=DEFAULT_THEME["accent"],
            outline=DEFAULT_THEME["fg"],
            width=1
        )
        
        # Draw "!" text
        font_size = self.theme_manager.get_scaled_size(12)
        self.button.create_text(
            size//2, size//2,
            text="!",
            fill="white",
            font=("Arial", font_size, "bold")
        )
    
    def show_popup(self, event):
        """Show the help popup dialog"""
        if self.popup:
            return
        
        # Create popup window
        self.popup = tk.Toplevel(self)
        self.popup.title("Help")
        self.popup.geometry("400x200")
        self.popup.resizable(False, False)
        
        # Make it modal
        self.popup.transient(self.winfo_toplevel())
        self.popup.grab_set()
        
        # Center the popup on screen
        self.popup.update_idletasks()
        width = self.popup.winfo_width()
        height = self.popup.winfo_height()
        x = (self.popup.winfo_screenwidth() // 2) - (width // 2)
        y = (self.popup.winfo_screenheight() // 2) - (height // 2)
        self.popup.geometry(f"{width}x{height}+{x}+{y}")
        
        # Create content
        main_frame = tk.Frame(self.popup, bg=DEFAULT_THEME["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title = tk.Label(
            main_frame,
            text="Page Instructions",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(2, "bold")
        )
        title.pack(pady=(0, 10))
        
        # Help text
        display_text = self.tip_text.replace(" • ", "\n• ")
        help_label = tk.Label(
            main_frame,
            text=display_text,
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(0),
            justify=tk.LEFT
        )
        help_label.pack(pady=(0, 20))
        
        # Close button
        close_btn = tk.Button(
            main_frame,
            text="Close",
            bg=DEFAULT_THEME["button_bg"],
            fg=DEFAULT_THEME["button_fg"],
            font=self.theme_manager.get_font(1),
            command=self.close_popup,
            bd=0,
            highlightthickness=0,
            padx=20,
            pady=5
        )
        close_btn.pack()
        
        # Bind escape key to close
        self.popup.bind("<Escape>", lambda e: self.close_popup())
        
        # Set focus to popup
        self.popup.focus_set()
    
    def close_popup(self):
        """Close the help popup"""
        if self.popup:
            self.popup.destroy()
            self.popup = None
    
    def update_theme(self):
        """Update the icon appearance when theme changes"""
        self.draw_icon()

class CustomTitleBar(tk.Frame):
    """Custom title bar for draggable window with collapse/expand functionality"""
    
    def __init__(self, root_window, title: str, on_close_callback, on_collapse_callback=None):
        super().__init__(root_window, height=30)
        self.configure(bg=DEFAULT_THEME["title_bg"])
        
        # Store the actual root window (parent of the main_container)
        self.root_window = root_window.winfo_toplevel()
        self.on_close = on_close_callback
        self.on_collapse = on_collapse_callback
        self.start_x = 0
        self.start_y = 0
        self.is_collapsed = False
        
        # Title
        self.title_label = tk.Label(
            self,
            text=title,
            bg=DEFAULT_THEME["title_bg"],
            fg=DEFAULT_THEME["title_fg"],
            font=("Segoe UI", 10, "bold")
        )
        self.title_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Buttons
        button_frame = tk.Frame(self, bg=DEFAULT_THEME["title_bg"])
        button_frame.pack(side=tk.RIGHT, padx=5, pady=2)
        
        if on_collapse_callback:
            self.collapse_btn = tk.Button(
                button_frame,
                text="─",
                bg=DEFAULT_THEME["button_bg"],
                fg=DEFAULT_THEME["button_fg"],
                width=3,
                height=1,
                command=self.toggle_collapse,
                bd=0,
                highlightthickness=0
            )
            self.collapse_btn.pack(side=tk.LEFT, padx=2)
        
        self.close_btn = tk.Button(
            button_frame,
            text="✕",
            bg=DEFAULT_THEME["button_bg"],
            fg=DEFAULT_THEME["button_fg"],
            width=3,
            height=1,
            command=on_close_callback,
            bd=0,
            highlightthickness=0
        )
        self.close_btn.pack(side=tk.LEFT, padx=2)
        
        # Bind mouse events for dragging
        self.bind("<Button-1>", self.start_drag)
        self.title_label.bind("<Button-1>", self.start_drag)
        self.bind("<B1-Motion>", self.on_drag)
        self.title_label.bind("<B1-Motion>", self.on_drag)
    
    def toggle_collapse(self):
        """Toggle between collapsed and expanded states"""
        self.is_collapsed = not self.is_collapsed
        if self.on_collapse:
            self.on_collapse(self.is_collapsed)
        
        # Update button text
        if self.is_collapsed:
            self.collapse_btn.configure(text="□")
        else:
            self.collapse_btn.configure(text="─")
    
    def start_drag(self, event):
        """Start dragging the window"""
        self.start_x = event.x_root
        self.start_y = event.y_root
    
    def on_drag(self, event):
        """Handle window dragging"""
        x = self.root_window.winfo_x() + (event.x_root - self.start_x)
        y = self.root_window.winfo_y() + (event.y_root - self.start_y)
        self.root_window.geometry(f"+{x}+{y}")
        self.start_x = event.x_root
        self.start_y = event.y_root

# =============================================================================
# MAIN APPLICATION
# =============================================================================

class MentalOmegaArsenal:
    """Main application class"""
    
    def __init__(self):
        # Initialize managers first
        self.theme_manager = ThemeManager()
        self.data_manager = DataManager()
        self.icon_manager = IconManager(self.theme_manager)
        
        self.root = tk.Tk()
        self.setup_window()
        
        # UI state
        self.current_faction = None
        self.comparison_units = []
        self.search_results = []
        
        # Create UI
        self.create_widgets()
        self.apply_theme()
        
        # Set up keyboard shortcuts
        self.setup_shortcuts()
        
        # Start with faction view
        self.show_factions()
    
    def setup_window(self):
        """Configure main window with UI scaling applied"""
        # Apply UI scaling to window dimensions
        ui_scale = self.theme_manager.custom_settings.get("ui_scale", 1.0)
        scaled_width = int(DEFAULT_WINDOW_SIZE[0] * ui_scale)
        scaled_height = int(DEFAULT_WINDOW_SIZE[1] * ui_scale)
        scaled_min_width = int(MIN_WINDOW_SIZE[0] * ui_scale)
        scaled_min_height = int(MIN_WINDOW_SIZE[1] * ui_scale)
        
        self.root.title(APP_TITLE)
        self.root.geometry(f"{scaled_width}x{scaled_height}")
        self.root.minsize(scaled_min_width, scaled_min_height)
        
        # Make window always on top
        self.root.attributes("-topmost", True)
        
        # Remove default title bar
        self.root.overrideredirect(True)
        
        # Set window opacity
        self.root.attributes("-alpha", self.theme_manager.custom_settings["opacity"])
        
        # Center window on screen
        self.center_window()
    
    def center_window(self):
        """Center window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Main container
        self.main_container = tk.Frame(self.root, bg=DEFAULT_THEME["bg"])
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Custom title bar
        self.title_bar = CustomTitleBar(
            self.main_container,
            APP_TITLE,
            self.on_close,
            self.on_collapse
        )
        self.title_bar.pack(fill=tk.X)
        
        # Content area
        self.content_frame = tk.Frame(self.main_container, bg=DEFAULT_THEME["bg"])
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Faction buttons (always visible at top)
        self.create_faction_toolbar()
        
        # Main content area (will be dynamically updated)
        self.main_content = tk.Frame(self.content_frame, bg=DEFAULT_THEME["bg"])
        self.main_content.pack(fill=tk.BOTH, expand=True)
    
    def create_faction_toolbar(self):
        """Create faction toolbar that's always visible"""
        self.faction_toolbar = tk.Frame(self.content_frame, bg=DEFAULT_THEME["title_bg"], height=50)
        self.faction_toolbar.pack(fill=tk.X, pady=(0, 5))
        self.faction_toolbar.pack_propagate(False)
        
        # Faction buttons
        faction_frame = tk.Frame(self.faction_toolbar, bg=DEFAULT_THEME["title_bg"])
        faction_frame.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.faction_buttons = {}
        for faction_name in FACTION_HIERARCHY:
            # Get faction icon - scaled down to fit
            icon = self.icon_manager.get_faction_icon(faction_name, (24, 24))
            
            btn = tk.Button(
                faction_frame,
                text="",  # Remove text
                image=icon,
                bg=DEFAULT_THEME["button_bg"],
                fg=DEFAULT_THEME["button_fg"],
                font=self.theme_manager.get_font(0),
                command=lambda f=faction_name: self.select_faction(f),
                bd=0,
                highlightthickness=0,
                padx=5,
                pady=5,
                width=30,  # Set fixed width
                height=30  # Set fixed height
            )
            if icon:
                btn.image = icon  # Keep reference
            btn.pack(side=tk.LEFT, padx=5)
            self.faction_buttons[faction_name] = btn
        
        # Navigation buttons
        nav_frame = tk.Frame(self.faction_toolbar, bg=DEFAULT_THEME["title_bg"])
        nav_frame.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Search button
        self.search_btn = tk.Button(
            nav_frame,
            text="🔍",
            bg=DEFAULT_THEME["button_bg"],
            fg=DEFAULT_THEME["button_fg"],
            width=3,
            command=self.show_search,
            bd=0,
            highlightthickness=0
        )
        self.search_btn.pack(side=tk.LEFT, padx=2)
        
        # Compare button
        self.compare_btn = tk.Button(
            nav_frame,
            text="📊",
            bg=DEFAULT_THEME["button_bg"],
            fg=DEFAULT_THEME["button_fg"],
            width=3,
            command=self.show_comparison,
            bd=0,
            highlightthickness=0
        )
        self.compare_btn.pack(side=tk.LEFT, padx=2)
        
        # Settings button
        self.settings_btn = tk.Button(
            nav_frame,
            text="⚙️",
            bg=DEFAULT_THEME["button_bg"],
            fg=DEFAULT_THEME["button_fg"],
            width=3,
            command=self.show_settings,
            bd=0,
            highlightthickness=0
        )
        self.settings_btn.pack(side=tk.LEFT, padx=2)
    
    def apply_theme(self):
        """Apply theme to all widgets"""
        self.theme_manager.apply_theme(self.main_container)
        self.theme_manager.apply_theme(self.content_frame)
        self.theme_manager.apply_theme(self.main_content)
        self.root.attributes("-alpha", self.theme_manager.custom_settings["opacity"])
    
    def setup_shortcuts(self):
        """Set up keyboard shortcuts"""
        self.root.bind("<Control-f>", lambda e: self.show_search())
        self.root.bind("<Escape>", lambda e: self.show_factions())
    
    def clear_main_content(self):
        """Clear the main content area"""
        for widget in self.main_content.winfo_children():
            widget.destroy()
    
    # Navigation methods
    def show_factions(self):
        """Show faction selection (initial view)"""
        self.current_faction = None
        self.clear_main_content()
        
        # Reset all faction buttons to normal state
        for faction_name, btn in self.faction_buttons.items():
            btn.configure(bg=DEFAULT_THEME["button_bg"])
        
        # Welcome message
        welcome_frame = tk.Frame(self.main_content, bg=DEFAULT_THEME["bg"])
        welcome_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title = tk.Label(
            welcome_frame,
            text="Welcome to Mental Omega Arsenal",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(4, "bold")
        )
        title.pack(pady=(0, 20))
        
        subtitle = tk.Label(
            welcome_frame,
            text="Select a faction from the top menu to begin browsing units",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["accent"],
            font=self.theme_manager.get_font(2)
        )
        subtitle.pack()
    
    def select_faction(self, faction: str):
        """Select a faction and show its units"""
        self.current_faction = faction
        
        # Update faction button states
        for faction_name, btn in self.faction_buttons.items():
            if faction_name == faction:
                btn.configure(bg=DEFAULT_THEME["select_bg"])
            else:
                btn.configure(bg=DEFAULT_THEME["button_bg"])
        
        self.show_faction_units(faction)
    
    def show_faction_units(self, faction: str, filter_category: str = None):
        """Show all units for a faction organized by category and subfaction"""
        self.clear_main_content()
        
        # Create scrollable area
        canvas = tk.Canvas(self.main_content, bg=DEFAULT_THEME["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.main_content, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=DEFAULT_THEME["bg"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Enable mouse wheel scrolling with improved event handling
        def _on_mousewheel(event):
            # Check if we can scroll
            if canvas.yview() != (0.0, 1.0):  # Not at top or bottom
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"  # Prevent event propagation to avoid conflicts
        
        def _bind_to_mousewheel(event):
            # Bind to all widgets to ensure scrolling works regardless of what's under the cursor
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            # Also bind to child widgets to catch events that might be consumed
            for child in scrollable_frame.winfo_children():
                _bind_recursive(child)
        
        def _bind_recursive(widget):
            """Recursively bind mousewheel to all child widgets"""
            try:
                widget.bind("<MouseWheel>", _on_mousewheel)
                for child in widget.winfo_children():
                    _bind_recursive(child)
            except:
                pass  # Skip widgets that don't support binding
        
        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)
        
        # Title
        title_text = f"{faction}"
        if filter_category:
            title_text += f" - {filter_category}"
        title = tk.Label(
            scrollable_frame,
            text=title_text,
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(4, "bold")
        )
        title.pack(pady=(0, 20))
        
        # Add help tip for faction units page
        help_tip = HelpTip(
            scrollable_frame,
            "Left-click on unit to view details • Right-click to add to comparison",
            self.theme_manager,
            bg=DEFAULT_THEME["bg"]
        )
        help_tip.place(relx=1.0, rely=0.0, anchor=tk.NE, x=-10, y=10)
        
        # Category buttons with "All" option
        category_frame = tk.Frame(scrollable_frame, bg=DEFAULT_THEME["bg"])
        category_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # "All" button to clear filter
        all_btn = tk.Button(
            category_frame,
            text="All",
            bg=DEFAULT_THEME["select_bg"] if not filter_category else DEFAULT_THEME["button_bg"],
            fg=DEFAULT_THEME["select_fg"] if not filter_category else DEFAULT_THEME["button_fg"],
            font=self.theme_manager.get_font(1),
            command=lambda: self.show_faction_units(faction, None),
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=5
        )
        all_btn.pack(side=tk.LEFT, padx=5)
        
        for category in UNIT_CATEGORIES:
            # Count units in this category across all subfactions
            total_units = 0
            for subfaction in FACTION_HIERARCHY[faction]["subfactions"]:
                units = self.data_manager.get_units_for_path(faction, subfaction, category)
                total_units += len(units)
            
            if total_units == 0:
                continue
            
            # Highlight active filter
            is_active = filter_category == category
            btn = tk.Button(
                category_frame,
                text=f"{category} ({total_units})",
                bg=DEFAULT_THEME["select_bg"] if is_active else DEFAULT_THEME["button_bg"],
                fg=DEFAULT_THEME["select_fg"] if is_active else DEFAULT_THEME["button_fg"],
                font=self.theme_manager.get_font(1),
                command=lambda c=category: self.show_faction_units(faction, c),
                bd=0,
                highlightthickness=0,
                padx=10,
                pady=5
            )
            btn.pack(side=tk.LEFT, padx=5)
        
        # General structure units (base faction)
        general_frame = tk.Frame(scrollable_frame, bg=DEFAULT_THEME["bg"])
        general_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Header for general structure
        header_label = tk.Label(
            general_frame,
            text="General structure:",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["accent"],
            font=self.theme_manager.get_font(2, "bold")
        )
        header_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Show general units by category
        for category in UNIT_CATEGORIES:
            if filter_category and category != filter_category:
                continue
                
            # Get base faction units for this category
            base_units = []
            for subfaction_name in FACTION_HIERARCHY[faction]["subfactions"]:
                subfaction_units = self.data_manager.get_units_for_path(faction, subfaction_name, category)
                for unit in subfaction_units:
                    # Check if this is a base faction unit (appears in all subfactions)
                    is_base = True
                    for other_subfaction in FACTION_HIERARCHY[faction]["subfactions"]:
                        if other_subfaction == subfaction_name:
                            continue
                        other_units = self.data_manager.get_units_for_path(faction, other_subfaction, category)
                        if not any(u.name == unit.name for u in other_units):
                            is_base = False
                            break
                    if is_base and unit not in base_units:
                        base_units.append(unit)
            
            if base_units:
                # Category label
                cat_label = tk.Label(
                    general_frame,
                    text=f"  {category}:",
                    bg=DEFAULT_THEME["bg"],
                    fg=DEFAULT_THEME["fg"],
                    font=self.theme_manager.get_font(1, "bold")
                )
                cat_label.pack(anchor=tk.W, pady=(5, 2))
                
                # Units grid
                units_grid = tk.Frame(general_frame, bg=DEFAULT_THEME["bg"])
                units_grid.pack(fill=tk.X, pady=(0, 5))
                
                # Display units in a grid
                units_per_row = 8
                for i, unit in enumerate(sorted(base_units, key=lambda u: u.name)):
                    row = i // units_per_row
                    col = i % units_per_row
                    
                    if col == 0:
                        row_frame = tk.Frame(units_grid, bg=DEFAULT_THEME["bg"])
                        row_frame.pack(fill=tk.X, pady=2)
                    
                    unit_btn = self.create_unit_button(row_frame, unit, size=(48, 48))
                    unit_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Subfaction-specific units
        for subfaction_name in FACTION_HIERARCHY[faction]["subfactions"]:
            # Get all units for this subfaction
            subfaction_units = []
            for category in UNIT_CATEGORIES:
                if filter_category and category != filter_category:
                    continue
                units = self.data_manager.get_units_for_path(faction, subfaction_name, category)
                subfaction_units.extend(units)
            
            # Filter out base faction units
            base_unit_names = set()
            for category in UNIT_CATEGORIES:
                if filter_category and category != filter_category:
                    continue
                # Find units that appear in all subfactions (base units)
                category_units = {}
                for sf in FACTION_HIERARCHY[faction]["subfactions"]:
                    sf_units = self.data_manager.get_units_for_path(faction, sf, category)
                    for unit in sf_units:
                        if unit.name not in category_units:
                            category_units[unit.name] = []
                        category_units[unit.name].append(sf)
                
                for unit_name, subfactions in category_units.items():
                    if len(subfactions) == len(FACTION_HIERARCHY[faction]["subfactions"]):
                        base_unit_names.add(unit_name)
            
            # Keep only subfaction-specific units
            subfaction_specific = [u for u in subfaction_units if u.name not in base_unit_names]
            
            if not subfaction_specific:
                continue
            
            subfaction_frame = tk.Frame(scrollable_frame, bg=DEFAULT_THEME["bg"])
            subfaction_frame.pack(fill=tk.X, padx=20, pady=10)
            
            # Subfaction header
            header_frame = tk.Frame(subfaction_frame, bg=DEFAULT_THEME["select_bg"])
            header_frame.pack(fill=tk.X)
            
            # Get subfaction icon
            icon_name = FACTION_HIERARCHY[faction]["subfactions"][subfaction_name]["icon"]
            icon = self.icon_manager.get_icon(f"{icon_name}.webp", (24, 24))
            
            header_label = tk.Label(
                header_frame,
                text=subfaction_name,
                image=icon,
                compound=tk.LEFT if icon else None,
                bg=DEFAULT_THEME["select_bg"],
                fg=DEFAULT_THEME["select_fg"],
                font=self.theme_manager.get_font(2, "bold")
            )
            if icon:
                header_label.image = icon
            header_label.pack(side=tk.LEFT, padx=10, pady=5)
            
            # Units grid for this subfaction
            units_grid = tk.Frame(subfaction_frame, bg=DEFAULT_THEME["bg"])
            units_grid.pack(fill=tk.X, pady=(5, 0))
            
            # Sort units by name
            subfaction_specific.sort(key=lambda u: u.name)
            
            # Display units in a grid
            units_per_row = 8  # Number of units per row
            for i, unit in enumerate(subfaction_specific):
                row = i // units_per_row
                col = i % units_per_row
                
                # Create row frame if needed
                if col == 0:
                    row_frame = tk.Frame(units_grid, bg=DEFAULT_THEME["bg"])
                    row_frame.pack(fill=tk.X, pady=2)
                
                # Unit button
                unit_btn = self.create_unit_button(row_frame, unit, size=(48, 48))
                unit_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def show_category_units(self, faction: str, category: str):
        """Show units for a specific category across all subfactions"""
        # Simply call show_faction_units with the category filter
        self.show_faction_units(faction, category)
    
    def create_unit_button(self, parent, unit: UnitData, size=(48, 48)):
        """Create a unit button with icon and comparison functionality"""
        # Try multiple icon path variants
        icon_variants = [
            f"{unit.faction.replace(' ', '_')}/subfaction/{unit.subfaction}/{unit.category}/icons/{unit.icon_filename}",
            f"{unit.faction}/subfaction/{unit.subfaction}/{unit.category}/icons/{unit.icon_filename}",
            f"{unit.faction.replace(' ', '_')}/subfaction/{unit.subfaction.replace(' ', '_')}/{unit.category.replace(' ', '_')}/icons/{unit.icon_filename}",
            f"{unit.faction}/{unit.category}/icons/{unit.icon_filename}",
            f"{unit.faction.replace(' ', '_')}/{unit.category.replace(' ', '_')}/icons/{unit.icon_filename}"
        ]
        
        icon = None
        for icon_path in icon_variants:
            icon = self.icon_manager.get_icon(icon_path, size)
            if icon:
                break
        
        # Create container for button and comparison indicator
        container = tk.Frame(parent, bg=DEFAULT_THEME["bg"])
        
        # Store unit reference in container for easy updates
        container.unit_data = unit
        container.indicator = None
        
        # Function to update button appearance
        def update_appearance():
            is_in_comparison = unit in self.comparison_units
            btn_bg = DEFAULT_THEME["button_bg"] if not is_in_comparison else "#004400"
            
            btn.configure(bg=btn_bg)
            
            # Update or remove indicator
            if container.indicator:
                container.indicator.destroy()
                container.indicator = None
            
            if is_in_comparison:
                container.indicator = tk.Label(
                    container,
                    text="✓",
                    bg="#00aa00",
                    fg="white",
                    font=self.theme_manager.get_font(0, "bold"),
                    width=2,
                    height=1
                )
                container.indicator.place(x=2, y=2)
        
        # Check if unit is already in comparison
        is_in_comparison = unit in self.comparison_units
        
        # Create button
        btn = tk.Button(
            container,
            text=unit.name if not icon else "",
            image=icon,
            compound=tk.TOP if icon else None,
            bg=DEFAULT_THEME["button_bg"] if not is_in_comparison else "#004400",
            fg=DEFAULT_THEME["button_fg"],
            font=self.theme_manager.get_font(0),
            bd=0,
            highlightthickness=0,
            padx=5,
            pady=5
        )
        
        if icon:
            btn.image = icon  # Keep reference
        
        # Add comparison indicator if in comparison
        if is_in_comparison:
            container.indicator = tk.Label(
                container,
                text="✓",
                bg="#00aa00",
                fg="white",
                font=self.theme_manager.get_font(0, "bold"),
                width=2,
                height=1
            )
            container.indicator.place(x=2, y=2)
        
        # Left-click: navigate to unit details
        def on_left_click(event):
            self.show_unit_details(unit)
        
        # Right-click: toggle comparison
        def on_right_click(event):
            self.toggle_comparison_and_refresh(unit)
        
        # Add tooltip on hover
        def on_enter(event):
            is_in_comp = unit in self.comparison_units
            btn.configure(bg=DEFAULT_THEME["hover"] if not is_in_comp else "#006600")
        
        def on_leave(event):
            is_in_comp = unit in self.comparison_units
            btn.configure(bg=DEFAULT_THEME["button_bg"] if not is_in_comp else "#004400")
        
        btn.bind("<Button-1>", on_left_click)
        btn.bind("<Button-3>", on_right_click)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        # Store update function in container for external access
        container.update_appearance = update_appearance
        
        btn.pack()
        return container
    
    def show_unit_details(self, unit: UnitData):
        """Show detailed unit information"""
        self.clear_main_content()
        
        details_frame = tk.Frame(self.main_content, bg=DEFAULT_THEME["bg"])
        details_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Button frame for back and comparison buttons
        button_frame = tk.Frame(details_frame, bg=DEFAULT_THEME["bg"])
        button_frame.pack(anchor=tk.W, pady=(0, 10))
        
        # Back button
        back_btn = tk.Button(
            button_frame,
            text="← Back",
            bg=DEFAULT_THEME["button_bg"],
            fg=DEFAULT_THEME["button_fg"],
            font=self.theme_manager.get_font(1),
            command=lambda: self.show_faction_units(unit.faction, None),
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=5
        )
        back_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Comparison button
        is_in_comparison = unit in self.comparison_units
        compare_btn_text = "✓ In Comparison" if is_in_comparison else "+ Add to Comparison"
        compare_btn_color = "#00aa00" if is_in_comparison else DEFAULT_THEME["accent"]
        
        compare_btn = tk.Button(
            button_frame,
            text=compare_btn_text,
            bg=compare_btn_color,
            fg=DEFAULT_THEME["button_fg"],
            font=self.theme_manager.get_font(1),
            command=lambda: self.toggle_comparison_and_refresh(unit),
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=5
        )
        compare_btn.pack(side=tk.LEFT)
        
        # Store reference to update button text later
        self.compare_btn = compare_btn
        
        # Unit header
        header_frame = tk.Frame(details_frame, bg=DEFAULT_THEME["bg"])
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Unit icon - try multiple path variants
        icon_variants = [
            f"{unit.faction.replace(' ', '_')}/subfaction/{unit.subfaction}/{unit.category}/icons/{unit.icon_filename}",
            f"{unit.faction}/subfaction/{unit.subfaction}/{unit.category}/icons/{unit.icon_filename}",
            f"{unit.faction.replace(' ', '_')}/subfaction/{unit.subfaction.replace(' ', '_')}/{unit.category.replace(' ', '_')}/icons/{unit.icon_filename}",
            f"{unit.faction}/{unit.category}/icons/{unit.icon_filename}",
            f"{unit.faction.replace(' ', '_')}/{unit.category.replace(' ', '_')}/icons/{unit.icon_filename}"
        ]
        
        icon = None
        for icon_path in icon_variants:
            icon = self.icon_manager.get_icon(icon_path, (64, 64))
            if icon:
                break
        
        if icon:
            icon_label = tk.Label(header_frame, image=icon, bg=DEFAULT_THEME["bg"])
            icon_label.image = icon  # Keep reference
            icon_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # Unit info
        info_frame = tk.Frame(header_frame, bg=DEFAULT_THEME["bg"])
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        name_label = tk.Label(
            info_frame,
            text=unit.name,
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(6, "bold")
        )
        name_label.pack(anchor=tk.W)
        
        faction_label = tk.Label(
            info_frame,
            text=f"{unit.faction} - {unit.subfaction}",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["accent"],
            font=self.theme_manager.get_font(2)
        )
        faction_label.pack(anchor=tk.W)
        
        category_label = tk.Label(
            info_frame,
            text=unit.category,
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(1)
        )
        category_label.pack(anchor=tk.W)
        
        # Add help tip for unit details page
        help_tip = HelpTip(
            details_frame,
            "Use Back button to return • Add to Comparison for side-by-side analysis",
            self.theme_manager,
            bg=DEFAULT_THEME["bg"]
        )
        help_tip.place(relx=1.0, rely=0.0, anchor=tk.NE, x=-10, y=10)
        
        # Properties table with article tables integrated
        self.create_properties_table(details_frame, unit)
    
    def create_properties_table(self, parent, unit: UnitData):
        """Create properties table for unit"""
        table_frame = tk.LabelFrame(
            parent,
            text="Properties",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(2, "bold")
        )
        table_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create scrollable frame for table
        canvas = tk.Canvas(table_frame, bg=DEFAULT_THEME["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=DEFAULT_THEME["bg"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Enable mouse wheel scrolling anywhere on the canvas with improved handling
        def _on_mousewheel(event):
            if canvas.yview() != (0.0, 1.0):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
        
        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            # Bind to child widgets
            for child in scrollable_frame.winfo_children():
                _bind_recursive_props(child)
        
        def _bind_recursive_props(widget):
            """Recursively bind mousewheel to all child widgets"""
            try:
                widget.bind("<MouseWheel>", _on_mousewheel)
                for child in widget.winfo_children():
                    _bind_recursive_props(child)
            except:
                pass
        
        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)
        
        # Add properties
        for key, value in unit.infobox_data.items():
            if key.startswith("_section_"):
                continue  # Skip section markers
                
            # Handle special formatting for certain properties
            if key.lower() in ["ground damage modifiers", "air damage modifiers", "ground modifiers", "air modifiers", "armor types", "requires", "allows", "build time multiplier(s)", "strong against", "weak against", "builds", "tech level", "tier"]:
                self._create_modifier_property(scrollable_frame, key, value)
            elif key.lower() in ["cost", "hit points", "power", "sight radius", "tech level", "tier"]:
                # Numeric properties - format with better spacing
                self._create_numeric_property(scrollable_frame, key, value)
            elif key.lower() in ["built by", "builds", "requires", "allows"]:
                # Unit/structure relationships
                self._create_modifier_property(scrollable_frame, key, value)
            else:
                # Standard properties
                self._create_standard_property(scrollable_frame, key, value)
        
        # Add article tables at the end of properties table (if any)
        if unit.article_tables:
            self._add_article_tables_to_properties(scrollable_frame, unit.article_tables)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _create_modifier_property(self, parent, key: str, value):
        """Create a special formatted property for modifiers and lists"""
        # Main property frame with alternating background
        bg_color = DEFAULT_THEME["bg"] if len(parent.winfo_children()) % 2 == 0 else "#252525"
        main_frame = tk.Frame(parent, bg=bg_color)
        main_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Property name with same background as row
        name_label = tk.Label(
            main_frame,
            text=f"{key}:",
            bg=bg_color,
            fg=DEFAULT_THEME["accent"],
            font=self.theme_manager.get_font(1, "bold"),
            width=20,
            anchor=tk.NW
        )
        name_label.pack(side=tk.LEFT, anchor=tk.NW)
        
        # Value frame for better layout with same background as row
        value_frame = tk.Frame(main_frame, bg=bg_color)
        value_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        if isinstance(value, list):
            # Display ALL list items in separate lines
            for item in value:
                item_label = tk.Label(
                    value_frame,
                    text=f"• {str(item)}",
                    bg=bg_color,
                    fg=DEFAULT_THEME["fg"],
                    font=self.theme_manager.get_font(1),
                    anchor=tk.W,
                    wraplength=600,
                    justify=tk.LEFT
                )
                item_label.pack(anchor=tk.W, pady=1)
        else:
            # Handle string values - show ALL content with proper wrapping
            text = str(value)
            if "," in text or ";" in text:
                # Split by common separators and display ALL items as list
                items = [item.strip() for item in text.replace(";", ",").split(",")]
                for item in items:
                    item_label = tk.Label(
                        value_frame,
                        text=f"• {item}",
                        bg=bg_color,
                        fg=DEFAULT_THEME["fg"],
                        font=self.theme_manager.get_font(1),
                        anchor=tk.W,
                        wraplength=600,
                        justify=tk.LEFT
                    )
                    item_label.pack(anchor=tk.W, pady=1)
            else:
                # Single line value - show with proper wrapping
                value_label = tk.Label(
                    value_frame,
                    text=text,
                    bg=bg_color,
                    fg=DEFAULT_THEME["fg"],
                    font=self.theme_manager.get_font(1),
                    anchor=tk.NW,
                    wraplength=600,
                    justify=tk.LEFT
                )
                value_label.pack(anchor=tk.W)
    
    def _create_numeric_property(self, parent, key: str, value):
        """Create a formatted property for numeric values"""
        # Alternating background color
        bg_color = DEFAULT_THEME["bg"] if len(parent.winfo_children()) % 2 == 0 else "#252525"
        prop_frame = tk.Frame(parent, bg=bg_color)
        prop_frame.pack(fill=tk.X, padx=10, pady=3)
        
        # Property name with same background as row
        name_label = tk.Label(
            prop_frame,
            text=f"{key}:",
            bg=bg_color,
            fg=DEFAULT_THEME["accent"],
            font=self.theme_manager.get_font(1, "bold"),
            width=20,
            anchor=tk.W
        )
        name_label.pack(side=tk.LEFT)
        
        # Format numeric value with emphasis
        value_text = str(value)
        if isinstance(value, (int, float)):
            # Add spacing for numeric values
            value_text = f"  {value_text}  "
        
        value_label = tk.Label(
            prop_frame,
            text=value_text,
            bg=bg_color,
            fg="#00ff00" if isinstance(value, (int, float)) else DEFAULT_THEME["fg"],  # Green for numbers
            font=self.theme_manager.get_font(1, "bold" if isinstance(value, (int, float)) else "normal"),
            anchor=tk.W,
            wraplength=600
        )
        value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def _create_standard_property(self, parent, key: str, value):
        """Create a standard formatted property"""
        # Alternating background color
        bg_color = DEFAULT_THEME["bg"] if len(parent.winfo_children()) % 2 == 0 else "#252525"
        prop_frame = tk.Frame(parent, bg=bg_color)
        prop_frame.pack(fill=tk.X, padx=10, pady=2)
        
        # Property name with same background as row
        name_label = tk.Label(
            prop_frame,
            text=f"{key}:",
            bg=bg_color,
            fg=DEFAULT_THEME["accent"],
            font=self.theme_manager.get_font(1, "bold"),
            width=20,
            anchor=tk.W
        )
        name_label.pack(side=tk.LEFT)
        
        # Property value with better text wrapping - show ALL information
        if isinstance(value, list):
            # Display all list items, each on its own line
            for item in value:
                item_label = tk.Label(
                    prop_frame,
                    text=f"• {str(item)}",
                    bg=bg_color,
                    fg=DEFAULT_THEME["fg"],
                    font=self.theme_manager.get_font(1),
                    anchor=tk.W,
                    wraplength=600
                )
                item_label.pack(anchor=tk.W, fill=tk.X)
        else:
            # Handle string values with proper wrapping
            value_text = str(value)
            value_label = tk.Label(
                prop_frame,
                text=value_text,
                bg=bg_color,
                fg=DEFAULT_THEME["fg"],
                font=self.theme_manager.get_font(1),
                anchor=tk.NW,
                wraplength=600,
                justify=tk.LEFT
            )
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def _add_article_tables_to_properties(self, parent, article_tables: List[Dict]):
        """Add article tables directly into the properties table"""
        for table_index, table in enumerate(article_tables):
            # Add separator line before each table (except first)
            if table_index > 0:
                separator_frame = tk.Frame(parent, bg=DEFAULT_THEME["bg"], height=2)
                separator_frame.pack(fill=tk.X, padx=10, pady=10)
                
                separator_line = tk.Frame(separator_frame, bg=DEFAULT_THEME["border"], height=1)
                separator_line.pack(fill=tk.X, pady=1)
            
            # Table title as a property
            table_title = table.get("title", f"Table {table_index + 1}")
            title_label = tk.Label(
                parent,
                text=f"• {table_title}:",
                bg=DEFAULT_THEME["bg"],
                fg=DEFAULT_THEME["accent"],
                font=self.theme_manager.get_font(1, "bold"),
                anchor=tk.W,
                pady=10 if table_index == 0 else 5
            )
            title_label.pack(fill=tk.X, padx=10, anchor=tk.W)
            
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            
            if not headers or not rows:
                # Show message if table is empty
                empty_label = tk.Label(
                    parent,
                    text="  No data available",
                    bg=DEFAULT_THEME["bg"],
                    fg=DEFAULT_THEME["fg"],
                    font=self.theme_manager.get_font(1),
                    anchor=tk.W,
                    pady=2
                )
                empty_label.pack(fill=tk.X, padx=20, anchor=tk.W)
                continue
            
            # Create a proper table container
            table_container = tk.Frame(parent, bg=DEFAULT_THEME["bg"])
            table_container.pack(fill=tk.X, padx=20, pady=5)
            
            # Calculate column widths (simple approach - equal width for now)
            num_columns = len(headers)
            column_width = 550 // num_columns  # Total width divided by number of columns
            
            # Create table headers
            header_row = tk.Frame(table_container, bg=DEFAULT_THEME["select_bg"])
            header_row.pack(fill=tk.X)
            
            for i, header in enumerate(headers):
                header_label = tk.Label(
                    header_row,
                    text=header,
                    bg=DEFAULT_THEME["select_bg"],
                    fg=DEFAULT_THEME["select_fg"],
                    font=self.theme_manager.get_font(0, "bold"),
                    width=column_width // 8,  # Approximate character width
                    anchor=tk.W,
                    padx=5,
                    pady=3
                )
                header_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
            
            # Create table rows with alternating colors
            for row_index, row in enumerate(rows):
                bg_color = DEFAULT_THEME["bg"] if row_index % 2 == 0 else "#252525"
                row_frame = tk.Frame(table_container, bg=bg_color)
                row_frame.pack(fill=tk.X)
                
                for i, cell in enumerate(row):
                    cell_text = str(cell)
                    
                    # Special handling for armament column - preserve newlines and format properly
                    if i == 1 and "\n" in cell_text:  # Armament is typically the second column
                        # Split armament into multiple lines but keep it readable
                        armament_lines = cell_text.split("\n")
                        # Clean up each line
                        cleaned_lines = []
                        for line in armament_lines:
                            line = line.strip()
                            if line and not line.startswith("•"):  # Add bullet if not present
                                line = "• " + line
                            cleaned_lines.append(line)
                        
                        cell_text = "\n".join(cleaned_lines)
                        
                        cell_label = tk.Label(
                            row_frame,
                            text=cell_text,
                            bg=bg_color,  # Use row background color
                            fg=DEFAULT_THEME["fg"],
                            font=self.theme_manager.get_font(0),
                            anchor=tk.NW,  # Align to top-left for multi-line
                            justify=tk.LEFT,
                            padx=5,
                            pady=2,
                            wraplength=column_width - 10
                        )
                    else:
                        # Handle other columns - remove newlines and truncate if too long
                        cell_text = cell_text.replace("\n", " ")
                        if len(cell_text) > 50:
                            cell_text = cell_text[:47] + "..."
                        
                        cell_label = tk.Label(
                            row_frame,
                            text=cell_text,
                            bg=bg_color,  # Use row background color
                            fg=DEFAULT_THEME["fg"],
                            font=self.theme_manager.get_font(0),
                            width=column_width // 8,  # Approximate character width
                            anchor=tk.W,
                            padx=5,
                            pady=2
                        )
                    
                    cell_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
    
    def show_search(self):
        """Show search dialog"""
        self.clear_main_content()
        
        search_frame = tk.Frame(self.main_content, bg=DEFAULT_THEME["bg"])
        search_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title = tk.Label(
            search_frame,
            text="Search Units",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(4, "bold")
        )
        title.pack(pady=(0, 20))
        
        # Add help tip for search page
        help_tip = HelpTip(
            search_frame,
            "Type to search units • Click result to view details • Use + button to compare",
            self.theme_manager,
            bg=DEFAULT_THEME["bg"]
        )
        help_tip.place(relx=1.0, rely=0.0, anchor=tk.NE, x=-10, y=10)
        
        # Search entry
        search_entry_frame = tk.Frame(search_frame, bg=DEFAULT_THEME["bg"])
        search_entry_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.search_entry = tk.Entry(
            search_entry_frame,
            bg=DEFAULT_THEME["button_bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(2),
            insertbackground=DEFAULT_THEME["fg"]
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.focus()
        
        self.search_entry.bind("<KeyRelease>", self.on_search)
        self.search_entry.bind("<Return>", self.on_search_select)
        
        # Results frame
        self.search_results_frame = tk.Frame(search_frame, bg=DEFAULT_THEME["bg"])
        self.search_results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Initial search
        self.on_search(None)
    
    def on_search(self, event):
        """Handle search input"""
        query = self.search_entry.get()
        results = self.data_manager.search_units(query)
        self.display_search_results(results)
    
    def display_search_results(self, results: List[SearchItem]):
        """Display search results"""
        # Clear previous results
        for widget in self.search_results_frame.winfo_children():
            widget.destroy()
        
        if not results:
            no_results = tk.Label(
                self.search_results_frame,
                text="No results found",
                bg=DEFAULT_THEME["bg"],
                fg=DEFAULT_THEME["fg"],
                font=self.theme_manager.get_font(2)
            )
            no_results.pack(pady=20)
            return
        
        # Create scrollable results
        canvas = tk.Canvas(self.search_results_frame, bg=DEFAULT_THEME["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.search_results_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=DEFAULT_THEME["bg"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Enable mouse wheel scrolling anywhere on the canvas with improved handling
        def _on_mousewheel(event):
            if canvas.yview() != (0.0, 1.0):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
        
        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            # Bind to child widgets
            for child in scrollable_frame.winfo_children():
                _bind_recursive_search(child)
        
        def _bind_recursive_search(widget):
            """Recursively bind mousewheel to all child widgets"""
            try:
                widget.bind("<MouseWheel>", _on_mousewheel)
                for child in widget.winfo_children():
                    _bind_recursive_search(child)
            except:
                pass
        
        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)
        
        # Display results
        for result in results:
            result_frame = tk.Frame(scrollable_frame, bg=DEFAULT_THEME["button_bg"])
            result_frame.pack(fill=tk.X, pady=2, padx=5)
            
            # Result button
            btn_text = f"  {result.name}\n    {result.faction} - {result.subfaction} - {result.category}"
            btn = tk.Button(
                result_frame,
                text=btn_text,
                bg=DEFAULT_THEME["button_bg"],
                fg=DEFAULT_THEME["button_fg"],
                font=self.theme_manager.get_font(1),
                command=lambda r=result: self.show_unit_details(r.unit_data),
                bd=0,
                highlightthickness=0,
                anchor=tk.W,
                pady=8
            )
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Check if unit is already in comparison
            is_in_comparison = result.unit_data in self.comparison_units
            compare_btn_text = "✓" if is_in_comparison else "+"
            compare_btn_color = "#00aa00" if is_in_comparison else DEFAULT_THEME["accent"]
            
            # Add to comparison button
            compare_btn = tk.Button(
                result_frame,
                text=compare_btn_text,
                bg=compare_btn_color,
                fg=DEFAULT_THEME["fg"],
                width=3,
                command=lambda r=result: self.toggle_comparison_and_refresh(r.unit_data),
                bd=0,
                highlightthickness=0
            )
            compare_btn.pack(side=tk.RIGHT, padx=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def on_search_select(self, event):
        """Handle search selection with Enter key"""
        query = self.search_entry.get()
        results = self.data_manager.search_units(query)
        if results:
            self.show_unit_details(results[0].unit_data)
    
    def toggle_comparison(self, unit: UnitData):
        """Toggle unit in comparison list (add if not present, remove if present)"""
        if unit in self.comparison_units:
            self.comparison_units.remove(unit)
        else:
            self.comparison_units.append(unit)
    
    def toggle_comparison_and_refresh(self, unit: UnitData):
        """Toggle unit in comparison list and update only the necessary UI elements"""
        self.toggle_comparison(unit)
        
        # Update the comparison button if it exists (in unit details view)
        is_in_comparison = unit in self.comparison_units
        compare_btn_text = "✓ In Comparison" if is_in_comparison else "+ Add to Comparison"
        compare_btn_color = "#00aa00" if is_in_comparison else DEFAULT_THEME["accent"]
        
        if hasattr(self, 'compare_btn') and self.compare_btn.winfo_exists():
            try:
                self.compare_btn.configure(
                    text=compare_btn_text,
                    bg=compare_btn_color
                )
            except tk.TclError:
                pass  # Ignore if widget is destroyed
        
        # Show brief notification
        action = "added to" if is_in_comparison else "removed from"
        # Create a temporary notification label
        notification = tk.Label(
            self.root,
            text=f"{unit.name} {action} comparison",
            bg=compare_btn_color,
            fg=DEFAULT_THEME["button_fg"],
            font=self.theme_manager.get_font(1),
            padx=10,
            pady=5,
            relief=tk.RAISED,
            borderwidth=1
        )
        
        # Position notification at the top center of the window
        notification.place(relx=0.5, rely=0.02, anchor=tk.CENTER)
        
        # Remove notification after 2 seconds
        self.root.after(2000, lambda: notification.destroy() if notification.winfo_exists() else None)
        
        # Update only the unit button that was clicked, not the entire page
        self.update_unit_button_visual(unit)
        
        # Update search results if currently showing search
        if hasattr(self, 'search_entry') and self.search_entry.winfo_exists():
            query = self.search_entry.get()
            if query:
                results = self.data_manager.search_units(query)
                self.display_search_results(results)
    
    def update_unit_button_visual(self, unit: UnitData):
        """Update only the visual appearance of a specific unit button"""
        # Find all unit buttons in the current view and update the one matching the unit
        def update_widgets(widget):
            try:
                if hasattr(widget, 'unit_data') and widget.unit_data == unit:
                    if hasattr(widget, 'update_appearance'):
                        widget.update_appearance()
                for child in widget.winfo_children():
                    update_widgets(child)
            except tk.TclError:
                # Widget has been destroyed, skip it
                pass
        
        # Update buttons in main content
        try:
            update_widgets(self.main_content)
        except tk.TclError:
            pass
        
        # Also update search results if visible
        if hasattr(self, 'search_results_frame'):
            try:
                update_widgets(self.search_results_frame)
            except tk.TclError:
                pass
    
    def show_comparison(self):
        """Show unit comparison view"""
        if len(self.comparison_units) == 0:
            self.clear_main_content()
            
            comparison_frame = tk.Frame(self.main_content, bg=DEFAULT_THEME["bg"])
            comparison_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            title = tk.Label(
                comparison_frame,
                text="Unit Comparison",
                bg=DEFAULT_THEME["bg"],
                fg=DEFAULT_THEME["fg"],
                font=self.theme_manager.get_font(4, "bold")
            )
            title.pack(pady=(0, 20))
            
            empty_label = tk.Label(
                comparison_frame,
                text="No units selected for comparison.\n\nAdd units using the + button next to unit names.",
                bg=DEFAULT_THEME["bg"],
                fg=DEFAULT_THEME["fg"],
                font=self.theme_manager.get_font(2),
                justify=tk.CENTER
            )
            empty_label.pack(pady=50)
            return
        
        # Store original window size if not in comparison view
        if not hasattr(self, '_original_window_size'):
            self._original_window_size = (self.root.winfo_width(), self.root.winfo_height())
        
        # Adjust window width based on number of units (minimum 1000, maximum 2000)
        window_width = min(2000, max(1000, 400 + len(self.comparison_units) * 300))
        self.root.geometry(f"{window_width}x{DEFAULT_WINDOW_SIZE[1]}")
        
        self.clear_main_content()
        
        # Create scrollable comparison area
        main_frame = tk.Frame(self.main_content, bg=DEFAULT_THEME["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title and controls frame
        title_frame = tk.Frame(main_frame, bg=DEFAULT_THEME["bg"])
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title = tk.Label(
            title_frame,
            text=f"Unit Comparison ({len(self.comparison_units)} units)",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(4, "bold")
        )
        title.pack(side=tk.LEFT)
        
        # Add help tip for comparison page (positioned lower to avoid blocking buttons)
        help_tip = HelpTip(
            main_frame,
            "Scroll horizontally to compare • Click property names to sync scroll • Use Remove button to exclude units",
            self.theme_manager,
            bg=DEFAULT_THEME["bg"]
        )
        help_tip.place(relx=1.0, rely=0.0, anchor=tk.NE, x=-10, y=50)
        
        # Control buttons
        controls_frame = tk.Frame(title_frame, bg=DEFAULT_THEME["bg"])
        controls_frame.pack(side=tk.RIGHT)
        
        # Clear all button
        clear_btn = tk.Button(
            controls_frame,
            text="Clear All",
            bg="#aa0000",
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(1),
            command=self.clear_comparison,
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=5
        )
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Back button
        back_btn = tk.Button(
            controls_frame,
            text="Back",
            bg=DEFAULT_THEME["button_bg"],
            fg=DEFAULT_THEME["button_fg"],
            font=self.theme_manager.get_font(1),
            command=self.show_factions,
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=5
        )
        back_btn.pack(side=tk.LEFT, padx=5)
        
        # Create scrollable area for comparison columns
        canvas = tk.Canvas(main_frame, bg=DEFAULT_THEME["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="horizontal", command=canvas.xview)
        scrollable_frame = tk.Frame(canvas, bg=DEFAULT_THEME["bg"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(xscrollcommand=scrollbar.set)
        
        # Enable mouse wheel scrolling for horizontal scroll with improved handling
        def _on_mousewheel(event):
            if canvas.xview() != (0.0, 1.0):
                canvas.xview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
        
        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            # Bind to child widgets
            for child in scrollable_frame.winfo_children():
                _bind_recursive_comp_h(child)
        
        def _bind_recursive_comp_h(widget):
            """Recursively bind mousewheel to all child widgets"""
            try:
                widget.bind("<MouseWheel>", _on_mousewheel)
                for child in widget.winfo_children():
                    _bind_recursive_comp_h(child)
            except:
                pass
        
        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)
        
        # Create comparison columns
        columns_frame = tk.Frame(scrollable_frame, bg=DEFAULT_THEME["bg"])
        columns_frame.pack(fill=tk.BOTH, expand=True)
        
        # Initialize list to store property canvases for synchronized scrolling
        property_canvases = []
        
        # Create properties for each unit
        for i, unit in enumerate(self.comparison_units):
            column_frame = tk.Frame(columns_frame, bg=DEFAULT_THEME["bg"])
            column_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
            
            # Unit header
            header_frame = tk.Frame(column_frame, bg=DEFAULT_THEME["select_bg"])
            header_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Unit icon - try multiple path variants
            icon_variants = [
                f"{unit.faction.replace(' ', '_')}/subfaction/{unit.subfaction}/{unit.category}/icons/{unit.icon_filename}",
                f"{unit.faction}/subfaction/{unit.subfaction}/{unit.category}/icons/{unit.icon_filename}",
                f"{unit.faction.replace(' ', '_')}/subfaction/{unit.subfaction.replace(' ', '_')}/{unit.category.replace(' ', '_')}/icons/{unit.icon_filename}",
                f"{unit.faction}/{unit.category}/icons/{unit.icon_filename}",
                f"{unit.faction.replace(' ', '_')}/{unit.category.replace(' ', '_')}/icons/{unit.icon_filename}"
            ]
            
            icon = None
            for icon_path in icon_variants:
                icon = self.icon_manager.get_icon(icon_path, (48, 48))
                if icon:
                    break
            
            if icon:
                icon_label = tk.Label(header_frame, image=icon, bg=DEFAULT_THEME["select_bg"])
                icon_label.image = icon  # Keep reference
                icon_label.pack(pady=5)
            
            # Unit name
            name_label = tk.Label(
                header_frame,
                text=unit.name,
                bg=DEFAULT_THEME["select_bg"],
                fg=DEFAULT_THEME["select_fg"],
                font=self.theme_manager.get_font(2, "bold")
            )
            name_label.pack()
            
            # Faction info
            faction_label = tk.Label(
                header_frame,
                text=f"{unit.faction}\n{unit.subfaction}",
                bg=DEFAULT_THEME["select_bg"],
                fg=DEFAULT_THEME["select_fg"],
                font=self.theme_manager.get_font(0)
            )
            faction_label.pack(pady=(0, 5))
            
            # Remove button
            remove_btn = tk.Button(
                header_frame,
                text="Remove",
                bg=DEFAULT_THEME["button_bg"],
                fg=DEFAULT_THEME["button_fg"],
                command=lambda u=unit: self.remove_from_comparison(u),
                bd=0,
                highlightthickness=0
            )
            remove_btn.pack(pady=5)
            
            # Properties
            prop_canvas = self.create_comparison_properties(column_frame, unit, property_canvases)
            property_canvases.append(prop_canvas)
        
        # Update all canvases with the complete list after creation
        for canvas_ref in property_canvases:
            canvas_ref.comparison_canvases = property_canvases
        
        canvas.pack(side="top", fill="both", expand=True)
        scrollbar.pack(side="bottom", fill="x")
    
    def create_comparison_properties(self, parent, unit: UnitData, comparison_canvases=None):
        """Create properties for comparison view and return the canvas"""
        props_frame = tk.LabelFrame(
            parent,
            text="Properties",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(1, "bold")
        )
        props_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollable frame
        canvas = tk.Canvas(props_frame, bg=DEFAULT_THEME["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(props_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=DEFAULT_THEME["bg"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Store reference to all property canvases for synchronized scrolling
        canvas.comparison_canvases = comparison_canvases if comparison_canvases is not None else []
        
        # Enable normal mouse wheel scrolling for vertical scroll (not synchronized) with improved handling
        def _on_mousewheel(event):
            print(f"DEBUG: Comparison Vertical MouseWheel - delta: {event.delta}, widget: {event.widget}")
            if canvas.yview() != (0.0, 1.0):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"  # Prevent default scrolling
        
        def _bind_to_mousewheel(event):
            print(f"DEBUG: Binding Comparison Vertical MouseWheel")
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            # Bind to child widgets
            for child in scrollable_frame.winfo_children():
                _bind_recursive_comp_v(child)
        
        def _bind_recursive_comp_v(widget):
            """Recursively bind mousewheel to all child widgets"""
            try:
                widget.bind("<MouseWheel>", _on_mousewheel)
                for child in widget.winfo_children():
                    _bind_recursive_comp_v(child)
            except:
                pass
        
        def _unbind_from_mousewheel(event):
            print(f"DEBUG: Unbinding Comparison Vertical MouseWheel")
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)
        
        # Store property labels and their frames for synchronized scrolling
        scrollable_frame.property_labels = {}
        scrollable_frame.property_frames = {}  # Store the frame for each property
        
        # Add properties with alternating colors
        for i, (key, value) in enumerate(unit.infobox_data.items()):
            if key.startswith("_section_"):
                continue
                
            # Alternating background color
            bg_color = DEFAULT_THEME["bg"] if i % 2 == 0 else "#252525"
            prop_frame = tk.Frame(scrollable_frame, bg=bg_color)
            prop_frame.pack(fill=tk.X, padx=5, pady=2)
            
            # Store the frame for this property
            scrollable_frame.property_frames[key.lower()] = prop_frame
            
            # Property name with same background as row
            name_label = tk.Label(
                prop_frame,
                text=f"{key}:",
                bg=bg_color,
                fg=DEFAULT_THEME["accent"],
                font=self.theme_manager.get_font(0, "bold"),
                anchor=tk.NW,
                width=15
            )
            name_label.pack(side=tk.LEFT, anchor=tk.NW)
            
            # Store reference to this property label for synchronized scrolling
            scrollable_frame.property_labels[key.lower()] = name_label
            
            # Add click event to synchronize scrolling
            def _on_property_click(event, prop_key=key.lower()):
                # Get the frame of the clicked property
                if prop_key in scrollable_frame.property_frames:
                    clicked_frame = scrollable_frame.property_frames[prop_key]
                    
                    # Scroll all other canvases to the same property
                    if hasattr(canvas, 'comparison_canvases'):
                        for col_canvas in canvas.comparison_canvases:
                            # Find the scrollable frame in this canvas
                            for widget in col_canvas.winfo_children():
                                if isinstance(widget, tk.Frame) and hasattr(widget, 'property_frames'):
                                    # Check if this property exists in this unit
                                    if prop_key in widget.property_frames:
                                        # Get the frame of this property in the other unit
                                        target_frame = widget.property_frames[prop_key]
                                        
                                        # Calculate the position to scroll to
                                        # Update first to ensure coordinates are correct
                                        widget.update_idletasks()
                                        target_y = target_frame.winfo_y()
                                        
                                        # Calculate scroll fraction
                                        scroll_region = col_canvas.bbox("all")
                                        if scroll_region:
                                            total_height = scroll_region[3]
                                            if total_height > 0:
                                                # Calculate the scroll position (0.0 to 1.0)
                                                scroll_fraction = target_y / total_height
                                                
                                                # Ensure the fraction is within valid range
                                                scroll_fraction = max(0.0, min(1.0, scroll_fraction))
                                                
                                                # Scroll to the property
                                                col_canvas.yview_moveto(scroll_fraction)
                                        break
            
            # Add hover effect to show property names are clickable
            def _on_enter(event):
                name_label.configure(cursor="hand2")
            
            def _on_leave(event):
                name_label.configure(cursor="")
            
            name_label.bind("<Button-1>", _on_property_click)
            name_label.bind("<Enter>", _on_enter)
            name_label.bind("<Leave>", _on_leave)
            
            # Property value with same background as row
            value_frame = tk.Frame(prop_frame, bg=bg_color)
            value_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            if isinstance(value, list):
                # Display list items with bullets
                for item in value:
                    item_label = tk.Label(
                        value_frame,
                        text=f"• {str(item)}",
                        bg=bg_color,
                        fg=DEFAULT_THEME["fg"],
                        font=self.theme_manager.get_font(0),
                        anchor=tk.W,
                        wraplength=200,
                        justify=tk.LEFT
                    )
                    item_label.pack(anchor=tk.W, pady=1)
            else:
                # Handle string values
                value_text = str(value)
                value_label = tk.Label(
                    value_frame,
                    text=value_text,
                    bg=bg_color,
                    fg=DEFAULT_THEME["fg"],
                    font=self.theme_manager.get_font(0),
                    anchor=tk.NW,
                    wraplength=200,
                    justify=tk.LEFT
                )
                value_label.pack(anchor=tk.W)
        
        # Add article tables at the end if any
        if unit.article_tables:
            self._add_comparison_article_tables(scrollable_frame, unit.article_tables)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Return the canvas for synchronized scrolling
        return canvas
    
    def _add_comparison_article_tables(self, parent, article_tables: List[Dict]):
        """Add article tables to comparison view"""
        for table_index, table in enumerate(article_tables):
            # Add separator line before each table
            if table_index > 0:
                separator_frame = tk.Frame(parent, bg=DEFAULT_THEME["bg"], height=2)
                separator_frame.pack(fill=tk.X, padx=5, pady=5)
                
                separator_line = tk.Frame(separator_frame, bg=DEFAULT_THEME["border"], height=1)
                separator_line.pack(fill=tk.X, pady=1)
            
            # Table title
            table_title = table.get("title", f"Table {table_index + 1}")
            title_label = tk.Label(
                parent,
                text=f"• {table_title}:",
                bg=DEFAULT_THEME["bg"],
                fg=DEFAULT_THEME["accent"],
                font=self.theme_manager.get_font(0, "bold"),
                anchor=tk.W,
                pady=5
            )
            title_label.pack(fill=tk.X, padx=5, anchor=tk.W)
            
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            
            if not headers or not rows:
                # Show message if table is empty
                empty_label = tk.Label(
                    parent,
                    text="  No data available",
                    bg=DEFAULT_THEME["bg"],
                    fg=DEFAULT_THEME["fg"],
                    font=self.theme_manager.get_font(0),
                    anchor=tk.W,
                    pady=2
                )
                empty_label.pack(fill=tk.X, padx=10, anchor=tk.W)
                continue
            
            # Create a compact table container for comparison
            table_container = tk.Frame(parent, bg=DEFAULT_THEME["bg"])
            table_container.pack(fill=tk.X, padx=5, pady=2)
            
            # Create table headers
            header_row = tk.Frame(table_container, bg=DEFAULT_THEME["select_bg"])
            header_row.pack(fill=tk.X)
            
            for i, header in enumerate(headers):
                header_label = tk.Label(
                    header_row,
                    text=header,
                    bg=DEFAULT_THEME["select_bg"],
                    fg=DEFAULT_THEME["select_fg"],
                    font=self.theme_manager.get_font(0, "bold"),
                    anchor=tk.W,
                    padx=3,
                    pady=2
                )
                header_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
            
            # Create table rows with alternating colors
            for row_index, row in enumerate(rows):
                bg_color = DEFAULT_THEME["bg"] if row_index % 2 == 0 else "#252525"
                row_frame = tk.Frame(table_container, bg=bg_color)
                row_frame.pack(fill=tk.X)
                
                for i, cell in enumerate(row):
                    cell_text = str(cell)
                    
                    # Handle long text in comparison view
                    if len(cell_text) > 30:
                        cell_text = cell_text[:27] + "..."
                    
                    cell_label = tk.Label(
                        row_frame,
                        text=cell_text,
                        bg=bg_color,
                        fg=DEFAULT_THEME["fg"],
                        font=self.theme_manager.get_font(0),
                        anchor=tk.W,
                        padx=3,
                        pady=1
                    )
                    cell_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
    
    def clear_comparison(self):
        """Clear all units from comparison list"""
        self.comparison_units.clear()
        # Reset window to default size when clearing comparison (with UI scaling)
        ui_scale = self.theme_manager.custom_settings.get("ui_scale", 1.0)
        scaled_width = int(DEFAULT_WINDOW_SIZE[0] * ui_scale)
        scaled_height = int(DEFAULT_WINDOW_SIZE[1] * ui_scale)
        self.root.geometry(f"{scaled_width}x{scaled_height}")
        self.show_comparison()  # Refresh comparison view
    
    def remove_from_comparison(self, unit: UnitData):
        """Remove unit from comparison list"""
        if unit in self.comparison_units:
            self.comparison_units.remove(unit)
            # Adjust window size based on remaining units (with UI scaling)
            ui_scale = self.theme_manager.custom_settings.get("ui_scale", 1.0)
            if len(self.comparison_units) == 0:
                scaled_width = int(DEFAULT_WINDOW_SIZE[0] * ui_scale)
                scaled_height = int(DEFAULT_WINDOW_SIZE[1] * ui_scale)
                self.root.geometry(f"{scaled_width}x{scaled_height}")
            else:
                base_width = min(2000, max(1000, 400 + len(self.comparison_units) * 300))
                scaled_width = int(base_width * ui_scale)
                scaled_height = int(DEFAULT_WINDOW_SIZE[1] * ui_scale)
                self.root.geometry(f"{scaled_width}x{scaled_height}")
            self.show_comparison()  # Refresh comparison view
    
    def show_settings(self):
        """Show settings dialog"""
        self.clear_main_content()
        
        # Create scrollable area for settings
        canvas = tk.Canvas(self.main_content, bg=DEFAULT_THEME["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.main_content, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=DEFAULT_THEME["bg"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            if canvas.yview() != (0.0, 1.0):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
        
        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            for child in scrollable_frame.winfo_children():
                _bind_recursive(child)
        
        def _bind_recursive(widget):
            try:
                widget.bind("<MouseWheel>", _on_mousewheel)
                for child in widget.winfo_children():
                    _bind_recursive(child)
            except:
                pass
        
        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)
        
        settings_frame = tk.Frame(scrollable_frame, bg=DEFAULT_THEME["bg"])
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title = tk.Label(
            settings_frame,
            text="Settings",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(4, "bold")
        )
        title.pack(pady=(0, 20))
        
        # Appearance settings
        appearance_frame = tk.LabelFrame(
            settings_frame,
            text="Appearance",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(2, "bold")
        )
        appearance_frame.pack(fill=tk.X, pady=10)
        
        # Opacity setting
        opacity_frame = tk.Frame(appearance_frame, bg=DEFAULT_THEME["bg"])
        opacity_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            opacity_frame,
            text="Window Opacity:",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(1)
        ).pack(side=tk.LEFT)
        
        self.opacity_var = tk.DoubleVar(value=self.theme_manager.custom_settings["opacity"])
        opacity_scale = tk.Scale(
            opacity_frame,
            from_=0.3,
            to=1.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.opacity_var,
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            highlightthickness=0
        )
        opacity_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        # UI Scaling settings frame
        ui_scaling_frame = tk.LabelFrame(
            settings_frame,
            text="UI Scaling",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(2, "bold")
        )
        ui_scaling_frame.pack(fill=tk.X, pady=10)
        
        # UI Scale setting
        ui_scale_frame = tk.Frame(ui_scaling_frame, bg=DEFAULT_THEME["bg"])
        ui_scale_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            ui_scale_frame,
            text="UI Scale:",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(1)
        ).pack(side=tk.LEFT)
        
        self.ui_scale_var = tk.DoubleVar(value=self.theme_manager.custom_settings.get("ui_scale", 1.0))
        ui_scale_scale = tk.Scale(
            ui_scale_frame,
            from_=0.5,
            to=2.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.ui_scale_var,
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            highlightthickness=0,
            command=lambda v: self.update_ui_scale_preview()
        )
        ui_scale_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        self.ui_scale_label = tk.Label(
            ui_scale_frame,
            text=f"{self.ui_scale_var.get():.1f}x",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["accent"],
            font=self.theme_manager.get_font(1),
            width=5
        )
        self.ui_scale_label.pack(side=tk.LEFT)
        
        # Font size setting
        font_frame = tk.Frame(ui_scaling_frame, bg=DEFAULT_THEME["bg"])
        font_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            font_frame,
            text="Font Size:",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(1)
        ).pack(side=tk.LEFT)
        
        self.font_size_var = tk.IntVar(value=self.theme_manager.custom_settings["font_size"])
        font_spinbox = tk.Spinbox(
            font_frame,
            from_=8,
            to=16,
            textvariable=self.font_size_var,
            bg=DEFAULT_THEME["button_bg"],
            fg=DEFAULT_THEME["fg"],
            width=10
        )
        font_spinbox.pack(side=tk.LEFT, padx=10)
        
        # Bold text toggle
        bold_frame = tk.Frame(ui_scaling_frame, bg=DEFAULT_THEME["bg"])
        bold_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            bold_frame,
            text="Bold Text:",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(1)
        ).pack(side=tk.LEFT)
        
        self.bold_text_var = tk.BooleanVar(value=self.theme_manager.custom_settings.get("bold_text", False))
        bold_check = tk.Checkbutton(
            bold_frame,
            variable=self.bold_text_var,
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            selectcolor=DEFAULT_THEME["select_bg"],
            activebackground=DEFAULT_THEME["bg"],
            activeforeground=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(1)
        )
        bold_check.pack(side=tk.LEFT, padx=10)
        
        # Image scaling settings frame
        image_scaling_frame = tk.LabelFrame(
            settings_frame,
            text="Image Scaling",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(2, "bold")
        )
        image_scaling_frame.pack(fill=tk.X, pady=10)
        
        # Icon scale setting
        icon_frame = tk.Frame(image_scaling_frame, bg=DEFAULT_THEME["bg"])
        icon_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            icon_frame,
            text="Unit Icon Scale:",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(1)
        ).pack(side=tk.LEFT)
        
        self.icon_scale_var = tk.DoubleVar(value=self.theme_manager.custom_settings["icon_scale"])
        icon_scale = tk.Scale(
            icon_frame,
            from_=0.5,
            to=2.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.icon_scale_var,
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            highlightthickness=0,
            command=lambda v: self.update_icon_scale_preview()
        )
        icon_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        self.icon_scale_label = tk.Label(
            icon_frame,
            text=f"{self.icon_scale_var.get():.1f}x",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["accent"],
            font=self.theme_manager.get_font(1),
            width=5
        )
        self.icon_scale_label.pack(side=tk.LEFT)
        
        # UI size settings frame
        ui_size_frame = tk.LabelFrame(
            settings_frame,
            text="UI Size",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(2, "bold")
        )
        ui_size_frame.pack(fill=tk.X, pady=10)
        
        # Window width setting
        width_frame = tk.Frame(ui_size_frame, bg=DEFAULT_THEME["bg"])
        width_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            width_frame,
            text="Window Width:",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(1)
        ).pack(side=tk.LEFT)
        
        self.window_width_var = tk.IntVar(value=self.theme_manager.custom_settings.get("window_width", DEFAULT_WINDOW_SIZE[0]))
        width_spinbox = tk.Spinbox(
            width_frame,
            from_=800,
            to=2560,
            textvariable=self.window_width_var,
            bg=DEFAULT_THEME["button_bg"],
            fg=DEFAULT_THEME["fg"],
            width=10
        )
        width_spinbox.pack(side=tk.LEFT, padx=10)
        
        # Window height setting
        height_frame = tk.Frame(ui_size_frame, bg=DEFAULT_THEME["bg"])
        height_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            height_frame,
            text="Window Height:",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(1)
        ).pack(side=tk.LEFT)
        
        self.window_height_var = tk.IntVar(value=self.theme_manager.custom_settings.get("window_height", DEFAULT_WINDOW_SIZE[1]))
        height_spinbox = tk.Spinbox(
            height_frame,
            from_=600,
            to=1440,
            textvariable=self.window_height_var,
            bg=DEFAULT_THEME["button_bg"],
            fg=DEFAULT_THEME["fg"],
            width=10
        )
        height_spinbox.pack(side=tk.LEFT, padx=10)
        
        # Apply size button
        apply_size_btn = tk.Button(
            ui_size_frame,
            text="Apply Window Size",
            bg=DEFAULT_THEME["accent"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(1),
            command=self.apply_window_size,
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=5
        )
        apply_size_btn.pack(pady=10)
        
        # Buttons
        button_frame = tk.Frame(settings_frame, bg=DEFAULT_THEME["bg"])
        button_frame.pack(pady=20)
        
        save_btn = tk.Button(
            button_frame,
            text="Save Settings",
            bg=DEFAULT_THEME["accent"],
            fg=DEFAULT_THEME["fg"],
            font=self.theme_manager.get_font(1),
            command=self.save_settings,
            bd=0,
            highlightthickness=0,
            padx=20,
            pady=5
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        reset_btn = tk.Button(
            button_frame,
            text="Reset to Defaults",
            bg=DEFAULT_THEME["button_bg"],
            fg=DEFAULT_THEME["button_fg"],
            font=self.theme_manager.get_font(1),
            command=self.reset_settings,
            bd=0,
            highlightthickness=0,
            padx=20,
            pady=5
        )
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        # Back button
        back_btn = tk.Button(
            button_frame,
            text="Back",
            bg=DEFAULT_THEME["button_bg"],
            fg=DEFAULT_THEME["button_fg"],
            font=self.theme_manager.get_font(1),
            command=self.show_factions,
            bd=0,
            highlightthickness=0,
            padx=20,
            pady=5
        )
        back_btn.pack(side=tk.LEFT, padx=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def apply_window_size(self):
        """Apply window size settings with UI scaling"""
        # Get base window size from settings
        base_width = self.window_width_var.get()
        base_height = self.window_height_var.get()
        
        # Apply UI scaling
        ui_scale = self.theme_manager.custom_settings.get("ui_scale", 1.0)
        scaled_width = int(base_width * ui_scale)
        scaled_height = int(base_height * ui_scale)
        
        # Apply scaled size to window
        self.root.geometry(f"{scaled_width}x{scaled_height}")
        
        # Update default window size for future reference (base size, not scaled)
        global DEFAULT_WINDOW_SIZE
        DEFAULT_WINDOW_SIZE = (base_width, base_height)
        
        print(f"Window size changed to {scaled_width}x{scaled_height} (base: {base_width}x{base_height}, scale: {ui_scale})")
    
    def update_ui_scale_preview(self):
        """Update the UI scale preview label"""
        self.ui_scale_label.configure(text=f"{self.ui_scale_var.get():.1f}x")
    
    def update_icon_scale_preview(self):
        """Update the icon scale preview label"""
        self.icon_scale_label.configure(text=f"{self.icon_scale_var.get():.1f}x")
    
    def save_settings(self):
        """Save settings and apply them"""
        self.theme_manager.custom_settings["opacity"] = self.opacity_var.get()
        self.theme_manager.custom_settings["font_size"] = self.font_size_var.get()
        self.theme_manager.custom_settings["icon_scale"] = self.icon_scale_var.get()
        self.theme_manager.custom_settings["ui_scale"] = self.ui_scale_var.get()
        self.theme_manager.custom_settings["bold_text"] = self.bold_text_var.get()
        self.theme_manager.custom_settings["window_width"] = self.window_width_var.get()
        self.theme_manager.custom_settings["window_height"] = self.window_height_var.get()
        
        # Clear icon cache to apply new icon scale
        self.icon_manager.icon_cache.clear()
        
        self.theme_manager.save_settings()
        self.apply_theme()
        self.refresh_current_view()
        
        messagebox.showinfo("Settings", "Settings saved successfully!")
        self.show_factions()
    
    def reset_settings(self):
        """Reset settings to defaults"""
        self.theme_manager.custom_settings = {
            "opacity": 0.9,
            "font_family": "Segoe UI",
            "font_size": 10,
            "font_weight": "normal",
            "icon_scale": 1.0,
            "ui_scale": 1.0,
            "bold_text": False,
            "window_width": DEFAULT_WINDOW_SIZE[0],
            "window_height": DEFAULT_WINDOW_SIZE[1]
        }
        
        # Clear icon cache
        self.icon_manager.icon_cache.clear()
        
        # Reset window size
        self.root.geometry(f"{DEFAULT_WINDOW_SIZE[0]}x{DEFAULT_WINDOW_SIZE[1]}")
        
        self.theme_manager.save_settings()
        self.apply_theme()
        self.refresh_current_view()
        
        messagebox.showinfo("Settings", "Settings reset to defaults!")
        self.show_factions()
    
    def refresh_current_view(self):
        """Refresh the current view to apply new settings"""
        # Store current view state
        if self.current_faction:
            faction = self.current_faction
            self.show_faction_units(faction)
        elif hasattr(self, 'search_entry') and self.search_entry.winfo_exists():
            query = self.search_entry.get()
            self.on_search(None)
        elif self.comparison_units:
            self.show_comparison()
        else:
            self.show_factions()
    
    def on_close(self):
        """Handle window close"""
        self.theme_manager.save_settings()
        self.root.quit()
        self.root.destroy()
    
    def on_collapse(self, is_collapsed: bool):
        """Handle window collapse/expand"""
        if is_collapsed:
            # Store current size before collapsing
            if not hasattr(self, '_expanded_size'):
                self._expanded_size = (self.root.winfo_width(), self.root.winfo_height())
            
            # Temporarily remove minimum size constraint to allow collapsing
            self.root.minsize(200, 30)
            
            # Hide the main container completely
            self.main_container.pack_forget()
            
            # Create a minimal collapsed container that fills the entire window
            self.collapsed_container = tk.Frame(self.root, bg=DEFAULT_THEME["title_bg"])
            self.collapsed_container.pack(fill=tk.BOTH, expand=True)
            
            # Create custom title bar for collapsed state
            collapsed_titlebar = tk.Frame(self.collapsed_container, bg=DEFAULT_THEME["title_bg"], height=30)
            collapsed_titlebar.pack(fill=tk.BOTH, expand=True)
            collapsed_titlebar.pack_propagate(False)
            
            # Add a draggable area that fills the entire collapsed toolbar
            drag_area = tk.Frame(collapsed_titlebar, bg=DEFAULT_THEME["title_bg"])
            drag_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Make the drag area draggable
            self._collapsed_start_x = 0
            self._collapsed_start_y = 0
            
            def collapsed_start_drag(event):
                self._collapsed_start_x = event.x_root
                self._collapsed_start_y = event.y_root
            
            def collapsed_on_drag(event):
                x = self.root.winfo_x() + (event.x_root - self._collapsed_start_x)
                y = self.root.winfo_y() + (event.y_root - self._collapsed_start_y)
                self.root.geometry(f"+{x}+{y}")
                self._collapsed_start_x = event.x_root
                self._collapsed_start_y = event.y_root
            
            drag_area.bind("<Button-1>", collapsed_start_drag)
            drag_area.bind("<B1-Motion>", collapsed_on_drag)
            
            # Button frame
            btn_frame = tk.Frame(collapsed_titlebar, bg=DEFAULT_THEME["title_bg"])
            btn_frame.pack(side=tk.RIGHT, padx=5, pady=2)
            
            # Expand button - call on_collapse directly instead of toggle_collapse
            expand_btn = tk.Button(
                btn_frame,
                text="□",
                bg=DEFAULT_THEME["button_bg"],
                fg=DEFAULT_THEME["button_fg"],
                width=3,
                height=1,
                command=lambda: self.on_collapse(False),
                bd=0,
                highlightthickness=0
            )
            expand_btn.pack(side=tk.LEFT, padx=2)
            
            # Close button
            close_btn = tk.Button(
                btn_frame,
                text="✕",
                bg=DEFAULT_THEME["button_bg"],
                fg=DEFAULT_THEME["button_fg"],
                width=3,
                height=1,
                command=self.on_close,
                bd=0,
                highlightthickness=0
            )
            close_btn.pack(side=tk.LEFT, padx=2)
            
            # Get current position
            current_x = self.root.winfo_x()
            current_y = self.root.winfo_y()
            
            # Resize window to minimal - set both size and position
            self.root.geometry(f"200x30+{current_x}+{current_y}")
            
            # Force update to ensure the window is resized properly
            self.root.update_idletasks()
            
        else:
            # Remove collapsed container if it exists
            if hasattr(self, 'collapsed_container') and self.collapsed_container:
                self.collapsed_container.destroy()
                self.collapsed_container = None
            
            # Restore main container
            self.main_container.pack(fill=tk.BOTH, expand=True)
            
            # Restore minimum size constraint
            self.root.minsize(*MIN_WINDOW_SIZE)
            
            # Get current position
            current_x = self.root.winfo_x()
            current_y = self.root.winfo_y()
            
            # Restore previous size
            if hasattr(self, '_expanded_size') and self._expanded_size:
                self.root.geometry(f"{self._expanded_size[0]}x{self._expanded_size[1]}+{current_x}+{current_y}")
            else:
                self.root.geometry(f"{DEFAULT_WINDOW_SIZE[0]}x{DEFAULT_WINDOW_SIZE[1]}+{current_x}+{current_y}")
            
            # Update the title bar state to match
            self.title_bar.is_collapsed = False
            self.title_bar.collapse_btn.configure(text="─")
            
            # Force update to ensure the window is resized properly
            self.root.update_idletasks()
    
    def start_drag(self, event):
        """Start dragging the window"""
        self.title_bar.start_x = event.x_root
        self.title_bar.start_y = event.y_root
    
    def on_drag(self, event):
        """Handle window dragging"""
        x = self.root.winfo_x() + (event.x_root - self.title_bar.start_x)
        y = self.root.winfo_y() + (event.y_root - self.title_bar.start_y)
        self.root.geometry(f"+{x}+{y}")
        self.title_bar.start_x = event.x_root
        self.title_bar.start_y = event.y_root
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    try:
        app = MentalOmegaArsenal()
        app.run()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start application: {e}")
        sys.exit(1)