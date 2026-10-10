# 贝果测试整理记录

按行为覆盖精简。真实故障图片保留，未删除素材。六个已知失败先修复并通过后才整理。

| 原测试或组合 | 覆盖去向与理由 |
|---|---|
| `test_warehouse_clean.py::test_settle_rechecks_full_capacity_after_successful_deposit` | 由结算 test_sale_retry 的完整操作图覆盖出售开关、满仓、空箱与唯一重试。 |
| `test_warehouse_clean.py::test_settle_full_limits_sale_retry` | 由结算 test_sale_retry 的完整操作图覆盖出售开关、满仓、空箱与唯一重试。 |
| `test_flows.py::test_open_box_stops_after_three_missed_interactions` | 由 bagel_run_flow/test_container_recovery 的真实输入序列覆盖补按、已开面板和三次交互上限；保留实机失败帧用例。 |
| `test_flows.py::test_open_box_retries_after_search_panel_closes` | 由 bagel_run_flow/test_container_recovery 的真实输入序列覆盖补按、已开面板和三次交互上限；保留实机失败帧用例。 |
| `test_flows.py::test_open_box_does_not_press_while_search_panel_open` | 由 bagel_run_flow/test_container_recovery 的真实输入序列覆盖补按、已开面板和三次交互上限；保留实机失败帧用例。 |
| `test_flows.py::test_open_box_retries_missed_interaction_once` | 由 bagel_run_flow/test_container_recovery 的真实输入序列覆盖补按、已开面板和三次交互上限；保留实机失败帧用例。 |
| `bagel_enter/test_confirm_entry.py::test_initial_zero_does_not_click_min` | 由 test_investment_flow 的真实金额、MIN、延迟归零及进入完整流程覆盖；异常读数与点击失败单测保留。 |
| `bagel_enter/test_confirm_entry.py::test_nonzero_investment_waits_for_new_zero_frame` | 由 test_investment_flow 的真实金额、MIN、延迟归零及进入完整流程覆盖；异常读数与点击失败单测保留。 |
| `bagel_enter/test_confirm_entry.py::test_live_500k_frame_clicks_min_only` | 由 test_investment_flow 的真实金额、MIN、延迟归零及进入完整流程覆盖；异常读数与点击失败单测保留。 |
| `bagel_route_vision/test_locate.py::test_live_other_spawns_rejected` | 同一底图和截图由 bagel_fixed_map/test_locate 历史真值清单统一验证；保留上层位置冲突及出生分类测试。 |
| `bagel_route_vision/test_locate.py::test_archived_route_positions` | 同一底图和截图由 bagel_fixed_map/test_locate 历史真值清单统一验证；保留上层位置冲突及出生分类测试。 |
| `bagel_route_vision/test_locate.py::test_missing_map_rejected` | 同一底图和截图由 bagel_fixed_map/test_locate 历史真值清单统一验证；保留上层位置冲突及出生分类测试。 |
| `bagel_route_vision/test_locate.py::test_other_spawns_rejected` | 同一底图和截图由 bagel_fixed_map/test_locate 历史真值清单统一验证；保留上层位置冲突及出生分类测试。 |
| `bagel_route_vision/test_locate.py::test_second_reference_box_cross_round` | 同一底图和截图由 bagel_fixed_map/test_locate 历史真值清单统一验证；保留上层位置冲突及出生分类测试。 |
| `bagel_route_vision/test_locate.py::test_spawn_cross_round` | 同一底图和截图由 bagel_fixed_map/test_locate 历史真值清单统一验证；保留上层位置冲突及出生分类测试。 |
| `bagel_minimap/test_register_minimap.py::test_other_spawns_rejected` | 非目标出生截图由固定底图历史真值清单覆盖；底层独立变换、锚点、几何边界仍保留。 |
| `bagel_clear_loadout/test_unload_next.py::test_confirmed_unload_selects_next_from_same_observation` | 完整清空流程覆盖逐格选择及搬运计数；不再单独锁定省略等待轮数的实现细节。 |
| `bagel_slots/test_inspect_safe_slots.py::test_warehouse_entry_crops_warehouse_positions` | 仓库/局内的真实容量识别与完整入仓回归覆盖坐标，取消对内部裁图调用参数的重复断言。 |
| `bagel_item_vision/test_choose.py::test_full_safe_leaves_lower_priority_results` | test_storage.py 的真实拖拽、材料故障图、金币和满箱流程覆盖选择结果；保留完整品质顺序和同品质类型顺序的纯逻辑测试。 |
| `bagel_item_vision/test_choose.py::test_currency_is_never_selected` | test_storage.py 的真实拖拽、材料故障图、金币和满箱流程覆盖选择结果；保留完整品质顺序和同品质类型顺序的纯逻辑测试。 |
| `bagel_item_vision/test_choose.py::test_swap_when_result_strictly_better_than_worst_safe` | test_storage.py 的真实拖拽、材料故障图、金币和满箱流程覆盖选择结果；保留完整品质顺序和同品质类型顺序的纯逻辑测试。 |
| `bagel_item_vision/test_choose.py::test_fill_empty_safe_with_best_result` | test_storage.py 的真实拖拽、材料故障图、金币和满箱流程覆盖选择结果；保留完整品质顺序和同品质类型顺序的纯逻辑测试。 |
| `bagel_item_vision/test_choose.py::test_material_is_lower_than_non_material_regardless_of_quality` | test_storage.py 的真实拖拽、材料故障图、金币和满箱流程覆盖选择结果；保留完整品质顺序和同品质类型顺序的纯逻辑测试。 |
| `test_warehouse_clean.py::test_filter_dialog_areas_and_zero_count` | 真实完整出售与零件数取消流程覆盖同样区域识别，不重复逐个调用识别 helper。 |
| `test_warehouse_clean.py::test_idle_and_sell_mode_areas` | 真实完整出售与零件数取消流程覆盖同样区域识别，不重复逐个调用识别 helper。 |
| `bagel_return/test_execute.py` 参数组合 | 两组代表短加载和长加载加对话黑屏，保留全部六个失败修复后再缩减组合。 |
| `bagel_return/test_execute.py` 参数组合 | 两种渐显画面和两个入口各出现一次，完整阻挡流程仍覆盖两个入口。 |
| `bagel_clear_loadout/test_clear_and_unload.py` 参数组合 | 完整清空已覆盖十件全卸；只保留另一背包容量下的道具卸装流程。 |
| `bagel_settle/test_sale_retry.py` 参数组合 | 结算十条业务分支各覆盖启动/局末两入口；满仓最终守卫另有直接测试，去掉无关四重展开。 |
| `bagel_store/test_transfer_guards.py` 参数组合 | 容量2至5的锁格识别由 inspect_safe_slots 全保留；完整输入流程保留最小容量、四格换物和五格无锁。 |
| `bagel_deposit/test_execute_capacity_deposit.py` 参数组合 | 中间容量由识别测试覆盖，完整入仓保留锁格和无锁两端。 |
| `bagel_store_carried/test_bulk_transfer.py` 参数组合 | 锁格中间容量由识别测试覆盖，转存的未知/空箱分支保留。 |
| `bagel_navigate/test_navigation.py` 参数组合 | 停稳后的四种结果全保留，两种移动模式与容器分别覆盖；容器恢复完整流程仍覆盖box/safe。 |
| `bagel_store/test_panel_transition.py` 参数组合 | 28张异常改由独立守卫逐图验证，收集/回读各一集成场景，取消56次重复业务搭建。 |
| `bagel_enter/test_clear_starting_loadout.py` 全部用例 | 启动清空完整流程与再次执行选图核验覆盖首次清空后的重新核验，应用重试测试覆盖不再清空。 |
| `bagel_enter/test_handle_starting_warehouse.py` 全部用例 | test_starting_warehouse_flow 从真实仓库开始执行完整转存、返回与入场。 |
| `bagel_enter/test_leave_starting_warehouse.py` 全部用例 | test_starting_warehouse_flow 保留返回无效、超时与点击失败。 |
| `bagel_enter/test_verify_zero_loadout.py` 全部用例 | 清空完整流程及 test_reject_unsafe_entry 保留非零拒绝，应用重试验证首次资格。 |
| `bagel_enter/test_handle_init.py` 全部用例 | test_speedup_flow 的复用操作场景与投资完整流程验证重新执行，不单独检查内部字段重置。 |
| `bagel_app/test_handle_init.py` 全部用例 | 正式 execute 重试预算与出售跨局计数测试验证本次任务状态。 |
| `bagel_app/test_settle_after_defeat.py` 全部用例 | 正式 execute 的失败收尾及应用配置测试验证实际结算参数，不单独重复委托调用。 |
| `bagel_store/test_transfer_status_gap.py` 全部用例 | test_unknown_retry 完整流程保留回读基线、状态恢复和持续未知停止。 |

