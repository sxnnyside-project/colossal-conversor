# Colossal Conversor — 用户指南

<p align="center">
  <em>安装、使用和排查 Colossal Conversor 日常问题所需的一切信息。</em>
</p>

<p align="center">
  <sub>语言: <a href="../en/README.md">English</a> · <a href="../es/README.md">Español</a> · <a href="../fr/README.md">Français</a> · <a href="../ja/README.md">日本語</a> · <a href="../pt/README.md">Português</a> · <a href="../zh/README.md">中文</a></sub>
</p>

---

## 1. Colossal Conversor 是什么？

Colossal Conversor 是一款离线桌面应用程序，用于在音频、视频、图片、文档、
电子表格和演示文稿格式之间进行转换。所有处理都通过 C++20 原生执行内核在
本地完成——转换本身不需要上传云端、不需要账户，也不依赖网络连接。完整的
技术概览请参阅主 [README](../../../README.md)。

本指南介绍应用程序的实际日常使用方法：安装、首次转换、批量处理与流水线
（pipeline），以及出现问题时的恢复方法。

## 2. 支持的平台

Colossal Conversor 面向 **macOS、Linux 和 Windows**。原生进程监督层为每
个平台都配备了专用后端，因此进程创建、输出捕获、取消操作和清理工作在各
平台上的行为都是一致的。

| 平台 | 状态 |
|---|---|
| macOS | 已验证——已构建、已测试，并用于日常开发 |
| Linux | 已实现（与 macOS 共用同一后端）；尚未在 Linux 运行环境中实际验证 |
| Windows | 已按照 Windows 进程 API 实现；尚未在 Windows 运行环境中实际验证 |

"已实现但尚未验证"意味着代码已经存在，并遵循正确的平台契约编写，但目前
还没有人确认该平台上的实际转换能够成功。随着验证的推进，此状态会持续更
新——当前状态请参阅主 README 的"平台支持"一节；如果你愿意协助验证 Linux
或 Windows，请参阅 [CONTRIBUTING.md](../../../CONTRIBUTING.md)。

## 3. 安装

安装 Colossal Conversor 本身与安装部分转换所需的外部工具是两件不同的事
（见下方"外部依赖"一节）。

### macOS / Linux

```bash
git clone https://github.com/sxnnyside-project/colossal-conservor.git
cd colossal-conservor
just install
just dev
```

### Windows

```powershell
git clone https://github.com/sxnnyside-project/colossal-conservor.git
cd colossal-conservor
just install
just dev
```

