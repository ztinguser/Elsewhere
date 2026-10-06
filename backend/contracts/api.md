# 后端接口基线 v1

日期：2026-10-07。用于 Part11 起的前端接入；基础地址为 `http://127.0.0.1:8000`，不带 `/api` 前缀。业务库版本 19，工作流版本 2，导出/备份格式版本 1。这些版本与本文件的接口基线版本各自独立。

`openapi.json` 固定路由、请求参数及公共响应协议；`examples.json` 保存通过接口取得的虚构离线样例，补充当前 OpenAPI 中未逐字段建模的成功响应。样例里的 ID、时间、正文和用量不是常量。不得用离线文学样例评估真实写作质量。

本次基线包含 37 条路径、49 个操作。样例包含 40 个 HTTP 请求响应及 `export_manifest` 导出包清单；SSE 的 response 为事件流字符串，204 的 response 为 null。`*_submit` 保存刚提交时的响应，`start_task` 为等待选择，`decide_task` 为完成；`start_ending` 与 `decide_ending` 分别展示尚不可用和已完成的终点内容。生成流程同时验证了重启、备份恢复和删除；未收录 Key、Cookie 值或内部提问理由。

## 连接与错误

- 先同源 `POST /session`，成功为 204，浏览器自动保存 HttpOnly、SameSite=Strict Cookie。后续 fetch、下载和 EventSource 同源携带 Cookie；不把会话放在 URL、localStorage 或请求正文。
- 只有 `GET /health`、`POST /session` 不需要已有会话。两者仍检查 Host 和来源。写请求必须有 `Origin: http://127.0.0.1:8000`；其他 Origin、Host 或浏览器 cross-site/same-site 标记会被拒绝。
- 后端重启后旧 Cookie 失效。收到 `401 SESSION_REQUIRED` 后重新建立会话，再读取任务与数据。失去会话不等于任务被取消，不自动重新发起生成。
- JSON 使用 UTF-8；204 没有正文，不调用 `.json()`。每个 HTTP 响应有 `X-Request-ID`。ZIP 和 SSE 使用各自的媒体类型。
- 错误统一为 `{"error":{"code":"...","message":"..."}}`，没有 FastAPI 默认的 `detail` 数组。前端用 code 分流、message 展示；不解析中文文案控制流程。
- HTTP 202 仅表示请求已被接收。请求失败看 HTTP 错误；生成失败看任务的 status/error_code/error_message。
- 列表直接返回数组，无分页外壳。缺失对象通常 404；详情以接口表为准。兼容新增响应字段，不根据正文或数组显示顺序推断 ID。

| HTTP / code | 含义与处理 |
| --- | --- |
| 400 `INVALID_HOST` | 使用固定的本机服务地址 |
| 403 `INVALID_ORIGIN` / `ORIGIN_REQUIRED` | 校对来源与开发代理；不尝试绕过 |
| 401 `SESSION_REQUIRED` | 重新建立本地会话 |
| 422 `VALIDATION_ERROR` | 请求字段或字段间约束不符合要求；保留输入 |
| 400 `MODEL_KEY_REQUIRED` | 设置 Key 后由用户继续；是否已保存决定见下文 |
| 502 `MODEL_AUTH_FAILED` / `MODEL_ACCESS_DENIED` | 更换 Key 或检查账号权限 |
| 502 `MODEL_BALANCE_LOW` | 余额不足；保留资料，用户处理后显式重试 |
| 502 `MODEL_NETWORK_ERROR` / `MODEL_TIMEOUT` / `MODEL_UNAVAILABLE` / `MODEL_RATE_LIMITED` | 连接、超时、服务不可用或限流，不由前端无限自动重试 |
| 502 `MODEL_REQUEST_INVALID` / `MODEL_REQUEST_FAILED` / `MODEL_INVALID_OUTPUT` | 模型请求或输出失败；保留输入和已发布内容 |
| 409 `HTTP_409` | 版本、当前业务状态、重复请求参数冲突或数据管理忙碌；重新读取当前对象 |
| 404 `HTTP_404` | 对象不存在；取消相应订阅或重新读取列表 |
| 405 `HTTP_405` | 方法不支持；`Allow` 指明可用方法 |
| 503 `DATA_MAINTENANCE` | 正在导出、备份或删除；保留未保存输入，稍后重试 |
| 500 `INTERNAL_ERROR` | 数据库/服务异常，不显示底层错误细节，不把这次操作显示为保存成功 |
| 其他 `HTTP_<状态码>` | 业务 HTTP 错误仍使用相同外壳，例如 Key 为空时 `HTTP_422` |

