from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsSimpleTextItem,
)
from test.harness.bagel_editor import add_step

from one_dragon.envs.env_config import EnvConfig
from zzz_od.application.bagel.bagel_flow import (
    BagelFlow,
    NavigationOptions,
    draft_path,
    load_published_flow,
    read_flow,
)
from zzz_od.gui.view.bagel.bagel_route_editor import (
    BagelRouteEditor,
    FlowMarkerItem,
    RoutePointItem,
)


def test_add_plain_move_has_no_container_and_keeps_explicit_parameters(
    editor: BagelRouteEditor,
) -> None:
    """靠近箱子后新增普通移动仍无容器，参数编辑支持撤销。"""
    editor.step_list.setCurrentRow(9)
    add_step(editor, 'move')
    step = editor.step
    assert step.action == 'move' and step.target is None
    assert not editor.target_combo.isVisible() and not editor.target_help.isVisible()
    assert editor.timeout_input.value() == 45
    assert editor.tolerance_input.value() == editor.passed_input.value() == 2
    assert editor.brake_default.isChecked()
    editor.target_combo.setCurrentIndex(1)
    assert editor.step == step
    editor.timeout_default.setChecked(False)
    editor.timeout_input.setValue(90)
    editor.edit_navigation()
    editor.tolerance_default.setChecked(False)
    editor.tolerance_input.setValue(3)
    editor.passed_default.setChecked(False)
    editor.passed_input.setValue(5)
    editor.edit_point()
    changed = editor.flow
    data = editor.step.to_dict()
    assert data['navigation'] == {'timeout': 90, 'final_mode': 'coordinate'}
    assert editor.step.waypoints[0].passed_radius == 5
    editor.undo()
    assert editor.step.waypoints[0].arrival_radius == 2
    editor.redo()
    assert editor.flow == changed


