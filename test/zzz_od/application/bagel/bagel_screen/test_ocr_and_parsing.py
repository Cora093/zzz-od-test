from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import numpy as np
import pytest

from one_dragon.base.operation.operation_round_result import OperationRoundResultEnum
from zzz_od.application.bagel.bagel_enter import BagelEnter
from zzz_od.application.bagel.bagel_investment import (
    mask_investment_coin,
    read_investment,
)
from zzz_od.application.bagel.bagel_screen import (
    complete_loadout,
    entry_warning,
    expected_map,
    read_area,
)

if TYPE_CHECKING:
    from test.conftest import TestContext

from unittest.mock import call

import cv2
from test.harness.bagel_loadout import mock_loadout_ocr

from one_dragon.base.geometry.rectangle import Rect
from zzz_od.application.bagel.bagel_screen import (
    parse_capacity_pair,
    parse_filter_count,
    read_loadout,
    zero_loadout,
)


@pytest.mark.parametrize(
    'name,value',
    [
        ('武备价值', ''),
        ('装备价值', '@0'),
        ('道具价值', '0 500'),
        ('背包数量', '1/0'),
        ('背包数量', '21/20'),
        ('安全箱数量', '0/5/5'),
    ],
)
def test_incomplete_values_cannot_trigger_clearing(name: str, value: str) -> None:
    """任一未知或非法读数不能当作非零触发物品搬运。"""
    values = {
        '武备价值': '0',
        '装备价值': '0',
        '道具价值': '78000',
        '背包数量': '0/20',
        '安全箱数量': '0/5',
    }
    values[name] = value
    assert not complete_loadout(values)


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        (
            '当前装备价值为0，未达到推荐价值258000，将会面临极大挑战，是否继续前往？',
            '零装备价值',
        ),
        ('存在未装备武备的代理人，是否直接出战？', '未装备武备'),
        ('未穿戴队伍装备（异体刃、抗蚀器），是否直接出战？', '未穿戴队伍装备'),
        ('未知弹窗，是否确认？', None),
        ('', None),
    ],
)
def test_entry_warning(text: str, expected: str | None) -> None:
    assert entry_warning(text) == expected


@pytest.mark.parametrize(
    'title, accepted',
    [
        ('[高危]雅努斯幻境', True),
        ('高危雅努斯幻境', True),
        ('[困难]雅努斯幻境', False),
        ('困难雅努斯幻境', False),
        ('高危雅努斯', False),
    ],
)
def test_expected_map_requires_high_risk(title: str, accepted: bool) -> None:
    """结算地图必须属于高危雅努斯，困难截图只能作负样本。"""
    assert expected_map(title) is accepted


@pytest.mark.parametrize('amount', ['0', '500K', '1M', '1.5M', '2M', '2.5M', '3M'])
def test_all_live_amounts_keep_complete_digits(
    test_context: TestContext, amount: str
) -> None:
    """七档实机金额完整读取，不能因金币位置变化截断首位。"""
    screen = test_context.load_screen('贝果-入场确认', f'投资{amount}-20261007-无损')
    assert read_investment(test_context, screen) == amount


def test_coin_read_as_two_no_longer_clicks_min(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
    no_round_wait: None,
) -> None:
    """原图确实把金币读成 2；实际入场节点应只确认零投资，不点 MIN。"""
    screen = test_context.load_screen('贝果-入场确认', '零投资金币误读2-20261007-无损')
    assert read_area(test_context, screen, '贝果-入场确认', '投资金额') == '20'
    assert read_investment(test_context, screen) == '0'
    op = BagelEnter(test_context)
    op.last_screenshot = screen
    op.zero_checked = True
    click = MagicMock(return_value=op.round_success())
    monkeypatch.setattr(op, 'round_by_find_and_click_area', click)
    assert op.confirm_entry().result == OperationRoundResultEnum.WAIT
    assert op.investment_confirmed
    assert click.call_args.args[2] == '零投资前往空洞'
    assert op.investment_retries == 0


@pytest.mark.parametrize('case', ['missing', 'multiple', 'digit_left'])
def test_unreliable_coin_location_stays_unknown(
    test_context: TestContext, case: str
) -> None:
    """金币缺失、重复或位于数字右侧时不能通过遮挡得到假零。"""
    screen = test_context.load_screen(
        '贝果-入场确认', '零投资金币误读2-20261007-无损'
    ).copy()
    crop = screen[700:754, 780:1140]
    coin = crop[:, 147:186].copy()
    if case == 'missing':
        crop[:, 147:186] = 0
    elif case == 'multiple':
        crop[:, 20:59] = coin
    else:
        crop[12:36, 10:18] = 255
    assert mask_investment_coin(crop) is None
    assert read_investment(test_context, screen) == ''