模型错误也会出现在后台任务中，此时查询任务本身仍为 HTTP 200。`STAGE_REVIEW_FAILED`、`NARRATIVE_REVIEW_FAILED`、`TASK_EXECUTION_FAILED`、`MODEL_SETUP_FAILED`、`WORKFLOW_VERSION_UNSUPPORTED`、`TASK_UNSUPPORTED` 等为任务失败原因。未知错误使用通用失败展示，并允许重新读取状态；不要将未知值解释成完成。

## 回忆、草稿与存档

| 请求 | 输入 | 成功响应 |
| --- | --- | --- |
| GET `/health` | 无 | 200 `{status:"ok"}` |
| GET `/drafts/{draft_id}` | 前端保存自己分配的稳定 draft_id | 200 草稿；不存在 404 |
| PUT `/drafts/{draft_id}` | time_text、content、expected_revision；新建为 0 | 200 `{id,revision}` |
| DELETE `/drafts/{draft_id}` | 查询参数 expected_revision ≥ 1 | 204 |
| POST `/memories` | time_text、content，均非空 | 201 `{id,revision}` |
| GET `/memories?q=…` | q 可省略，连续关键词匹配时间和正文 | 200 回忆数组，保持手动顺序 |
| GET `/memories/{memory_id}` | 无 | 200 单条回忆 |
| PUT `/memories/{memory_id}` | time_text、content、expected_revision ≥ 1 | 200 `{id,revision}` |
| DELETE `/memories/{memory_id}` | 查询参数 expected_revision ≥ 1 | 204 |
| PUT `/memories/order` | `{ids:[完整正式回忆ID列表]}` | 204 |
| POST `/memories/polish` | `{content:"当前编辑正文"}` | 200 `{content,prompts,model,usage}` |
| GET `/life/archive` | 无 | 200 `{revision,confirmed_revision,confirmed_at,is_confirmed}` |
| POST `/life/archive/confirm` | `{expected_revision:当前档案revision}` | 200 同上 |

草稿允许空时间和正文；正式回忆不允许。草稿与回忆详情都有 id、time_text、content、revision、created_at、updated_at；回忆还有排序 position。日期时间戳为带时区的字符串，用户的 time_text 是自由文本，不能自动当成日期比较。

润色只返回建议，不修改草稿或回忆。prompts 是 0—3 个可选问题字符串；usage 可能为 null，不承诺每次都有全部 token 字段。用户采用后仍需正式保存；迟到的润色不得覆盖后续编辑。取消/失败保留原编辑内容。

草稿保存不改变存档状态；正式回忆增删改或排序变化使存档失效。没有正式回忆时存档不能确认。q 非空的搜索子集不能用于全量排序。读取无 Key、无模型调用；revision 用于冲突检测，不能靠客户端自增假装保存成功。

## 分叉、问卷与确认

| 请求 | 输入 | 成功响应 |
| --- | --- | --- |
| POST `/branches` | request_id、memory_id、alternative、expected_revision（档案版本） | 201 `{id}` |
| GET `/branches` | 无 | 200 分支数组，创建时间倒序 |
| GET `/branches/{branch_id}` | 无 | 200 分支与固定 snapshot |
| POST `/branches/{branch_id}/plan` | 无正文 | 202 Task |
| GET `/branches/{branch_id}/plan` | 无 | 200 Plan |
| POST `/branches/{branch_id}/plan/answers` | expected_revision（方案版本）、answers | 202 Task |
| POST `/branches/{branch_id}/plan/confirm` | expected_revision（方案版本） | 200 已确认 Plan |

创建分支不自动调用模型，先固定档案快照和创建时本地日期 target_date。request_id 对同一次操作保持不变；同 ID 同参数返回原分支，不同参数为冲突。初始分叉需存档确认，旧分支继续及模拟改选不受当前存档失效影响。

分支字段：id、parent_id、fact_version_id、fork_fact_id、alternative、target_date、assumptions、status、created_at、updated_at、fork_choice_id、stage_count、current_time_text、fork_decision、facts_outdated。详情另有 snapshot；列表没有完整快照。parent_id/fork_choice_id/fork_decision/current_time_text 可为 null，facts_outdated 可为 null（旧档案无法判断）。分支 status 为 draft/ready/completed；是否正在生成或等待输入必须结合任务，不能只看 ready。

Plan 字段：branch_id、revision、status、plan、questions、answers。plan 包含 change、preserved、affected、external_conditions、information_limits、assumptions、blockers；其中四类事实条目是 `{fact_id,detail}`，assumptions/blockers 为字符串数组。questions 的每项只有 question_id、question、assumption，没有内部 reason；题数用 questions.length，最多三题，一次展示。

