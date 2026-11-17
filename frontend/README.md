# 观澜：可选研究工作台

## 启动

在有 Python 环境的机器、仓库根目录执行：

    python -m pip install -r requirements.txt
    python server.py

打开终端显示的本机地址，把同一终端显示的访问令牌粘贴到页面，点击连接。
默认监听 127.0.0.1:8765。令牌仅保存在页面内存，不写 localStorage。
可通过 RESEARCH_UI_TOKEN 环境变量指定令牌；不要放在 URL、截图或 Git 中。

上传 PDF/XLSX（最大 20 MB），选择演示或正式分析。正式模式需要服务端 DEEPSEEK_API_KEY，且必须勾选数据传输授权。
默认一个分析进程，最多八个活动任务，单任务超时 900 秒。--workers 2 可显式开启两个工作线程。
任务与材料存放 workspace/web/；服务重启后未完成任务标记中断，不自动重跑以免重复费用。
不要同时运行两个共享同一 data-dir 的服务实例。日志和上传材料不会自动清理，管理员需管理磁盘空间。

## 可选部署与安全边界

CLI 不依赖 server.py 或 frontend。服务器压力大时不启动 Web 服务即可。
Web 服务是单用户本地工具，不是公网生产服务。仅本机绑定，并检查 Host、Origin、Bearer 令牌；不支持跨域调用。
远程机器建议通过受控 SSH 隧道访问，保留同端口 localhost 转发；不要改成 0.0.0.0 直接暴露公网。
多用户部署需要另加 HTTPS、身份权限、配额、存储隔离和上传沙箱。文件头与 ZIP 大小检查不是恶意文档沙箱。
文件上传没有自动重试；网络超时请先刷新任务列表，避免重复提交。
直接打开 index.html 时只能导入本地结果，不能上传到服务器。

## A2UI 实现范围

明确固定为 A2UI v0.9，不声称是最新版本或全协议实现。已核对上游 a2ui-project/a2ui 的 specification/v0_9/json/server_to_client.json、client_to_server.json 和 minimal catalog 示例。
实现 createSurface、updateComponents、根路径 updateDataModel、deleteSurface，以及 Text、Column、Row、Button 四种白名单组件。
组件目录 ID 使用 https://a2ui.org/specification/v0_9/catalogs/minimal/catalog.json。
不支持函数表达式、动态模板、子路径数据更新、任意组件或脚本。遇到不支持内容明确报错。
上传、令牌、列表是宿主固定 UI；结果详情由后端生成 NDJSON 协议消息并驱动渲染，不仅仅是给 JSON 换个名字。
下载按钮生成 v0.9 action envelope，由宿主本地处理，只允许 download_result，不执行任意服务器动作。
GET /api/jobs/{id}/ui 返回完整 NDJSON 响应；当前不是实时逐 token 流，不声称支持完整流式协商或官方渲染器一致性认证。

## 测试

    node --check frontend/app.js
    node --check frontend/a2ui.js
    node tests/test_frontend.cjs
    python scripts/verify_release.py

本机没有 Python，不执行后端测试。目标机器需验证：鉴权失败、非法文件、队列满、正式模式未授权、重启中断、下载、A2UI 更新及移动端操作。
