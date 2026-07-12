Table UI Cleanup Patch
======================

What changed:
- removed the heavy black/green match panels from the game table screen;
- kept the table background visible as the main play surface;
- replaced large route panels with very subtle dashed route guides;
- moved route scores to side badges:
  - bot route scores on the left side;
  - player route scores on the right side;
- removed extra top HUD clutter from the table screen:
  - no deck/discard text blocks;
  - no big W/L/D line;
  - no section headers like "Bot routes" / "Your routes" / "Your hand";
- kept only small useful chips:
  - phase + difficulty;
  - match time;
  - pause button;
  - temporary bot/threat messages if needed;
- kept the hand area clean: only cards are shown.

Background asset:
- assets/background/game_table.png is still the table background placeholder.
- Later you can replace this file with your final generated table background using the same filename.
- The code will automatically use the new image.

Main file changed:
- main.py
