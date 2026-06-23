# Security

本文档记录当前项目已经加入的安全边界，以及为什么需要这些边界。

当前项目仍处于开发阶段，所以 `DEBUG=True` 可以暂时保留，方便看 Django 报错和调试数据库问题。上线前必须改成 `DEBUG=False`，并补齐生产环境安全配置。

## CSRF

CSRF 防的是“用户已经登录或浏览器已经带有可信 cookie 时，被第三方页面诱导发起写操作”。

本项目虽然现在还没有正式登录体系，但已经有会改变状态的接口：

- 创建会话
- 发送聊天消息
- 置顶会话
- 删除会话
- 生成工单

这些接口如果没有 CSRF 校验，浏览器访问恶意页面时，恶意页面可以诱导用户浏览器向本地或线上服务发送 POST/PATCH/DELETE 请求。即使当前只是本地项目，也应该从一开始把写操作边界加上，避免后面接登录时忘记补。

当前做法：

- Django 保留 `CsrfViewMiddleware`。
- 聊天页面 `<form>` 中输出 `{% csrf_token %}`，确保浏览器拿到 `csrftoken` cookie。
- 前端所有 POST/PATCH/DELETE 请求统一走 `csrfFetch()`。
- `csrfFetch()` 从 `csrftoken` cookie 读取 token，并设置 `X-CSRFToken`。
- Ninja 写接口使用 `csrf_required` 包装，显式拒绝缺失或无效 CSRF token 的请求。

为什么不关闭 CSRF：

- 关闭后本地调试更省事，但会把错误习惯带到正式接口。
- 本项目有会话和工单状态，写接口必须有基本请求来源校验。
- Django 已经提供成熟机制，没有必要自己造一套 token 方案。

## XSS

XSS 防的是“用户输入、RAG 引用、模型输出中夹带 HTML/JS，最终被浏览器当成页面代码执行”。

本项目 XSS 风险比较高，因为页面会展示多种不可信内容：

- 用户输入
- 模型输出
- RAG 引用原文
- 会话标题
- 错误信息
- 工单 JSON 内容

这些内容都不能默认可信。特别是模型输出和 RAG 引用，看起来像系统生成内容，但来源仍然可能包含用户文本或外部数据。

当前做法：

- Django template 保持默认 autoescape，不使用 `mark_safe`。
- 会话标题由 Django template 自动转义。
- 前端普通文本走 `escapeHtml()`。
- RAG 引用逐行拆分后再转义，不直接插入原始 HTML。
- Markdown 渲染使用 `marked.parse()` 后再走 `DOMPurify.sanitize()`。
- 如果 `marked` 或 `DOMPurify` 没有加载成功，fallback 也只返回转义后的纯文本，不返回原始 HTML。
- Markdown 链接协议限制为 `http`、`https`、`mailto`、`tel` 和相对链接，避免 `javascript:` 这类危险协议。
- SSE error 消息插入页面前会先转义。

为什么 Markdown 也要净化：

- Markdown 可以生成 HTML。
- 模型可能输出 `<script>`、`<img onerror=...>`、`javascript:` 链接。
- 用户可以把恶意内容放进问题里，再经模型或历史记录展示回来。
- 所以 Markdown 渲染不能直接 `innerHTML = marked.parse(text)`。

## DEBUG

当前不改 `DEBUG`，原因是项目还没上线，调试 Django、PostgreSQL、pgvector、Ollama 链路时需要完整错误页。

上线前必须改：

```env
DJANGO_DEBUG=0
```

上线前还要检查：

- `DJANGO_SECRET_KEY` 必须换成真实随机值。
- `DJANGO_ALLOWED_HOSTS` 只允许真实域名。
- Cookie 安全属性按 HTTPS 环境开启。
- 静态文件由生产方式托管。
- 数据库密码不能使用示例值。
- 任何 API key 只能放在环境变量或密钥系统中，不能提交到 git。

## 测试覆盖

当前测试覆盖：

- 缺少 CSRF token 的写接口会返回 `403`。
- 带合法 CSRF token 的写接口可以正常执行。
- 会话标题中的 `<script>` 会被转义展示，不会作为脚本执行。

后续如果新增写接口，应同时补 CSRF 测试。

后续如果新增富文本展示区域，应保证它使用现有 Markdown sanitize 或 HTML escape 路径。
