# Elsewhere backend

在此目录执行 `uv sync`，然后运行 `uv run backend`。服务监听 `127.0.0.1:8000`，使用独立用户数据目录；开发环境可参照 `.env.example` 设置 `ELSEWHERE_DATA_DIR`。同一数据目录只运行一个后端进程，不使用多个 Uvicorn worker。

写请求需要 `Origin: http://127.0.0.1:8000`，Host 同样为 `127.0.0.1:8000`。无需 Key 即可使用本地回忆、存档和阅读接口。

## 后台生成（Part08 第一个功能节点）

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

本节点尚未提供取消、恢复接口及 LangGraph 检查点；interrupted 的继续执行和版本核对由 Part08 第二个功能节点完成，当前不能用 retry 代替恢复。

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
