# This file is a derivative work of the skinpy library by t-mart.
# Original source: https://github.com/t-mart/skinpy
# The code has been copied and adapted for local use in this project.

from __future__ import annotations

from typing import Literal, Union, TypeAlias, Iterable, TYPE_CHECKING, Sequence
from pathlib import Path

import numpy as np
from numpy import s_
from attrs import frozen
from PIL import Image, ImageDraw

# --- Start of content from types.py ---

# x, y, color
ImageColor: TypeAlias = np.ndarray[tuple[int, int, int], np.dtype[np.uint8]]

# (x, y, z)
R3: TypeAlias = tuple[int, int, int]

# (x, y)
R2: TypeAlias = tuple[int, int]

# (r, g, b, a)
RGBA: TypeAlias = tuple[int, int, int, int]

# face identifiers
XFaceId: TypeAlias = Literal["left", "right"]
YFaceId: TypeAlias = Literal["front", "back"]
ZFaceId: TypeAlias = Literal["up", "down"]
FaceId: TypeAlias = Union[XFaceId, YFaceId, ZFaceId]

# body part names
BodyPartId: TypeAlias = Literal["head", "torso", "left_arm", "right_arm",
                                "left_leg", "right_leg"]

PolygonPoints: TypeAlias = tuple[
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
]

StrPath: TypeAlias = Union[str, Path]

# --- End of content from types.py ---

# --- Start of content from render.py ---


@frozen
class Polygon:
    points: PolygonPoints
    color: RGBA

    def draw(self, draw: ImageDraw.ImageDraw) -> None:
        draw.polygon(
            xy=[tuple(p) for p in self.points],  # type: ignore
            fill=tuple(self.color),  # type: ignore
        )

    def with_offset(self, offset: tuple[int, int]) -> Polygon:
        offsetted = (
            (self.points[0][0] + offset[0], self.points[0][1] + offset[1]),
            (self.points[1][0] + offset[0], self.points[1][1] + offset[1]),
            (self.points[2][0] + offset[0], self.points[2][1] + offset[1]),
            (self.points[3][0] + offset[0], self.points[3][1] + offset[1]),
        )
        return Polygon(
            offsetted,
            self.color,
        )

    @property
    def min_x(self) -> int:
        return min(p[0] for p in self.points)

    @property
    def max_x(self) -> int:
        return max(p[0] for p in self.points)

    @property
    def min_y(self) -> int:
        return min(p[1] for p in self.points)

    @property
    def max_y(self) -> int:
        return max(p[1] for p in self.points)


COS_30 = np.cos(np.pi / 6)


@frozen(kw_only=True)
class Perspective:
    x: XFaceId
    y: YFaceId
    z: ZFaceId
    scaling_factor: int = 10

    @classmethod
    def new(
        cls,
        *,
        x: XFaceId,
        y: YFaceId,
        z: ZFaceId,
        scaling_factor: int = 10,
    ) -> Perspective:
        return cls(
            x=x,
            y=y,
            z=z,
            scaling_factor=scaling_factor,
        )

    @property
    def x_dir(self) -> int:
        return 1 if self.x == "left" else -1

    @property
    def y_dir(self) -> int:
        return 1 if self.y == "front" else -1

    @property
    def z_dir(self) -> int:
        return 1 if self.z == "up" else -1

    def map_iso(self, x: int, y: int, z: int) -> tuple[int, int]:
        # "p" for projected, i guess
        xp = x * self.x_dir * self.scaling_factor
        yp = y * self.y_dir * self.scaling_factor
        zp = z * self.z_dir * self.scaling_factor

        iso_x = (xp - yp) * COS_30
        iso_y = -(((xp + yp) / 2) + zp)

        points = tuple(np.array((iso_x, iso_y)).round().astype(int).tolist())

        return (points[0], points[1])

    def make_polygon(
        self,
        x: int,
        y: int,
        z: int,
        face_id: FaceId,
        color: RGBA,
    ) -> Polygon:
        if face_id in ("front", "back"):
            if face_id == "front":
                y_offset = y
            else:
                y_offset = y + 1
            points = (
                self.map_iso(x, y_offset, z),
                self.map_iso(x + 1, y_offset, z),
                self.map_iso(x + 1, y_offset, z + 1),
                self.map_iso(x, y_offset, z + 1),
            )
        elif face_id in ("left", "right"):
            if face_id == "left":
                x_offset = x
            else:
                x_offset = x + 1
            points = (
                self.map_iso(x_offset, y, z),
                self.map_iso(x_offset, y + 1, z),
                self.map_iso(x_offset, y + 1, z + 1),
                self.map_iso(x_offset, y, z + 1),
            )
        else:
            if face_id == "down":
                z_offset = z
            else:  # down
                z_offset = z + 1
            points = (
                self.map_iso(x, y, z_offset),
                self.map_iso(x + 1, y, z_offset),
                self.map_iso(x + 1, y + 1, z_offset),
                self.map_iso(x, y + 1, z_offset),
            )

        return Polygon(
            points,
            color,
        )

    @property
    def visible_faces(self) -> tuple[FaceId, FaceId, FaceId]:
        return (self.x, self.y, self.z)


