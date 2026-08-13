"""PyVista/VTK 기반 지역 식생 glyph 렌더러."""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pyvista as pv
from vtkmodules.util.numpy_support import numpy_to_vtk
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkRenderingCore import vtkActor, vtkGlyph3DMapper

from .growth_models import render_states
from .models import RegionVisualizationSnapshot, RenderState
from .species_profiles import profile_by_key


class VegetationRenderer:
    """actor를 재사용하고 point/scale 배열만 갱신하는 glyph renderer."""

    def __init__(self, plotter):
        self.plotter = plotter
        self.snapshot: RegionVisualizationSnapshot | None = None
        self._ground_actor = None
        self._actors: list[vtkActor] = []
        self._datasets: dict[tuple[str, str, int], vtkPolyData] = {}

    def clear(self) -> None:
        for actor in self._actors:
            self.plotter.renderer.RemoveActor(actor)
        self._actors.clear()
        self._datasets.clear()
        if self._ground_actor is not None:
            self.plotter.remove_actor(self._ground_actor)
            self._ground_actor = None
        self.snapshot = None
        self.plotter.render()

    def set_snapshot(self, snapshot: RegionVisualizationSnapshot) -> None:
        self.clear()
        self.snapshot = snapshot
        ground = pv.Plane(
            center=(snapshot.area_w / 2, snapshot.area_h / 2, 0),
            direction=(0, 0, 1),
            i_size=max(1.0, snapshot.area_w),
            j_size=max(1.0, snapshot.area_h),
            i_resolution=max(1, min(20, int(snapshot.area_w))),
            j_resolution=max(1, min(20, int(snapshot.area_h))),
        )
        self._ground_actor = self.plotter.add_mesh(
            ground, color="#B8C99D", show_edges=True, edge_color="#879A72",
            opacity=0.82, pickable=False,
        )
        self._create_glyph_actors(render_states(snapshot, 0))
        self.plotter.show_grid(
            xtitle="X (m)", ytitle="Y (m)", ztitle="높이 (m)",
            bounds=(0, snapshot.area_w, 0, snapshot.area_h, 0, 1),
        )
        self.plotter.view_isometric()
        self.plotter.camera.up = (0.0, 0.0, 1.0)
        self.plotter.reset_camera()
        self.plotter.render()

    @staticmethod
    def _source_for(profile_key: str, component: str, layer: int):
        profile = profile_by_key(profile_key)
        if component == "trunk":
            return pv.Cylinder(
                center=(0, 0, 0), direction=(0, 0, 1), radius=0.5,
                height=1.0, resolution=8, capping=True,
            )
        if profile.shape in ("layered_conifer", "pyramid"):
            resolution = 9 if profile.shape == "pyramid" else 11
            return pv.Cone(
                center=(0, 0, 0), direction=(0, 0, 1), height=1.0,
                radius=0.5, resolution=resolution, capping=True,
            )
        if profile.shape.startswith("shrub_"):
            return pv.Sphere(radius=0.5, theta_resolution=10, phi_resolution=7)
        return pv.Sphere(radius=0.5, theta_resolution=12, phi_resolution=8)

    @staticmethod
    def _polydata(points: np.ndarray, scales: np.ndarray) -> vtkPolyData:
        data = vtkPolyData()
        vtk_points = vtkPoints()
        vtk_points.SetData(numpy_to_vtk(points.astype(np.float32), deep=True))
        data.SetPoints(vtk_points)
        arr = numpy_to_vtk(scales.astype(np.float32), deep=True)
        arr.SetName("scale")
        data.GetPointData().AddArray(arr)
        data.GetPointData().SetActiveVectors("scale")
        return data

    def _add_glyph_actor(self, key: tuple[str, str, int], points: np.ndarray,
                         scales: np.ndarray, color: str, opacity: float) -> None:
        dataset = self._polydata(points, scales)
        mapper = vtkGlyph3DMapper()
        mapper.SetInputData(dataset)
        mapper.SetSourceData(self._source_for(*key))
        mapper.SetScaleArray("scale")
        mapper.SetScaleModeToScaleByVectorComponents()
        mapper.ScalingOn()
        mapper.OrientOff()
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(pv.Color(color).float_rgb)
        actor.GetProperty().SetOpacity(opacity)
        self.plotter.renderer.AddActor(actor)
        self._actors.append(actor)
        self._datasets[key] = dataset

    def _geometry_arrays(self, states: tuple[RenderState, ...]):
        buckets: dict[tuple[str, str, int], tuple[list, list]] = defaultdict(lambda: ([], []))
        for state in states:
            profile = profile_by_key(state.profile_key)
            h = state.rendered_height_m.value
            crown_l = min(h, state.rendered_crown_length_m.value)
            crown_w = state.rendered_crown_width_m.value
            trunk_h = max(0.15, h - crown_l * (0.84 if state.kind == "shrub" else 0.72))
            # 실제 DBH는 계산에 그대로 보존하고, 단순 cylinder가 지나치게 가늘게
            # 보이는 문제만 렌더링 전용 비선형 보정으로 완화한다.
            boost = 1.0 + profile.trunk_visual_boost * np.exp(
                -state.diameter_m / profile.trunk_boost_decay_m
            )
            trunk_d = max(profile.trunk_min_visible_m, state.diameter_m * boost)
            if state.kind == "tree":
                key = (state.profile_key, "trunk", 0)
                buckets[key][0].append((state.x_m, state.y_m, trunk_h / 2))
                buckets[key][1].append((trunk_d, trunk_d, trunk_h))

            layers = max(1, profile.crown_layers)
            for layer in range(layers):
                frac = (layer + 0.5) / layers
                z = max(0.08, h - crown_l + crown_l * frac)
                taper = 1.0 - 0.24 * layer / max(1, layers - 1)
                if profile.shape in (
                    "open_oval", "rounded", "dense_oval", "spreading",
                    "shrub_rounded", "shrub_spreading", "shrub_multistem",
                ):
                    offset = profile.crown_irregularity * crown_w
                    x = state.x_m + offset * np.sin(state.instance_id * 1.73 + layer)
                    y = state.y_m + offset * np.cos(state.instance_id * 1.31 + layer)
                else:
                    x, y = state.x_m, state.y_m
                key = (state.profile_key, "crown", layer)
                buckets[key][0].append((x, y, z))
                width = crown_w * taper
                shrub_shape = profile.shape.startswith("shrub_")
                layer_h = crown_l / (layers * (0.72 if shrub_shape else 0.58))
                buckets[key][1].append((width, width, max(0.18, layer_h)))
        return {
            key: (np.asarray(points, dtype=float), np.asarray(scales, dtype=float))
            for key, (points, scales) in buckets.items()
        }

    def _create_glyph_actors(self, states: tuple[RenderState, ...]) -> None:
        for key, (points, scales) in self._geometry_arrays(states).items():
            profile = profile_by_key(key[0])
            color = "#76543A" if key[1] == "trunk" else profile.color
            opacity = 1.0 if key[1] == "trunk" else profile.opacity
            self._add_glyph_actor(key, points, scales, color, opacity)

    def update_year(self, year: int) -> None:
        if self.snapshot is None:
            return
        arrays = self._geometry_arrays(render_states(self.snapshot, year))
        # snapshot 내 개체/프로파일 구성은 고정이므로 key와 point 수는 연도에 따라 동일하다.
        for key, dataset in self._datasets.items():
            points, scales = arrays[key]
            dataset.GetPoints().SetData(numpy_to_vtk(points.astype(np.float32), deep=True))
            scale_arr = numpy_to_vtk(scales.astype(np.float32), deep=True)
            scale_arr.SetName("scale")
            dataset.GetPointData().RemoveArray("scale")
            dataset.GetPointData().AddArray(scale_arr)
            dataset.GetPointData().SetActiveVectors("scale")
            dataset.Modified()
        self.plotter.render()
