from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from test.harness.bagel_loadout import (
    WatchedClear,
    paint_count,
    running_operation,
    unload_frames,
    warehouse_frames,
)
from test.harness.bagel_loadout import controller as controller

from zzz_od.application.bagel.bagel_clear_loadout import (
    LOADOUT_CENTERS,
)
from zzz_od.application.bagel.bagel_store_carried import (
    WAREHOUSE_SAFE_CENTERS,
)

if TYPE_CHECKING:
    from test.conftest import TestContext
    from test.harness.bagel_loadout import TransferController

import time

from test.harness.bagel_loadout import (
    detail_frame,
)

from one_dragon.base.geometry.point import Point


def test_complete_clear_flow(
    test_context: TestContext, controller: TransferController
) -> None:
    """完整跑图验证先清内容物、逐格卸装、返回备战并全零；不点前往空洞。"""
    warehouse = warehouse_frames(test_context)
    equipment = unload_frames(test_context)
    controller.set_phases(
        [
            {
                'frame': ('贝果-备战', 'clear_loadout_carried'),
                'exit': ('on_click_in', [180, 980, 450, 1060]),
            },
            {'frame': warehouse[0], 'exit': ('on_click_in', '贝果-仓库', '放入仓库')},
            {'frame': warehouse[2], 'exit': ('on_click_in', '菜单', '返回')},
            *[
                {'frame': equipment[i], 'exit': ('transfer', center)}
                for i, center in enumerate(LOADOUT_CENTERS)
            ],
            {'frame': equipment[-1]},
        ]
    )
    op = WatchedClear(test_context)
    with running_operation(op):
        result = op.execute()
        assert result.success, result.status
        assert result.data['moved'] == 12
        assert (
            len(controller.recorded_clicks) == 23
        )  # 导航两下、批量入仓一下、十件装备各两下。
        assert controller.phase_idx == 23
        assert not controller.recorded_scrolls


@pytest.mark.parametrize('start_index', [6])
def test_empty_containers_skip_warehouse_and_unload(
    test_context: TestContext,
    controller: TransferController,
    start_index: int,
) -> None:
    """背包 0/50 或 0/20 且安全箱为空时，完整流程只点击已装备槽。"""
    frames = unload_frames(test_context)
    centers = LOADOUT_CENTERS[start_index:]
    controller.set_phases(
        [
            *[
                {'frame': frames[i], 'exit': ('transfer', LOADOUT_CENTERS[i])}
                for i in range(start_index, len(LOADOUT_CENTERS))
            ],
            {'frame': frames[-1]},
        ]
    )
    op = WatchedClear(test_context)
    with running_operation(op):
        result = op.execute()
        assert result.success and result.status == '战备已全部清空'
        assert result.data['moved'] == len(centers)
        assert [pos.tuple() for pos in controller.recorded_clicks] == [
            center.tuple() for center in centers for _ in range(2)
        ]


def test_empty_backpack_with_safe_item_still_visits_warehouse(
    test_context: TestContext,
    controller: TransferController,
) -> None:
    """背包空但安全箱非空时仍先批量转存，再卸下剩余道具。"""
    equipment = unload_frames(test_context)
    prepare = equipment[-2].copy()
    paint_count(test_context, prepare, '贝果-备战', '安全箱数量', '1/5')
    warehouse = warehouse_frames(test_context)
    before, after = warehouse[2].copy(), warehouse[2].copy()
    x, y = WAREHOUSE_SAFE_CENTERS[0].tuple()
    before[y - 40 : y + 40, x - 40 : x + 40] = warehouse[0][187:267, 227:307]
    for screen in (before, after):
        paint_count(test_context, screen, '贝果-仓库', '背包数量', '0/20')
    controller.set_phases(
        [
            {'frame': prepare, 'exit': ('on_click_in', [180, 980, 450, 1060])},
            {'frame': before, 'exit': ('on_click_in', '贝果-仓库', '放入仓库')},
            {'frame': after, 'exit': ('on_click_in', '菜单', '返回')},
            {'frame': equipment[-2], 'exit': ('transfer', LOADOUT_CENTERS[-1])},
            {'frame': equipment[-1]},
        ]
    )
    op = WatchedClear(test_context)
    with running_operation(op):
        result = op.execute()
        assert result.success, result.status
        assert result.data['moved'] == 2
        assert len(controller.recorded_clicks) == 5
        assert controller.phase_idx == 5


