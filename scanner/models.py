from dataclasses import dataclass


@dataclass
class StructureItem:
    type: str | None
    normalized_type: str | None
    depth: int
    title: str | None
    alt: str | None
    kids_count: int
    object_ref: str | None = None
    alt_source: str | None = None
