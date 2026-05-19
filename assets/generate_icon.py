from PIL import Image, ImageDraw
import os

def generate_icon(path: str) -> None:
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    for size in sizes:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Dark circle background
        draw.ellipse([2, 2, size - 2, size - 2], fill=(26, 26, 46, 255))
        # White 'S' approximated as a simple arc pair
        margin = size // 5
        draw.arc([margin, margin, size - margin, size // 2], 200, 340, fill='white', width=max(1, size // 12))
        draw.arc([margin, size // 2, size - margin, size - margin], 20, 160, fill='white', width=max(1, size // 12))
        images.append(img)
    images[0].save(path, format='ICO', sizes=[(s, s) for s in sizes], append_images=images[1:])
    print(f"Icon saved to {path}")

if __name__ == '__main__':
    out = os.path.join(os.path.dirname(__file__), 'icon.ico')
    generate_icon(out)
