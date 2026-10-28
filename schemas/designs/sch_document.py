"""Constructor document. Mirrors frontend/src/entities/furniture/model/document.ts; sizes are in mm.

The API exposes the document as a plain JSON object, this schema only validates it on the way in.
Geometry rules (shelf spans, drawer widths) are checked by the frontend kernel.
"""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from enums.designs_enum import MaterialEnum
from schemas.sch_base import BaseSchema

MAX_NODES = 200
MAX_DEPTH = 8


class EmptyFillSchema(BaseSchema):
    type: Literal["empty"]


class ShelvesFillSchema(BaseSchema):
    type: Literal["shelves"]
    count: int = Field(ge=1, le=12)


class RodFillSchema(BaseSchema):
    type: Literal["rod"]


class DrawersFillSchema(BaseSchema):
    type: Literal["drawers"]
    count: int = Field(ge=1, le=8)


type FillSchema = Annotated[
    EmptyFillSchema | ShelvesFillSchema | RodFillSchema | DrawersFillSchema, Field(discriminator="type")
]


class DoorSchema(BaseSchema):
    hinge: Literal["left", "right", "double"]


class CellNodeSchema(BaseSchema):
    id: str = Field(min_length=1, max_length=32)
    kind: Literal["cell"]
    fill: FillSchema
    door: DoorSchema | None = None


class SplitChildSchema(BaseSchema):
    # None means "takes an equal share of the remaining space"
    size: int | None = Field(default=None, ge=50, le=3600)
    node: "LayoutNodeSchema"


class SplitNodeSchema(BaseSchema):
    id: str = Field(min_length=1, max_length=32)
    kind: Literal["split"]
    axis: Literal["x", "y"]
    children: list[SplitChildSchema] = Field(min_length=2, max_length=12)
    door: DoorSchema | None = None


type LayoutNodeSchema = Annotated[CellNodeSchema | SplitNodeSchema, Field(discriminator="kind")]


class SizeSchema(BaseSchema):
    width: int = Field(ge=300, le=3600)
    height: int = Field(ge=300, le=2800)
    depth: int = Field(ge=250, le=900)


class MaterialsSchema(BaseSchema):
    body: MaterialEnum
    fronts: MaterialEnum


class FacadeSchema(BaseSchema):
    type: Literal["open", "hinged", "sliding"]
    panels: int = Field(default=2, ge=2, le=4)


class HardwareSchema(BaseSchema):
    # "none" is push-to-open fronts
    handles: Literal["bar", "knob", "none"] = "bar"


class DesignDocumentSchema(BaseSchema):
    schema_version: Literal[1]
    size: SizeSchema
    plinth: int = Field(ge=0, le=200)
    materials: MaterialsSchema
    facade: FacadeSchema
    # Optional: documents saved before it appeared mean bar handles
    hardware: HardwareSchema | None = None
    layout: LayoutNodeSchema

    @model_validator(mode="after")
    def _check_tree(self) -> Self:
        ids: set[str] = set()

        def walk(node: CellNodeSchema | SplitNodeSchema, depth: int) -> None:
            if depth > MAX_DEPTH:
                raise ValueError(f"layout is deeper than {MAX_DEPTH} levels")
            if node.id in ids:
                raise ValueError(f"duplicate node id {node.id!r}")
            ids.add(node.id)
            if len(ids) > MAX_NODES:
                raise ValueError(f"layout has more than {MAX_NODES} nodes")
            if isinstance(node, SplitNodeSchema):
                for child in node.children:
                    walk(child.node, depth + 1)

        walk(self.layout, 1)
        return self


SplitChildSchema.model_rebuild()
