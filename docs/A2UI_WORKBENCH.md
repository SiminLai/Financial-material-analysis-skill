# 上传与 A2UI 工作台改造

## 位置与原因

| 位置 | 修改 | 原因 |
| --- | --- | --- |
| frontend/index.html、styles.css | 侧栏、概况卡、任务列表、上传区、详情区；响应式浅色绿灰视觉 | 减少操作层级，明确区分材料管理与研究结论 |
| frontend/app.js | 上传、模式确认、筛选、轮询、结果下载、本地导入 | 连接真实任务接口，不生成虚构任务数据 |
| frontend/a2ui.js | v0.9 白名单消息和组件处理、数据绑定、动作 envelope、循环限制 | 将服务端 UI 数据限制在可控组件内，禁止任意 HTML/脚本 |
| runtime/a2ui.py | 研究结果转协议消息 | 后端控制结果布局，数字与证据来自原结果 |
| server.py | 可选本机服务、令牌、上传检查、单进程任务队列、超时及重启恢复 | 保持 CLI 独立，约束资源消耗与重复执行 |
| tests/test_frontend.cjs | 协议生命周期、绑定、动作、安全边界测试 | 替换旧查看器测试，覆盖当前组件处理行为 |
| tests/test_web_service.py | 消息、文件类型、队列及恢复测试 | 提供目标 Python 环境的回归检查 |

## 协议核对来源

官方仓库：a2ui-project/a2ui。核对路径：specification/v0_9/json/server_to_client.json、json/client_to_server.json、catalogs/minimal/examples/3_interactive_button.json。
当前固定旧版 v0.9 子集，是为了提供小体积无构建依赖实现；不冒充最新协议或完整官方 SDK。
前端不加载第三方脚本、字体、图片或 CDN。协议消息用 textContent 安全展示。

## 验证边界

Node 静态检查与协议单元测试在本机执行；Python、真实上传分析、浏览器视觉检查需目标机器执行。
演示模式仍需安装解析及图依赖，但不调用大模型。正式运行会有模型费用和材料传输。
此批不自动提交或推送 Git；此前功能分支保持不变。
