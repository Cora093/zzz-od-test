from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from zzz_od.application.bagel import bagel_usage
from zzz_od.application.bagel.bagel_config import BagelConfig
from zzz_od.application.bagel.bagel_usage import stop_guidance


@pytest.mark.parametrize('exists', [False, True])
def test_log_screenshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exists: bool
) -> None:
    """接口返回文件名不等于写入成功。"""
    path = tmp_path / 'scene.png'
    if exists:
        path.write_bytes(b'fixture')
    logger = MagicMock()
    monkeypatch.setattr(bagel_usage, 'log', logger)
    monkeypatch.setattr(
        bagel_usage.debug_utils, 'get_debug_image_path', lambda name: str(path)
    )
    bagel_usage.log_screenshot('scene')
    assert logger.info.call_count == int(exists)
    assert logger.warning.call_count == int(not exists)
    if exists:
        assert logger.info.call_args.args[1] == path.resolve()


@pytest.mark.parametrize(
    'clean,custom,limit', [(False, True, 0), (True, False, 1), (True, True, 7)]
)
def test_log_start(
    config: BagelConfig,
    monkeypatch: pytest.MonkeyPatch,
    clean: bool,
    custom: bool,
    limit: int,
) -> None:
    """验证开关、筛选、无限次数和实际重试上限。"""
    config.auto_clean_warehouse = clean
    config.clean_mode = 'custom' if custom else 'default'
    config.clean_types = ['装备']
    config.clean_qualities = ['Z']
    config.max_success_rounds = limit
    config.max_failure_retries = 9
    logger = MagicMock()
    monkeypatch.setattr(bagel_usage, 'log', logger)
    bagel_usage.log_start(config)
    messages = [
        call.args[0] % call.args[1:] if len(call.args) > 1 else call.args[0]
        for call in logger.info.call_args_list
    ]
    text = '\n'.join(messages)
    assert f'成功次数上限：{limit or "不限"}' in text
    assert '整体重试次数上限：9' in text
    assert (
        '空箱结算跳过出售，仍核对安全箱和仓库容量；安全箱为空且容量可读时，满仓也可继续'
        in text
    )
    assert '仍残留或满仓则停止' not in text
    assert ('出售范围：' in text) == clean
    if clean:
        assert ('装备、Z' in text) == custom
        assert '已有库存也会出售' in text
    else:
        assert '只入仓，不出售物品' in text


@pytest.mark.parametrize(
    'status,include,exclude',
    [
        ('仓库已满且安全箱仍有物资，禁止批量出售', '安全箱仍有物品', '结算完成'),
        ('结算后安全箱仍有物资', '请检查现场', '安全箱已空'),
        ('仅部分入仓，安全箱 2 -> 1 格', '停止重复点击', '已完成结算'),
        (
            '整体重试已用 0/0，已完成仓库结算，停止自动重开',
            '当前停在结算仓库',
            '正在重开',
        ),
        ('本局失败：定位失败；入仓或清理失败：异常', '请先处理上述原因', '已完成结算'),
        ('未知入场确认', '请检查现场', '自动重试'),
        ('异常', '请检查现场', '已完成结算'),
        ('连续 3 局安全箱为空，未计成功，停止自动重开', '完成返回流程', '正在重开'),
    ],
)
def test_stop_guidance(status: str, include: str, exclude: str) -> None:
    """提示只解释已确定的结果。"""
    text = stop_guidance(status)
    assert include in text
    assert exclude not in text
