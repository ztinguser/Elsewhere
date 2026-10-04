# Elsewhere backend

在此目录执行 `uv sync`，然后运行 `uv run backend`。服务监听 `127.0.0.1:8000`，使用独立用户数据目录；开发环境可参照 `.env.example` 设置 `ELSEWHERE_DATA_DIR`。同一数据目录只运行一个后端进程，不使用多个 Uvicorn worker。

写请求需要 `Origin: http://127.0.0.1:8000`，Host 同样为 `127.0.0.1:8000`。无需 Key 即可使用本地回忆、存档和阅读接口。

## 后台生成

以下请求接受后返回 HTTP 202，不等待模型生成。验证失败仍返回 4xx；后台执行失败记录在任务的 `status`、`error_code` 和 `error_message` 中。

| 请求 | 响应 |
| --- | --- |
| `POST /branches/{id}/plan` | 初始方案任务 |
| `POST /branches/{id}/plan/answers` | 答案整理任务；答案随任务先保存 |
| `POST /branches/{id}/start` | 首阶段任务 |
| `POST /branches/{id}/choices/{choice_id}/decision` | `{choice, task}` |
| `POST /branches/{id}/stages/{position}/narrative` | `{status, task}`；内容齐全时 status 为 completed |
| `POST /branches/{id}/tasks/{task_id}/retry` | 新任务；重复重试同一旧任务返回同一后继任务 |

任务包含稳定 `id`、`branch_id`、`status`、当前 `stage`、`waiting_reason`、`waiting_object_id`、`retry_of`、`retry_count`。相同请求不会重复调用模型。失败后需显式调用重试接口；方案本身存在前提冲突时读取方案并修改前提创建新分支，不能反复自动重试。

全局按入队顺序执行一个任务，每个分支最多一个活跃任务。阶段推演之后自动接续文学内容；正式结果仍通过原方案、阶段、章节和 ending 读取接口获取。方案确认仍为同步操作，不自动启动人生推演。

### 状态与等待

- `queued → running → waiting_input / completed / failed`。
- 等待原因 `questionnaire`、`plan_confirmation` 的关联对象为分支 ID；`simulation_choice` 的关联对象为模拟选择 ID。等待用户时不占用执行位置。
- 提交问卷或模拟决定时，在同一事务内结束等待任务并创建下一任务；确认方案仅结束方案等待任务。无 Key 提交模拟决定沿用既有行为：保留决定，将对应任务标为失败，配置 Key 后重试。
- 已生成阶段保留，文学失败只重试缺失正文。到达选择节点且正文已发布后，任务为 waiting_input；到达终点并发布全部终点内容后为 completed。
- 关闭浏览器不影响后台执行。退出后端或重启识别到遗留 queued/running 时转为 interrupted；waiting_input 保留原内容。

### 取消与恢复

| 请求 | 行为 |
| --- | --- |
| `POST /branches/{id}/tasks/{task_id}/cancel` | 取消 queued、running、waiting_input 或 interrupted，返回当前任务；重复取消幂等 |
| `POST /branches/{id}/tasks/{task_id}/resume` | 恢复 interrupted 或 cancelled，返回 HTTP 202 和同一任务；重复恢复不重复入队 |
| `POST /branches/{id}/tasks/{task_id}/retry` | 重试 failed，创建关联的新任务；不用于中断恢复 |

取消先保存状态，再中止当前调用；已发布正文、有效事件、问卷答案和模拟决定均保留。每次恢复分配新的 execution_id，迟到的旧执行不能发布结果。已结束任务不能取消，已有后续任务时不能恢复旧取消任务。

恢复先核对任务和检查点版本，再核对已保存成果。仅恢复原问卷、确认或选择等待、或成果已经齐全时不需要 Key；还需继续生成时要求 Key，缺少 Key 不改变原停止状态。程序重启不自动继续收费调用。

`life.sqlite` 保存正式档案、任务和草稿；`workflow.sqlite` 使用 LangGraph SQLite 检查点保存步骤结果。任务图 thread_id 为任务 ID，命名步骤为 `<任务ID>:<步骤名>`。方案生成、推演生成/评审、文学生成/复核分别保存结果；等待节点使用 interrupt，业务接口处理用户输入后才结束对应等待。客户端不直接提交 LangGraph 恢复指令。

中断后重放未完成的编排，跳过已持久化的模型步骤和正式结果；草稿按任务、内容类型及尝试次数复用原版本，保留返工次数。发布与任务状态、检查点之间若有落盘时间差，以业务库成果对账，不重复正文和段落。没有可靠落盘的在途调用可能重跑，不保证只计费一次，也不从某一个字继续。失败后的显式 retry 开始新尝试，仍复用已发布内容。

当前工作流版本为 `2`。迁移 v018 将未使用检查点的旧版任务迁入本版本，未知的任务或检查点版本拒绝恢复/重试，不静默从头生成。修改步骤含义或提示词导致旧结果不可复用时，后续开发应同步升级工作流版本。凭据只在运行时注入，不进入图状态；图执行禁用外部追踪。

### 查询与 SSE

- `GET /branches/{id}/tasks`：任务列表，按创建顺序。
- `GET /branches/{id}/tasks/{task_id}`：当前完整任务。
- `GET /branches/{id}/tasks/{task_id}/events`：SSE；以 `Last-Event-ID` 请求头或 `after` 查询参数从上次序号继续（请求头优先）。

事件序号 `id` 为数据库内递增序号，不保证单任务连续。事件类型：

| event | data |
| --- | --- |
| `task` | 任务状态、步骤、等待原因与关联对象、错误、更新时间 |
| `stage_published` | 已保存的阶段 position |
| `narrative_published` | 阶段 position、内容 kind、正式 version_id |
| `snapshot` | 当前任务状态快照；无新序号 |

状态事件与对应状态修改在同一事务中保存；发布事件与业务发布同事务保存。运行中约每15秒发送保活注释；任务离开 queued/running 后补完事件、发送 snapshot 并结束流，客户端应关闭 EventSource，下一次操作后订阅新任务。重连可补取已保存事件，也可直接查询任务和正式内容。即使游标已追平或超前，结束前仍返回 snapshot，不丢失最终状态及等待原因。事件不包含问卷内部理由、模型提示或未审核正文，不逐字推送草稿。

## 本地测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

测试使用临时数据目录及假模型。测试和验收文档沿用仓库现有忽略设置，保留在本地。