def test_unknown_prepare_never_clicks(
    test_context: TestContext,
    controller: TransferController,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """有一项未知时先重读，持续失败也不会清空其它已识别物品。"""
    controller.set_phases([{'frame': ('贝果-备战', 'clear_loadout_carried')}])
    monkeypatch.setattr(
        'zzz_od.application.bagel.bagel_clear_loadout.read_loadout',
        MagicMock(return_value={}),
    )
    op = WatchedClear(test_context)
    with running_operation(op):
        result = op.execute()
        assert not result.success and '五项携带识别不完整' in result.status
        assert not controller.recorded_clicks


def test_no_room_for_equipment_stops_in_warehouse(
    test_context: TestContext,
    controller: TransferController,
) -> None:
    """内容物虽已转存，剩余空位不足时不能再尝试卸装或出售。"""
    warehouse = warehouse_frames(test_context)[2].copy()
    paint_count(test_context, warehouse, '贝果-仓库', '仓库数量', '279/280')
    prepare = test_context.load_screen('贝果-备战', 'clear_loadout_tools_only').copy()
    paint_count(test_context, prepare, '贝果-备战', '背包数量', '2/20')
    backpack_view = prepare.copy()
    backpack_view[:, :960] = test_context.load_screen(
        '贝果-备战', 'clear_loadout_carried'
    )[:, :960]
    controller.set_phases(
        [
            {'frame': prepare, 'exit': ('on_click_in', [1490, 800, 1620, 850])},
            # 模拟切回背包视图后出现前往仓库，再进入只有一个空位的仓库。
            {'frame': backpack_view, 'exit': ('on_click_in', [180, 980, 450, 1060])},
            {'frame': warehouse},
        ]
    )
    op = WatchedClear(test_context)
    with running_operation(op):
        result = op.execute()
        assert not result.success and '仓库空位不足' in result.status
        assert len(controller.recorded_clicks) == 2


@pytest.mark.parametrize(
    'kind', ['unchanged', 'detail', 'wrong_value', 'wrong_container']
)
def test_double_click_unconfirmed_result_stops_after_allowed_retry(
    test_context: TestContext,
    controller: TransferController,
    kind: str,
) -> None:
    """无变化只重试一次；停在详情或去向异常不重试。"""
    frames = unload_frames(test_context)
    before, after = frames[-2], frames[-1].copy()
    source = LOADOUT_CENTERS[-1]
    if kind == 'unchanged':
        after = before
    elif kind == 'detail':
        after = detail_frame(test_context, before, source)
    elif kind == 'wrong_value':
        paint_count(test_context, after, '贝果-备战', '道具价值', '3000')
    else:
        paint_count(test_context, after, '贝果-备战', '背包数量', '1/20')
    phases = [{'frame': before, 'exit': ('transfer', source)}]
    if kind == 'unchanged':
        phases.append({'frame': after, 'exit': ('transfer', source)})
    phases.append({'frame': after})
    controller.set_phases(phases)
    op = WatchedClear(test_context)
    with running_operation(op):
        for _ in range(30):
            op.screenshot()
            result = op.unload_next()
            if result.is_fail:
                break
        assert result.is_fail, result.status
        assert len(controller.recorded_clicks) == (4 if kind == 'unchanged' else 2)
        assert all(pos.tuple() == source.tuple() for pos in controller.recorded_clicks)
        assert op.moved == 0


def test_each_slot_can_retry_once_after_confirmed_no_change(
    test_context: TestContext,
    controller: TransferController,
) -> None:
    """两件道具均首次双击未生效、重试成功，各自只有一次重试额度。"""
    frames = unload_frames(test_context)
    phases: list[dict] = []
    for index in (-3, -2):
        source = LOADOUT_CENTERS[index + 1]
        phases.extend(
            [
                {'frame': frames[index], 'exit': ('transfer', source)},
                {'frame': frames[index], 'exit': ('transfer', source)},
            ]
        )
    phases.append({'frame': frames[-1]})
    controller.set_phases(phases)
    op = WatchedClear(test_context)
    with running_operation(op):
        for _ in range(40):
            op.screenshot()
            result = op.unload_next()
            if result.is_success or result.is_fail:
                break
        assert result.is_success, result.status
        assert op.moved == 2
        assert len(controller.recorded_clicks) == 8


def test_double_click_then_pause_only_verifies_result(
    test_context: TestContext,
    controller: TransferController,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """双击完成后暂停恢复只核验卸装结果，不重复发送双击。"""
    frames = unload_frames(test_context)
    source = LOADOUT_CENTERS[-1]
    controller.set_phases(
        [{'frame': frames[-2], 'exit': ('transfer', source)}, {'frame': frames[-1]}]
    )
    op = WatchedClear(test_context)
    original = controller.click

    def click(pos: Point, press_time: float = 0, **kwargs: object) -> bool:
        result = original(pos, press_time, **kwargs)
        if len(controller.recorded_clicks) == 2:
            op.handle_pause()
            op.handle_resume()
        return result

    monkeypatch.setattr(controller, 'click', click)
    with running_operation(op):
        for _ in range(5):
            op.screenshot()
            result = op.unload_next()
            if result.is_success:
                break
        assert result.is_success, result.status
        assert op.moved == 1
        assert len(controller.recorded_clicks) == 2


def test_pause_after_double_click_disables_retry(
    test_context: TestContext,
    controller: TransferController,
) -> None:
    """双击后暂停过，即使画面未变也不重发输入。"""
    before = unload_frames(test_context)[-2]
    source = LOADOUT_CENTERS[-1]
    controller.set_phases(
        [{'frame': before, 'exit': ('transfer', source)}, {'frame': before}]
    )
    op = WatchedClear(test_context)
    with running_operation(op):
        op.screenshot()
        op.unload_next()
        op.screenshot()
        assert '双击转入仓库' in op.unload_next().status
        op.handle_pause()
        op.handle_resume()
        for _ in range(15):
            op.screenshot()
            result = op.unload_next()
            if result.is_fail:
                break
        assert result.is_fail, result.status
        assert len(controller.recorded_clicks) == 2
        assert op.moved == 0


@pytest.mark.parametrize('animated_slot', [0, 2])
def test_empty_slot_animation_does_not_block_completed_unload(
    test_context: TestContext,
    controller: TransferController,
    animated_slot: int,
) -> None:
    """第二件已转存，其他空槽或有物槽的图标变化不能阻止确认。"""
    after = test_context.load_screen('贝果-备战', 'clear_loadout_second_weapon_stored')
    previous = after.copy()
    state = 'clear_loadout_empty' if animated_slot == 0 else 'clear_loadout_carried'
    alternate = test_context.load_screen('贝果-备战', state)
    # 明确合成同一槽位的另一种图标外观，其余像素和五项读数保留现场。
    x, y = LOADOUT_CENTERS[animated_slot].tuple()
    previous[y - 32 : y + 32, x - 32 : x + 32] = alternate[
        y - 32 : y + 32, x - 32 : x + 32
    ]
    controller.set_phases([{'frame': after}])
    op = WatchedClear(test_context)
    op.pending = True
    op.pending_center = LOADOUT_CENTERS[1]
    op.pending_group = '武备价值'
    op.before_values = {
        '武备价值': '180000',
        '装备价值': '160000',
        '道具价值': '78000',
        '背包数量': '0/50',
        '安全箱数量': '0/5',
    }
    op.pending_started = time.monotonic()
    op.moved = 1
    op.last_screenshot = previous
    assert op.unload_next().status == '等待卸装结果稳定'
    op.last_screenshot = after
    assert not op.unload_next().is_fail
    assert op.moved == 2
    assert not controller.recorded_clicks
    inspect = WatchedClear(test_context)
    inspect.last_screenshot = previous
    assert inspect.inspect_loadout().status == '等待备战格子稳定'
    inspect.last_screenshot = after
    assert inspect.inspect_loadout().status == '背包安全箱已空'


@pytest.mark.parametrize('change', ['value', 'occupied', 'unknown'])
def test_unload_still_rejects_unstable_or_unknown_observation(
    test_context: TestContext,
    controller: TransferController,
    change: str,
) -> None:
    """图标动画可忽略，但读数、占用变化或未知槽位仍不得报告转存完成。"""
    after = test_context.load_screen('贝果-备战', 'clear_loadout_second_weapon_stored')
    previous = after.copy()
    if change == 'value':
        paint_count(test_context, previous, '贝果-备战', '武备价值', '180000')
    else:
        x, y = LOADOUT_CENTERS[1].tuple()
        if change == 'unknown':
            previous[y - 32 : y + 32, x - 32 : x + 32] = 0
        else:
            carried = test_context.load_screen('贝果-备战', 'clear_loadout_carried')
            previous[y - 32 : y + 32, x - 32 : x + 32] = carried[
                y - 32 : y + 32, x - 32 : x + 32
            ]
    controller.set_phases([{'frame': after}])
    op = WatchedClear(test_context)
    op.pending = True
    op.pending_center = LOADOUT_CENTERS[1]
    op.pending_group = '武备价值'
    op.before_values = {
        '武备价值': '180000',
        '装备价值': '160000',
        '道具价值': '78000',
        '背包数量': '0/50',
        '安全箱数量': '0/5',
    }
    op.pending_started = time.monotonic()
    op.last_screenshot = after
    assert op.unload_next().status == '等待卸装结果稳定'
    op.last_screenshot = previous
    assert not op.unload_next().is_success
    op.last_screenshot = after
    assert op.unload_next().status == '等待卸装结果稳定'
    assert op.moved == 0
    assert not controller.recorded_clicks
