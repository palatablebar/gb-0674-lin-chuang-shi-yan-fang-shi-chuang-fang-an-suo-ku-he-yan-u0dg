# 访视与冻结定义

样例均为虚构编号，无身份信息。受试者入组日期由subjects表唯一确定，记录中的入组基准必须完全一致。采样日期和入组日期均转为Asia/Shanghai日历日期，差值为访视日；时刻先统一UTC。
方案选择按当前受试者assignment和该次发生时刻查半开生效窗，匹配必须唯一，不能使用全局最新方案。v1访视V1=[5,10)、V2=[12,17)；v2为[6,11)、[13,18)。受试者00001于10月10日转v2，其他受试者仍用v1。
PRIMARY计入访视完成，RETEST只替代该次测量值。首次记录必须唯一且在访视窗内。缺首次访视、重复首次和窗外访视均阻断，复检不能填补漏访或消除原偏离。
复检须引用同受试者同访视的PRIMARY，晚于原采样且不超过72小时，版本必须更高。同最高版本复检冲突时保留原结果并阻断。所有检验值以mg/dL输出，g/L乘100。
锁库须所有规定访视完成，无偏离、复检问题和隔离行。冻结包包含每条选定结果、原始行号、方案版本与访视窗。此工具只验证试验数据完整性，不做诊断判断或生产锁库。

## 中心交接裁决

CSV 可选末两列 `center`（报送中心码）与 `handoff`（交接单号），旧11列表头按 `default_center` 补中心。上下文 `centers` 为中心码册，`transfers` 为受试者转移事件（`at` 生效时刻、`from`/`to` 中心、`handoff` 依据文号），数据集级覆盖放在 `context.<dataset>.json`。

责任中心取访视时刻最近一次已生效（半开，`transfer.at <= visit.at`）转移的转入中心；无生效转移取默认中心。方案选择、访视窗、偏离、复检选定与冻结清单均携带 `owner_center` 与 `handoff`，责任归属全链路共享。

| 原因码 | 含义 | 是否阻断 | 去向 |
|---|---|---|---|
| `BAD_CENTER` | 报送中心不在册 | 是 | 隔离 quarantine |
| `HANDOFF_CONFLICT` | 同交接单同中心存在不同原值 | 是 | 隔离 quarantine |
| `HANDOFF_RETRY` | 同交接单同中心同业务指纹重试，去重不新增访视 | 否 | center_evidence |
| `CENTER_DUPLICATE` | 非责任中心同次访视报送，原始记录保留 | 否 | center_evidence |
| `CENTER_CONFLICT` | 无转移依据却多中心同报，责任中心未定 | 是 | center_blocks→偏离 |
| `CENTER_OWNER_MISSING` | 仅非责任中心报送，责任中心无记录 | 是 | 偏离复核 |

业务指纹剔除传输编号 `id` 与物理行号，因此同一交接重试不会产生第二条访视；行守恒计入 `handoff_retry` 与 `center_duplicate`。冻结包新增 `handoff.json`（转移事件、中心册、证据与阻断）和 `handoff_evidence.csv`，封印哈希覆盖交接裁决。重算异常返回 `RERUN_FAILED`，数据库不写入，旧批次保持原 revision 与封印。
