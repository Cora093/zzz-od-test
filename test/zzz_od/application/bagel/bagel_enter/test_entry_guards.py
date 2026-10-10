from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from one_dragon.base.operation.operation_round_result import OperationRoundResultEnum
from zzz_od.application.bagel.bagel_enter import BagelEnter

if TYPE_CHECKING:
    from test.conftest import TestContext


from pathlib import Path

from test.harness.bagel_loadout import mock_loadout_ocr

from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.screen import screen_utils
from one_dragon.utils import cv2_utils


def test_opening_map_is_closed_before_hud(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """开局大地图不能空等自动关闭，识别后应主动关闭。"""
    test_context.mock_screen('贝果-局内', '六昏街南站地图-原生1080')
    op = BagelEnter(test_context)
    op.zero_checked = True
    op.investment_confirmed = True
    op.confirmed_warnings.update({'零装备价值', '未装备武备', '未穿戴队伍装备'})
    click = MagicMock(return_value=True)
    monkeypatch.setattr(test_context.controller, 'click', click)
    op.screenshot()
    result = op.confirm_entry()
    assert result.result == OperationRoundResultEnum.WAIT
    assert result.status == '关闭开局大地图'
    click.assert_called()


@pytest.mark.parametrize('attack_visible', [True, False])
@pytest.mark.parametrize('investment_confirmed', [True, False])
def test_entry_uses_attack_button_after_investment(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
    attack_visible: bool,
    investment_confirmed: bool,
) -> None:
    """左侧文字被遮挡仍可确认加载；攻击按钮缺失或未核验投资不能放行。"""
    test_context.mock_screen('贝果-局内', '高危A出生-原生1080')
    op = BagelEnter(test_context)
    op.zero_checked = True
    op.investment_confirmed = investment_confirmed
    op.screenshot()
    op.last_screenshot = op.last_screenshot.copy()
    op.last_screenshot[160:250, 60:500] = 0
    if not attack_visible:
        rect = test_context.screen_loader.get_area('战斗画面', '按键-普通攻击').rect
        op.last_screenshot[rect.y1 : rect.y2, rect.x1 : rect.x2] = 0
    click = MagicMock()
    monkeypatch.setattr(test_context.controller, 'click', click)
    result = op.confirm_entry()
    if attack_visible and investment_confirmed:
        assert result.is_success
        assert result.status == '已进入雅努斯高危'
    elif attack_visible:
        assert result.is_fail
        assert result.status == '未核对高危零投资，停止并保留现场'
    else:
        assert result.result == OperationRoundResultEnum.WAIT
    click.assert_not_called()


@pytest.mark.parametrize(
    'amount',
    ['', 'O', '00', '0.0', '0/500000', '?0', '500,000', '0K', '0M', '1.5', '5OOK', 'K'],
)
def test_unclear_investment_has_bounded_reads_without_clicks(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
    no_round_wait: None,
    amount: str,
) -> None:
    """识别不明限次重读，不能把近似零当成零，也不能猜金额点击 MIN。"""
    op = BagelEnter(test_context)
    op.zero_checked = True
    monkeypatch.setattr(
        op,
        'round_by_find_area',
        lambda _screen, _name, area: (
            op.round_success() if area == '投资标题' else op.round_retry()
        ),
    )
    monkeypatch.setattr(
        'zzz_od.application.bagel.bagel_enter.read_investment', lambda *_: amount
    )
    click = MagicMock()
    monkeypatch.setattr(op, 'round_by_find_and_click_area', click)
    for _ in range(3):
        result = op.confirm_entry()
        assert result.result == OperationRoundResultEnum.RETRY
        assert result.status == '投资金额识别不明，重新核对'
    assert op.confirm_entry().is_fail
    assert not op.investment_confirmed
    click.assert_not_called()


@pytest.mark.parametrize(
    'click_result', ['success', 'not_found', 'failed', 'unconfigured']
)
def test_min_click_result_requires_recheck(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
    no_round_wait: None,
    click_result: str,
) -> None:
    """点击、找不到按钮、输入失败和区域缺失都不能记为零投资已确认。"""
    op = BagelEnter(test_context)
    op.zero_checked = True
    monkeypatch.setattr(
        op,
        'round_by_find_area',
        lambda _screen, _name, area: (
            op.round_success() if area == '投资标题' else op.round_retry()
        ),
    )
    monkeypatch.setattr(
        'zzz_od.application.bagel.bagel_enter.read_investment', lambda *_: '1000000'
    )
    results = {
        'success': op.round_success(),
        'not_found': op.round_retry('未找到 投资最小值'),
        'failed': op.round_retry('点击失败 投资最小值'),
        'unconfigured': op.round_fail('区域未配置 投资最小值'),
    }
    click = MagicMock(return_value=results[click_result])
    monkeypatch.setattr(op, 'round_by_find_and_click_area', click)
    result = op.confirm_entry()
    expected = (
        OperationRoundResultEnum.WAIT
        if click_result == 'success'
        else results[click_result].result
    )
    assert result.result == expected
    assert not op.investment_confirmed
    assert op.investment_retries == 1
    assert click.call_args.args[2] == '投资最小值'


def test_repeated_investment_does_not_change_amount(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
    no_round_wait: None,
) -> None:
    """已经点击入场后不因金额闪动再次归零或确认。"""
    op = BagelEnter(test_context)
    op.zero_checked = True
    op.investment_confirmed = True
    monkeypatch.setattr(
        op,
        'round_by_find_area',
        lambda _screen, _name, area: (
            op.round_success() if area == '投资标题' else op.round_retry()
        ),
    )
    monkeypatch.setattr(
        'zzz_od.application.bagel.bagel_enter.read_investment', lambda *_: '500000'
    )
    click = MagicMock()
    monkeypatch.setattr(op, 'round_by_find_and_click_area', click)
    assert op.confirm_entry().status == '零投资入场未生效'
    click.assert_not_called()


@pytest.mark.parametrize('investment_confirmed', [False, True])
def test_death_during_entry_is_forwarded_only_after_verified_investment(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
    investment_confirmed: bool,
) -> None:
    """零投资已确认的入场死亡交正式任务结算，不能绕过投资校验假称已入场。"""
    test_context.mock_screen('贝果-结算', '高危空局失败-原生1080')
    op = BagelEnter(test_context)
    op.zero_checked = True
    op.investment_confirmed = investment_confirmed
    op.screenshot()
    click = MagicMock()
    monkeypatch.setattr(test_context.controller, 'click', click)
    result = op.confirm_entry()
    assert result.is_success == investment_confirmed
    if investment_confirmed:
        assert result.status == '已进入雅努斯高危'
    click.assert_not_called()


def test_world_away_from_reception_uses_map_transport(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """普通大世界不要求先站在达塔面前，传送后再按画面确认入口。"""
    test_context.mock_screen('贝果-局内', '高危A出生-原生1080')
    op = BagelEnter(test_context)
    op.screenshot()
    monkeypatch.setattr(op, 'round_by_find_area', lambda *_args: op.round_retry())
    monkeypatch.setattr(
        op, 'check_and_update_current_screen', lambda *_args: '大世界-普通'
    )
    monkeypatch.setattr(op, '_at_reception', lambda: False)
    transport = MagicMock(return_value=OperationResult(True, '传送完成'))
    monkeypatch.setattr(
        'zzz_od.application.bagel.bagel_enter.Transport.execute', transport
    )
    result = op.open_hub()
    assert not result.is_fail
    assert result.status == '等待研究站传送落地'
    transport.assert_called_once()


def test_wengine_warehouse_uses_map_transport(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """识别普通音擎仓库后经大世界传送。"""
    test_context.mock_screen('贝果-局内', '高危A出生-原生1080')
    op = BagelEnter(test_context)
    op.screenshot()
    monkeypatch.setattr(op, 'round_by_find_area', lambda *_args: op.round_retry())
    monkeypatch.setattr(
        op, 'check_and_update_current_screen', lambda *_args: '仓库-音擎仓库'
    )
    monkeypatch.setattr(op, '_at_reception', lambda: False)
    transport = MagicMock(return_value=OperationResult(True, '传送完成'))
    monkeypatch.setattr(
        'zzz_od.application.bagel.bagel_enter.Transport.execute', transport
    )
    result = op.open_hub()
    assert not result.is_fail
    assert result.status == '等待研究站传送落地'
    transport.assert_called_once()


@pytest.mark.parametrize('missing_material_area', [False, True])
def test_wengine_warehouse_is_recognized_in_bagel_scope(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
    missing_material_area: bool,
) -> None:
    """贝果应用画面范围不包含音擎仓库，入口按标题补认。"""
    image = (
        Path(__file__).resolve().parents[4]
        / 'one_dragon/base/screen/screen_loader/test_get_match_screen_name/storage_wengine.webp'
    )
    screen = cv2_utils.read_image(str(image))
    if missing_material_area:
        monkeypatch.delitem(
            test_context.screen_loader._screen_area_map, '仓库-材料道具.标题-材料道具'
        )
    test_context.screen_loader.enter_scope('bagel')
    try:
        assert screen_utils.get_match_screen_name(test_context, screen) is None
        op = BagelEnter(test_context)
        op.last_screenshot = screen
        assert op._ordinary_warehouse() == '仓库-音擎仓库'
    finally:
        test_context.screen_loader.exit_scope()


def test_wengine_warehouse_without_global_match_uses_title(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """全局画面匹配为未知时，只凭完整仓库标题进入已有传送流程。"""
    image = (
        Path(__file__).resolve().parents[4]
        / 'one_dragon/base/screen/screen_loader/test_get_match_screen_name/storage_wengine.webp'
    )
    op = BagelEnter(test_context)
    op.last_screenshot = cv2_utils.read_image(str(image))
    monkeypatch.setattr(op, '_at_reception', lambda: False)
    monkeypatch.setattr(op, 'check_and_update_current_screen', lambda *_args: None)
    transport = MagicMock(return_value=OperationResult(True, '传送完成'))
    monkeypatch.setattr(
        'zzz_od.application.bagel.bagel_enter.Transport.execute', transport
    )
    result = op.open_hub()
    assert not result.is_fail
    assert result.status == '等待研究站传送落地'
    transport.assert_called_once()
    assert test_context.screen_loader.current_screen_name == '仓库-音擎仓库'


@pytest.mark.parametrize('missing_warehouse_areas', [False, True])
def test_unknown_screen_never_transports_or_clicks(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
    missing_warehouse_areas: bool,
) -> None:
    """无法识别的画面不尝试通用返回或地图传送。"""
    test_context.mock_screen('贝果-局内', '高危A出生-原生1080')
    op = BagelEnter(test_context)
    op.screenshot()
    if missing_warehouse_areas:
        for name in ('材料道具', '音擎仓库', '驱动仓库'):
            monkeypatch.delitem(
                test_context.screen_loader._screen_area_map, f'仓库-{name}.标题-{name}'
            )
    monkeypatch.setattr(op, 'round_by_find_area', lambda *_args: op.round_retry())
    monkeypatch.setattr(op, 'check_and_update_current_screen', lambda *_args: None)
    transport = MagicMock()
    click = MagicMock()
    monkeypatch.setattr(
        'zzz_od.application.bagel.bagel_enter.Transport.execute', transport
    )
    monkeypatch.setattr(test_context.controller, 'click', click)
    result = op.open_hub()
    assert result.is_fail
    transport.assert_not_called()
    click.assert_not_called()


def test_other_gameplay_screen_is_left_untouched(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """已识别的其他玩法局内也不能调用会退出战斗的通用传送。"""
    test_context.mock_screen('贝果-局内', '高危A出生-原生1080')
    op = BagelEnter(test_context)
    op.screenshot()
    monkeypatch.setattr(op, 'round_by_find_area', lambda *_args: op.round_retry())
    monkeypatch.setattr(
        op, 'check_and_update_current_screen', lambda *_args: '战斗画面'
    )
    transport = MagicMock()
    monkeypatch.setattr(
        'zzz_od.application.bagel.bagel_enter.Transport.execute', transport
    )
    assert op.open_hub().is_fail
    transport.assert_not_called()


def test_transport_failure_is_reported_without_repeating(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """传送失败立即停，不重试有副作用的地图操作。"""
    test_context.mock_screen('贝果-局内', '高危A出生-原生1080')
    op = BagelEnter(test_context)
    op.screenshot()
    monkeypatch.setattr(op, 'round_by_find_area', lambda *_args: op.round_retry())
    monkeypatch.setattr(op, '_at_reception', lambda: False)
    monkeypatch.setattr(op, 'check_and_update_current_screen', lambda *_args: '菜单')
    transport = MagicMock(return_value=OperationResult(False, '未找到传送点'))
    monkeypatch.setattr(
        'zzz_od.application.bagel.bagel_enter.Transport.execute', transport
    )
    result = op.open_hub()
    assert result.is_fail and result.status == '未找到传送点'
    assert not op.transport_started
    transport.assert_called_once()


def test_landing_without_reception_stops_without_interacting(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """传送成功不能代替落地后的达塔识别。"""
    test_context.mock_screen('贝果-局内', '高危A出生-原生1080')
    op = BagelEnter(test_context)
    op.screenshot()
    op.transport_started = True

    def find_area(_screen: object, _name: str, area: str) -> object:
        """模拟已落地但达塔提示缺失。"""
        return op.round_success() if area == '快捷手册' else op.round_retry()

    monkeypatch.setattr(op, 'round_by_find_area', find_area)
    monkeypatch.setattr(op, '_at_reception', lambda: False)
    interact = MagicMock()
    monkeypatch.setattr(test_context.controller, 'interact', interact)
    assert op.open_hub().is_fail
    interact.assert_not_called()


@pytest.mark.parametrize(
    'checked,repeat,expected',
    [
        (False, False, '尚未核对零携带'),
        (True, True, '已处理的入场提示再次出现'),
    ],
)
def test_confirmation_guard(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
    checked: bool,
    repeat: bool,
    expected: str,
) -> None:
    """未核验及已经点过的弹窗都不再次输入。"""
    test_context.mock_screen('贝果-入场确认', '高危零装备价值-原生1080')
    op = BagelEnter(test_context)
    op.zero_checked = checked
    if repeat:
        op.confirmed_warnings.add('零装备价值')
    click = MagicMock()
    monkeypatch.setattr(test_context.controller, 'click', click)
    op.screenshot()
    result = op.confirm_entry()
    assert expected in result.status
    assert result.result == OperationRoundResultEnum.FAIL
    click.assert_not_called()


def test_unrelated_confirmation_is_not_accepted(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """退出确认与入场确认按钮重叠，必须拒绝完整提示不符的弹窗。"""
    test_context.mock_screen('贝果-退出确认', '主动退出-原生1080')
    op = BagelEnter(test_context)
    op.zero_checked = True
    click = MagicMock()
    monkeypatch.setattr(test_context.controller, 'click', click)
    op.screenshot()
    result = op.confirm_entry()
    assert result.is_fail
    assert result.status == '未知入场确认，停止并保留现场'
    click.assert_not_called()


def test_carried_equipment_prevents_entry(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """有队伍装备和道具时停在备战，不能消费任何出战确认。"""
    test_context.mock_screen('贝果-备战', '仍带装备道具-1440缩放')
    op = BagelEnter(test_context)
    click = MagicMock()
    monkeypatch.setattr(test_context.controller, 'click', click)
    op.screenshot()
    assert op.verify_zero_loadout().is_fail
    assert not op.zero_checked
    click.assert_not_called()


@pytest.mark.parametrize('area_index', [0, 1, 2])
@pytest.mark.parametrize(
    'full_values,crop_values',
    [
        (['0', '@500'], None),
        ([], ['0', '@500']),
        (['0', '500'], ['0']),
    ],
)
def test_conflicting_value_prevents_entry(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
    area_index: int,
    full_values: list[str],
    crop_values: list[str] | None,
) -> None:
    """任一价值区存在非零证据时，面板或标题条裁剪读到零均不得点击入场。"""
    area, label = (
        ('武备价值', '代理人武备'),
        ('装备价值', '装备'),
        ('道具价值', '道具'),
    )[area_index]
    mock_loadout_ocr(
        test_context, monkeypatch, area, [label, *full_values], crop_values
    )
    op = BagelEnter(test_context)
    op.last_screenshot = test_context.load_screen('贝果-备战', '高危零携带-原生1080')
    monkeypatch.setattr(
        op, 'round_by_find_area', MagicMock(return_value=op.round_success())
    )
    click = MagicMock(return_value=op.round_success())
    monkeypatch.setattr(op, 'round_by_find_and_click_area', click)

    for _ in range(4):
        assert op.verify_zero_loadout().result == OperationRoundResultEnum.WAIT
        click.assert_not_called()
    assert op.verify_zero_loadout().is_fail
    assert not op.zero_checked
    click.assert_not_called()


def test_repeat_investment_page_does_not_click(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """已确认过零投资却仍在原页时等待，而不重复点击。"""
    test_context.mock_screen('贝果-入场确认', '高危零投资-原生1080')
    op = BagelEnter(test_context)
    op.zero_checked = True
    op.investment_confirmed = True
    monkeypatch.setattr(
        'zzz_od.application.bagel.bagel_enter.read_investment', lambda *_: '0'
    )
    click = MagicMock()
    monkeypatch.setattr(test_context.controller, 'click', click)
    op.screenshot()
    result = op.confirm_entry()
    assert result.result == OperationRoundResultEnum.RETRY
    assert result.status == '零投资入场未生效'
    click.assert_not_called()


def test_hud_without_investment_check_stops(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """即使已见贝果 HUD，未经零投资核验也不得报告成功。"""
    test_context.mock_screen('贝果-局内', '高危A出生-原生1080')
    op = BagelEnter(test_context)
    op.zero_checked = True
    op.confirmed_warnings.update({'零装备价值', '未装备武备', '未穿戴队伍装备'})
    click = MagicMock()
    monkeypatch.setattr(test_context.controller, 'click', click)
    op.screenshot()
    result = op.confirm_entry()
    assert result.is_fail
    assert result.status == '未核对高危零投资，停止并保留现场'
    click.assert_not_called()