def test_rebuild_tenth_step_without_any_template(
    editor: BagelRouteEditor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """删除第十步后通过真实新增窗口重建，保存重开保持相同执行含义。"""
    editor.step_list.setCurrentRow(9)
    original = editor.step
    editor.delete_step()
    editor.step_list.setCurrentRow(8)
    monkeypatch.setattr(
        'zzz_od.gui.view.bagel.bagel_route_editor.load_published_flow',
        MagicMock(side_effect=AssertionError('新建不应读取正式模板')),
    )
    add_step(editor, 'approach', 'safe', 'small_steps', original.waypoints[-1].xy)
    editor.advanced_toggle.click()
    editor.interaction_default.click()
    editor.interaction_input.setValue(
        original.navigation.effective_interaction_distance
    )
    editor.interaction_input.editingFinished.emit()
    rebuilt = editor.step
    assert rebuilt.action == original.action and rebuilt.target == original.target
    assert [p.xy for p in rebuilt.waypoints] == [p.xy for p in original.waypoints]
    assert rebuilt.navigation.effective_timeout(
        'safe'
    ) == original.navigation.effective_timeout('safe')
    assert (
        rebuilt.navigation.effective_interaction_distance
        == original.navigation.effective_interaction_distance
    )
    assert rebuilt.navigation.effective_final_mode('safe') == 'small_steps'
    assert editor.mode_combo.currentData() == 'small_steps'
    editor.save_draft()
    reloaded = read_flow(draft_path(editor.map_id))
    assert reloaded.steps[9] == rebuilt
    monkeypatch.setattr(
        'zzz_od.gui.view.bagel.bagel_route_editor.load_published_flow',
        load_published_flow,
    )
    reopened = BagelRouteEditor(99)
    reopened.step_list.setCurrentRow(9)
    assert reopened.step == rebuilt
    assert reopened.mode_combo.currentData() == 'small_steps'
    reopened.close()
    reopened.deleteLater()


def test_switch_to_small_steps_without_previous_movement(
    editor: BagelRouteEditor,
) -> None:
    """没有前置位置、目的地又与出生点相同，仍可切换碎步且不创建方向点。"""
    flow = editor.flow
    editor._change(replace(flow, steps=(flow.steps[0], flow.steps[-1])), 0)
    add_step(editor, 'approach', 'safe', xy=editor.models[editor.map_id].spawn)
    before = editor.flow
    assert editor.mode_combo.isEnabled()
    assert editor.mode_combo.count() == 2
    assert editor.mode_combo.currentData() == 'coordinate'
    editor.mode_combo.setCurrentIndex(editor.mode_combo.findData('small_steps'))
    assert len(editor.step.waypoints) == 1
    assert not hasattr(editor, 'direction_input')
    assert editor.step.waypoints[0].xy == editor.models[editor.map_id].spawn
    editor.undo()
    assert editor.flow == before


@pytest.mark.parametrize('action', ['move', 'approach'])
@pytest.mark.parametrize('mode', ['coordinate', 'small_steps'])
def test_movement_mode_and_completion_are_independent(
    editor: BagelRouteEditor, action: str, mode: str
) -> None:
    """两种完成条件都能使用两种移动方式，保存回读始终只有一个目的地。"""
    add_step(editor, action, mode=mode, xy=(111, 83))
    assert editor.type_input.category_combo.currentText() == '移动'
    assert (
        editor.type_input.form.labelForField(editor.action_combo).text() == '完成条件'
    )
    assert editor.mode_combo.currentData() == mode
    assert editor.step.navigation.final_mode == mode
    assert len(editor.step.waypoints) == 1
    assert editor.step.waypoints[0].xy == (111, 83)
    assert editor.target_combo.isVisible() == (action == 'approach')
    assert (
        BagelFlow.from_dict(editor.flow.to_dict(), validate_order=False) == editor.flow
    )


@pytest.mark.parametrize('action', ['spawn', 'interact', 'exit'])
def test_non_movement_creation_with_and_without_target(
    editor: BagelRouteEditor, action: str
) -> None:
    """检查、箱子操作和退出分别验证新增入口，移动由专门场景覆盖。"""
    before = editor.flow
    add_step(editor, action, target='safe')
    assert editor.step.action == action
    if action in ('spawn', 'exit'):
        assert editor.step.target is None
    else:
        assert editor.step.target == 'safe'
    editor.undo()
    assert editor.flow == before


def test_cancel_creation_preserves_flow(editor: BagelRouteEditor) -> None:
    """取消新增不改流程或撤销栈。"""
    before = editor.flow
    count = len(editor.undo_stack[editor.map_id])
    add_step(editor, 'approach', cancel=True)
    assert editor.flow == before and len(editor.undo_stack[editor.map_id]) == count


def test_checks_select_execution_and_survive_reorder(
    editor: BagelRouteEditor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """点击行不选择执行；勾选随稳定标识保留，清单顺序随列表更新。"""
    editor.step_list.setCurrentRow(1)
    assert not editor.run_button.isEnabled()
    factory = MagicMock()
    monkeypatch.setattr(
        'zzz_od.gui.view.bagel.bagel_route_editor.FlowTrialWorker', factory
    )
    editor.start_trial()
    factory.assert_not_called()
    assert '勾选' in editor.trial_info.text()
    before = editor.flow
    editor.step_list.item(1).setCheckState(Qt.CheckState.Checked)
    editor.step_list.item(3).setCheckState(Qt.CheckState.Checked)
    assert editor.flow == before
    assert '2 → 4' in editor.selection_info.text()
    chosen = set(editor.checked_steps[editor.map_id])
    editor.move_step(1)
    assert editor.checked_steps[editor.map_id] == chosen
    assert '3 → 4' in editor.selection_info.text()
    editor.check_current()
    assert len(editor.checked_steps[editor.map_id]) == 1
    editor.check_steps(False)
    assert not editor.run_button.isEnabled()


def test_mouse_drag_and_undo_save_only_draft(
    editor: BagelRouteEditor, qapp: QApplication
) -> None:
    """Qt 鼠标拖点后撤销重做，保存只影响开发草稿。"""
    published = load_published_flow('janus_high_a')
    editor.step_list.setCurrentRow(1)
    original = editor.step.waypoints[0].xy
    start = editor.view.mapFromScene(QPointF(*original))
    end = editor.view.mapFromScene(QPointF(original[0] + 4, original[1] + 2))
    QTest.mousePress(editor.view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(editor.view.viewport(), end, delay=30)
    QTest.mouseRelease(editor.view.viewport(), Qt.MouseButton.LeftButton, pos=end)
    qapp.processEvents()
    changed = editor.flow
    assert changed != published
    editor.undo()
    assert editor.flow == published
    editor.redo()
    assert editor.flow == changed
    editor.save_draft()
    assert read_flow(draft_path(editor.map_id)) == changed
    assert load_published_flow(editor.map_id) == published


def test_non_movement_has_no_markers_and_movement_remains_clickable(
    editor: BagelRouteEditor,
    qapp: QApplication,
) -> None:
    """隐藏非移动标点、文字与地标后，移动点仍可选择，且不改执行勾选。"""
    original = editor.flow
    editor.step_list.setCurrentRow(3)
    items = editor.view.scene().items()
    markers = [item for item in items if isinstance(item, FlowMarkerItem)]
    destinations = [step.waypoints[-1].xy for step in original.steps if step.waypoints]
    assert sorted((item.pos().x(), item.pos().y()) for item in markers) == sorted(
        [editor.models[editor.map_id].spawn, *destinations]
    )
    assert (
        len([item for item in items if isinstance(item, QGraphicsEllipseItem)])
        == len(destinations) + 1
    )
    assert [
        item.text() for item in items if isinstance(item, QGraphicsSimpleTextItem)
    ] == ['出生位置']
    assert not editor.position_heading.isVisible()
    assert not editor.navigation_heading.isVisible()
    assert not editor.timeout_default.isVisible()
    assert editor.brief.isVisible()
    assert not editor.rules.isVisible()
    point = editor.view.mapFromScene(QPointF(*destinations[0]))
    QTest.mouseClick(editor.view.viewport(), Qt.MouseButton.LeftButton, pos=point)
    qapp.processEvents()
    assert editor.step_list.currentRow() == 1
    assert editor.position_heading.isVisible()
    assert editor.tolerance_input.isVisible()
    assert editor.mode_combo.isVisible()
    assert editor.flow == original
    assert not editor.checked_steps[editor.map_id]
    circles = [
        item
        for item in editor.view.scene().items()
        if type(item) is QGraphicsEllipseItem
    ]
    point = original.steps[1].waypoints[0]
    assert sorted(item.rect().width() / 2 for item in circles) == sorted(
        [point.arrival_radius, point.passed_radius]
    )


def test_spawn_marker_is_fixed_and_check_range_is_selected_only(
    editor: BagelRouteEditor,
    qapp: QApplication,
) -> None:
    """出生点常驻可点击，只有检查步骤显示范围，鼠标拖动不改地图或流程。"""
    original = editor.flow
    editor.step_list.setCurrentRow(9)
    assert (
        len([i for i in editor.view.scene().items() if isinstance(i, RoutePointItem)])
        == 1
    )
    assert not any(
        isinstance(i, QGraphicsLineItem) and i.pen().style() == Qt.PenStyle.DashLine
        for i in editor.view.scene().items()
    )
    assert not any(i.data(0) == 'spawn_range' for i in editor.view.scene().items())
    spawn = editor.models[editor.map_id].spawn
    start = editor.view.mapFromScene(QPointF(*spawn))
    QTest.mouseClick(editor.view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    qapp.processEvents()
    assert editor.step.action == 'spawn'
    circle = next(i for i in editor.view.scene().items() if i.data(0) == 'spawn_range')
    assert circle.rect().width() == 10
    end = editor.view.mapFromScene(QPointF(spawn[0] + 5, spawn[1] + 5))
    QTest.mousePress(editor.view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(editor.view.viewport(), end, delay=30)
    QTest.mouseRelease(editor.view.viewport(), Qt.MouseButton.LeftButton, pos=end)
    qapp.processEvents()
    marker = next(i for i in editor.view.scene().items() if i.data(0) == 'spawn')
    assert marker.pos() == QPointF(*spawn)
    assert editor.flow == original


def test_trace_visibility_preserves_positions_and_gaps(
    editor: BagelRouteEditor,
) -> None:
    """轨迹开关只控制显示，重新显示后仍不能跨定位缺失处连线。"""
    original = editor.flow
    positions = [(100, 100), (102, 100), None, (110, 100), (110, 102)]
    for xy in positions:
        editor._observe({'kind': 'observation', 'position': xy, 'angle': 0})

    def trace_path() -> QGraphicsPathItem:
        """按图例颜色取得实际轨迹。"""
        return next(
            item
            for item in editor.view.scene().items()
            if isinstance(item, QGraphicsPathItem)
            and item.pen().color().name() == '#007e50'
        )

    assert trace_path().pen().style() == Qt.PenStyle.DashLine
    for visible in (False, True):
        editor.trace_check.setChecked(visible)
        path = trace_path().path()
        if visible:
            assert path.elementCount() == 4
            assert [path.elementAt(i).isMoveTo() for i in range(4)] == [
                True,
                False,
                True,
                False,
            ]
        else:
            assert path.isEmpty()
        assert editor.trace == positions
        assert editor.flow == original
    editor.map_combo.setCurrentIndex(1)
    assert editor.trace == []


def test_existing_step_type_is_editable_and_undo_restores_all(
    editor: BagelRouteEditor,
) -> None:
    """类型转换保留标识、名称、位置和勾选，撤销恢复原高级参数。"""
    editor.step_list.setCurrentRow(8)
    editor.check_current()
    original = editor.flow
    old = editor.step
    editor.action_combo.setCurrentIndex(editor.action_combo.findData('approach'))
    assert editor.step.action == 'approach'
    assert editor.step.id == old.id and editor.step.name == old.name
    assert editor.step.waypoints[-1].xy == old.waypoints[-1].xy
    assert editor.step.navigation.effective_timeout(
        'box'
    ) == old.navigation.effective_timeout(None)
    assert old.id in editor.checked_steps[editor.map_id]
    editor.undo()
    assert editor.flow == original
    editor.type_input.category_combo.setCurrentText('箱子操作')
    assert not editor.step.waypoints
    assert not editor.coordinate_row.isVisible()
    editor.undo()
    assert editor.flow == original


def test_editing_approach_preserves_hidden_legacy_parameters(
    editor: BagelRouteEditor,
) -> None:
    """拖动、坐标和范围编辑后保存回读，保留旧高级参数与碎步方式。"""
    editor.step_list.setCurrentRow(9)
    editor._replace_step(
        replace(
            editor.step,
            navigation=NavigationOptions(
                timeout=123,
                brake_distance=4,
                final_mode='small_steps',
                interaction_distance=8,
            ),
        )
    )
    editor.interaction_default.setChecked(False)
    editor.interaction_input.setValue(9)
    editor.edit_navigation()
    editor.timeout_default.setChecked(False)
    editor.timeout_input.setValue(120)
    editor.edit_navigation()
    editor.tolerance_default.setChecked(False)
    editor.tolerance_input.setValue(1.5)
    editor.edit_point()
    before = editor.flow
    editor.drag_point(0, (223, 115))
    assert editor.step.waypoints[0].xy == (223, 115)
    editor.x_input.setValue(225)
    editor.y_input.setValue(117)
    editor.edit_point()
    assert editor.step.waypoints[0].xy == (225, 117)
    assert editor.step.waypoints[0].tolerance == 1.5
    assert editor.step.navigation == NavigationOptions(
        timeout=120,
        brake_distance=4,
        final_mode='small_steps',
        interaction_distance=9,
    )
    editor.save_draft()
    assert read_flow(draft_path(editor.map_id)) == editor.flow
    editor.undo()
    editor.undo()
    assert editor.flow == before


def test_target_change_keeps_effective_settings_and_position(
    editor: BagelRouteEditor,
) -> None:
    """旧步骤隐式方式和超时在更换目标时固定为原有效值，坐标不变。"""
    editor.step_list.setCurrentRow(9)
    original = editor.flow
    step = editor.step
    assert step.navigation.final_mode == 'small_steps'
    editor.target_combo.setCurrentIndex(editor.target_combo.findData('box'))
    changed = editor.step
    assert [p.xy for p in changed.waypoints] == [p.xy for p in step.waypoints]
    assert changed.navigation.effective_final_mode('box') == 'small_steps'
    assert changed.navigation.effective_timeout(
        'box'
    ) == step.navigation.effective_timeout('safe')
    assert (
        changed.navigation.effective_interaction_distance
        == step.navigation.effective_interaction_distance
    )
    assert [p.arrival_radius for p in changed.waypoints] == [
        p.arrival_radius for p in step.waypoints
    ]
    assert all(p.stage == 'box' for p in changed.waypoints)
    editor.undo()
    assert editor.flow == original


def test_export_changes_only_chosen_resource(
    editor: BagelRouteEditor, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """导出只写明确的正式流程文件，不自动保存草稿。"""
    dialog = MagicMock()
    dialog.exec.return_value = True
    monkeypatch.setattr(
        'zzz_od.gui.view.bagel.bagel_route_editor.MessageBox',
        MagicMock(return_value=dialog),
    )
    monkeypatch.setattr(
        'zzz_od.gui.view.bagel.bagel_route_editor.resource_root',
        lambda _: tmp_path / 'published',
    )
    editor.export_flow()
    assert read_flow(tmp_path / 'published' / 'flow.yml') == editor.flow
    assert not draft_path(editor.map_id).exists()


def test_action_reorder_invalid_save_and_undo(editor: BagelRouteEditor) -> None:
    """收集移到开箱前允许继续编辑，但禁止保存。"""
    editor.step_list.setCurrentRow(3)
    editor.move_step(-1)
    editor.save_draft()
    assert '保存失败' in editor.status.text()
    assert not draft_path(editor.map_id).exists()
    editor.undo()
    editor.save_draft()
    assert draft_path(editor.map_id).exists()


def test_stop_button_uses_main_program_key(
    editor: BagelRouteEditor,
) -> None:
    """独立启动读取主程序配置，复用上下文时显示其自定义按键。"""
    EnvConfig(MagicMock()).key_stop_running = 'f8'
    editor._refresh_stop_shortcut()
    assert editor.stop_button.text() == '停止 F8'
    editor.ctx = SimpleNamespace(key_stop_running='f7')
    editor._refresh_stop_shortcut()
    assert editor.stop_button.text() == '停止 F7'
    assert editor.stop_button.shortcut().isEmpty()


def test_running_locks_editing_and_close_waits(
    editor: BagelRouteEditor, monkeypatch: pytest.MonkeyPatch
) -> None:
    """开始试跑后不能编辑或销毁线程，关闭请求只请求停止。"""
    from PySide6.QtGui import QCloseEvent
    from PySide6.QtWidgets import QGraphicsItem

    worker = MagicMock()
    worker.isRunning.return_value = True
    factory = MagicMock(return_value=worker)
    monkeypatch.setattr(
        'zzz_od.gui.view.bagel.bagel_route_editor.FlowTrialWorker',
        factory,
    )
    editor.step_list.setCurrentRow(1)
    editor.step_list.item(1).setCheckState(Qt.CheckState.Checked)
    editor.step_list.item(4).setCheckState(Qt.CheckState.Checked)
    selected = (editor.flow.steps[1].id, editor.flow.steps[4].id)
    editor.start_trial()
    assert factory.call_args.args[2] == selected
    assert not editor.step_list.isEnabled()
    before = editor.flow
    assert not editor.name_edit.isEnabled()
    assert not editor.map_combo.isEnabled()
    editor.drag_point(0, (999, 999))
    assert editor.flow == before
    for item in editor.view.scene().items():
        if isinstance(item, RoutePointItem):
            assert not item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable
    event = QCloseEvent()
    editor.closeEvent(event)
    assert not event.isAccepted()
    worker.stop.assert_called_once()
    worker.isRunning.return_value = False
    worker.ctx = None
    editor._close_pending = False
    editor._trial_finished()
    assert editor.map_combo.isEnabled()
    assert editor.worker is None
    worker.deleteLater.assert_called_once()


def test_disclosures_preserve_custom_values_and_draft(editor: BagelRouteEditor) -> None:
    """折叠不重置迁移参数，编辑坐标、保存和撤销仍保留高级设置。"""
    editor.step_list.setCurrentRow(8)
    original = editor.flow
    nav = editor.step.navigation
    passed = editor.step.waypoints[0].passed_tolerance
    assert nav.brake_distance == 6
    assert editor.name_edit.isVisible() and editor.point_name.isVisible()
    assert editor.x_input.isVisible() and editor.y_input.isVisible()
    assert not editor.timeout_input.isVisible()
    assert not editor.passed_input.isVisible()
    assert not editor.brake_input.isVisible()
    assert not editor.rules.isVisible()
    assert '有单独设置' in editor.advanced_toggle.text()
    editor.advanced_toggle.click()
    editor.help_toggle.click()
    assert editor.timeout_input.isVisible()
    assert editor.brake_input.value() == 6
    assert editor.rules.isVisible()
    editor.advanced_toggle.click()
    editor.help_toggle.click()
    assert editor.flow == original
    assert not editor.undo_stack[editor.map_id]
    editor.x_input.setValue(editor.x_input.value() + 1)
    editor.edit_point()
    assert editor.step.navigation == nav
    assert editor.step.waypoints[0].passed_tolerance == passed
    editor.save_draft()
    assert read_flow(draft_path(editor.map_id)) == editor.flow
    editor.undo()
    assert editor.flow == original


def test_disclosures_follow_step_type_without_resetting_editor(
    editor: BagelRouteEditor,
) -> None:
    """已展开区域随动作显示适用字段，切到非移动不泄漏旧参数和说明。"""
    editor.step_list.setCurrentRow(1)
    original = editor.flow
    editor.advanced_toggle.click()
    editor.help_toggle.click()
    assert editor.timeout_input.isVisible() and editor.passed_input.isVisible()
    editor.step_list.setCurrentRow(9)
    assert editor.timeout_input.isVisible()
    assert not editor.passed_input.isVisible() and not editor.brake_input.isVisible()
    assert editor.interaction_input.isVisible() and editor.target_help.isVisible()
    assert editor.position_heading.text() == '目的地 · 地图像素'
    assert (editor.x_input.value(), editor.y_input.value()) == editor.step.waypoints[
        -1
    ].xy
    editor.step_list.setCurrentRow(10)
    assert editor.rules.isVisible()
    assert not editor.advanced_toggle.isVisible()
    assert not editor.coordinate_row.isVisible()
    assert not editor.parameter_help.isVisible() and not editor.target_help.isVisible()
    editor.step_list.setCurrentRow(1)
    assert editor.timeout_input.isVisible() and editor.passed_input.isVisible()
    assert editor.flow == original
