# FloatingNote（悬浮笔记）

Windows 桌面悬浮笔记工具：置顶显示、块状笔记、一键复制、托盘常驻、开机自启，可打包成免 Python 依赖的便携程序。

仓库地址：<https://github.com/mumu0215/FloatingNote>

## 功能

- **无边框悬浮窗**：无系统标题栏，无最小化 / 最大化 / 关闭按钮
- **置顶半透明**：可切换钉选置顶
- **笔记块展示**：列表卡片显示，过长自动截断预览
- **左键复制**：点击笔记块，完整内容写入剪贴板
- **右键菜单**：编辑 / 复制 / 删除
- **底部输入 + 保存**：主窗口底部常驻输入框与「保存」按钮
- **可调大小**：拖边缘或右下角缩放，尺寸与位置自动记住
- **托盘常驻**：隐藏到托盘后台运行；托盘菜单退出
- **开机自启**：写入当前用户注册表 `Run` 项（可在托盘开关）
- **单实例**：通过 `floating_note.pid` 避免重复启动

## 环境要求

- Windows 10 / 11
- 源码运行：Python 3.10+
- 打包：需本机已装 Python，以及可用的 C 编译器（Nuitka 使用，如 Visual Studio Build Tools）

## 快速开始（源码）

```bat
dev.bat
```

后台启动 / 停止：

```bat
start.bat
stop.bat
```

依赖见 `requirements.txt`（`pystray`、`Pillow`）。首次运行脚本会自动创建 `.venv` 并安装。

## 便携包（免 Python）

```bat
build_exe.bat
```

生成目录：

```text
release/FloatingNote/
  FloatingNote.exe    # 双击运行
  *.dll / tcl / tk / ...
  data/               # 笔记与配置
```

将整个 `release/FloatingNote` 文件夹复制到任意位置即可使用，目标机无需安装 Python。

> 说明：当前为 **standalone 文件夹分发**（exe + 运行库），不是单一 exe。整夹拷贝即可。

## 使用说明

| 操作 | 方式 |
|------|------|
| 写笔记并保存 | 底部输入框输入 → 点「保存」（或 `Ctrl+S` / `Ctrl+Enter`） |
| 复制笔记 | 左键点击笔记块 |
| 编辑 / 删除 | 右键笔记块 |
| 移动窗口 | 拖动顶部细条 `······` |
| 调整大小 | 拖窗口边缘，或右下角 `◢` |
| 置顶开关 | 顶部「钉」 |
| 隐藏到托盘 | 顶部「–」 |
| 再次显示 | 托盘图标 → 显示窗口 |
| 退出 | 托盘 → 退出 |
| 开机自启 | 托盘 → 开启 / 关闭开机自启 |

## 数据文件

运行时在程序根目录（源码为项目根；便携包为 `FloatingNote.exe` 同级）生成：

| 路径 | 说明 |
|------|------|
| `data/notes.json` | 笔记内容 |
| `data/config.json` | 窗口大小、位置、透明度、自启等 |
| `floating_note.pid` | 当前进程 PID（供 `stop.bat` 使用） |

仓库内提供空的默认 `data/` 模板；本地使用后的内容不会强制覆盖。

## 项目结构

```text
FloatingNote/
  app_entry.py          # 打包入口
  build_exe.bat         # Nuitka 便携包构建
  dev.bat / start.bat / stop.bat
  dev.sh / start.sh / stop.sh
  requirements.txt
  src/
    main.py             # 主界面、托盘、交互
    storage.py          # JSON 读写
    autostart.py        # Windows 开机自启
    paths.py            # 源码 / 打包路径解析
  data/
    notes.json          # 默认空笔记
    config.json         # 默认配置
```

## 开发说明

- UI：`tkinter`（无边框 `overrideredirect`）
- 托盘：`pystray` + `Pillow`
- 打包：`Nuitka` standalone（见 `build_exe.bat`）
- 自启：`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`，项名 `FloatingNote`

## License

MIT
