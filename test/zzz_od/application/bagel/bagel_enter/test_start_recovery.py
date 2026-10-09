from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from test.harness.bagel_loadout import controller as controller
from test.harness.bagel_loadout import running_operation
from test.harness.fixture_controller import WatchdogOperationMixin

from one_dragon.base.operation.operation_base import OperationResult
from zzz_od.application.bagel.bagel_enter import BagelEnter
from zzz_od.application.bagel.bagel_store_carried import BagelStoreCarried

if TYPE_CHECKING:
    from test.conftest import TestContext
    from test.harness.fixture_controller import FixtureController


class WatchedEnter(WatchdogOperationMixin, BagelEnter):
    """真实节点执行，观察恢复是否先于启动仓库。"""

    watchdog_max_rounds: int = 25


@pytest.mark.parametrize('state', ['高危空局失败-原生1080', '主动退出-原生1080'])
def test_recovery_reaches_warehouse_before_entry(
    test_context: TestContext, controller: FixtureController, state: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """恢复结算或退出提示后先转存启动仓库，不能直接进入选图。"""
    screen = '贝果-退出确认' if state == '主动退出-原生1080' else '贝果-结算'
    phases = [{'frame': (screen, state), 'exit': ('on_click_in', screen, '确认' if screen == '贝果-退出确认' else '继续')}]
    if screen == '贝果-退出确认':
        phases.append({'frame': ('贝果-结算', '高危空局失败-原生1080'), 'exit': ('on_click_in', '贝果-结算', '继续')})
    phases.append({'frame': ('贝果-仓库', '空局仓库-原生1080')})
    monkeypatch.setattr(BagelStoreCarried, 'execute', lambda _: OperationResult(False, '测试已到启动转存'))
    controller.set_phases(phases)
    op = WatchedEnter(test_context, allow_clear_loadout=True)
    with running_operation(op):
        result = op.execute()
    assert not result.success and '测试已到启动转存' in result.status
    assert controller.phase_idx == len(phases) - 1


def test_map_recovery_requires_first_entry(test_context: TestContext, controller: FixtureController) -> None:
    """后续入场不能消耗遗留局。"""
    controller.set_phases([{'frame': ('贝果-局内', '高危开局大地图-原生1080')}])
    op = WatchedEnter(test_context)
    with running_operation(op):
        result = op.execute()
    assert not result.success
    assert not controller.recorded_clicks


@pytest.mark.parametrize('from_hud', [False, True])
def test_verified_map_exits_then_stores(
    test_context: TestContext, controller: FixtureController, monkeypatch: pytest.MonkeyPatch,
    from_hud: bool,
) -> None:
    """完整节点图：查询地图、关闭地图、正常退出、继续结算后才转存。"""
    phases = ([{'frame': ('贝果-局内', '高危A出生-原生1080')}] if from_hud else [])
    phases.extend([
        {'frame': ('贝果-局内', '高危开局大地图-原生1080'), 'exit': ('on_click_in', '贝果-局内', '大地图返回')},
        {'frame': ('贝果-局内', '高危A出生-原生1080')},
        {'frame': ('贝果-局内', '暂停菜单-原生1080'), 'exit': ('on_click_in', '战斗-菜单', '按钮-退出战斗')},
        {'frame': ('贝果-退出确认', '主动退出-原生1080'), 'exit': ('on_click_in', '贝果-退出确认', '确认')},
        {'frame': ('贝果-结算', '高危空局失败-原生1080'), 'exit': ('on_click_in', '贝果-结算', '继续')},
        {'frame': ('贝果-仓库', '空局仓库-原生1080')},
    ])
    controller.set_phases(phases)
    keys: list[str] = []

    def key(key: str, press_time: float = 0) -> None:
        """只有预期地图查询与暂停输入才能推进画面。"""
        assert key == ('m' if from_hud and not keys else 'esc')
        keys.append(key)
        controller._advance_phase()

    monkeypatch.setattr(controller, 'btn_press', key, raising=False)
    monkeypatch.setattr(BagelStoreCarried, 'execute', lambda _: OperationResult(False, '已到启动转存'))
    op = WatchedEnter(test_context, allow_clear_loadout=True)
    with running_operation(op):
        result = op.execute()
    assert not result.success and '已到启动转存' in result.status
    assert keys == (['m', 'esc'] if from_hud else ['esc'])
    assert controller.phase_idx == len(phases) - 1


@pytest.mark.parametrize('title', ['[困难]雅努斯幻境', '[高危]城郊幻境', ''])
def test_unknown_map_never_exits(
    test_context: TestContext, controller: FixtureController, monkeypatch: pytest.MonkeyPatch, title: str,
) -> None:
    """地图不符或读数不明，不能关闭地图并继续退出。"""
    controller.set_phases([{'frame': ('贝果-局内', '高危开局大地图-原生1080')}])
    monkeypatch.setattr('zzz_od.application.bagel.bagel_enter.read_area', lambda *_: title)
    op = WatchedEnter(test_context, allow_clear_loadout=True)
    with running_operation(op):
        result = op.execute()
    assert not result.success and '不是高危雅努斯' in result.status
    assert not controller.recorded_clicks
