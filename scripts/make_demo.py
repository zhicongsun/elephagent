#!/usr/bin/env python3
"""Generate intro animation GIF and combine with terminal recording."""

from PIL import Image, ImageDraw, ImageFont
import math

W, H = 860, 520
BG = (30, 30, 46)  # Catppuccin Mocha base
TEXT_COLOR = (205, 214, 244)
ACCENT = (137, 180, 250)  # blue
PEACH = (250, 179, 135)   # peach
FPS_DELAY = 50  # ms per frame

def get_font(size):
    for path in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/Library/Fonts/Arial.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()

def load_logo(path, size, make_circular=False):
    img = Image.open(path).convert("RGBA")
    img.thumbnail((size, size), Image.LANCZOS)
    if make_circular:
        mask = Image.new("L", img.size, 0)
        d = ImageDraw.Draw(mask)
        d.ellipse([0, 0, img.size[0]-1, img.size[1]-1], fill=255)
        img.putalpha(mask)
    return img

def paste_centered(canvas, img, cx, cy):
    x = cx - img.width // 2
    y = cy - img.height // 2
    canvas.paste(img, (x, y), img)

def make_intro_frames():
    # Load logos — elephagent keeps white bg, tools get circular crop
    el_logo_raw = Image.open("assets/logo.png").convert("RGBA")
    el_logo_raw.thumbnail((120, 120), Image.LANCZOS)

    # Give elephagent logo a rounded-rect white card
    card_pad = 16
    card_w = el_logo_raw.width + card_pad * 2
    card_h = el_logo_raw.height + card_pad * 2
    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card)
    card_draw.rounded_rectangle([0, 0, card_w - 1, card_h - 1],
                                radius=18, fill=(255, 255, 255, 255))
    card.paste(el_logo_raw, (card_pad, card_pad), el_logo_raw)
    el_logo = card

    tool_logo_size = 56
    claude_logo = load_logo("assets/claude.webp", tool_logo_size, make_circular=True)
    cursor_logo = load_logo("assets/cursor.webp", tool_logo_size, make_circular=True)
    codex_logo  = load_logo("assets/codex.webp",  tool_logo_size, make_circular=True)

    font_title = get_font(30)
    font_label = get_font(14)
    font_tag = get_font(15)

    # Layout — golden ratio inspired vertical split
    # Top section: elephagent at ~35% height
    # Bottom section: tools at ~72% height
    el_cx, el_cy = W // 2, int(H * 0.30)
    tool_y = int(H * 0.68)
    spacing = 200
    tool_xs = [W // 2 - spacing, W // 2, W // 2 + spacing]
    tools = [
        (claude_logo, "Claude Code", tool_xs[0], tool_y),
        (cursor_logo, "Cursor",      tool_xs[1], tool_y),
        (codex_logo,  "Codex",       tool_xs[2], tool_y),
    ]

    title_y = el_cy + el_logo.height // 2 + 14

    frames = []

    def draw_base(draw, canvas, el_alpha=255):
        if el_alpha >= 255:
            paste_centered(canvas, el_logo, el_cx, el_cy)
        else:
            tmp = el_logo.copy()
            r, g, b, a = tmp.split()
            a = a.point(lambda x: int(x * el_alpha / 255))
            tmp = Image.merge("RGBA", (r, g, b, a))
            paste_centered(canvas, tmp, el_cx, el_cy)
        tc = tuple(int(c * min(el_alpha, 255) / 255) for c in TEXT_COLOR)
        draw.text((el_cx, title_y), "elephagent",
                  fill=tc, font=font_title, anchor="mt")

    def draw_tool(draw, canvas, idx, alpha=255):
        logo, name, cx, cy = tools[idx]
        if alpha >= 255:
            paste_centered(canvas, logo, cx, cy)
        else:
            tmp = logo.copy()
            r, g, b, a = tmp.split()
            a = a.point(lambda x: int(x * alpha / 255))
            tmp = Image.merge("RGBA", (r, g, b, a))
            paste_centered(canvas, tmp, cx, cy)
        tc = tuple(int(c * min(alpha, 255) / 255) for c in TEXT_COLOR)
        draw.text((cx, cy + logo.height // 2 + 10), name,
                  fill=tc, font=font_label, anchor="mt")

    # Arrow endpoints (just below title → just above each tool logo)
    arrow_top_y = title_y + 28
    arrow_bot_y_offset = -14  # above tool logo top edge

    # --- Phase 1: elephagent logo + title fade in (10 frames) ---
    for i in range(10):
        alpha = int(255 * (i + 1) / 10)
        frame = Image.new("RGBA", (W, H), BG + (255,))
        draw = ImageDraw.Draw(frame)
        draw_base(draw, frame, el_alpha=alpha)
        frames.append(frame.convert("RGB"))

    # --- Phase 2: Hold (6 frames) ---
    for _ in range(6):
        frame = Image.new("RGBA", (W, H), BG + (255,))
        draw = ImageDraw.Draw(frame)
        draw_base(draw, frame)
        frames.append(frame.convert("RGB"))

    # --- Phase 3: Three tools fade in together (8 frames) ---
    for i in range(8):
        alpha = int(255 * (i + 1) / 8)
        frame = Image.new("RGBA", (W, H), BG + (255,))
        draw = ImageDraw.Draw(frame)
        draw_base(draw, frame)
        for j in range(3):
            draw_tool(draw, frame, j, alpha=alpha)
        frames.append(frame.convert("RGB"))

    # --- Phase 4: Connection lines appear + dots animate (28 frames) ---
    LINE_COLOR = (70, 70, 100)
    for step in range(28):
        frame = Image.new("RGBA", (W, H), BG + (255,))
        draw = ImageDraw.Draw(frame)
        draw_base(draw, frame)
        for j in range(3):
            draw_tool(draw, frame, j)

        # Line fade in over first 6 frames
        line_alpha = min(1.0, step / 6.0)
        lc = tuple(int(c * line_alpha) for c in LINE_COLOR)

        progress = (step % 14) / 14.0

        for j in range(3):
            _, _, tcx, tcy = tools[j]
            sx, sy = el_cx, arrow_top_y
            ex, ey = tcx, tcy - tools[j][0].height // 2 + arrow_bot_y_offset

            # Draw line
            draw.line([(sx, sy), (ex, ey)], fill=lc, width=2)

            if step >= 4:
                # Dot going down (elephagent → tool) — accent blue
                t1 = (progress + j * 0.12) % 1.0
                dx1 = sx + (ex - sx) * t1
                dy1 = sy + (ey - sy) * t1
                draw.ellipse([dx1 - 5, dy1 - 5, dx1 + 5, dy1 + 5], fill=ACCENT)

                # Dot going up (tool → elephagent) — peach
                t2 = (progress + 0.5 + j * 0.12) % 1.0
                dx2 = ex + (sx - ex) * t2
                dy2 = ey + (sy - ey) * t2
                draw.ellipse([dx2 - 5, dy2 - 5, dx2 + 5, dy2 + 5], fill=PEACH)

        # Tagline fades in after frame 12
        if step > 12:
            tag_a = min(255, int(255 * (step - 12) / 8))
            tc = tuple(int(c * tag_a / 255) for c in TEXT_COLOR)
            draw.text((W // 2, H - 40),
                      "One memory layer for all your AI coding agents",
                      fill=tc, font=font_tag, anchor="mm")

        frames.append(frame.convert("RGB"))

    # --- Phase 5: Hold final (14 frames) ---
    for _ in range(14):
        frames.append(frames[-1])

    return frames

def save_gif(frames, path, delay=FPS_DELAY):
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=delay, loop=0, optimize=True)

def combine_gifs(intro_path, terminal_path, output_path):
    intro = Image.open(intro_path)
    terminal = Image.open(terminal_path)

    intro_frames = []
    try:
        while True:
            intro_frames.append(intro.copy().convert("RGB"))
            intro.seek(intro.tell() + 1)
    except EOFError:
        pass

    term_frames = []
    term_durations = []
    terminal.seek(0)
    try:
        while True:
            term_frames.append(terminal.copy().convert("RGB").resize((W, H), Image.LANCZOS))
            term_durations.append(terminal.info.get("duration", 50))
            terminal.seek(terminal.tell() + 1)
    except EOFError:
        pass

    all_frames = intro_frames + term_frames
    all_durations = [FPS_DELAY] * len(intro_frames) + term_durations

    all_frames[0].save(output_path, save_all=True, append_images=all_frames[1:],
                       duration=all_durations, loop=0, optimize=True)

if __name__ == "__main__":
    print("Generating intro animation...")
    intro_frames = make_intro_frames()
    save_gif(intro_frames, "assets/intro.gif")
    print(f"Intro: {len(intro_frames)} frames")

    print("Combining with terminal recording...")
    combine_gifs("assets/intro.gif", "assets/terminal.gif", "assets/demo.gif")

    import os
    size_kb = os.path.getsize("assets/demo.gif") / 1024
    print(f"Final demo.gif: {size_kb:.0f} KB")
