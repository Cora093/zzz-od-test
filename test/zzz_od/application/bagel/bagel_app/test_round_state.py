from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from test.harness.bagel_safe_slots import lock_safe_suffix

from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.utils import cv2_utils
from zzz_od.application.bagel import bagel_app
from zzz_od.application.bagel.bagel_app import BagelApp
from zzz_od.application.bagel.bagel_config import BagelConfig
from zzz_od.application.bagel.bagel_deposit import BagelDeposit
from zzz_od.application.bagel.bagel_enter import BagelEnter
from zzz_od.application.bagel.bagel_run_record import BagelRunRecord
from zzz_od.application.bagel.bagel_settle import BagelSettleWarehouse
from zzz_od.application.bagel.bagel_slots import WAREHOUSE_SAFE_CENTERS

if TYPE_CHECKING:
    from test.conftest import TestContext

    from zzz_od.application.bagel.bagel_config import BagelConfig
    from zzz_od.application.bagel.bagel_run_record import BagelRunRecord


@pytest.mark.parametrize('pending', [False, True])
@pytest.mark.parametrize('limit,expected', [(1, True), (-1, False)])
def test_readiness_uses_current_config_and_preserves_old_record(
    config: BagelConfig,
    record: BagelRunRecord,
    legacy_collection: dict,
    pending: bool,
    limit: int,
    expected: bool,
) -> None:
    """不要求物资目标；旧局不拦截启动，也不能绕过当前配置校验。"""
    if not pending:
        legacy_collection['pending'] = None
        record.update('collection', legacy_collection)
    before = Path(record.file_path).read_bytes()
    config.data['max_success_rounds'] = limit
    ctx = MagicMock()
    result = BagelApp(ctx, config, record).check_ready()
    assert result.is_success is expected
    if not expected:
        assert result.is_fail
        assert '贝果配置无效' in result.status
    assert record.get('collection') == legacy_collection
    assert Path(record.file_path).read_bytes() == before
    assert not ctx.controller.mock_calls