def test_mask_keeps_input_and_all_amount_pixels(test_context: TestContext) -> None:
    """遮挡只生成新图，保持尺寸，不改变金币右侧的完整金额。"""
    screen = test_context.load_screen('贝果-入场确认', '投资500K-20261007-无损')
    crop = screen[700:754, 780:1140]
    before = crop.copy()
    result = mask_investment_coin(crop)
    assert result is not None and result.shape == crop.shape
    assert np.array_equal(crop, before)
    assert np.array_equal(result[:, 151:], crop[:, 151:])


@pytest.mark.parametrize(
    'state,expected',
    [
        ('高危零装备价值', '零装备价值'),
        ('未装备武备', '未装备武备'),
        ('未穿戴队伍装备', '未穿戴队伍装备'),
    ],
)
def test_entry_warning_native(
    test_context: TestContext, state: str, expected: str
) -> None:
    """原生截图必须识别完整提示，不能只凭确认按钮点击。"""
    screen = test_context.load_screen('贝果-入场确认', f'{state}-原生1080')
    text = read_area(test_context, screen, '贝果-入场确认', '提示')
    assert entry_warning(text) == expected, text


@pytest.mark.parametrize(
    'state,expected',
    [
        ('高危零携带-原生1080', True),
        ('高危零携带-道具零误读O-20260929', True),
        ('零携带-原生1080', True),
        ('城郊高危零携带-20260926', True),
        ('仍带装备道具-1440缩放', False),
    ],
)
def test_zero_loadout_real_screen(
    test_context: TestContext, state: str, expected: bool
) -> None:
    """实拍零携带与未清空物资应分别通过和拒绝。"""
    screen = test_context.load_screen('贝果-备战', state)
    values = read_loadout(test_context, screen)
    assert zero_loadout(values) is expected, values
    assert values['武备价值'] == '0'
    assert values['装备价值'] == ('0' if expected else '60000')
    assert values['道具价值'] == ('0' if expected else '38000')


