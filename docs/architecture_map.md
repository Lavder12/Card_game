# Architecture Map

This document maps out the internal structure of the codebase to help developers and AI agents quickly locate relevant sections.

### High-Level Structure

**1. Root Directory**
* `main.py`: The entry point. Imports and initializes the application from `src`.
* `data/`: Contains all JSON save and configuration files (`settings.json`, `deck.json`, `stats.json`, `history.json`, `achievements.json`, `tutorial.json`).
* `docs/`: Project documentation and architecture maps.
  * `patches/`: Historical UI and feature patch notes.
* `assets/`: Image resources (cards, backgrounds, menu tiles).
* `music/`: Audio files.
* `story/`: Contains `stages.json` defining the campaign configuration.
* `tools/`: Utility scripts (e.g. `search_model_snapshots.py`).
* `logs/`: Application logs.

**2. Source Code (`src/` module)**

* **`config.py`**: Constants (colors, dimensions), settings management (`Settings` class), localization dictionaries (`STRINGS`), path routing (`wpath`, `rpath`), and statistics tracking (`Stats`, `MatchRecord`).
* **`state.py`**: Global state variables (screen, clock, language, loaded fonts, sounds).
* **`models.py`**: Game logic abstractions. Defines `Card`, `NumEntry`, `Caravan`, `PlayerState`, `BotPersonality`. Also includes the deck rules engine (`can_play_number_on_caravan`, `play_number`, `check_game_end`).
* **`bot.py`**: Bot AI decision engine. Evaluates board positions (`heuristic`), manages Minimax search (`bot_choose_move`), and executes turns (`bot_take_turn`).
* **`audio.py`**: Audio abstraction. `SoundManager` class for sound effects and music channels.
* **`particles.py`**: Visual effects. `ParticleSystem` for confetti, sparks, and screen shakes.
* **`network.py`**: Multiplayer implementation. Contains `NetworkManager` for LAN/Hamachi, lobby screen logic, and match event synchronization.
* **`ui.py`**: Graphics and UI primitives. Contains background loaders, `CardAnimation`, `CardArt` drawing, and standard UI elements (buttons, sliders). Also contains `draw_board()` which coordinates the rendering of the play table.
* **`screens.py`**: Game flow and view logic. Contains secondary menus (pause, settings, stats), the `main_menu()`, the core match orchestrator `run_match()`, the Dustway campaign loop, and the tutorial system (`run_tutorial()`).
* **`achievements.py`**: Logic for loading, triggering, and drawing achievement popups.