`just install` 会同步 Python 依赖并编译原生扩展。`just dev` 用于启动应
用程序。如果你尚未安装 `just`，请参阅其
[安装说明](https://github.com/casey/just#installation)，或者直接执行主
README 中描述的 `uv sync --all-groups` 及原生 CMake 构建步骤。

## 4. 外部依赖

部分转换类别会调用外部工具；其余则完全在进程内运行，无需任何额外工具。

| 工具 | 用途 |
|---|---|
| FFmpeg | 音频和视频转换 |
| LibreOffice | 文档、电子表格和演示文稿转换 |
| Poppler（`pdftoppm`） | 文档转图片的分页渲染 |
| Pandoc | Markdown ↔ 文档格式转换 |
| ImageMagick | BMP/PPM/TGA 以外的图片转换（这三种格式为原生处理，无需外部工具） |

查看当前已具备的工具：

```bash
just verify-tools
```

安装缺失的工具：

- **macOS**：`bash tools/macos_install_deps.sh`（Homebrew）
- **Linux**：`bash tools/linux_install_deps.sh`（自动检测 apt、dnf 或 pacman）
- **Windows**：在 PowerShell 中运行 `tools/windows_install_deps.ps1`（winget，若已安装则使用 Chocolatey）

安装这些工具本身**并不能**保证所有转换都能成功——它只是让相应的引擎变得
可用。应用程序会在运行时检测每个工具，只提供它实际能够执行的转换。

## 5. 首次转换

1. 启动应用程序（`just dev`）。
2. 点击 **Select File(s)**，或将文件拖入接收区域。
3. Colossal Conversor 会检测输入格式，并按类别仅显示它实际能够生成的目
   标格式。
4. 点击目标格式。
5. 如需使用默认目的地以外的位置，点击 **Save As...** 选择（或确认）目
   的地。
6. 点击 **Convert**（或按 <kbd>Enter</kbd> 键）。

完成后，会弹出一个对话框告知生成了多少个文件，并提供打开结果或在文件管
理器中显示的按钮。

## 6. 多文件处理

点击 **Select File(s)** 选择多个文件，或一次拖入多个文件。Colossal
Conversor 只会显示所有选中输入共同支持的输出格式。通过 **Save As...**
选择一个目标**文件夹**（而非单个文件），然后点击 **Convert**——每个输入
都会在该文件夹中生成各自的输出。

## 7. 多输出转换

某些转换会从单个输入生成多个文件——例如将 PDF 的每一页渲染为单独的图
片。这会根据你选择的格式组合自动识别；你选择的目的地会成为一个文件夹，
其中包含所有生成的页面，完成对话框会显示实际生成的文件数量。

## 8. 流水线（Pipeline）

有些转换无法一步完成，会在内部自动拆分为多个阶段——例如，将演示文稿转
换为图片时，会先经过一个中间的 PDF 阶段。你无需为此进行任何配置：像往
常一样选择输入和目标格式即可，进度条会显示当前正在执行的阶段。流水线完
成（或失败、被取消）后，中间文件会被自动清理。

## 9. 选择输出格式

格式网格中显示的目标格式，永远只是 Colossal Conversor 能够从当前输入实
际生成的格式——它不会展示自己无法执行的转换。选择某个格式后，会出现一
条保真度提示（例如 "high"、"medium"、"layout"），说明输出对原始内容的
保留程度——这在不同能力的格式之间转换时很有用（例如将带样式的文档转换
为纯文本）。

## 10. 选择目的地

**Save As...** 用于选择输出的保存位置。对于单输出转换，选择一个文件路
径；对于批量转换或多输出转换，则选择一个文件夹。如果你没有明确选择，应
用程序会在输入文件旁边提出一个合理的默认位置。

## 11. 取消操作

在转换进行过程中点击 **Cancel** 即可停止转换。这会真正终止底层进程（而
不仅仅是改变界面状态）——不会将任何部分输出报告为成功结果，状态栏会显
示 "Conversion cancelled"，与成功和失败状态均不相同。取消后可以立即开
始新的转换。

## 12. 错误与恢复

如果转换失败，会弹出对话框以简明的语言说明发生了什么，并提供 **Show
Details...** 按钮以查看底层技术输出（仅在你主动查看时才会显示）。应用
程序不会因转换失败而崩溃或卡死——关闭对话框，根据需要调整输入、目标格
式或目的地后重试即可。

## 13. 缺少依赖

如果某个转换需要一个未安装的工具，错误消息会明确说明这一点并指出具体工
具名称——不会与普通错误混淆。运行 `just verify-tools` 查看完整情况，安
装缺失工具的方法请参见上方"外部依赖"一节。

## 14. 支持的格式

应用程序内的格式网格是权威的实时列表——它由转换引擎实际使用的同一个目
录（catalog）生成，因此永远不会宣传当前版本实际无法完成的转换。总体而
言，Colossal Conversor 支持：

- **音频**：MP3、WAV、FLAC、AAC、OGG 等常见格式。
- **视频**：MP4、MKV、MOV、AVI、WebM 等常见格式。
- **图片**：PNG、JPEG、WebP、BMP、TIFF、GIF 等常见格式。
- **文档**：DOC/DOCX、ODT、RTF、TXT、PDF、Markdown、HTML、EPUB。
- **电子表格**：XLS/XLSX、ODS、CSV、TSV。
- **演示文稿**：PPTX/PPT、ODP。

在应用程序中选择一个输入文件，即可查看该文件对应的准确、实时的目标格式
列表。

## 15. 故障排查

**我以为可以用的转换没有出现。** 目标格式列表是根据你所选输入的检测格式
生成的——请检查输入是否被正确检测（显示在文件名旁边），以及该格式组合
是否确实受支持。

**"缺少依赖"错误。** 运行 `just verify-tools`，然后安装提示中指出的工具
（参见上方"外部依赖 / 缺少依赖"）。

**转换立即失败。** 请查看错误对话框中的 **Show Details...**。常见原因
包括：输入文件损坏或无法读取，或检测到的输入实际上并不符合该格式（例如
扩展名被错误重命名的文件）。

**点击 Cancel 后界面看起来没有反应。** 对于耗时很短的转换，操作可能在
Cancel 生效之前就已经完成——这是预期行为，并非缺陷；最终结果会是正常的
成功或失败，而不是界面卡死。

**目的地路径无效。** 请确认文件夹存在且你拥有写入权限；对于单文件输出，
请确认其上级文件夹存在。

**仍然无法解决？** 请提交 issue——参见 [SUPPORT.md](../../../SUPPORT.md)。

---

<p align="center">
  <sub><a href="../../../README.md">Colossal Conversor</a> 文档的一部分 — A Sxnnyside Project Release</sub>
</p>
