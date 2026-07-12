UX buttons and table background patch
=====================================

Changed:
- Normal match result button now says "New Match" / "Новый бой" instead of a vague retry label.
- Story matches no longer show a misleading immediate retry button on the generic result screen.
- Story result screen now uses "Continue" / "Продолжить" to move to the story result.
- Story win screen now gives meaningful choices: "Map" / "К карте" or "Next stage" / "Следующий этап".
- Story loss screen now gives meaningful choices: "Rematch" / "Реванш" or "Map" / "К карте". The rematch button really starts the same stage again.
- Added a custom table background hook:
  `assets/background/game_table.png`
- Added a placeholder `game_table.png` and README. Replace it later with your final table artwork using the same filename.

Main file changed:
- main.py
