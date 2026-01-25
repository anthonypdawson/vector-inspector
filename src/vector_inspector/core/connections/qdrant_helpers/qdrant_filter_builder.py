from typing import Any
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchText, MatchAny, MatchExcept, Range


def build_filter(where: dict[str, Any] | None = None) -> Filter | None:
    """Build a Qdrant `Filter` from a Chroma-style `where` dict.

    This mirrors the previous inline logic in `QdrantConnection._build_qdrant_filter`.
    """
    if not where:
        return None

    try:
        must_conditions: list[FieldCondition] = []
        must_not_conditions: list[FieldCondition] = []

        for key, value in where.items():
            if isinstance(value, dict):
                for op, val in value.items():
                    if op == "$eq":
                        must_conditions.append(FieldCondition(key=key, match=MatchValue(value=val)))
                    elif op == "$ne":
                        must_not_conditions.append(FieldCondition(key=key, match=MatchValue(value=val)))
                    elif op == "$in":
                        must_conditions.append(FieldCondition(key=key, match=MatchAny(any=val)))
                    elif op == "$nin":
                        must_conditions.append(FieldCondition(key=key, match=MatchExcept(**{"except": val})))
                    elif op == "$contains":
                        must_conditions.append(FieldCondition(key=key, match=MatchText(text=str(val))))
                    elif op == "$not_contains":
                        must_not_conditions.append(FieldCondition(key=key, match=MatchText(text=str(val))))
                    elif op in ["$gt", "$gte", "$lt", "$lte"]:
                        range_args = {}
                        if op == "$gt":
                            range_args["gt"] = val
                        elif op == "$gte":
                            range_args["gte"] = val
                        elif op == "$lt":
                            range_args["lt"] = val
                        elif op == "$lte":
                            range_args["lte"] = val
                        must_conditions.append(FieldCondition(key=key, range=Range(**range_args)))
            else:
                must_conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

        if must_conditions or must_not_conditions:
            return Filter(must=must_conditions if must_conditions else None,
                          must_not=must_not_conditions if must_not_conditions else None)
        return None
    except Exception:
        return None
