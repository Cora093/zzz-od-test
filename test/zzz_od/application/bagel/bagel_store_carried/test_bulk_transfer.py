from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from test.harness.bagel_loadout import (
    WatchedStore,
    paint_count,
    running_operation,
    warehouse_frames,
)
from test.harness.bagel_loadout import controller as controller
from test.harness.bagel_safe_slots import lock_safe_suffix

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_round_result import OperationRoundResultEnum
from zzz_od.application.bagel.bagel_store_carried import (
    WAREHOUSE_SAFE_CENTERS,
    BagelStoreCarried,
    backpack_centers,
    read_carried_backpack,
)
from zzz_od.application.bagel.bagel_transfer import carried_slot_state

if TYPE_CHECKING:
    from test.conftest import TestContext
    from test.harness.bagel_loadout import TransferController


@pytest.mark.parametrize(
    'state,expected',
    [
        ('clear_loadout_backpack_carried', 2),
        ('clear_loadout_prepare_warehouse_empty', 0),
    ],
)
def test_warehouse_recording(
    test_context: TestContext, state: str, expected: int
) -> None:
    """仓库只定位左侧完整格子行，不把右侧库存当作携带物。"""
    screen = test_context.load_screen('贝果-仓库', state)
    op = BagelStoreCarried(test_context)
    # 有物帧的录像鼠标遮住「仓」字，必须等待新帧，不能放宽为模糊仓库匹配。
    assert op.round_by_find_area(screen, '贝果-仓库', '放入仓库').is_success is (
        expected == 0
    )
    centers = backpack_centers(screen)
    assert len(centers) == 30
    assert (
        sum(carried_slot_state(screen, center) is True for center in centers)
        == expected
    )
    assert all(
        carried_slot_state(screen, center) is False for center in WAREHOUSE_SAFE_CENTERS
    )


def test_settlement_rewards_are_not_backpack_items(test_context: TestContext) -> None:
    """撤离奖励会推低背包标题；格子定位不得包含上方奖励物品。"""
    screen = test_context.load_screen('贝果-仓库', '满仓安全箱余一件-20260924')
    info = read_carried_backpack(test_context, screen)
    assert info is not None and info[0] == (0, 20)
    assert info[1] > 300
    centers = backpack_centers(screen, info[1])
    assert centers and all(center.y > 350 for center in centers)


@pytest.mark.parametrize('safe', [False, True])
def test_bulk_transfer_and_stacking(
    test_context: TestContext,
    controller: TransferController,
    safe: bool,
) -> None:
    """一次批量按钮清空背包和安全箱；已有堆叠允许仓库占用不变。"""
    before, _, done = warehouse_frames(test_context)
    before, done = before.copy(), done.copy()
    paint_count(test_context, done, '贝果-仓库', '仓库数量', '186/280')
    if safe:
        x, y = WAREHOUSE_SAFE_CENTERS[0].tuple()
        before[y - 40 : y + 40, x - 40 : x + 40] = before[187:267, 227:307]
    controller.set_phases(
        [
            {'frame': before, 'exit': ('on_click_in', '贝果-仓库', '放入仓库')},
            {'frame': done},
        ]
    )
    op = WatchedStore(test_context)
    with running_operation(op):
        result = op.execute()
        assert result.success, result.status
        assert result.data['moved'] == (3 if safe else 2)
        assert len(controller.recorded_clicks) == 1
        assert not controller.recorded_scrolls


@pytest.mark.parametrize(
    'kind',
    ['unchanged', 'partial', 'warehouse_decreased', 'wrong_container', 'capacity'],
)
def test_unconfirmed_bulk_transfer_stops_without_reclick(
    test_context: TestContext,
    controller: TransferController,
    kind: str,
) -> None:
    """无变化、部分入仓、数量异常均停止；批量按钮始终只点一次。"""
    frames = warehouse_frames(test_context)
    after = frames[0].copy() if kind == 'unchanged' else frames[1].copy()
    if kind == 'warehouse_decreased':
        paint_count(test_context, after, '贝果-仓库', '仓库数量', '185/280')
    elif kind == 'wrong_container':
        x, y = WAREHOUSE_SAFE_CENTERS[0].tuple()
        after[y - 40 : y + 40, x - 40 : x + 40] = frames[0][187:267, 227:307]
    elif kind == 'capacity':
        paint_count(test_context, after, '贝果-仓库', '背包数量', '1/20')
    controller.set_phases(
        [
            {'frame': frames[0], 'exit': ('on_click_in', '贝果-仓库', '放入仓库')},
            {'frame': after},
        ]
    )
    op = WatchedStore(test_context)
    with running_operation(op):
        result = op.execute()
        assert not result.success
        assert len(controller.recorded_clicks) == 1
        assert op.moved == (1 if kind == 'partial' else 0)


