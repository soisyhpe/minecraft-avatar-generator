#!/usr/bin/env python3
"""
CLI tool to download Minecraft skin textures and generate
2D and 3D avatars from a player's hash, username, or UUID.
"""

import argparse
import sys
import urllib.request
import json
import base64
from pathlib import Path
from io import BytesIO
from typing import Optional

# Attempt to import required libraries
try:
    from PIL import Image
    # Import from our local, copied version of the rendering code
    from renderer import Skin, Perspective, InputImageException
except ImportError as e:
    print(f"Error: Missing required library or module: {e.name}",
          file=sys.stderr)
    print(
        "Please ensure all dependencies are installed by running: uv pip sync pyproject.toml",
        file=sys.stderr)
    sys.exit(1)

# Type alias for clarity
ImageType = Image.Image

# Constants
TEXTURE_URL_TEMPLATE: str = "http://textures.minecraft.net/texture/{hash}"
MOJANG_UUID_URL: str = "https://api.mojang.com/users/profiles/minecraft/{username}"
MOJANG_PROFILE_URL: str = "https://sessionserver.mojang.com/session/minecraft/profile/{uuid}"
SKIN_SIZE = (64, 64)

# Coordinates for 2D head parts on a 64x64 skin layout
HEAD_FRONT_BOX = (8, 8, 16, 16)
OVERLAY_FRONT_BOX = (40, 8, 48, 16)


def get_hash_from_player(username: str = None,
                         uuid: str = None) -> Optional[str]:
    """Fetches a player's skin hash from their username or UUID via the Mojang API."""
    if not username and not uuid:
        return None

    try:
        # 1. Get UUID from username if necessary
        if username:
            print(f"Fetching profile for username: {username}...",
                  file=sys.stderr)
            with urllib.request.urlopen(
                    MOJANG_UUID_URL.format(username=username)) as response:
                if response.status != 200:
                    print(
                        f"Error: Could not find player with username '{username}' (HTTP {response.status})",
                        file=sys.stderr)
                    return None
                uuid = json.loads(response.read())['id']

        # 2. Get skin profile from UUID
        print(f"Fetching skin profile for UUID: {uuid}...", file=sys.stderr)
        with urllib.request.urlopen(
                MOJANG_PROFILE_URL.format(uuid=uuid)) as response:
            if response.status != 200:
                print(
                    f"Error: Could not get profile for UUID '{uuid}' (HTTP {response.status})",
                    file=sys.stderr)
                return None
            data = json.loads(response.read())

        # 3. Decode base64 texture data and extract skin URL
        textures_b64 = data['properties'][0]['value']
        textures_json = base64.b64decode(textures_b64).decode('utf-8')
        skin_url = json.loads(textures_json)['textures']['SKIN']['url']

        # 4. Extract hash from URL
        skin_hash = Path(skin_url).stem
        return skin_hash

    except Exception as e:
        print(f"An error occurred during API lookup: {e}", file=sys.stderr)
        return None


def fetch_texture_data(hash_str: str) -> Optional[bytes]:
    """Downloads the raw skin texture image data from its hash."""
    url = TEXTURE_URL_TEMPLATE.format(hash=hash_str)
    print(f"Downloading texture from {url}...", file=sys.stderr)

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print(f"HTTP Error {response.status} during download.",
                      file=sys.stderr)
                return None
            return response.read()

    except urllib.error.URLError as e:
        print(f"Network Error: {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unknown error during download: {e}", file=sys.stderr)
        return None


def _validate_and_convert_skin(image_data: bytes) -> Optional[ImageType]:
    """Validates skin image data and converts it to a standard Pillow Image object."""
    try:
        image = Image.open(BytesIO(image_data))
        if image.size not in [SKIN_SIZE, (64, 32)]:
            print(
                f"Error: Texture is not 64x64 or 64x32 (received size: {image.size}).",
                file=sys.stderr)
            return None

        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        if image.size == (64, 32):
            new_image = Image.new("RGBA", SKIN_SIZE, (0, 0, 0, 0))
            new_image.paste(image, (0, 0))
            new_image.paste(image.crop((0, 16, 16, 32)), (16, 48))
            return new_image

        return image
    except Exception as e:
        print(f"Error during image validation: {e}", file=sys.stderr)
        return None


