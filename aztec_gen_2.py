from aztec_code_generator import AztecCode
from PIL import Image, ImageDraw, ImageFont
import os

# ---------- SETTINGS ----------
output_dir = "aztec_codes"
os.makedirs(output_dir, exist_ok=True)

rows = 4
cols = 4

# Physical target: about 3.4 cm at 300 DPI
code_size = 300

# Layout
margin_x = 100
margin_y = 100
spacing_x = 80
spacing_y = 120

# Extra room below code for label text
label_height = 70

# A4 at 300 DPI
A4_WIDTH = 2480
A4_HEIGHT = 3508

# Aztec generation sharpness
module_size = 16

# Orientation dot settings
dot_radius = 0 # 8 for the dot
dot_offset = 90   # distance from top-left corner of each cell

# Grid style
grid_line_width = 2

# ---------- TRY TO LOAD A BIGGER FONT ----------
def get_font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except:
        return ImageFont.load_default()

font = get_font(1)

# ---------- CELL SIZE ----------
cell_width = code_size
cell_height = code_size + label_height

# ---------- GENERATE INDIVIDUAL AZTEC PNGs ----------
for i in range(1, 9):
    text = f"Aztec{i:03d}"
    path = os.path.join(output_dir, f"{text}.png")

    code = AztecCode(text)
    code.save(path, module_size=10)

# ---------- CREATE A4 CANVAS ----------
canvas = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), "white")
draw = ImageDraw.Draw(canvas)

# ---------- PLACE CODES ----------
idx = 1
for r in range(rows):
    for c in range(cols):
        code_num = ((idx - 1) % 8) + 1
        text = f"code{code_num:03d}"
        img_path = os.path.join(output_dir, f"{text}.png")

        # top-left of this whole cell
        x = margin_x + c * (cell_width + spacing_x)
        y = margin_y + r * (cell_height + spacing_y)

        # load aztec image
        img = Image.open(img_path).convert("RGB")
        img = img.resize((code_size, code_size))

        # paste code
        canvas.paste(img, (x, y))

        # ----- orientation dot -----
        # Top-left inside the code area.
        # This helps you detect print orientation with contour logic.
        dot_cx = x + dot_offset
        dot_cy = y + dot_offset
        draw.ellipse(
            (
                dot_cx - dot_radius,
                dot_cy - dot_radius,
                dot_cx + dot_radius,
                dot_cy + dot_radius,
            ),
            fill="black"
        )

        # ----- larger text below code -----
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]

        text_x = x + (code_size - text_w) // 2
        text_y = y + code_size + 10
        draw.text((text_x, text_y), text, fill="black", font=font)

        # ----- cutting grid / cut box -----
        # Draw one rectangle around each full printable sticker cell
        draw.rectangle(
            (
                x - 30,
                y - 30,
                x + cell_width + 30,
                y + cell_height + 30,
            ),
            outline="black",
            width=grid_line_width
        )

        idx += 1

# ---------- OPTIONAL PAGE BORDER ----------
draw.rectangle((10, 10, A4_WIDTH - 10, A4_HEIGHT - 10), outline="black", width=2)

# ---------- SAVE ----------
canvas.save("aztec_a4_sheet_with_grid.pdf", "PDF", resolution=300.0)

print("Saved aztec_a4_sheet_with_grid.pdf")