def test_full_warehouse_does_not_click(
    test_context: TestContext, controller: TransferController
) -> None:
    """满仓不出售腾位，也不尝试批量入仓。"""
    screen = warehouse_frames(test_context)[0].copy()
    paint_count(test_context, screen, '贝果-仓库', '仓库数量', '280/280')
    controller.set_phases([{'frame': screen}])
    op = WatchedStore(test_context)
    with running_operation(op):
        result = op.execute()
        assert not result.success and '仓库已满' in result.status
        assert not controller.recorded_clicks


def test_offscreen_items_use_bulk_button_without_scrolling(
    test_context: TestContext,
    controller: TransferController,
) -> None:
    """总占用非零但物品不在可见页时仍直接批量入仓，无须翻页。"""
    done = warehouse_frames(test_context)[2]
    offscreen = done.copy()
    paint_count(test_context, offscreen, '贝果-仓库', '背包数量', '6/50')
    controller.set_phases(
        [
            {'frame': offscreen, 'exit': ('on_click_in', '贝果-仓库', '放入仓库')},
            {'frame': done},
        ]
    )
    op = WatchedStore(test_context)
    with running_operation(op):
        result = op.execute()
        assert result.success, result.status
        assert result.data['moved'] == 6
        assert not controller.recorded_scrolls
        assert len(controller.recorded_clicks) == 1


def test_settlement_only_moves_safe_item_not_reward(
    test_context: TestContext,
    controller: TransferController,
) -> None:
    """带撤离奖励的仓库仍只转存安全箱；奖励由原有返回流程处理。"""
    before = test_context.load_screen('贝果-仓库', '满仓安全箱余一件-20260924').copy()
    paint_count(test_context, before, '贝果-仓库', '仓库数量', '279/280')
    after = before.copy()
    source = WAREHOUSE_SAFE_CENTERS[4]
    x, y = source.tuple()
    after[y - 40 : y + 40, x - 40 : x + 40] = before[857:937, 227:307]
    paint_count(test_context, after, '贝果-仓库', '仓库数量', '280/280')
    controller.set_phases(
        [
            {'frame': before, 'exit': ('on_click_in', '贝果-仓库', '放入仓库')},
            {'frame': after},
        ]
    )
    op = WatchedStore(test_context)
    with running_operation(op):
        result = op.execute()
        assert result.success, result.status
        assert result.data['moved'] == 1
        assert len(controller.recorded_clicks) == 1
        assert controller.recorded_clicks[0].tuple() != source.tuple()


def test_bulk_result_can_arrive_late(
    test_context: TestContext,
    controller: TransferController,
) -> None:
    """批量按钮点击后短暂旧帧只等待，结果出现后核验完成，不补点。"""
    before, _, after = warehouse_frames(test_context)
    controller.set_phases(
        [
            {'frame': before, 'exit': ('on_click_in', '贝果-仓库', '放入仓库')},
            {'frame': before, 'exit': ('on_polls', 2)},
            {'frame': after},
        ]
    )
    op = WatchedStore(test_context)
    with running_operation(op):
        result = op.execute()
        assert result.success, result.status
        assert result.data['moved'] == 2
        assert len(controller.recorded_clicks) == 1


