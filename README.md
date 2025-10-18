# Minecraft Avatar Generator

> A command-line utility to generate 2D and 3D isometric renders of Minecraft skins from a player's username, UUID, or skin hash.

![3D Head Render](examples/head_render.png)

This tool can fetch Minecraft skin textures and generate several types of avatars, including simple 2D faces and high-quality 3D isometric renders of either the player's head or their full body.

## Table of Contents

- [Background](#background)
- [Install](#install)
- [Usage](#usage)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)

## Background

The core 3D rendering logic in `skin_renderer.py` is derived from the excellent [skinpy](https://github.com/t-mart/skinpy) library by t-mart. The code was copied and adapted for local use in this project to provide additional features and modifications.

## Install

Install the tool from PyPI using `pip`:

```shell
pip install minecraft-avatar-generator
```

## Usage

The script provides several command-line options to specify the input, render type, and output.

```shell
mc-avatar
```

```
usage: mc-avatar [-h] (--hash HASH | --username USERNAME | --uuid UUID) -o OUTPUT [-t {texture,face,overlay,avatar,isometric}] [-s SIZE] [--part {full,head}]

Minecraft avatar generator from a texture hash, username, or UUID.

options:
  -h, --help            show this help message and exit

Input:
  --hash HASH           The texture hash.
  --username USERNAME   A Minecraft player username.
  --uuid UUID           A Minecraft player UUID.

Output options:
  -o OUTPUT, --output OUTPUT
                        Output file path (.png).
  -t {texture,face,overlay,avatar,isometric}, --type {texture,face,overlay,avatar,isometric}
                        Type of render to generate.
  -s SIZE, --size SIZE  Side length in pixels for square outputs like 'avatar' and 'isometric'. (default: 2048)
  --part {full,head}    For isometric renders, choose which part of the skin to render.
```

## Examples

### 3D Isometric Head Render (default 2048px)

**Command:**
```shell
python render_skin.py --username Siphano -o examples/head_render.png -t isometric --part head
```

**Result:**

![3D Head Render](examples/head_render.png)

---

### 3D Isometric Full Body Render (default 2048px)

**Command:**
```shell
python render_skin.py --username Siphano -o examples/full_render.png -t isometric --part full
```

**Result:**

![3D Full Body Render](examples/full_render.png)

---

### 2D Avatar (128px)

**Command:**
```shell
python render_skin.py --username Siphano -o examples/avatar.png -t avatar -s 128
```

**Result:**

![2D Avatar](examples/avatar.png)

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project does not currently have a license. You are free to add one, for example, [MIT](https://choosealicense.com/licenses/mit/).