回答例子：`{"expected_revision":1,"answers":[{"question_id":"q1","answer":"虚构：预算3000元"},{"question_id":"q2","use_assumption":true}]}`。每题必须填写非空 answer 或显式 use_assumption=true，不能两者都有或都没有；必须覆盖原问卷，不能增加题号。答案只用于当前分支。最终 Plan 仍展示原问卷及已提交答案，不会产生第二轮问题。

Plan.status 为 waiting_input/awaiting_confirmation/confirmed/blocked。blockers 有内容时需修改前提另建分支。零问题仍须确认。确认是同步操作，不自动开始人生推演。

## 阶段、决定、正文与阅读

| 请求 | 输入 | 成功响应 |
| --- | --- | --- |
| POST `/branches/{id}/start` | 无 | 202 首阶段 Task |
| GET `/branches/{id}/stages` | 无 | 200 阶段数组，position 升序 |
| GET `/branches/{id}/stages/{position}` | 无 | 200 阶段、events、choice |
| POST `/branches/{id}/choices/{choice_id}/decision` | `{option_index:0}` 或 `{custom_decision:"…"}` | 202 `{choice,task}` |
| POST `/branches/{id}/choices/{choice_id}/fork` | `{request_id:"…",decision:{option_index:1}}` | 202 `{id,task}`，id 是子分支 |
| POST `/branches/{id}/stages/{position}/narrative` | 无 | 202 `{status,task}`，已齐全时 status=completed |
| GET `/branches/{id}/chapters` | 无 | 200 正式阶段章节数组 |
| GET `/branches/{id}/chapters/{position}` | 阶段位置 | 200 单章 |
| GET `/branches/{id}/ending` | 无 | 200 `{target_date,reached_target,status,today,retrospective}` |
| GET `/branches/{id}/reading-position` | 无 | 200 阅读位置或 null |
| PUT `/branches/{id}/reading-position` | paragraph_id、char_offset（默认0） | 200 阅读位置 |

模拟选择索引从 0 开始，position 从 1 开始，两者不要混用。choice 为 null 或含 id、stage_id、branch_id、stage_position、data、decision_input、decision、decided_at；data 有 situation 和 options。decision 为实际决定文本，未选时为 null。

每阶段一个章节，阶段停在 choice 或 target。阶段详情保留评审依据、事件和事件 data；前端默认展示正文与选择，不要求展示内部依据。当前及之前章节发布后才可首次决定。重复同一决定不重复生成，不同决定请使用 fork，不能覆盖原决定。首次提交决定时缺 Key 可能返回 400，但决定和失败任务已保存，必须读取当前选择与任务后重试该任务，不能假定这次完全没有落盘。

改选只适用于已决定节点，继承父分支固定快照、终点、已确认方案及安全前缀，立即排队生成。父分支保持原样；子分支重新分配自己的阶段、选择、章节、段落 ID，不复制阅读位置。无 Key 仍会创建子分支，后台 Task 以 MODEL_KEY_REQUIRED 失败。

章节字段：id（章节ID）、version_id、position、kind、stage_id、stage_position、choice_id、title、revision、status、paragraphs。段落有 id、version_id、position、content。正式内容 status=published。保留稳定 ID，不能每次按段落数组下标重建阅读位置。

ending.status：unavailable（未到终点，today/retrospective 均 null）、pending（已到终点，可能已有一个已发布部分）、completed（两部分均已发布）。阶段正文、today、retrospective 独立发布，后续失败保留已发布部分；不要仅凭 reached_target=true 宣布全部生成完成。

阅读位置有 branch_id、chapter_id、version_id、paragraph_id、char_offset、updated_at。char_offset 按 Unicode 字符计数；JavaScript 转换时按 code point 计数，不能直接使用 UTF-16 字符串 length。跨分支段落或超出段落长度会被拒绝。阅读不发起模型调用。

## 任务与 SSE

| 请求 | 成功响应与用途 |
| --- | --- |
| GET `/branches/{id}/tasks` | 200 Task 数组，创建顺序 |
| GET `/branches/{id}/tasks/{task_id}` | 200 Task |
| POST `…/tasks/{task_id}/cancel` | 200 Task；取消 queued/running/waiting_input/interrupted，重复取消幂等 |
| POST `…/tasks/{task_id}/resume` | 202 同一 Task；继续 interrupted/cancelled，重复请求不重复入队 |
| POST `…/tasks/{task_id}/retry` | 202 新 Task；处理 failed，重复重试同一旧任务返回同一后继任务 |
| GET `…/tasks/{task_id}/events` | 200 text/event-stream |

