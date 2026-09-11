# 壁纸

程序启动时会扫描本目录以及**用户壁纸目录**，把找到的图片列进「设置 → 外观」。

支持格式：`.jpg` / `.jpeg` / `.png` / `.webp` / `.bmp`

## 目录里有什么

- `miku_meteor.jpg` —— **随程序分发的默认壁纸**（夜空流星），首次启动就会用它。
- 其它图片不随仓库分发：开发时用到的另外几张初音未来插画来自 pixiv，
  版权归各画师所有，没有一起提交。想用的话自己放进来即可。

## 放自己的图片

**推荐**：直接用程序里的「**设置 → 外观 → 添加图片…**」，程序会把图片复制到
用户壁纸目录并立刻应用；也可以点「打开壁纸文件夹」批量拖图进去。

用户壁纸目录（持久保存，重启 exe 不会丢）：

| 平台 | 路径 |
| --- | --- |
| Windows | `%APPDATA%\ComfyUI_TagSelect\wallpapers\` |
| Linux | `~/.config/ComfyUI_TagSelect/wallpapers/` |
| macOS | `~/Library/Application Support/ComfyUI_TagSelect/wallpapers/` |

> 便携模式（程序目录下有 `portable.txt`）时为 `<程序目录>\userdata\wallpapers\`。

## ⚠️ 关于本目录

**不要**把图片放进这里给**打包好的 exe** 用 —— 单文件 exe 的 `assets/` 是每次启动
都会重新解包的临时目录（PyInstaller 的 `sys._MEIPASS`），放进去下次启动就没了。

本目录只在两种情况有意义：

1. 源码运行时（`python app.py`）；
2. 自己重新打包 —— `ComfyUI_TagSelect.spec` 会把整个 `assets/` 打进去，
   这里的图片就成为 exe 的**内置壁纸**。

壁纸会自动铺满整个窗口：程序用 `KeepAspectRatioByExpanding` + 居中裁剪绘制，
任何窗口比例下都不会出现空白。

> 壁纸版权归原作者所有，随附的默认壁纸仅供个人学习自用，请勿商用。
