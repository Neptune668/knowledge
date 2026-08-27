# 前后端接口契约（API 蓝图）

> 统一约定：
> - 认证方式：除登录接口外，请求头携带 `Authorization: Bearer <access_token>`。
> - 数据格式：请求/响应均为 `application/json`（上传接口为 `multipart/form-data`，AI 问答为 `text/event-stream`）。
> - 统一响应包裹：`{ "code": 0, "message": "success", "data": ... }`，`code=0` 成功，非 0 见错误码。
> - 分页参数：`page`（从 1 起）、`page_size`（默认 20），响应含 `list`、`total`。

---

## 一、统一错误码

| code | 含义 |
| --- | --- |
| 0 | 成功 |
| 40001 | 参数校验失败 |
| 40100 | 未认证 / Token 缺失或过期 |
| 40300 | 无操作权限（RBAC 拒绝） |
| 40301 | 无数据权限（知识单元访问被拒） |
| 40400 | 资源不存在 |
| 40900 | 冲突（唯一约束、状态机非法流转） |
| 42900 | 触发限流 |
| 50000 | 服务器内部错误 |

---

## 二、接口清单

| 接口编号 | 接口名称 | 请求方式 | 路径 | 请求参数（含类型/必填/示例） | 返回数据结构（含字段说明） | 异常状态码说明 |
| --- | --- | --- | --- | --- | --- | --- |
| API-01 | 用户登录 | POST | `/api/auth/login` | `username` string 必填（3-32 字符，示例 `admin`）；`password` string 必填（示例 `Passw0rd!`） | `data.access_token` string JWT；`data.user_info` object（`id`、`username`、`display_name`、`department_id`、`department_name`、`roles[]`）；`data.permissions[]` string 权限码列表 | 40001 参数缺失；40100 用户名或密码错误；40900 账号已停用；42900 登录限流 |
| API-02 | 用户登出 | POST | `/api/auth/logout` | 无 body（Header 带 Token） | `data: null`（Token 加入黑名单） | 40100 未认证 |
| API-03 | 获取当前用户信息 | GET | `/api/auth/me` | 无 | `data` = user_info + permissions（同登录） | 40100 Token 过期 |
| API-04 | 获取部门树 | GET | `/api/org/departments` | 无 | `data[]`：`id`、`parent_id`、`name`、`leader_id`、`sort_order`、`children[]`（递归） | 40300 无权限 |
| API-05 | 新增部门 | POST | `/api/org/departments` | `parent_id` long 可选（NULL 顶级）；`name` string 必填；`leader_id` long 可选；`sort_order` int 可选默认 0 | `data.id` 新部门 ID | 40001 名称空；40300 无权限；40900 名称冲突 |
| API-06 | 更新部门 | PUT | `/api/org/departments/{id}` | `name`/`leader_id`/`parent_id`/`sort_order` 可选 | `data: null` | 40001；40300；40400 部门不存在 |
| API-07 | 删除部门 | DELETE | `/api/org/departments/{id}` | 无 | `data: null` | 40300；40400；40900 存在子部门或成员 |
| API-08 | 用户列表 | GET | `/api/org/users` | `keyword` string 可选；`department_id` long 可选；`status` int 可选；`page`、`page_size` | `data.list[]`：`id`、`username`、`display_name`、`department_id`、`department_name`、`status`、`roles[]`、`created_at`；`data.total` | 40300 无权限 |
| API-09 | 新增用户 | POST | `/api/org/users` | `username` 必填唯一；`display_name` 必填；`password` 必填；`department_id` 可选；`role_ids[]` 可选 | `data.id` | 40001 校验失败；40300；40900 用户名已存在 |
| API-10 | 编辑用户 | PUT | `/api/org/users/{id}` | `display_name`、`department_id`、`role_ids[]` 可选 | `data: null` | 40001；40300；40400 用户不存在 |
| API-11 | 重置密码 | PUT | `/api/org/users/{id}/password` | `new_password` string 必填 | `data: null` | 40001 密码强度不足；40300；40400 |
| API-12 | 启停用用户 | PUT | `/api/org/users/{id}/status` | `status` int 必填（1/0） | `data: null` | 40001；40300；40400；40900 不允许停用自己 |
| API-13 | 角色列表 | GET | `/api/org/roles` | 无 | `data[]`：`id`、`role_name`、`role_code`、`description`、`permissions[]` | 40300 |
| API-14 | 新增角色 | POST | `/api/org/roles` | `role_name` 必填；`role_code` 必填唯一；`description` 可选 | `data.id` | 40001；40300；40900 编码冲突 |
| API-15 | 编辑角色 | PUT | `/api/org/roles/{id}` | `role_name`、`description` 可选 | `data: null` | 40001；40300；40400 |
| API-16 | 分配角色权限 | POST | `/api/org/roles/{id}/permissions` | `permissions[]` string 必填（权限码数组，全量覆盖） | `data: null` | 40001 权限码非法；40300；40400 |
| API-17 | 删除角色 | DELETE | `/api/org/roles/{id}` | 无 | `data: null` | 40300；40400；40900 角色仍被用户引用 |
| API-18 | 知识导入（上传） | POST | `/api/knowledge/import` | `files[]` file 必填（PDF/MD/DOCX/TXT）；`category` string 可选；multipart 表单 | `data.task_id` string 导入任务 ID（异步解析） | 40001 格式/大小非法；40300；42900 上传限流 |
| API-19 | 查询导入进度 | GET | `/api/knowledge/import/{task_id}` | 无 | `data.status`（`processing`/`success`/`failed`）；`data.progress` int 0-100；`data.results[]`（文件名、成功单元数、错误信息） | 40400 任务不存在 |
| API-20 | 知识单元列表 | GET | `/api/knowledge/units` | `keyword` 可选；`category` 可选；`status` 可选；`page`、`page_size` | `data.list[]`：`id`、`unit_code`、`title`、`category`、`file_type`、`status`、`permission_summary`、`creator_name`、`updated_at`；`data.total` | 40300 |
| API-21 | 知识单元详情 | GET | `/api/knowledge/units/{id}` | 无 | `data`：单元全字段 + `permissions[]`（`target_type`、`target_id`、`target_name`） | 40300；40400 |
| API-22 | 更新知识单元 | PUT | `/api/knowledge/units/{id}` | `title` 可选；`content` 可选；`category` 可选；`tags[]` 可选；`summary` 可选 | `data: null`（更新后触发向量重同步） | 40001；40300；40400；40900 版本冲突 |
| API-23 | 批量删除知识单元 | DELETE | `/api/knowledge/units` | `unit_ids[]` long 必填 | `data.deleted_count` int | 40001 空列表；40300；40400 部分不存在 |
| API-24 | 配置数据权限 | POST | `/api/knowledge/units/{id}/permissions` | `permissions[]` object 必填（`target_type` 枚举 `global/department/role/user`、`target_id` long 可选，`global` 时省略） | `data: null`（即时生效） | 40001 实体类型非法；40300；40400 |
| API-25 | 权限校验（供智能体调用） | POST | `/api/knowledge/check-permissions` | `user_id` long 必填；`unit_ids[]` long 必填 | `data.authorized_unit_ids[]`；`data.unauthorized_unit_ids[]` | 40001；40300 无调用权限；40400 用户不存在 |
| API-26 | AI 流式问答 | POST | `/api/ai/chat/stream` | `question` string 必填；`session_id` string 可选（不传则新建） | SSE 事件流：`token`（增量文本）、`citation`（引用单元 `id/title/authorized`）、`permission_denied`（未授权单元提示）、`done`（含 `session_id`、token 统计） | 40001 问题为空；40100 未登录；40301 全部无权限；42900 限流；50000 |
| API-27 | 会话历史列表 | GET | `/api/ai/sessions` | `page`、`page_size` | `data.list[]`：`session_id`、`title`、`last_message`、`updated_at` | 40100 |
| API-28 | 会话消息历史 | GET | `/api/ai/sessions/{session_id}` | 无 | `data[]`：`role`（user/assistant）、`content`、`citations[]`、`created_at` | 40100；40400 |
| API-29 | 看板核心指标 | GET | `/api/dashboard/metrics` | `start_date`/`end_date` 可选（时间范围） | `data.total_access`、`data.unique_users`、`data.total_units`、`data.total_tokens`、`data.avg_response_time_ms` | 40300 |
| API-30 | 高频问题 TOP 榜 | GET | `/api/dashboard/rankings/questions` | `limit` int 可选默认 10；`start_date`/`end_date` 可选 | `data[]`：`question`、`count`、`related_unit_id` | 40300 |
| API-31 | 知识单元热度榜 | GET | `/api/dashboard/rankings/units` | `limit` int 可选默认 10；`start_date`/`end_date` 可选 | `data[]`：`unit_id`、`title`、`access_count` | 40300 |
| API-32 | Token/耗时趋势 | GET | `/api/dashboard/stats/tokens` | `granularity`（`day`/`week`）必填；`start_date`/`end_date` 可选 | `data[]`：`date`、`total_tokens`、`avg_response_time_ms` | 40001 粒度非法；40300 |
| API-33 | FAQ 推荐列表 | GET | `/api/settlement/faqs/recommendations` | `status` 可选默认 `pending_review`；`page`、`page_size` | `data.list[]`：`id`、`question`、`recommend_count`、`related_unit_id`、`suggested_answer`、`created_at`；`data.total` | 40300 |
| API-34 | FAQ 审核 | POST | `/api/settlement/faqs/{id}/review` | `action` string 必填（`approve`/`reject`）；`edited_answer` string 可选（approve 时可用） | `data: null`（approve 时写入缓存） | 40001 action 非法；40300；40400；40900 已审核 |
| API-35 | 已发布 FAQ 库 | GET | `/api/settlement/faqs` | `status=published`；`keyword` 可选；`page`、`page_size` | `data.list[]`：`id`、`question`、`answer`、`category`、`hit_count`、`cache_status`、`reviewed_at` | 40300 |
| API-36 | 知识缺口列表 | GET | `/api/settlement/knowledge-gaps` | `status` 可选；`page`、`page_size` | `data.list[]`：`id`、`question_pattern`、`ask_count`、`last_asked_at`、`status`、`resolved_unit_id` | 40300 |
| API-37 | 缺口一键建档 | POST | `/api/settlement/knowledge-gaps/{id}/resolve` | `unit_id` long 可选（关联补全单元） | `data: null`（status→resolved） | 40300；40400；40900 已处理 |

---

## 三、自查说明

1. **业务目标映射**：PRD 的 5 大能力（知识维护、组织权限、AI 鉴权问答、数据看板、知识沉淀）均已映射到前端 6 大页面组、后端 8 大模块与 37 个接口。
2. **CRUD 覆盖**：用户/角色/部门/知识单元/FAQ/缺口均具备增删改查；权限类配置（角色权限、数据权限、FAQ 审核）为独立的写接口，已覆盖。
3. **补充隐含接口**：相比 PRD 原始接口清单，新增了登出、当前用户信息、部门 CRUD、角色 CRUD、导入进度、会话历史、缺口建档等接口，以闭合业务闭环。
4. **[待确认] 项**：SSE 断点续传、分页默认值、限流阈值、JWT 双 Token、状态枚举等，已在两份说明书及上文标注。