Task 的稳定前端字段：id、branch_id、kind、status、stage、waiting_reason、waiting_object_id、retry_of、retry_count、error_code、error_message、created_at、updated_at。当前响应还含 input_data、workflow_version、execution_id；它们供诊断，不应由页面修改或拼装成 LangGraph 恢复指令。stage 只作步骤描述，不根据某个阶段名称推断成功。

| status | 前端行为 |
| --- | --- |
| queued / running | 展示排队或运行，可取消；等待查询/SSE |
| waiting_input | 展示对应问卷、确认或模拟选择；这是正常暂停 |
| interrupted | 后端退出后的可恢复状态，用户明确继续 |
| cancelled | 保留已有成果，用户可以明确继续 |
| failed | 显示错误并提供显式重试；不循环自动点击重试 |
| completed | 读取正式内容；确认等待结束的任务完成不代表整条人生完成 |

waiting_reason 为 questionnaire / plan_confirmation / simulation_choice，前两者 waiting_object_id 为分支 ID，后者为选择节点 ID；其他状态通常为 null。排队全局串行，同一分支最多一个活跃任务，等待输入不占执行位置。恢复仅还原已保存等待或已完成结果时不需要 Key；还需生成才要求 Key。后端重启不自动继续收费调用。

SSE 的 id 是数据库递增序号，不保证单任务连续。重连发送 `Last-Event-ID` 或查询参数 `after`，请求头优先。事件如下：

| event | data |
| --- | --- |
| task | id、branch_id、status、stage、waiting_reason、waiting_object_id、error_code、error_message、updated_at |
| stage_published | position |
| narrative_published | position、kind、version_id |
| snapshot | 当前任务公开状态，同 task 字段，无新序号 |
| deleted | id、branch_id；任务已删除 |

运行时约15秒一次保活注释。任务离开 queued/running 后补完事件、发送 snapshot 并结束流；即使游标已追平或超前仍有 snapshot。前端收到 snapshot 或 deleted 后主动关闭 EventSource，下一次操作订阅对应任务，避免浏览器自动重连终态。断流不取消后台任务；可先查询任务，再决定是否重连。SSE 不传未审核正文。

## 数据、凭据与故障边界

| 请求 | 成功响应 |
| --- | --- |
| GET `/model/credentials` | 200 `{configured,storage}`；storage=none/session/system |
| PUT `/model/credentials` | 输入 key、remember（默认false）；200 配置状态，不回传 Key |
| DELETE `/model/credentials` | 200 清除后的状态 |
| POST `/model/verify` | 200 `{verified,model,json_output,usage}`；会调用模型 |
| GET `/data` | 200 directory、life_database、workflow_database、backup_directory、deletion_pending |
| POST `/data/export` | 200 ZIP 下载，UTF-8 JSON 档案＋工作流库＋manifest |
| POST `/data/backups` | 201 `{id,created_at,size}`；创建一致数据库备份 |
| GET `/data/backups` | 200 上述备份数组，保存时间倒序 |
| GET `/data/backups/{backup_id}` | 200 ZIP 下载 |
| DELETE `/data/branches/{branch_id}` | 200 `{deleted_branches,deleted_tasks}` |
| DELETE `/data` | 200 同上 |

安全记住不可用时退回本次会话，并通过配置响应说明状态；不将 Key 明文落盘。凭据操作不清除人生资料，人生资料删除不清除 Key。

导出是 ZIP 内的 JSON 全档案，不是可直接导入的备份。备份 ZIP 内为 life.sqlite、workflow.sqlite 和校验清单。停机恢复命令见 backend/README.md，仅恢复到新的空目录，不覆盖旧目录。

导出/备份不取消生成，等候空档最多5秒，仍忙则409；数据维护期间新保存请求503。删除先取消关联任务再等待停止，仍忙时409，保留数据但任务可能已取消。删除父分支包含所有后代，并清理相关应用管理备份；不清除用户另存导出。全量清空包含草稿、快照、任务、检查点和应用备份。

断网、缺 Key、余额不足时，已保存回忆、草稿、章节、阅读位置、导出备份仍可使用。数据文件损坏、迁移失败或版本过新时，启动可能直接失败；不承诺提供可用 HTTP 错误页，也不自动创建空库冒充恢复成功。运行期间数据库异常通常为500；删除中途失败后保留恢复标记并暂停写入，重启先完成清理。不要通过删除数据库解决错误，应停止后端并使用经过验证的备份恢复流程。
