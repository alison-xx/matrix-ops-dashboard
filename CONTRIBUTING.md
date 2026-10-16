# 参与贡献

欢迎提 issue 和 PR。动手之前请先读一遍下面几条约定：

1. **零依赖**：服务端只用 Python 标准库，前端只用原生 JS，不要引入框架和构建步骤。新的第三方文件放进 `dashboard/static/vendor/`，写清出处、版本、许可证和校验值，并且只用允许再分发的许可证。
2. **只读**：工作台不能有任何写入、发布或调用外部服务的代码。
3. **示例数据先行**：新功能要能在 `--demo` 下演示。需要新的数据就改 `dashboard/demo/make_demo.py`，同时在 `dashboard/README.md` 的「数据目录约定」里补上字段说明。
4. **单个数据源出错不能拖垮整页**：读数据要包在 `section()` 里，出错时返回空状态，并把错误写进 `errors`。
5. **截图只用示例数据**，提交前检查一遍 diff 里有没有真实账号、链接、邮箱、本机路径。

提交前在本地跑一遍：

```bash
python3 -m py_compile dashboard/server.py dashboard/demo/make_demo.py
node --check dashboard/static/app.js
python3 dashboard/server.py --demo --port 8799   # 打开每个页面看一遍，浏览器控制台不能有报错
```

新增平台：在 `server.py` 的 `PLATS` 和 `_ALIAS` 里加平台 key 和别名，在 `static/app.js` 的 `PLAT`、`PLAT_ORDER` 里加显示名，在 `style.css` 里加 `.pl-<key>` 图标和 `--p-<key>` 品牌色。
