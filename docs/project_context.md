# Project Context & Environment Notes (Caravan Card Game)

> [!NOTE]
> This file is a persistent context memory for AI assistants (like Antigravity) to instantly understand the environment and project structure in future conversations.

## 1. Environment & Setup Details
* **Operating System**: Windows
* **Python Version**: `3.14.5` (very new, standard `pygame` wheels are not available and building from source fails).
* **Game Engine**: **Pygame Community Edition (`pygame-ce`)** version `2.5.7` is installed and verified working.
  * *Do not attempt to install the legacy `pygame` package, as it will trigger compilation errors on Python 3.14. `pygame-ce` is 100% backwards-compatible.*
* **Run Command**: 
  ```bash
  python main.py
  ```

## 2. Project Architecture & Structure
The game is a fully featured, high-fidelity clone of **Caravan** (the card game from *Fallout: New Vegas*).
The codebase is modularized under the `src/` directory.

* **`main.py`**: The entry point. It imports the app orchestrator from `src`.
* **`src/`**: Contains core modules:
  * `config.py` / `state.py`: Constants, localization dictionary (`STRINGS`), user settings, global app state.
  * `models.py`: Game logic, `PlayerState`, `Caravan`, `Card`, deck rules engine, Bot Personalities.
  * `screens.py`: UI views, menu loops, and the main `run_match()` orchestrator. Includes the 4 Main Game Modes (vs Bot, Story Mode, vs Player, Tutorial).
  * `ui.py` / `particles.py` / `audio.py`: Rendering routines, animations, effects, audio manager.
  * `bot.py` / `network.py` / `achievements.py`: AI, multiplayer logic (Firebase REST), achievement triggers.
* **`assets/`**: Card assets, character icons, menu tiles, and background table graphics.
* **`music/`**: Background music files (e.g. `music.mp3`).
* **`story/`**: Contains `stages.json` defining the Dustway campaign configurations.
* **Data (Saves & Settings)**: Runtime save and config files are now safely stored in the OS AppData folder (`%APPDATA%/Dustway` on Windows, `~/.config/Dustway` on Linux/Mac) to prevent loss on reinstall:
  * `settings.json`, `deck.json`, `stats.json`, `history.json`, `achievements.json`, `tutorial.json`.
* **`docs/`**: Documentation (`project_context.md`), feature proposals (`improvement_ideas.md`), architecture maps, and historical patch notes (in `patches/`).
* **`tools/`** and **`logs/`**: Utility scripts and application logs.

## 3. Main Menu Design
* Features **4 large tile cards** (vs Bot, Story Mode, vs Player, Tutorial) with custom illustrated card overlays loaded from `assets/menu_tiles/` (`bot.png`, `campaign.png`, `network.png`, `tutorial.png`), with rich hover effects and gradients.
* **Standard Tile Dimensions**: All main menu tiles are standardized to **877x1303** pixels. This includes a 10-pixel transparent padding around the central card art to allow the game's dynamic CSS-like borders and glow effects to show through.
* Bottom bar of small utility buttons (Settings, Deck, Stats, Achievements, History, Quit).
* Dynamically scales and draws the custom background loaded from `assets/background/main_menu.png`.
* All sizing is proportional to WIDTH/HEIGHT.

## 4. Story Mode & Campaign ("Dustway" / "Пыльный тракт")
* 9 stages in sequence: Beetle (Жук) ➔ Mira (Мира) ➔ Torm (Торм) ➔ Nika (Ника) ➔ Velt (Вельт) ➔ Orren (Оррен) ➔ Rowen (Ровен) ➔ Green (Грин) ➔ Fang (Клык).
* Stage definitions, dialogue, and reward/rules conditions are stored in `story/stages.json`.
* Uses a dedicated `campaign_map_screen` showing stage progression as a visual, interactive map (`history_map.jpeg`).
  * Features authentic UI markers: animated red pushpins for the active stage, penciled "X" marks for completed stages, and dashed travel lines showing the caravan route.
  * Information tooltips are drawn to look like old parchment/paper.
