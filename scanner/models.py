from dataclasses import dataclass, field


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
    parent_type: str | None = None
    ancestor_types: list[str] = field(default_factory=list)
    child_types: list[str] = field(default_factory=list)
    attributes: dict[str, object] = field(default_factory=dict)