def get_iso_polys(
    enumerator: Iterable[tuple[R3, FaceId, ImageColor]],
    perspective: Perspective | None = None,
) -> Iterable[Polygon]:
    if perspective is None:
        perspective = Perspective.new(
            x="left",
            y="front",
            z="up",
            scaling_factor=10,
        )

    for (x, y, z), face_id, color in enumerator:
        if face_id in perspective.visible_faces:
            color_t = (
                color[0],
                color[1],
                color[2],
                color[3],
            )
            poly = perspective.make_polygon(
                x,
                y,
                z,
                face_id,
                color_t,
            )
            yield poly


def render_isometric(
    polys: Sequence[Polygon],
    background_color: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    min_x = min(poly.min_x for poly in polys)
    max_x = max(poly.max_x for poly in polys)
    min_y = min(poly.min_y for poly in polys)
    max_y = max(poly.max_y for poly in polys)
    img_width = max_x - min_x
    img_height = max_y - min_y

    img = Image.new(
        "RGBA",
        (img_width, img_height),
        color=background_color,  # type: ignore
    )
    draw = ImageDraw.Draw(img)

    for poly in polys:
        offset_poly = poly.with_offset((-min_x, -min_y))
        offset_poly.draw(draw)

    return img


# --- End of content from render.py ---

# --- Start of content from skin.py ---


class UnmappedVoxelError(Exception):
    pass


class InputImageException(Exception):
    pass


def _subarray(*, data: ImageColor, origin: R2, offset: R2) -> ImageColor:
    assert len(origin) == len(offset)
    slices = tuple(slice(o, o + s) for o, s in zip(origin, offset))
    return data[slices]


FORWARD_SLICE = s_[:]
REVERSE_SLICE = s_[::-1]


@frozen
class Face:
    image_color: ImageColor
    id_: FaceId
    order: tuple[slice, slice]

    @classmethod
    def new(
        cls,
        part_image_color: ImageColor,
        id_: FaceId,
        part_shape: R3,
    ) -> Face:
        x_shape, y_shape, z_shape = part_shape
        order_x = FORWARD_SLICE
        order_y = REVERSE_SLICE
        if id_ in ("up", "down"):
            image_color_shape = (x_shape, y_shape)
            if id_ == "up":
                face_image_origin = (y_shape, 0)
            else:  # down
                face_image_origin = (y_shape + x_shape, 0)
        elif id_ in ("left", "right"):
            image_color_shape = (y_shape, z_shape)
            if id_ == "left":
                face_image_origin = (0, y_shape)
                order_x = REVERSE_SLICE
            else:  # right
                face_image_origin = (y_shape + x_shape, y_shape)
        else:  # front or back
            image_color_shape = (x_shape, z_shape)
            if id_ == "front":
                face_image_origin = (y_shape, y_shape)
            else:  # back
                face_image_origin = (y_shape + x_shape + y_shape, y_shape)
                order_x = REVERSE_SLICE

        image_color = _subarray(
            data=part_image_color,
            origin=face_image_origin,
            offset=image_color_shape,
        )

        return cls(
            image_color=image_color,
            id_=id_,
            order=(order_x, order_y),
        )

    def enumerate_color(self) -> Iterable[tuple[R2, ImageColor]]:
        for x, y in np.ndindex(self.image_color.shape[:2]):
            coord = (x, y)
            color = self.image_color[self.order][x, y]
            yield coord, color

    def get_color(self, x: int | slice, y: int | slice) -> ImageColor:
        try:
            return self.image_color[self.order][x, y]
        except IndexError:
            coord = (x, y)
            raise UnmappedVoxelError(f"{coord} contains unmapped voxels")

    def set_color(self, x: int | slice, y: int | slice, color: RGBA):
        self.get_color(x, y)[:] = color

    @property
    def shape(self) -> tuple[int, int]:
        return (self.image_color.shape[0], self.image_color.shape[1])


@frozen
class BodyPart:
    id_: BodyPartId
    image_color: ImageColor
    model_origin: R3

    up: Face
    down: Face
    left: Face
    right: Face
    front: Face
    back: Face

    @classmethod
    def new(
        cls,
        *,
        id_: BodyPartId,
        skin_image_color: ImageColor,
        part_shape: R3,
        part_model_origin: R3,
        part_image_origin: R2,
    ) -> BodyPart:
        image_color = _subarray(
            data=skin_image_color,
            origin=part_image_origin,
            offset=(
                part_shape[0] * 2 + part_shape[1] * 2,
                part_shape[1] + part_shape[2],
            ),
        )

        def face_for_id(face_name: FaceId) -> Face:
            return Face.new(
                part_image_color=image_color,
                id_=face_name,
                part_shape=part_shape,
            )

        return cls(
            id_=id_,
            image_color=image_color,
            model_origin=part_model_origin,
            up=face_for_id("up"),
            down=face_for_id("down"),
            left=face_for_id("left"),
            right=face_for_id("right"),
            front=face_for_id("front"),
            back=face_for_id("back"),
        )

    @property
    def faces(self) -> tuple[Face, ...]:
        return (self.up, self.down, self.left, self.right, self.front,
                self.back)

    def get_face_for_id(self, face_id: FaceId) -> Face:
        if face_id == "up":
            return self.up
        elif face_id == "down":
            return self.down
        elif face_id == "left":
            return self.left
        elif face_id == "right":
            return self.right
        elif face_id == "front":
            return self.front
        else:  # face_id == "back"
            return self.back

    @property
    def shape(self) -> tuple[int, int, int]:
        return (
            self.front.shape[0],
            self.left.shape[0],
            self.front.shape[1],
        )

    def enumerate_color(self) -> Iterable[tuple[R3, FaceId, ImageColor]]:
        for face in self.faces:
            for xy_coord, color in face.enumerate_color():
                if face.id_ in ("up", "down"):
                    x, y = xy_coord
                    if face.id_ == "down":
                        z = 0
                    else:  # up
                        z = self.shape[2] - 1
                elif face.id_ in ("left", "right"):
                    y, z = xy_coord
                    if face.id_ == "left":
                        x = 0
                    else:
                        x = self.shape[0] - 1
                else:  # front or back
                    x, z = xy_coord
                    if face.id_ == "front":
                        y = 0
                    else:
                        y = self.shape[1] - 1
                xyz_coord = (x, y, z)

                yield xyz_coord, face.id_, color

    def get_color(self, x: int | slice, y: int | slice, z: int | slice,
                  face: FaceId) -> ImageColor:
        if face == "up" and z == self.shape[2] - 1:
            return self.up.get_color(x, y)
        elif face == "down" and z == 0:
            return self.down.get_color(x, y)
        elif face == "left" and x == 0:
            return self.left.get_color(y, z)
        elif face == "right" and x == self.shape[0] - 1:
            return self.right.get_color(y, z)
        elif face == "front" and y == 0:
            return self.front.get_color(x, z)
        elif face == "back" and y == self.shape[1] - 1:
            return self.back.get_color(x, z)

        coord = (x, y, z, face)
        raise UnmappedVoxelError(f"{coord} contains unmapped voxels")

    def set_color(
        self,
        x: int | slice,
        y: int | slice,
        z: int | slice,
        face: FaceId,
        color: RGBA,
    ):
        self.get_color(x, y, z, face)[:] = color

    def get_iso_polys(self, perspective: Perspective) -> Iterable[Polygon]:
        yield from get_iso_polys(
            self.enumerate_color(),
            perspective=perspective,
        )

    def to_isometric_image(
        self,
        perspective: Perspective,
        background_color: tuple[int, int, int, int] | None = None,
    ) -> Image.Image:
        return render_isometric(
            polys=list(self.get_iso_polys(perspective)),
            background_color=background_color,
        )


@frozen
class Skin:
    image_color: ImageColor

    head: BodyPart
    torso: BodyPart
    left_arm: BodyPart
    right_arm: BodyPart
    left_leg: BodyPart
    right_leg: BodyPart

    @classmethod
    def new(cls, image_color: ImageColor | None = None) -> Skin:
        if image_color is None:
            image_color = np.zeros(
                (
                    64,  # 64 pixels x (left to right)
                    64,  # 64 pixels y (top to bottom)
                    4,  # 4 color channels (RGBA)
                ),
                dtype=np.uint8,
            )

        assert image_color.shape == (64, 64, 4)

        head = BodyPart.new(
            id_="head",
            skin_image_color=image_color,
            part_shape=(8, 8, 8),
            part_model_origin=(4, 0, 24),
            part_image_origin=(0, 0),
        )
        torso = BodyPart.new(
            id_="torso",
            skin_image_color=image_color,
            part_shape=(8, 4, 12),
            part_model_origin=(4, 2, 12),
            part_image_origin=(16, 16),
        )
        left_arm = BodyPart.new(
            id_="left_arm",
            skin_image_color=image_color,
            part_shape=(4, 4, 12),
            part_model_origin=(0, 2, 12),
            part_image_origin=(40, 16),
        )
        right_arm = BodyPart.new(
            id_="right_arm",
            skin_image_color=image_color,
            part_shape=(4, 4, 12),
            part_model_origin=(12, 2, 12),
            part_image_origin=(32, 48),
        )
        left_leg = BodyPart.new(
            id_="left_leg",
            skin_image_color=image_color,
            part_shape=(4, 4, 12),
            part_model_origin=(4, 2, 0),
            part_image_origin=(0, 16),
        )
        right_leg = BodyPart.new(
            id_="right_leg",
            skin_image_color=image_color,
            part_shape=(4, 4, 12),
            part_model_origin=(8, 2, 0),
            part_image_origin=(16, 48),
        )

        return cls(
            image_color=image_color,
            head=head,
            torso=torso,
            left_arm=left_arm,
            right_arm=right_arm,
            left_leg=left_leg,
            right_leg=right_leg,
        )

    @classmethod
    def filled(cls, color: RGBA) -> Skin:
        skin = cls.new()
        for body_part in skin.body_parts:
            for face in body_part.faces:
                face.image_color[:] = color
        return skin

    @classmethod
    def from_image(cls, image: Image.Image) -> Skin:
        if image.size != (64, 64):
            raise InputImageException(
                f"Image size must be 64x64 pixels, but got {image.size}")

        if image.mode != "RGBA":
            image = image.convert("RGBA")

        image_arr = np.swapaxes(np.asarray(image), 0, 1)

        skin = cls.new()
        skin.image_color[:] = image_arr
        return skin

    @classmethod
    def from_path(cls, path: StrPath) -> Skin:
        image = Image.open(path)
        return cls.from_image(image)

    @property
    def body_parts(self) -> tuple[BodyPart, ...]:
        return (
            self.left_leg,
            self.right_leg,
            self.left_arm,
            self.torso,
            self.right_arm,
            self.head,
        )

    def get_body_part_for_id(self, body_part_id: BodyPartId) -> BodyPart:
        if body_part_id == "head":
            return self.head
        elif body_part_id == "torso":
            return self.torso
        elif body_part_id == "left_arm":
            return self.left_arm
        elif body_part_id == "right_arm":
            return self.right_arm
        elif body_part_id == "left_leg":
            return self.left_leg
        else:  # body_part_id == "right_leg"
            return self.right_leg

    @property
    def shape(self) -> R3:
        return (16, 8, 32)

    def enumerate_color(
        self,) -> Iterable[tuple[R3, BodyPartId, FaceId, ImageColor]]:
        for body_part in self.body_parts:
            for xyz_coord, face_id, color in body_part.enumerate_color():
                offset = (
                    body_part.model_origin[0] + xyz_coord[0],
                    body_part.model_origin[1] + xyz_coord[1],
                    body_part.model_origin[2] + xyz_coord[2],
                )
                yield offset, body_part.id_, face_id, color

    def get_color(self, x: int, y: int, z: int, face: FaceId) -> ImageColor:
        for bp in self.body_parts:
            if ((bp.model_origin[0] <= x < bp.model_origin[0] + bp.shape[0]) and
                (bp.model_origin[1] <= y < bp.model_origin[1] + bp.shape[1]) and
                (bp.model_origin[2] <= z < bp.model_origin[2] + bp.shape[2])):
                x_rel = x - bp.model_origin[0]
                y_rel = y - bp.model_origin[1]
                z_rel = z - bp.model_origin[2]
                return bp.get_color(x_rel, y_rel, z_rel, face)

        raise UnmappedVoxelError((x, y, z, face))

    def set_color(self, x: int, y: int, z: int, face: FaceId, color: RGBA):
        self.get_color(x, y, z, face)[:] = color

    def to_image(self) -> Image.Image:
        image_arr = np.swapaxes(self.image_color, 0, 1)
        image = Image.fromarray(image_arr, mode="RGBA")  # type: ignore
        return image

    def to_isometric_image(
        self,
        perspective: Perspective,
        background_color: tuple[int, int, int, int] | None = None,
    ) -> Image.Image:
        origin = (
            0 if perspective.x == "left" else self.shape[0] - 1,
            0 if perspective.y == "front" else self.shape[1] - 1,
            0 if perspective.z == "down" else self.shape[2] - 1,
        )

        def dist_to_origin(body_part: BodyPart) -> float:
            return float(
                np.linalg.norm(
                    np.array(body_part.model_origin) - np.array(origin)))

        parts = sorted(self.body_parts, key=dist_to_origin, reverse=True)

        polys: list[Polygon] = []
        for part in parts:
            for poly in part.get_iso_polys(perspective):
                offset = perspective.map_iso(*part.model_origin)
                polys.append(poly.with_offset(offset))

        return render_isometric(
            polys=polys,
            background_color=background_color,
        )


# --- End of content from skin.py ---