* On victory, rewards are calculated and written to progress, prompting "Continue" ➔ "Map" or "Next Stage".
* On defeat, prompts the player with "Rematch" (instantly replays the same stage) or "Map" (returns to map).

## 5. Tutorial System
* 15 progressive levels stored in `TUTORIAL_LEVELS` list.
* Level types: `info` (explanation dialogues), `play` (simplified matches), `full_match` (standard gameplay).
* Levels unlock sequentially; progress is saved in `tutorial.json`.
* Key screens: `tutorial_level_select()`, `_tutorial_info_screen()`, `_tutorial_result_screen()`, `run_tutorial()`.

## 6. Table & Board UI Polish
* **Table Background**: Uses a custom asset hook loaded from `assets/background/game_table.png`.
* **Clean Layout**: Removed heavy black/green panels and section headers. Replaced with subtle dashed route guidelines, ensuring cards are clearly visible over the table background.
* **Score Badges**: Moved to the sides (Bot route scores on the left; Player route scores on the right) and positioned vertically above (player) or below (bot) stacks to prevent overlapping with cards.
* **Large Cards**: Card dimensions on the board and hand area are enlarged. The hand area is expanded to fit bigger cards comfortably.
* **Regular click targeting**: Playing a number card can be done by clicking anywhere in the target caravan column. Face cards (J, Q, K, Joker) still target specific cards.
* **Card Deal Animation**: Animation starts from the player's hand area instead of flying from the top bot area.
* **Bot Delay**: Bot moves are executed after a slight delayed pause (`get_bot_delay_ms`) to simulate thinking rather than instant plays.

## 7. Settings Screen Polish
* Redesigned settings panel into a "worn metal/cloth panel" style.
* Stacked options vertically to avoid text overlap in Russian/English localization.
* Grouped settings into: Sound, Game, Screen, Profile.
* Volume sliders include percentage readings.
* Card back selector is removed from the settings screen (deck customization handles card visual choices).

## 8. Multiplayer & Networking (Firebase)
* **Architecture**: The game uses a global matchmaking system powered by a Google Firebase Realtime Database (`FIREBASE_URL`).
* **Connection**: Instead of heavy libraries, it uses Python's built-in `urllib.request` to execute REST API calls (`GET`, `PUT`, `PATCH`).
* **Matchmaking Loop**:
  * `NetworkManager` queries the `/lobbies` node.
  * If a "waiting" lobby is found, the user connects as a Client. If not, they generate a lobby and wait as the Host.
  * A background `_threading.Thread` polls the DB every 0.5s to sync game states.
* **Private Rooms (Room Codes)**:
  * Players can create "Private" lobbies, which generates a 4-digit code (e.g., `4815`).
  * Private lobbies are ignored by the standard "Find Random Match" search.
  * Friends can join via the "Join via Code" UI element using keyboard input.
* **Friend System**:
  * Each player is automatically assigned a unique 6-character `friend_code` on startup.
  * `main.py` silently calls `sync_profile()` to sync their name and avatar to Firebase under `/users/<friend_code>`.
  * In the profile screen, users can view their friend code, enter a friend's code to add them, and view their friends list (with names and avatars dynamically fetched via background thread).
* **Error Handling**: The polling loop safely handles missing arrays (Firebase optimization) and network timeouts without disconnecting the user.

## 9. Developer / Running Tips
* If sound or music fails to load, the game has internal exception handling (`AUDIO_OK` checks) and runs in silent mode.
* UI coordinates in `draw_board` top bar and layout elements use proportional offsets (`tw * 0.17` etc.) for resolution-independent scaling.
* Non-game screens automatically use the main menu background, while the gameplay screen uses the table background.