def test_pause_after_storage_click_only_checks_result(
    test_context: TestContext,
    controller: TransferController,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """批量按钮点击后暂停恢复，仅核对结果，不再次点击。"""
    before, _, after = warehouse_frames(test_context)
    controller.set_phases(
        [
            {'frame': before, 'exit': ('on_click_in', '贝果-仓库', '放入仓库')},
            {'frame': after},
        ]
    )
    op = WatchedStore(test_context)
    original = controller.click

    def pause_click(pos: Point, press_time: float = 0, **kwargs: object) -> bool:
        """按钮点击后模拟暂停并恢复。"""
        result = original(pos, press_time, **kwargs)
        op.handle_pause()
        op.handle_resume()
        return result

    monkeypatch.setattr(controller, 'click', pause_click)
    with running_operation(op):
        result = op.execute()
        assert result.success, result.status
        assert result.data['moved'] == 2
        assert len(controller.recorded_clicks) == 1


@pytest.mark.parametrize('after_click', [False, True])
@pytest.mark.parametrize(
    'kind,reason',
    [
        ('occupied', '背包格子与占用数不符'),
        ('unknown', '背包格子状态不清'),
        ('missing_rows', '无法定位背包完整格子行'),
    ],
)
def test_zero_count_with_unconfirmed_slots_stops(
    test_context: TestContext,
    controller: TransferController,
    kind: str,
    reason: str,
    after_click: bool,
) -> None:
    """数量模拟为零时仍核验真实格子；持续冲突或未知五帧后停止，不误报转存成功。"""
    before, _, empty = warehouse_frames(test_context)
    screen = before.copy() if kind == 'occupied' else empty.copy()
    paint_count(test_context, screen, '贝果-仓库', '背包数量', '0/50')
    if kind == 'unknown':
        screen[198:258, 237:297] = 0
    elif kind == 'missing_rows':
        screen[160:780, 210:850] = 20
    phases = [{'frame': screen}]
    if after_click:
        phases.insert(
            0, {'frame': before, 'exit': ('on_click_in', '贝果-仓库', '放入仓库')}
        )
    controller.set_phases(phases)
    op = WatchedStore(test_context)
    with running_operation(op):
        result = op.execute()
        assert not result.success and reason in result.status
        assert op.read_misses == 5
        assert op.moved == 0
        assert op._stable_image is None
        assert len(controller.recorded_clicks) == (1 if after_click else 0)
        assert not controller.recorded_scrolls


@pytest.mark.parametrize('kind', ['unchanged', 'partial', 'empty_retry'])
def test_recovery_transfer_returns_remaining_without_extra_click(
    test_context: TestContext,
    controller: TransferController,
    kind: str,
) -> None:
    """启动转存用稳定两帧报告残留；出售后即使空包也只补点一次。"""
    before, partial, empty = warehouse_frames(test_context)
    if kind == 'empty_retry':
        controller.set_phases([{'frame': empty}])
    else:
        controller.set_phases(
            [
                {'frame': before, 'exit': ('on_click_in', '贝果-仓库', '放入仓库')},
                {'frame': before if kind == 'unchanged' else partial},
            ]
        )
    op = WatchedStore(
        test_context, return_on_remaining=True, click_when_empty=kind == 'empty_retry'
    )
    with running_operation(op):
        result = op.execute()
    assert result.success, result.status
    assert result.status == (
        '携带物已全部转存' if kind == 'empty_retry' else '仓库已满'
    )
    assert len(controller.recorded_clicks) == 1


@pytest.mark.parametrize('pending', [False, True])
def test_warehouse_animation_does_not_block_bulk_transfer(
    test_context: TestContext,
    controller: TransferController,
    pending: bool,
) -> None:
    """两张真实动画帧用于批量按钮；已发送输入时不得补点。"""
    before = test_context.load_screen('贝果-仓库', 'clear_carried_six_before')
    after = test_context.load_screen('贝果-仓库', 'clear_carried_six_animation')
    controller.set_phases(
        [{'frame': after, 'exit': ('on_click_in', '贝果-仓库', '放入仓库')}]
    )
    op = WatchedStore(test_context)
    if pending:
        op.pending = True
        op.pending_started = time.monotonic()
        op.before_counts = (6, 0, 182, 50, 280)
    with running_operation(op):
        op.last_screenshot = before
        assert op.store_next().status == (
            '等待转存后格子稳定' if pending else '等待仓库格子稳定'
        )
        op.last_screenshot = after
        result = op.store_next()
        assert result.status == (
            '入仓操作后物品未完整转出，等待核对' if pending else '等待批量入仓结果'
        )
        assert len(controller.recorded_clicks) == (0 if pending else 1)
        assert op.moved == 0


@pytest.mark.parametrize('change', ['unknown', 'occupied', 'count', 'layout', 'page'])
def test_warehouse_requires_consecutive_complete_observations(
    test_context: TestContext,
    controller: TransferController,
    change: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """数量、占用、布局变化及未知帧必须打断稳定记录，不能提前批量入仓。"""
    screen = test_context.load_screen('贝果-仓库', 'clear_carried_six_before')
    changed = screen.copy()
    if change == 'unknown':
        changed[320:380, 237:297] = 0
    elif change == 'occupied':
        changed[320:380, 237:297] = screen[198:258, 237:297]
        changed[198:258, 237:297] = screen[320:380, 237:297]
    elif change == 'count':
        paint_count(test_context, changed, '贝果-仓库', '仓库数量', '?')
    elif change == 'layout':
        changed[172:768, 210:850] = screen[180:776, 210:850]
    controller.set_phases(
        [{'frame': screen, 'exit': ('on_click_in', '贝果-仓库', '放入仓库')}]
    )
    op = WatchedStore(test_context)
    with running_operation(op):
        op.last_screenshot = screen
        assert op.store_next().status == '等待仓库格子稳定'
        op.last_screenshot = changed
        if change == 'page':
            with monkeypatch.context() as patch:
                patch.setattr(op, 'round_by_find_area', lambda *_: op.round_retry())
                assert not op.store_next().is_success
        else:
            assert not op.store_next().is_success
        op.last_screenshot = screen
        assert op.store_next().status == '等待仓库格子稳定'
        assert not controller.recorded_clicks
        op.last_screenshot = screen.copy()
        assert op.store_next().status == '等待批量入仓结果'
        assert len(controller.recorded_clicks) == 1


@pytest.mark.parametrize(
    'state',
    [
        '仓库批量出售中',
        '仓库快速选择',
        '出售二次确认-20260921',
        '出售获得硬币-20260921',
    ],
)
@pytest.mark.parametrize('pending', [False, True])
def test_sale_state_stops_before_transfer_or_success(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
    pending: bool,
) -> None:
    """空箱也不能在出售状态报告完成；转存后遇到出售界面同样停止。"""
    test_context.mock_screen('贝果-仓库', state)
    click = MagicMock()
    monkeypatch.setattr(test_context.controller, 'click', click)
    op = BagelStoreCarried(test_context)
    op.pending = pending
    op.moved = 2
    op.screenshot()
    result = op.store_next()
    assert result.is_fail and '出售状态' in result.status
    assert op.moved == 2
    assert op._stable_image is None
    click.assert_not_called()


@pytest.mark.parametrize('pending', [False, True])
def test_empty_backpack_requires_two_verified_frames(
    test_context: TestContext,
    controller: TransferController,
    pending: bool,
) -> None:
    """真实空包与空安全箱连续两帧核验后才完成；已点击时同时核对转存数量。"""
    screen = test_context.load_screen(
        '贝果-仓库', 'clear_loadout_prepare_warehouse_empty'
    )
    controller.set_phases([{'frame': screen}])
    op = WatchedStore(test_context)
    if pending:
        op.pending = True
        op.pending_started = time.monotonic()
        op.before_counts = (2, 0, 186, 50, 280)
    with running_operation(op):
        op.last_screenshot = screen
        first = op.store_next()
        assert first.result == OperationRoundResultEnum.WAIT
        assert first.status == ('等待转存后格子稳定' if pending else '等待仓库格子稳定')
        op.last_screenshot = screen.copy()
        result = op.store_next()
        assert result.is_success and result.status == '携带物已全部转存'
        assert result.data == {'moved': 2 if pending else 0, 'warehouse': (188, 280)}
        assert not controller.recorded_clicks


@pytest.mark.parametrize(
    'kind,reason',
    [
        ('occupied', '背包格子与占用数不符'),
        ('unknown', '背包格子状态不清'),
        ('missing_rows', '无法定位背包完整格子行'),
    ],
)
def test_invalid_zero_count_frame_breaks_empty_backpack_stability(
    test_context: TestContext,
    controller: TransferController,
    kind: str,
    reason: str,
) -> None:
    """零读数下出现冲突、未知或定位失败后，必须重新取得连续两张完整空包帧。"""
    empty = test_context.load_screen(
        '贝果-仓库', 'clear_loadout_prepare_warehouse_empty'
    )
    changed = empty.copy()
    if kind == 'occupied':
        changed = test_context.load_screen(
            '贝果-仓库', 'clear_carried_six_before'
        ).copy()
        paint_count(test_context, changed, '贝果-仓库', '背包数量', '0/50')
    elif kind == 'unknown':
        changed[198:258, 237:297] = 0
    else:
        changed[160:780, 210:850] = 20
    controller.set_phases([{'frame': empty}])
    op = WatchedStore(test_context)
    with running_operation(op):
        op.last_screenshot = empty
        assert op.store_next().status == '等待仓库格子稳定'
        op.last_screenshot = changed
        result = op.store_next()
        assert result.result == OperationRoundResultEnum.WAIT
        assert result.status == reason
        assert op._stable_image is None
        op.last_screenshot = empty
        assert op.store_next().status == '等待仓库格子稳定'
        op.last_screenshot = empty.copy()
        assert op.store_next().is_success
        assert not controller.recorded_clicks


@pytest.mark.parametrize('capacity', [2, 5])
@pytest.mark.parametrize('unknown', [False, True])
def test_startup_clear_distinguishes_locked_from_unknown(
    test_context: TestContext,
    controller: TransferController,
    capacity: int,
    unknown: bool,
) -> None:
    """空仓库中的锁格不算携带物，未知格则用完五帧预算后停止。"""
    screen = lock_safe_suffix(
        test_context.load_screen('贝果-仓库', 'clear_loadout_prepare_warehouse_empty'),
        capacity,
        WAREHOUSE_SAFE_CENTERS,
    )
    if unknown:
        center = WAREHOUSE_SAFE_CENTERS[0]
        screen[center.y - 48 : center.y + 48, center.x - 48 : center.x + 48] = 0
    controller.set_phases([{'frame': screen}])
    op = BagelStoreCarried(test_context)
    with running_operation(op):
        op.last_screenshot = screen
        result = op.store_next()
        for _ in range(4 if unknown else 1):
            result = op.store_next()
    if unknown:
        assert result.is_fail and '无法完整识别' in result.status
    else:
        assert result.is_success and result.status == '携带物已全部转存'
    assert controller.recorded_clicks == []
