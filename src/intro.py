import pygame
import os


def play_intro(screen, video_path):
    """
    Plays an mp4 intro video with audio.
    Press any key or click mouse to skip.
    Includes fade-in/fade-out transitions.
    """
    if not os.path.exists(video_path):
        print(f"Intro video not found at {video_path}")
        return

    try:
        import cv2
        import numpy as np
    except ImportError:
        print("OpenCV not installed, skipping intro.")
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Could not open intro video.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0 or fps is None:
        fps = 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    vid_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()

    # Pre-calculate the target resize dimensions.
    # First resize in OpenCV (fast C code), then only do a small pygame scale if needed.
    # Preserve aspect ratio — fit inside screen with letterboxing.
    vid_aspect = vid_w / vid_h
    scr_aspect = screen_w / screen_h

    if vid_aspect > scr_aspect:
        # Video is wider than screen — fit width, letterbox top/bottom
        target_w = screen_w
        target_h = int(screen_w / vid_aspect)
    else:
        # Video is taller — fit height, letterbox left/right
        target_h = screen_h
        target_w = int(screen_h * vid_aspect)

    offset_x = (screen_w - target_w) // 2
    offset_y = (screen_h - target_h) // 2

    # Start audio
    audio_path = video_path.replace(".mp4", ".mp3")
    audio_playing = False
    if os.path.exists(audio_path):
        try:
            pygame.mixer.music.load(audio_path)
            from src import state as _st
            pygame.mixer.music.set_volume(0.0 if _st.app_settings.muted else _st.app_settings.volume)
            pygame.mixer.music.play()
            audio_playing = True
        except Exception as e:
            print(f"Could not play intro audio: {e}")

    # Fade parameters
    FADE_IN_FRAMES = int(fps * 0.8)   # 0.8 seconds fade in
    FADE_OUT_FRAMES = int(fps * 0.6)  # 0.6 seconds fade out

    skipped = False
    frame_idx = 0
    fade_overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)

    # Clear the screen to black first
    screen.fill((0, 0, 0))
    pygame.display.flip()
    pygame.event.clear()
    pygame.mouse.set_visible(False)

    start_ticks = pygame.time.get_ticks()

    while True:
        current_ticks = pygame.time.get_ticks()
        elapsed_sec = (current_ticks - start_ticks) / 1000.0
        target_frame = int(elapsed_sec * fps)
        
        frames_to_advance = target_frame - frame_idx
        
        if frames_to_advance < 0:
            # We are ahead of time, just wait
            clock.tick(fps)
            continue
            
        if frames_to_advance > 0:
            # We are behind. Skip frames to catch up.
            for _ in range(frames_to_advance - 1):
                cap.grab()
                frame_idx += 1
                
            ret, frame = cap.read()
            frame_idx += 1
            
            if not ret:
                break
        else:
            # Perfectly on time, read the next frame
            ret, frame = cap.read()
            frame_idx += 1
            if not ret:
                break

        # --- Resize in OpenCV (much faster than pygame smoothscale on huge frames) ---
        frame_resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

        # Convert BGR -> RGB
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)

        # Create pygame surface — numpy transpose for surfarray
        frame_t = np.ascontiguousarray(np.transpose(frame_rgb, (1, 0, 2)))
        surf = pygame.surfarray.make_surface(frame_t)

        # Draw black background (for letterboxing) then the frame
        screen.fill((0, 0, 0))
        screen.blit(surf, (offset_x, offset_y))

        # --- Fade in ---
        if frame_idx < FADE_IN_FRAMES:
            alpha = int(255 * (1.0 - frame_idx / FADE_IN_FRAMES))
            fade_overlay.fill((0, 0, 0, alpha))
            screen.blit(fade_overlay, (0, 0))

        # --- Fade out (last N frames of the video) ---
        frames_left = total_frames - frame_idx
        if frames_left <= FADE_OUT_FRAMES and frames_left > 0:
            alpha = int(255 * (1.0 - frames_left / FADE_OUT_FRAMES))
            fade_overlay.fill((0, 0, 0, alpha))
            screen.blit(fade_overlay, (0, 0))

        pygame.display.flip()

        # Handle events — skip on any key/click
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                cap.release()
                if audio_playing:
                    pygame.mixer.music.stop()
                import sys
                from src import state
                if state.app_settings:
                    state.app_settings.save()
                pygame.quit()
                sys.exit()
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                skipped = True

        if skipped:
            break

        clock.tick(fps)

    cap.release()

    # Smooth fade-out on skip (quick ~0.4s fade)
    if skipped or True:
        fade_steps = 12
        for i in range(fade_steps):
            alpha = int(255 * (i + 1) / fade_steps)
            fade_overlay.fill((0, 0, 0, alpha))
            screen.blit(fade_overlay, (0, 0))
            pygame.display.flip()
            pygame.time.delay(33)

    if audio_playing:
        pygame.mixer.music.fadeout(300)
        pygame.time.delay(300)

    screen.fill((0, 0, 0))
    pygame.display.flip()
    pygame.mouse.set_visible(True)

    # Clear any queued events so we don't instantly trigger menu actions
    pygame.event.clear()
