from typing import Any

WARDROBE_DOCUMENT: dict[str, Any] = {
    "schemaVersion": 1,
    "size": {"width": 1800, "height": 2400, "depth": 600},
    "plinth": 80,
    "materials": {"body": "oak", "fronts": "sage"},
    "facade": {"type": "hinged", "panels": 2},
    "layout": {
        "id": "root",
        "kind": "split",
        "axis": "x",
        "door": None,
        "children": [
            {
                "size": None,
                "node": {
                    "id": "a",
                    "kind": "split",
                    "axis": "y",
                    "door": {"hinge": "left"},
                    "children": [
                        {
                            "size": 400,
                            "node": {"id": "a1", "kind": "cell", "fill": {"type": "shelves", "count": 1}, "door": None},
                        },
                        {"size": None, "node": {"id": "a2", "kind": "cell", "fill": {"type": "rod"}, "door": None}},
                    ],
                },
            },
            {"size": 600, "node": {"id": "b", "kind": "cell", "fill": {"type": "drawers", "count": 3}, "door": None}},
        ],
    },
}