def test_enter_refuses_settlement_with_safe_items(
    config: BagelConfig,
    record: BagelRunRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """结算仓库安全箱还有物资时，不触发下一局入场。"""
    screen = cv2_utils.read_image(
        str(
            Path(__file__).resolve().parents[5]
            / 'screens/贝果-仓库/满仓安全箱余一件-20260924.webp'
        )
    )
    ctx = MagicMock()
    ctx.controller.screenshot.return_value = (0.0, screen)
    app = BagelApp(ctx, config, record)
    app.initial_clear_pending = False
    monkeypatch.setattr(
        app, 'round_by_find_area', lambda *_args: MagicMock(is_success=True)
    )
    result = app.enter()
    assert result.is_fail
    assert '安全箱仍有物资' in result.status
    ctx.controller.interact.assert_not_called()
    ctx.controller.click.assert_not_called()


def test_application_consumes_first_entry_even_before_spawn(
    config: BagelConfig,
    record: BagelRunRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """资格按启动隔离，不因入场失败、出生点未识别或暂停而重复授予。"""
    monkeypatch.setattr(
        'zzz_od.application.bagel.bagel_app.release_flow_inputs', lambda _: None
    )
    ctx = MagicMock()
    app = BagelApp(ctx, config, record)
    monkeypatch.setattr(app, 'screenshot', MagicMock())
    monkeypatch.setattr(
        app, 'round_by_find_area', MagicMock(return_value=app.round_fail())
    )
    allowed: list[bool] = []

    def enter(op: BagelEnter) -> OperationResult:
        """记录入场资格，并模拟第一次入场尚未成功就停止。"""
        assert op.recovery_auto_clean == config.auto_clean_warehouse
        assert op.recovery_filter_areas == config.clean_filter_areas()
        allowed.append(op.allow_clear_loadout)
        return OperationResult(False, '模拟入场失败')

    monkeypatch.setattr(BagelEnter, 'execute', enter)
    assert app.enter().is_fail
    assert app.attempts == 0
    app.handle_pause()
    app.handle_resume()
    assert app.enter().is_fail
    assert allowed == [True, False]
    app.handle_init()
    assert app.enter().is_fail
    assert allowed == [True, False, True]


@pytest.mark.parametrize('unknown', [False, True])
def test_next_round_requires_known_empty_safe(
    test_context: TestContext,
    config: BagelConfig,
    record: BagelRunRecord,
    monkeypatch: pytest.MonkeyPatch,
    unknown: bool,
) -> None:
    """后续局可以从有锁格的空箱进入；未知格不能触发入场操作。"""
    screen = lock_safe_suffix(
        test_context.load_screen('贝果-仓库', '入仓后安全箱空-r07-118s'),
        4,
        WAREHOUSE_SAFE_CENTERS,
    )
    if unknown:
        center = WAREHOUSE_SAFE_CENTERS[0]
        screen[center.y - 48 : center.y + 48, center.x - 48 : center.x + 48] = 0
    test_context.add_mock_screenshot(screen)
    op = BagelApp(test_context, config, record)
    op.initial_clear_pending = False
    enter = MagicMock(return_value=OperationResult(True, '模拟入场成功'))
    monkeypatch.setattr(BagelEnter, 'execute', enter)
    result = op.enter()
    if unknown:
        assert result.is_fail and '状态不明' in result.status
        enter.assert_not_called()
    else:
        assert result.is_success
        enter.assert_called_once()


@pytest.mark.parametrize(
    'status,success,limit',
    [
        ('已返回贝果入口', True, 1),
        ('已返回大世界', True, 1),
        ('执行超时', False, 1),
        ('已返回贝果入口', True, 0),
    ],
)
def test_return_after_success(
    config: BagelConfig,
    record: BagelRunRecord,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    success: bool,
    limit: int,
) -> None:
    """调用实际返回包装和完成判断，节点流转和计数保持原样。"""
    app = BagelApp(MagicMock(), config, record)
    app.success_rounds = 1
    config.max_success_rounds = limit
    logger = MagicMock()
    monkeypatch.setattr(bagel_app, 'log', logger)
    monkeypatch.setattr(
        bagel_app.BagelReturn, 'execute', lambda self: OperationResult(success, status)
    )
    result = app.return_after_success()
    assert result.is_success == success
    if success:
        decision = app.decide_success_rounds()
        assert decision.status == ('已成功入仓 1 局' if limit else '继续入场')
    messages = [
        call.args[0] % call.args[1:] if len(call.args) > 1 else call.args[0]
        for call in logger.info.call_args_list
    ]
    text = '\n'.join(messages)
    assert ('已达到成功次数上限' in text) == (success and limit > 0)
    if success and limit:
        assert ('并返回大世界' in text) == (status == '已返回大世界')
    assert app.success_rounds == 1 and app.failure_retries_used == 0


def test_three_rounds_sell_second_and_final_only(
    config: BagelConfig,
    record: BagelRunRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """每局重建结算操作仍跨局累计；第二局到期，第三局正常结束补卖。"""
    config.sell_interval = 2
    config.max_success_rounds = 3
    decisions: list[bool] = []

    def execute(op: BagelSettleWarehouse) -> OperationResult:
        due = getattr(op, 'sell_due', True)
        decisions.append(due)
        return OperationResult(
            True, BagelDeposit.STATUS_DONE, data={'sale_completed': due}
        )

    monkeypatch.setattr(BagelSettleWarehouse, 'execute', execute)
    app = BagelApp(MagicMock(), config, record)
    for _ in range(3):
        assert app.settle().is_success
    assert decisions == [False, True, True]
    assert app.success_rounds == 3
    assert app.rounds_since_sell == 0


def test_failure_deposit_counts_but_empty_does_not(
    config: BagelConfig,
    record: BagelRunRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """失败入仓计出售间隔，空箱不计；失败终止不会触发正常结束补卖。"""
    config.sell_interval = 3
    config.max_success_rounds = 1
    statuses = iter(
        [BagelDeposit.STATUS_DONE, BagelDeposit.STATUS_EMPTY, BagelDeposit.STATUS_DONE]
    )
    decisions: list[bool] = []

    def execute(op: BagelSettleWarehouse) -> OperationResult:
        due = getattr(op, 'sell_due', True)
        decisions.append(due)
        return OperationResult(True, next(statuses), data={'sale_completed': False})

    monkeypatch.setattr(BagelSettleWarehouse, 'execute', execute)
    app = BagelApp(MagicMock(), config, record)
    assert app.settle_after_defeat().is_success
    assert app.settle_after_defeat().is_success
    assert app.settle_after_defeat().is_success
    assert decisions == [False, False, False]
    assert app.rounds_since_sell == 2 and app.success_rounds == 0
    app.handle_init()
    assert app.rounds_since_sell == 0


def test_failed_settlement_does_not_reset_count(
    config: BagelConfig,
    record: BagelRunRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """出售失败不清零，也不增加成功次数。"""
    app = BagelApp(MagicMock(), config, record)
    app.rounds_since_sell = 2
    monkeypatch.setattr(
        BagelSettleWarehouse, 'execute', lambda _: OperationResult(False, '筛选失败')
    )
    assert app.settle().is_fail
    assert app.rounds_since_sell == 2 and app.success_rounds == 0
