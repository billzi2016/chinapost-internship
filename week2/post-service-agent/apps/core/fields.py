from __future__ import annotations

import json

from django.db import models


class VectorField(models.Field):
    description = "pgvector vector field with SQLite text fallback"

    def __init__(self, dimensions: int, *args, **kwargs) -> None:
        self.dimensions = dimensions
        super().__init__(*args, **kwargs)

    def db_type(self, connection) -> str:
        if connection.vendor == "postgresql":
            return f"vector({self.dimensions})"
        return "text"

    def from_db_value(self, value, expression, connection):
        if value is None or isinstance(value, list):
            return value
        text = str(value).strip()
        if text.startswith("["):
            return [float(item) for item in text.strip("[]").split(",") if item]
        return json.loads(text)

    def get_prep_value(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return "[" + ",".join(str(float(item)) for item in value) + "]"

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["dimensions"] = self.dimensions
        return name, path, args, kwargs
