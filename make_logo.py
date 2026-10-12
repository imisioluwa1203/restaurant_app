from PIL import Image, ImageDraw
import os

OUT = "static/images"
os.makedirs(OUT, exist_ok=True)
ORANGE = "#ff7a1a"
LIGHT = "#ffb074"

def draw_mark(d, dy=0):
    d.pieslice((212, 312 + dy, 812, 912 + dy), 180, 360, fill=ORANGE)
    d.rounded_rectangle((152, 612 + dy, 872, 676 + dy), radius=32, fill=ORANGE)
    d.ellipse((472, 252 + dy, 552, 332 + dy), fill=ORANGE)
    d.arc((272, 372 + dy, 752, 852 + dy), 205, 250, fill=LIGHT, width=22)

icon = Image.new("RGB", (1024, 1024), "#111111")
draw_mark(ImageDraw.Draw(icon), dy=48)
icon.save(f"{OUT}/app_icon.png")

logo = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
draw_mark(ImageDraw.Draw(logo))
logo = logo.crop(logo.getbbox())
logo.thumbnail((512, 512))
logo.save(f"{OUT}/logo.png")

fav = icon.resize((64, 64), Image.LANCZOS)
fav.save(f"{OUT}/favicon.png")
fav.save(f"{OUT}/favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
print("Done: app_icon.png, logo.png, favicon.png, favicon.ico")