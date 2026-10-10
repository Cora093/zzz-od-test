from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest
from test.harness.bagel_storage import BagelDragController as BagelDragController
from test.harness.bagel_storage import WatchedCloseSearch as WatchedCloseSearch
from test.harness.bagel_storage import WatchedDeposit as WatchedDeposit
from test.harness.bagel_storage import _clicks_in_area as _clicks_in_area
from test.harness.bagel_storage import controller as controller
from test.harness.fixture_controller import (
    enter_running_state,
    reset_running_state,
)

from one_dragon.base.operation.operation_round_result import OperationRoundResultEnum
from zzz_od.application.bagel.bagel_app import BagelApp
from zzz_od.application.bagel.bagel_close_search import BagelCloseSearch
from zzz_od.application.bagel.bagel_config import BagelConfig
from zzz_od.application.bagel.bagel_map_model import BagelMapModel
from zzz_od.application.bagel.bagel_navigate import BagelNavigate
from zzz_od.application.bagel.bagel_open_box import BagelOpenBox
from zzz_od.application.bagel.bagel_operation import BagelOperation
from zzz_od.application.bagel.bagel_route_vision import (
    BagelRouteVision,
    BagelSpawnMatcher,
)
from zzz_od.application.bagel.bagel_run_record import BagelRunRecord
from zzz_od.application.bagel.bagel_store import BagelStoreSafe
from zzz_od.application.bagel.bagel_unlock_safe import BagelUnlockSafe

if TYPE_CHECKING:
    from test.conftest import TestContext


@pytest.mark.parametrize(
    'cls,method',
    [
        (BagelNavigate, 'check_start'),
        (BagelNavigate, 'move_to_target'),
        (BagelOpenBox, 'open_box'),
        (BagelOpenBox, 'wait_search'),
        (BagelStoreSafe, 'store_next'),
        (BagelStoreSafe, 'confirm_transfer'),
        (BagelUnlockSafe, 'enter_unlock'),
        (BagelUnlockSafe, 'wait_unlock_ui'),
        (BagelUnlockSafe, 'timing_hits'),
        (BagelUnlockSafe, 'wait_search'),
        (BagelCloseSearch, 'close_panel'),
    ],
)
def test_defeat_interrupts_local_actions(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
    cls: type[BagelOperation],
    method: str,
) -> None:
    """真实失败结算必须优先于导航、补按 F 和拖拽等动作。"""
    test_context.mock_screen('贝果-结算', '高危空局失败-原生1080')
    op = cls(test_context)
    op.screenshot()
    monkeypatch.setattr(
        test_context.controller, 'stop_moving_forward', MagicMock(), raising=False
    )
    for name in ('move_w', 'interact', 'drag_to', 'click'):
        monkeypatch.setattr(test_context.controller, name, MagicMock(), raising=False)
    result = getattr(op, method)()
    assert result.is_fail and result.status == BagelOperation.STATUS_DEFEATED
    if method == 'move_to_target':
        test_context.controller.stop_moving_forward.assert_called()
    for name in ('move_w', 'interact', 'drag_to', 'click'):
        getattr(test_context.controller, name).assert_not_called()


@pytest.mark.parametrize(
    'screen,state,defeated',
    [
        ('贝果-结算', '空局失败-原生1080', True),
        ('贝果-局内', '雅努斯出生-r01-39s', False),
    ],
)
def test_defeat_does_not_require_map_title(
    test_context: TestContext,
    screen: str,
    state: str,
    defeated: bool,
) -> None:
    """困难结算同样识别为失败，正常局内不能误判。"""
    test_context.mock_screen(screen, state)
    op = BagelOpenBox(test_context)
    op.screenshot()
    assert op.is_bagel_result() is defeated


@pytest.mark.parametrize('map_id', ['janus_high_a', 'janus_high_b'])
def test_map_projection_matches_navigation(map_id: str) -> None:
    """投影参考帧中心与运行定位一致，透明区不能冒充可通行区。"""
    root = Path(__file__).parent / 'bagel_fixed_map/data'
    model = BagelMapModel.load(map_id)
    vision = BagelRouteVision(map_id)
    assert model.reference_centers
    assert np.any(model.coverage == 0)
    assert np.all(model.rgba[:, :, 3][model.coverage == 0] == 0)
    for name, center in model.reference_centers:
        path = root / map_id / f'reference_{name}.png'
        image = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
        located = vision.locate(image)
        assert located is not None
        assert np.linalg.norm(np.asarray(located) - center) < 2
    spawn = root / map_id / 'reference_spawn.png'
    assert (
        BagelSpawnMatcher().match(
            cv2.imdecode(np.fromfile(spawn, np.uint8), cv2.IMREAD_COLOR)
        )
        == map_id
    )


