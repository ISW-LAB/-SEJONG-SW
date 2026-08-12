"""지역 내부의 재현 가능한 deterministic jittered-grid 배치."""
from __future__ import annotations

import hashlib
import json
import math
import random

from .models import VegetationGroup, VegetationInstance


def stable_seed(region_name: str, environment: str, area_w: float, area_h: float,
                groups: tuple[VegetationGroup, ...]) -> tuple[int, str]:
    payload = {
        "region": region_name,
        "environment": environment,
        "area": [area_w, area_h],
        "groups": [
            [g.species, g.kind, g.quantity, g.initial_diameter, g.diameter_unit]
            for g in groups
        ],
    }
    serial = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(serial.encode("utf-8")).hexdigest()
    return int(digest[:16], 16), digest


def place_instances(groups: tuple[VegetationGroup, ...], width: float, height: float,
                    seed: int) -> tuple[VegetationInstance, ...]:
    total = sum(g.quantity for g in groups)
    if total <= 0:
        return ()
    width = max(1.0, float(width))
    height = max(1.0, float(height))
    aspect = width / height
    cols = max(1, math.ceil(math.sqrt(total * aspect)))
    rows = max(1, math.ceil(total / cols))
    cell_w, cell_h = width / cols, height / rows
    rng = random.Random(seed)

    slots = list(range(rows * cols))
    rng.shuffle(slots)
    instances: list[VegetationInstance] = []
    instance_id = 0
    for group in groups:
        for _ in range(group.quantity):
            slot = slots[instance_id]
            row, col = divmod(slot, cols)
            jitter_x = rng.uniform(-0.28, 0.28) * cell_w
            jitter_y = rng.uniform(-0.28, 0.28) * cell_h
            x = min(width - 0.02, max(0.02, (col + 0.5) * cell_w + jitter_x))
            y = min(height - 0.02, max(0.02, (row + 0.5) * cell_h + jitter_y))
            instances.append(VegetationInstance(
                instance_id, group.group_id, group.species, group.kind, x, y,
            ))
            instance_id += 1
    return tuple(instances)