## 10. Video Intro System
* **Implementation**: The game plays a cinematic MP4 intro (`src/intro.py`) immediately on launch.
* **Tech Stack**: Uses `opencv-python` (`cv2`) for fast frame decoding/resizing (C-optimized `cv2.resize`), and `pygame.mixer` for concurrent audio playback.
* **A/V Sync**: High-resolution video (e.g. 1440p 60FPS) causes Python rendering delays. To fix this, the main loop uses real-time elapsed checking (`pygame.time.get_ticks()`) and drops visual frames using `cap.grab()` when it falls behind, guaranteeing perfect audio/video synchronization.
* **Audio Extraction**: `moviepy` is utilized as a developer tool to extract `.mp3` tracks from `.mp4` files because OpenCV cannot read audio streams.

## 11. Standalone Executable Build (PyInstaller)
* **Compilation**: The game compiles to a fully standalone `.exe` using PyInstaller.
* **Build Command**: 
  `python -m PyInstaller --name "Dustway" --noconfirm --onedir --windowed --add-data "assets;assets" --add-data "music;music" --add-data "story;story" --distpath "Build_Release" main.py`
* **Asset Pathing Gotcha**: In PyInstaller 6.0+ `--onedir` builds, the actual executable is placed in the root directory, but all bundled DLLs, python runtime, and `--add-data` folders are placed inside a subfolder named `_internal`. 
* **Path Resolution**: To fix missing assets in the compiled game, all file loads (like `main.py` loading the intro and cursor) *must* use `src.config.rpath("assets", ...)`, which dynamically checks for `sys._MEIPASS` at runtime to locate the `_internal` folder correctly.

## 12. Save File Security (Anti-Cheat)
* **Mechanism**: To prevent players from easily modifying their caps, stats, or decks using a text editor, all local progression files (Settings, Stats, History, Decks, Campaign, Tutorial, Achievements) are encrypted via `src/security.py`.
* **Format**: Data is serialized to JSON, signed using a `SHA-256 HMAC` hash (mixed with a hardcoded `SECRET_SALT`), and then the entire payload (`hash:json`) is encoded into `Base64`.
* **Tamper Protection**: If a user decodes the Base64, edits the JSON, and re-encodes it, the game will detect a signature mismatch on load and reject the file, reverting to defaults.
* **Migration / Fallback**: To avoid breaking saves for existing players updating to the secured version, `secure_load()` implements an automatic migration. If it detects a plaintext JSON file (starts with `{` or `[`), it loads the file as normal JSON and immediately re-saves it into the secure Base64 format.

## 13. UI Refactoring & Modularity
* **Aesthetic Shift**: The game's UI is actively being modernized from a basic "green terminal" aesthetic (using `draw_panel`) to a richer "worn wood, leather, and parchment" style.
* **Global Helpers**: Shared UI rendering functions like `draw_wooden_board(rect)` and `draw_parchment(rect)` have been extracted to the global scope in `src/screens.py`. This ensures consistency across different menus (like the Profile and Background Selection screens).
* **Pending Overhauls**: The old `deck_builder_menu` has been completely removed from the game pending a total visual and functional redesign to match the new standards.

## 14. Git & GitHub Integration & Online Server Status (July 2026)
* **GitHub Repository**: The project is cleanly linked to `https://github.com/Lavder12/Card_game.git` on branch `main` under author `Lavder12`.
* **Clean Working Directory**: Added a comprehensive `.gitignore` excluding build folders (`Build_Release/`, `build/`, `dist/`), Python bytecode (`__pycache__/`), and runtime logs (`logs/`).
* **Resolved Desktop `.git` Conflict**: Removed an accidentally initialized `.git` repository on the Windows Desktop `C:\Users\Home0\Desktop\.git` that previously caused IDE Source Control to track 1024 unrelated desktop shortcuts and files.
* **Firebase Realtime Database Status (`FIREBASE_URL`)**: Verified online status and connectivity for `https://dustway-default-rtdb.europe-west1.firebasedatabase.app`. Realtime Database read/write rules have been updated and confirmed working (`.read: true, .write: true`), successfully returning live data (`global_caps` fund and registered user profiles).

