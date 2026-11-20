# 深度登记 临床试验访视窗与方案锁库核验

规模：中型。使用者：临床试验数据管理员。核心规则：按入组基准计算访视半开窗，方案修订按受试者生效时间选版；漏访不可用复检伪填。

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 记录采信 | 执行并复核记录采信与中心交接裁决 | `POST /api/intake` | `app/modules/intake/rules.py`、`app/modules/intake/handoff.py` | `tests/test_intake.py`、`tests/test_handoff.py` |
| M2 方案版本 | 执行并复核方案版本 | `POST /api/protocol` | `app/modules/protocol/rules.py` | `tests/test_protocol.py` |
| M3 访视排窗 | 执行并复核访视排窗 | `POST /api/windows` | `app/modules/windows/rules.py` | `tests/test_windows.py` |
| M4 偏离复核 | 执行并复核偏离复核 | `POST /api/deviation` | `app/modules/deviation/rules.py` | `tests/test_deviation.py` |
| M5 复检裁决 | 执行并复核复检裁决 | `POST /api/retest` | `app/modules/retest/rules.py` | `tests/test_retest.py` |
| M6 锁库检查 | 执行并复核锁库检查 | `POST /api/locking` | `app/modules/locking/rules.py` | `tests/test_locking.py` |
| M7 冻结归档 | 执行并复核冻结归档 | `POST /api/archive` | `app/modules/archive/rules.py` | `tests/test_archive.py` |

## 陷阱登记

| TRAP | 现象 | 朴素实现 | 本项目处理 | 处理位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-01 | 旧编码检验单位 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/intake/rules.py` | `tests/test_intake.py::test_legacy_real` |
| TRAP-02 | BOM表头 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/intake/rules.py` | `tests/test_intake.py::test_bom_real` |
| TRAP-08 | 受试者前导零 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/intake/rules.py` | `tests/test_intake.py::test_leading_zero_real` |
| TRAP-04 | 分段表头 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/intake/rules.py` | `tests/test_intake.py::test_header_real` |
| TRAP-05 | 缺列记录 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/intake/rules.py` | `tests/test_intake.py::test_columns_real` |
| TRAP-18 | 空态 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/intake/rules.py` | `tests/test_intake.py::test_empty_types` |
| TRAP-07 | 缺失检验值 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/protocol/rules.py` | `tests/test_protocol.py::test_sentinel_real` |
| TRAP-25 | 个体方案生效重叠 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/protocol/rules.py` | `tests/test_protocol.py::test_overlap_assignment` |
| TRAP-15 | 检验单位换算 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/protocol/rules.py` | `tests/test_protocol.py::test_unit_conversion_real` |
| TRAP-23 | 访视窗末端 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/windows/rules.py` | `tests/test_windows.py::test_half_open_end` |
| TRAP-11 | UTC日历归一 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/windows/rules.py` | `tests/test_windows.py::test_utc_day_equivalence` |
| TRAP-31 | 跨中心同次访视重复 | 按受试者合并重复锁库或按中心各自放行 | 按转移交接单裁决唯一责任中心，非责任报送留证不计访视 | `app/modules/intake/handoff.py` | `tests/test_handoff.py::test_transfer_dataset_lockable_with_unique_owner` |
| TRAP-32 | 交接重试重复建访视 | 重试报文生成第二条访视 | 业务指纹去重，重试仅留证据不新增访视 | `app/modules/intake/handoff.py` | `tests/test_handoff.py::test_handoff_retry_does_not_add_visit` |
| TRAP-33 | 无依据多中心同报 | 静默选一条放行 | `CENTER_CONFLICT` 阻断并展示原因 | `app/modules/intake/handoff.py` | `tests/test_handoff.py::test_center_conflict_without_transfer_basis_blocks` |
| TRAP-34 | 责任中心缺报 | 用非责任记录替代放行 | `CENTER_OWNER_MISSING` 阻断，原始记录保留 | `app/modules/deviation/rules.py` | `tests/test_handoff.py::test_owner_missing_when_only_non_owner_reports` |
| TRAP-35 | 重算失败覆盖旧版 | 失败结果写入导致历史丢失 | 捕获异常返回 `RERUN_FAILED`，旧批次不动 | `app/main.py` | `tests/test_handoff.py::test_rerun_failure_keeps_previous_version` |

## 对账规则

原始逻辑输入=采纳行+隔离行+空行+重复表头+同值重复+交接重试+非责任中心报送。业务计算按 DATA-DICTIONARY.md 分别核验，不能把上级与下级重复加总。所有隔离保留编号、原值、原始行号和稳定原因码；交接证据保留报送中心、责任中心、交接依据、原因码与原始行号。

## 已知不覆盖

数据来自仓内样例或用户粘贴文件，不连接外部业务生产系统。平台不执行实际资金划转或行政审批。
