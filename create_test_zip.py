#!/usr/bin/env python3
"""
Creates a test ZIP file containing sample images for testing purposes.
Generates colored rectangles as PNG images and packages them into a ZIP file.
"""

import os
import zipfile
from PIL import Image, ImageDraw, ImageFont
import io

def create_test_image(width=800, height=600, color=(255, 0, 0), text="Test Image"):
    """Create a test image with specified dimensions, color, and text."""
    image = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(image)

    # Try to use a default font, fallback to basic if not available
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        try:
            font = ImageFont.load_default()
        except:
            font = None

    # Add text to image
    if font:
        # Get text bounding box for centering
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (width - text_width) // 2
        y = (height - text_height) // 2

        draw.text((x, y), text, fill=(255, 255, 255), font=font)

    return image

def create_test_zip(zip_filename="test_images.zip", num_images=5):
    """Create a ZIP file with test images."""

    # Define colors and names for test images
    test_data = [
        ((255, 100, 100), "Red Image"),
        ((100, 255, 100), "Green Image"),
        ((100, 100, 255), "Blue Image"),
        ((255, 255, 100), "Yellow Image"),
        ((255, 100, 255), "Magenta Image"),
        ((100, 255, 255), "Cyan Image"),
        ((255, 165, 0), "Orange Image"),
        ((128, 0, 128), "Purple Image")
    ]

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for i in range(min(num_images, len(test_data))):
            color, text = test_data[i]

            # Create image
            img = create_test_image(color=color, text=text)

            # Save image to bytes buffer
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_bytes = img_buffer.getvalue()

            # Add to ZIP with filename
            filename = f"test_image_{i+1:02d}_{text.lower().replace(' ', '_')}.png"
            zipf.writestr(filename, img_bytes)

            print(f"Added: {filename}")

    print(f"\nCreated ZIP file: {zip_filename}")
    print(f"File size: {os.path.getsize(zip_filename):,} bytes")

    # List contents
    print("\nZIP Contents:")
    with zipfile.ZipFile(zip_filename, 'r') as zipf:
        for info in zipf.infolist():
            print(f"  {info.filename} ({info.file_size:,} bytes)")

def main():
    """Main function to create test ZIP file."""
    print("Creating test ZIP file with sample images...")

    # Create ZIP with default settings
    create_test_zip()

    # Optionally create a larger ZIP with more images
    create_larger = input("\nCreate a larger ZIP with 8 images? (y/n): ").lower().strip()
    if create_larger == 'y':
        create_test_zip("test_images_large.zip", 8)

if __name__ == "__main__":
    main()
