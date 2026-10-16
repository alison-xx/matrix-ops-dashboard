# 第三方文件（固定版本，本地存放，页面不依赖外网）

| 文件 | 来源 | 版本 | 许可证 | 校验 |
|---|---|---|---|---|
| `echarts-5.6.0.min.js` | https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js | 5.6.0 | Apache-2.0（`licenses/echarts-LICENSE.txt`） | 与 npm 官方包 `echarts-5.6.0.tgz` 里的 `dist/echarts.min.js` 比对，SHA-256 `bf4a2235…e11c07b1` 一致 |
| `logos/tiktok.svg` | https://cdn.jsdelivr.net/npm/simple-icons@16.30.0/icons/tiktok.svg | simple-icons 16.30.0 | CC0-1.0（`licenses/simple-icons-LICENSE.md`） | 抖音与 TikTok 同款音符标 |
| `logos/kuaishou.svg` | https://cdn.jsdelivr.net/npm/simple-icons@16.30.0/icons/kuaishou.svg | 16.30.0 | CC0-1.0 | 快手 |
| `logos/bilibili.svg` | 同上 `icons/bilibili.svg` | 16.30.0 | CC0-1.0 | |
| `logos/xiaohongshu.svg` | 同上 `icons/xiaohongshu.svg` | 16.30.0 | CC0-1.0 | |
| `logos/sinaweibo.svg` | 同上 `icons/sinaweibo.svg` | 16.30.0 | CC0-1.0 | |
| `logos/zhihu.svg` | 同上 `icons/zhihu.svg` | 16.30.0 | CC0-1.0 | |
| `logos/wechat.svg` | 同上 `icons/wechat.svg` | 16.30.0 | CC0-1.0 | 用于公众号 |
| `logos/wechat-channels.svg` | https://cdn.jsdelivr.net/npm/remixicon@4.6.0/icons/Logos/wechat-channels-fill.svg | Remix Icon 4.6.0 | Apache-2.0（`licenses/remixicon-LICENSE.txt`） | simple-icons 没有视频号 |

品牌色取自 simple-icons 数据文件（`data/simple-icons.json`）：TikTok `#000000`、快手 `#FF4906`、bilibili `#00A1D6`、小红书 `#FF2442`、新浪微博 `#E6162D`、知乎 `#0084FF`、微信 `#07C160`；视频号用其标识橙 `#FA9D3B`，B站在看板里用其另一品牌色「哔哩粉」`#FB7299`，避免和知乎蓝撞色。

商标归各平台所有。这些标识只用于在看板里区分平台，不做任何仿冒平台的界面。

动效不用第三方库：v3 起改用浏览器原生 Web Animations API（GSAP 的许可不允许随开源仓库再分发，已移除）。

升级时：换新版本号下载、重新校验、改文件名和 `index.html` 里的引用，并更新本表。