## 文件合并

同一模块的简单方法测试合并为行为文件；测试函数与参数保持原样，不以合并文件冒充删除覆盖。

- `zzz-od-test/test/zzz_od/application/bagel/test_defeat.py` → `zzz-od-test/test/zzz_od/application/bagel/test_behavior.py`
- `zzz-od-test/test/zzz_od/application/bagel/test_deposit_flows.py` → `zzz-od-test/test/zzz_od/application/bagel/test_behavior.py`
- `zzz-od-test/test/zzz_od/application/bagel/test_map_projection.py` → `zzz-od-test/test/zzz_od/application/bagel/test_behavior.py`
- `zzz-od-test/test/zzz_od/application/bagel/test_rounds_flows.py` → `zzz-od-test/test/zzz_od/application/bagel/test_behavior.py`
- `zzz-od-test/test/zzz_od/application/bagel/test_spawn_hud_gap.py` → `zzz-od-test/test/zzz_od/application/bagel/test_behavior.py`
- `zzz-od-test/test/zzz_od/application/bagel/test_storage_flows.py` → `zzz-od-test/test/zzz_od/application/bagel/test_behavior.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_app/test_check_ready.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_app/test_round_state.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_app/test_enter.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_app/test_round_state.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_app/test_enter_safe_capacity.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_app/test_round_state.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_app/test_return_after_success.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_app/test_round_state.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_app/test_sell_interval.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_app/test_round_state.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_clean/test_allow_safe_items.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_clean/test_sale_guards.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_clean/test_safe_clear_capacity.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_clean/test_sale_guards.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_clear_loadout/test_execute_clear_loadout.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_clear_loadout/test_clear_and_unload.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_clear_loadout/test_unload_next.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_clear_loadout/test_clear_and_unload.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_enter/test_close_opening_map.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_enter/test_entry_guards.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_enter/test_confirm_entry.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_enter/test_entry_guards.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_enter/test_open_hub_from_other_screens.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_enter/test_entry_guards.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_enter/test_reject_unsafe_entry.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_enter/test_entry_guards.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_item_vision/test_badge_crops.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_item_vision/test_quality_and_badges.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_item_vision/test_identify_quality.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_item_vision/test_quality_and_badges.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_route_vision/test_is_at_spawn.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_route_vision/test_spawn_and_heading.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_route_vision/test_locate.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_route_vision/test_spawn_and_heading.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_route_vision/test_player_angle.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_route_vision/test_spawn_and_heading.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_screen/test_complete_loadout.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_screen/test_ocr_and_parsing.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_screen/test_entry_warning.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_screen/test_ocr_and_parsing.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_screen/test_investment_coin.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_screen/test_ocr_and_parsing.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_screen/test_native_ocr.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_screen/test_ocr_and_parsing.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_screen/test_parse.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_screen/test_ocr_and_parsing.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_screen/test_read_loadout.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_screen/test_ocr_and_parsing.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_screen/test_zero_loadout.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_screen/test_ocr_and_parsing.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_settle/test_final_capacity_guard.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_settle/test_final_state.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_settle/test_final_safe_capacity.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_settle/test_final_state.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_slots/test_inspect_safe_slots.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_slots/test_slot_evidence.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_slots/test_slot_texture_guard.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_slots/test_slot_evidence.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_store/test_confirm_transfer_safe_state.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_store/test_transfer_guards.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_store/test_drag_retry.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_store/test_transfer_guards.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_store/test_execute_capacity.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_store/test_transfer_guards.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_store/test_store_next_capacity.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_store/test_transfer_guards.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_store_carried/test_backpack_centers.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_store_carried/test_bulk_transfer.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_store_carried/test_execute_store_carried.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_store_carried/test_bulk_transfer.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_store_carried/test_store_next.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_store_carried/test_bulk_transfer.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_store_carried/test_store_next_capacity_carried.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_store_carried/test_bulk_transfer.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_transfer/test_carried_slot_state.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_transfer/test_double_click_and_slots.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_transfer/test_double_click_item.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_transfer/test_double_click_and_slots.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_usage/test_log_screenshot.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_usage/test_messages.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_usage/test_log_start.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_usage/test_messages.py`
- `zzz-od-test/test/zzz_od/application/bagel/bagel_usage/test_stop_guidance.py` → `zzz-od-test/test/zzz_od/application/bagel/bagel_usage/test_messages.py`
- `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_add_step.py` → `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_actions.py`
- `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_checked_changed.py` → `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_actions.py`
- `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_drag_point.py` → `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_actions.py`
- `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_draw.py` → `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_actions.py`
- `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_edit_action.py` → `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_actions.py`
- `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_edit_point.py` → `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_actions.py`
- `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_edit_step.py` → `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_actions.py`
- `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_export_flow.py` → `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_actions.py`
- `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_move_step.py` → `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_actions.py`
- `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_refresh_stop_shortcut.py` → `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_actions.py`
- `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_start_trial.py` → `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_actions.py`
- `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_update_disclosures.py` → `zzz-od-test/test/zzz_od/gui/view/bagel/bagel_route_editor/test_editor_actions.py`

根目录综合测试最终拆为 `test_storage.py`、`test_deposit.py`、`test_rounds.py` 与 `test_spawn_and_defeat.py`，分别维护入箱、入仓、整局和出生/失败行为。
