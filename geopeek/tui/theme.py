"""Geopeek TUI theme — Catppuccin Mocha inspired palette."""

from __future__ import annotations

from textual.design import ColorSystem


# Catppuccin Mocha palette
CATPPUCCIN_MOCHA = {
    "rosewater": "#f5e0dc",
    "flamingo": "#f2cdcd",
    "pink": "#f5c2e7",
    "mauve": "#cba6f7",
    "red": "#f38ba8",
    "maroon": "#eba0ac",
    "peach": "#fab387",
    "yellow": "#f9e2af",
    "green": "#a6e3a1",
    "teal": "#94e2d5",
    "sky": "#89dceb",
    "sapphire": "#74c7ec",
    "blue": "#89b4fa",
    "lavender": "#b4befe",
    "text": "#cdd6f4",
    "subtext1": "#bac2de",
    "subtext0": "#a6adc8",
    "overlay2": "#9399b2",
    "overlay1": "#7f849c",
    "overlay0": "#6c7086",
    "surface2": "#585b70",
    "surface1": "#45475a",
    "surface0": "#313244",
    "base": "#1e1e2e",
    "mantle": "#181825",
    "crust": "#11111b",
}

GEOPEEK_THEME = ColorSystem(
    primary=CATPPUCCIN_MOCHA["blue"],
    secondary=CATPPUCCIN_MOCHA["mauve"],
    warning=CATPPUCCIN_MOCHA["yellow"],
    error=CATPPUCCIN_MOCHA["red"],
    success=CATPPUCCIN_MOCHA["green"],
    accent=CATPPUCCIN_MOCHA["teal"],
    foreground=CATPPUCCIN_MOCHA["text"],
    background=CATPPUCCIN_MOCHA["base"],
    surface=CATPPUCCIN_MOCHA["surface0"],
    panel=CATPPUCCIN_MOCHA["mantle"],
    boost=CATPPUCCIN_MOCHA["surface1"],
    dark=True,
    luminosity_spread=0.15,
    text_alpha=0.95,
    variables={
        "block-cursor-background": CATPPUCCIN_MOCHA["teal"],
        "block-cursor-foreground": CATPPUCCIN_MOCHA["base"],
        "footer-key-foreground": CATPPUCCIN_MOCHA["teal"],
        "input-selection-background": f"{CATPPUCCIN_MOCHA['blue']} 35%",
        "border": CATPPUCCIN_MOCHA["surface1"],
        "border-blurred": CATPPUCCIN_MOCHA["surface0"],
        "scrollbar": f"{CATPPUCCIN_MOCHA['overlay0']} 40%",
        "scrollbar-hover": f"{CATPPUCCIN_MOCHA['overlay1']} 70%",
        "scrollbar-background": CATPPUCCIN_MOCHA["mantle"],
    },
)