def test_spawn_hud_ocr_gap_recovers(test_context: TestContext, monkeypatch) -> None:
    """入场后单帧普通攻击按钮漏识别不应直接结束整局。"""
    app = BagelApp(test_context, BagelConfig(1, 'one_dragon'), BagelRunRecord(1))
    match = MagicMock(return_value='janus_high_a')
    monkeypatch.setattr(app, '_spawn_matcher', lambda: MagicMock(match=match))
    monkeypatch.setattr(app, 'round_by_find_area', lambda *_: app.round_fail('漏识别'))
    assert app.check_spawn().result == OperationRoundResultEnum.WAIT
    assert app.attempts == 0
    test_context.mock_screen('贝果-局内', '雅努斯出生-r01-39s')
    app.screenshot()
    monkeypatch.setattr(
        app,
        'round_by_find_area',
        lambda _image, _screen, area: (
            app.round_success() if area == '按键-普通攻击' else app.round_fail('未命中')
        ),
    )
    assert app.check_spawn().status == BagelApp.STATUS_A
    assert app.attempts == 1


def test_spawn_unknown_screen_stops_after_limit(
    test_context: TestContext, monkeypatch
) -> None:
    """持续未知画面仍留现场，不算非支持出生点。"""
    app = BagelApp(test_context, BagelConfig(1, 'one_dragon'), BagelRunRecord(1))
    monkeypatch.setattr(app, 'round_by_find_area', lambda *_: app.round_fail('未知'))
    for _ in range(3):
        assert app.check_spawn().result == OperationRoundResultEnum.WAIT
    from zzz_od.application.bagel.bagel_operation import BagelOperation

    result = app.check_spawn()
    assert result.status == BagelOperation.STATUS_ROUND_FAILED
    assert result.data == '未识别贝果局内画面'
    assert app.attempts == 0


def test_close_waits_and_retries_before_confirming_hud(
    test_context: TestContext,
    controller: BagelDragController,
) -> None:
    """搜查中等待，首次关闭未生效时再次关闭，看到 HUD 才结束。"""
    controller.set_phases(
        [
            {'frame': ('贝果-局内', '武备箱搜查中-r07'), 'exit': ('on_polls', 2)},
            {
                'frame': ('贝果-局内', '武备箱已入箱-实机'),
                'exit': ('on_click_in', '贝果-局内', '搜查返回'),
            },
            {
                'frame': ('贝果-局内', '武备箱已入箱-实机'),
                'exit': ('on_click_in', '贝果-局内', '搜查返回'),
            },
            {'frame': ('贝果-局内', '高危A出生-原生1080')},
        ]
    )
    op = WatchedCloseSearch(test_context)
    enter_running_state(test_context)
    try:
        assert op.execute().success
        assert controller.phase_idx == 3
        assert len(controller.recorded_clicks) == 2
        assert controller.recorded_drags == []
        assert controller.recorded_inputs == []
    finally:
        reset_running_state(test_context, op)


def test_full_capacity_and_empty_safe_without_growth_is_unproven(
    test_context: TestContext,
    controller: BagelDragController,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """满仓点击后箱空而占用没变，不靠堆叠推测计成功。"""
    controller.set_phases(
        [
            {
                'frame': ('贝果-仓库', '带物资仓库-r07-117s'),
                'exit': ('on_click_in', '贝果-仓库', '放入仓库'),
            },
            {'frame': ('贝果-仓库', '入仓后安全箱空-r07-118s')},
        ]
    )
    op = WatchedDeposit(test_context)
    monkeypatch.setattr(op, '_warehouse_pair', lambda: (280, 280))
    enter_running_state(test_context)
    try:
        result = op.execute()
        assert not result.success
        assert '不能证明物资已入仓' in result.status
        assert _clicks_in_area(test_context, controller, '放入仓库') == 1
    finally:
        reset_running_state(test_context, op)