def create_2d_avatar(base_image: ImageType, render_type: str) -> ImageType:
    """Generates a 2D avatar (face or full overlay)."""
    face = base_image.crop(HEAD_FRONT_BOX)
    if render_type in ("overlay", "avatar"):
        overlay = base_image.crop(OVERLAY_FRONT_BOX).convert("RGBA")
        rgba_face = face.convert("RGBA")
        rgba_face.paste(overlay, (0, 0), mask=overlay)
        face = rgba_face
    return face


def create_isometric_avatar(skin_image: ImageType, part: str,
                            size: int) -> Optional[ImageType]:
    """Generates an isometric 3D avatar using the local skin renderer."""
    try:
        skin = Skin.from_image(skin_image)
        scaling_factor = max(size // 20, 1)
        perspective = Perspective(x="left",
                                  y="front",
                                  z="up",
                                  scaling_factor=scaling_factor)

        if part == 'head':
            return skin.head.to_isometric_image(perspective)
        elif part == 'full':
            return skin.to_isometric_image(perspective)
        else:
            print(f"Error: Unknown isometric part '{part}'.", file=sys.stderr)
            return None

    except (InputImageException, Exception) as e:
        print(f"Error during isometric rendering: {e}", file=sys.stderr)
        return None


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description=
        "Minecraft avatar generator from a texture hash, username, or UUID.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Input group
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--hash", type=str, help="The texture hash.")
    input_group.add_argument("--username",
                             type=str,
                             help="A Minecraft player username.")
    input_group.add_argument("--uuid",
                             type=str,
                             help="A Minecraft player UUID.")

    # Output options
    parser.add_argument("-o",
                        "--output",
                        type=Path,
                        required=True,
                        help="Output file path (.png).")
    parser.add_argument(
        "-t",
        "--type",
        type=str,
        choices=["texture", "face", "overlay", "avatar", "isometric"],
        default="avatar",
        help="Type of render to generate.")
    parser.add_argument(
        "-s",
        "--size",
        type=int,
        default=2048,
        help=
        "Side length in pixels for square outputs like 'avatar' and 'isometric'."
    )
    parser.add_argument(
        "--part",
        type=str,
        choices=['full', 'head'],
        default='head',
        help="For isometric renders, choose which part of the skin to render.")

    args = parser.parse_args()

    # 1. Get skin hash
    skin_hash = args.hash
    if not skin_hash:
        skin_hash = get_hash_from_player(username=args.username, uuid=args.uuid)
        if not skin_hash:
            print("Could not retrieve skin hash. Aborting.", file=sys.stderr)
            sys.exit(1)

    # 2. Fetch and validate skin texture
    image_data = fetch_texture_data(skin_hash)
    if image_data is None:
        print("Failed to download texture. Aborting.", file=sys.stderr)
        sys.exit(1)

    skin_image = _validate_and_convert_skin(image_data)
    if skin_image is None:
        sys.exit(1)

    # 3. Create the render
    output_image = None
    if args.type == "texture":
        output_image = skin_image
    elif args.type in ["face", "overlay", "avatar"]:
        output_image = create_2d_avatar(skin_image, args.type)
    elif args.type == "isometric":
        output_image = create_isometric_avatar(skin_image, args.part, args.size)

    if output_image is None:
        print("Failed to create avatar. Aborting.", file=sys.stderr)
        sys.exit(1)

    # 4. Post-process and save
    if args.type == "isometric":
        # For isometric renders, scale down and center to preserve aspect ratio
        output_image.thumbnail((args.size, args.size), Image.Resampling.LANCZOS)
        final_image = Image.new("RGBA", (args.size, args.size), (0, 0, 0, 0))
        paste_pos = ((args.size - output_image.width) // 2,
                     (args.size - output_image.height) // 2)
        final_image.paste(output_image, paste_pos)
        output_image = final_image
    elif args.type == "avatar":
        # For 2D avatars, scale up directly to the target size with a pixelated look
        output_image = output_image.resize((args.size, args.size),
                                           Image.Resampling.NEAREST)

    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        output_image.save(args.output, "PNG")
        print(f"Success! Render saved to: {args.output.resolve()}",
              file=sys.stderr)
    except IOError as e:
        print(f"Error saving file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unknown error during save: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
