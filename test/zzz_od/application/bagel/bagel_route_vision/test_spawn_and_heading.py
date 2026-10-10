from __future__ import annotations

import cv2
import numpy as np
import pytest
from test.zzz_od.application.bagel.bagel_route_vision.conftest import (
    archived_crop,
    archived_state,
)

from one_dragon.utils import cal_utils
from zzz_od.application.bagel.bagel_minimap import MinimapMatch
from zzz_od.application.bagel.bagel_route_vision import BagelRouteVision


def test_spawn_not_entire_route(vision: BagelRouteVision) -> None:
    """路线末端可定位，但不能再次算作 A 出生。"""
    assert vision.is_at_spawn(archived_crop(7, 30))
    assert not vision.is_at_spawn(archived_crop(7, 32, near_box=True))
    assert not vision.is_at_spawn(archived_crop(2, 32))


def test_competing_regions_check_every_pair(
    vision: BagelRouteVision,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """前两处分区位置相同、第三处偏离时仍须拒绝，不能改图像表示绕过。"""
    image = archived_crop(1, 39)
    x, y = (100 - value for value in vision.map.origin)
    calls: list[int] = []

    def fake_matches(*_args: object) -> tuple[MinimapMatch, ...]:
        """模拟一张底图中的多个合理匹配位置。"""
        calls.append(1)
        return tuple(
            MinimapMatch(((1, 0, 0), (0, 1, 0)), (x + delta, y), 10, 10, 0)
            for delta in (0, 0, 6)
        )

    monkeypatch.setattr(
        'zzz_od.application.bagel.bagel_map_locator.match_feature_regions', fake_matches
    )
    assert vision.locate(image) is None
    assert vision.last_location.reason == 'ambiguous_position'
    assert len(calls) == 1


@pytest.mark.parametrize(
    'state,expected',
    [
        ('雅努斯出生-r01-39s.webp', 0),
        ('雅努斯出生-r07-30s.webp', 0),
        ('雅努斯箱前-r07-32s.webp', 250),
        ('雅努斯转角定位失败-1440缩放.webp', 260),
    ],
)
def test_archived_arrow(vision: BagelRouteVision, state: str, expected: float) -> None:
    """独立截图尖端朝向与人工核对方向一致，容纳低分辨率边缘误差。"""
    angle = vision.player_angle(archived_state(state))
    assert angle is not None
    assert abs(cal_utils.angle_delta(angle, expected)) < 7


@pytest.mark.parametrize('angle', [0, 45, 90, 135, 180, 225, 270, 315])
def test_rotated_arrow(vision: BagelRouteVision, angle: float) -> None:
    """旋转真实箭头检查象限和正负号，覆盖越过零度。"""
    crop = archived_state('雅努斯出生-r01-39s.webp')
    transform = cv2.getRotationMatrix2D((100, 100), -angle, 1)
    rotated = cv2.warpAffine(crop, transform, (201, 201))
    actual = vision.player_angle(rotated)
    assert actual is not None
    assert abs(cal_utils.angle_delta(actual, angle)) < 7


@pytest.mark.parametrize('kind', ['blank', 'uniform', 'missing_arrow', 'wrong_shape'])
def test_unreadable_arrow_stops(vision: BagelRouteVision, kind: str) -> None:
    """空画面、纯色黄色块或只有扇区时不能凭背景猜朝向。"""
    crop = np.zeros((201, 201, 3), np.uint8)
    if kind == 'uniform':
        cv2.circle(crop, (100, 100), 10, (0, 200, 255), -1)
    elif kind == 'missing_arrow':
        crop = archived_state('雅努斯出生-r01-39s.webp')
        crop[80:121, 80:121] = 0
    elif kind == 'wrong_shape':
        crop = crop[:100]
    assert vision.player_angle(crop) is None
