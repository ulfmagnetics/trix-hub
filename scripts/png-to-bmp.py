import argparse
from PIL import Image

def main():
    parser = argparse.ArgumentParser(description='Convert PNG images to 24-bit BMP format')
    parser.add_argument('input', help='Input PNG file path')
    parser.add_argument('output', help='Output BMP file path')

    args = parser.parse_args()

    # Open the PNG file
    img = Image.open(args.input)

    # Ensure it's RGB mode (24-bit)
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Save as 24-bit BMP
    img.save(args.output, format='BMP')
    print(f'Successfully converted {args.input} to {args.output}')

if __name__ == '__main__':
    main()