@pytest.mark.parametrize('area_name', ['武备价值', '装备价值', '道具价值'])
@pytest.mark.parametrize('amount', ['1000', '1000000'])
def test_synthetic_nonzero_loadout_not_zero(
    test_context: TestContext,
    area_name: str,
    amount: str,
) -> None:
    """完整标题条中的多位金额必须保留高位，不能只读出末尾零。"""
    screen = test_context.load_screen('贝果-备战', '高危零携带-原生1080').copy()
    area = test_context.screen_loader.get_area('贝果-备战', area_name)
    rect = area.pc_rect
    left = rect.x2 - 175
    cv2.rectangle(
        screen, (left, rect.y1 + 2), (rect.x2 - 2, rect.y2 - 2), (140, 140, 140), -1
    )
    cv2.putText(
        screen,
        amount,
        (left + 5, rect.y2 - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    values = read_loadout(test_context, screen)
    assert values[area_name] == amount, values
    assert not zero_loadout(values)


def test_zero_investment_real_screen(test_context: TestContext) -> None:
    """实拍高危投资页的金额区域必须完整且只读出 0。"""
    screen = test_context.load_screen('贝果-入场确认', '高危零投资-原生1080')
    assert read_area(test_context, screen, '贝果-入场确认', '投资金额') == '0'


@pytest.mark.parametrize('amount, x', [('500000', 825), ('1000000', 800)])
def test_synthetic_nonzero_investment_not_zero(
    test_context: TestContext,
    amount: str,
    x: int,
) -> None:
    """在实拍页合成不同宽度白色金额，防止截断非零数字误认为零。"""
    screen = test_context.load_screen('贝果-入场确认', '高危零投资-原生1080').copy()
    cv2.rectangle(screen, (780, 700), (1139, 753), (28, 28, 28), -1)
    cv2.putText(
        screen,
        amount,
        (x, 740),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.1,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    text = read_area(test_context, screen, '贝果-入场确认', '投资金额')
    assert text == amount


@pytest.mark.parametrize(
    'text,expected',
    [
        ('全部(235/280)', (235, 280)),
        ('全部 (259/280)', (259, 280)),
        ('全部(280/280)', (280, 280)),
        ('乱码', None),
        ('全部(300/280)', None),
        ('全部(0/0)', None),
    ],
)
def test_parse_capacity_pair(text: str, expected: tuple[int, int] | None) -> None:
    """占用与容量成对解析；满仓 280/280 有效，颠倒或零容量拒绝。"""
    assert parse_capacity_pair(text) == expected


@pytest.mark.parametrize(
    'text,expected',
    [
        ('符合以上条件的道具数量:0', 0),
        ('符合以上条件的道具数量：12', 12),
        ('数量:3', 3),
        ('符合以上条件的道具数量0', 0),
        ('乱码', None),
        ('12', None),
    ],
)
def test_parse_filter_count(text: str, expected: int | None) -> None:
    """筛选件数必须带数量或「符合」上下文，不能把旁边数字当成件数。"""
    assert parse_filter_count(text) == expected


@pytest.mark.parametrize(
    'full_texts,crop_texts,expected,full_fallback',
    [
        (['装备', '0'], None, '0', False),
        (['装备', '1000'], None, '1000', False),
        (['0'], ['0'], '0', False),
        (['装备0'], ['装备', '0'], '0', False),
        (['装备'], ['装备', '@0'], '0', False),
        (['装备'], ['装备', '@1000'], '1000', False),
        (['装备', '0', '0'], ['装备', '0'], '0', False),
        (['装备', '0', '@500'], None, '', False),
        (['装备', '0', '500元'], None, '', False),
        (['装备'], ['装备', '0', '@500'], '', False),
        (['装备'], ['装备', '0', '1,000'], '', False),
        (['装备', '0', '500'], ['装备', '0'], '', False),
        (['@500'], ['装备', '@0'], '', False),
        ([], [], '', True),
        (['装备'], ['装备'], '', True),
        (['装备'], ['装备', '0', '0'], '', True),
        (['装备'], ['装备', '1000', '0'], '', True),
        (['装备'], ['装备', '@0', '#0'], '', True),
        (['装备'], ['装备', '@@@0'], '', True),
        (['装备'], ['O'], '', True),
    ],
)
def test_read_loadout_panel_then_crop(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
    full_texts: list[str],
    crop_texts: list[str] | None,
    expected: str,
    full_fallback: bool,
) -> None:
    """面板须有标题和唯一数字，失败才裁完整标题条；无法确认不得当零。"""
    screen = test_context.load_screen('贝果-备战', '高危零携带-原生1080')
    ocr = mock_loadout_ocr(
        test_context, monkeypatch, '装备价值', full_texts, crop_texts
    )

    values = read_loadout(test_context, screen)

    assert values == {
        '武备价值': '0',
        '装备价值': expected,
        '道具价值': '0',
        '背包数量': '0/20',
        '安全箱数量': '0/5',
    }
    assert zero_loadout(values) is (expected == '0')
    assert ocr.call_args_list[0] == call(
        screen, rect=Rect(1000, 0, 1920, 1080), crop_first=True
    )
    assert ocr.call_count == 3 + (crop_texts is not None) + full_fallback
    rect = test_context.screen_loader.get_area('贝果-备战', '装备价值').pc_rect
    assert (
        call(screen, rect=rect, crop_first=False) in ocr.call_args_list
    ) is full_fallback
    for name in ('背包数量', '安全箱数量'):
        area = test_context.screen_loader.get_area('贝果-备战', name)
        ocr.assert_any_call(
            screen, rect=area.pc_rect, crop_first=True, color_range=area.color_range
        )


@pytest.mark.parametrize(
    'state,values',
    [
        ('clear_loadout_carried', ('270000', '160000', '78000', '2/50', '0/5')),
        ('clear_loadout_empty', ('0', '0', '0', '0/20', '0/5')),
        ('clear_loadout_tools_only', ('0', '0', '78000', '0/20', '0/5')),
    ],
)
def test_prepare_recording(
    test_context: TestContext, state: str, values: tuple[str, ...]
) -> None:
    """归档画面识别五项；灰色空武备图案及左侧库存不得算携带物。"""
    screen = test_context.load_screen('贝果-备战', state)
    actual = read_loadout(test_context, screen)
    assert tuple(actual.values()) == values, actual
    assert complete_loadout(actual)


def test_dense_inventory_is_not_sent_to_ocr(
    test_context: TestContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """实际识别录像画面，避免左侧大量库存文本增加每次核验的开销。"""
    screen = test_context.load_screen(
        '贝果-备战', 'clear_loadout_dense_inventory'
    ).copy()
    matcher = test_context.ocr_service.ocr_matcher
    spy = MagicMock(wraps=matcher.ocr)
    monkeypatch.setattr(matcher, 'ocr', spy)
    assert tuple(read_loadout(test_context, screen).values()) == (
        '0',
        '0',
        '18000',
        '0/20',
        '0/5',
    )
    assert spy.call_count > 0
    assert all(call.args[0].shape[1] < 1000 for call in spy.call_args_list)


@pytest.mark.parametrize(
    ('changes', 'expected'),
    [
        ({}, True),
        ({'武备价值': '3000'}, False),
        ({'装备价值': '60000'}, False),
        ({'道具价值': '38000'}, False),
        ({'背包数量': '1/20'}, False),
        ({'安全箱数量': '1/5'}, False),
        ({'安全箱数量': '0/0'}, False),
        ({'背包数量': ''}, False),
    ],
)
def test_zero_loadout(changes: dict[str, str], expected: bool) -> None:
    values = {
        '武备价值': '0',
        '装备价值': '0',
        '道具价值': '0',
        '背包数量': '0/20',
        '安全箱数量': '0/5',
    }
    values.update(changes)
    assert zero_loadout(values) is expected
