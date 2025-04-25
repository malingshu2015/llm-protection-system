# 使用 PyInstaller 构建本地大模型防护系统

本文档提供了使用 PyInstaller 构建本地大模型防护系统可执行文件的详细指南。

## 前提条件

在开始构建之前，请确保您的系统满足以下要求：

1. Python 3.9 或更高版本
2. pip 包管理器
3. 虚拟环境工具（推荐使用 venv 或 conda）
4. Git（用于克隆代码库）

## 构建步骤

### 1. 准备环境

首先，克隆代码库并创建虚拟环境：

```bash
# 克隆代码库
git clone https://github.com/yourusername/LLM-firewall.git
cd LLM-firewall

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 2. 安装依赖项

安装项目依赖项和 PyInstaller：

```bash
pip install -r requirements.txt
pip install pyinstaller
```

### 3. 使用构建脚本

我们提供了一个自动化构建脚本，可以在不同平台上构建可执行文件：

```bash
python build.py
```

这个脚本会自动执行以下操作：
- 清理之前的构建文件
- 安装必要的依赖项
- 使用 PyInstaller 构建可执行文件
- 创建分发包

### 4. 手动构建（可选）

如果您想手动控制构建过程，可以直接使用 PyInstaller：

```bash
# 使用 spec 文件构建
pyinstaller pyinstaller.spec --clean
```

## 构建输出

构建完成后，您将在以下位置找到构建结果：

- **可执行文件**：`dist/llm-protection-system/`（Windows/Linux）或 `dist/本地大模型防护系统.app`（macOS）
- **分发包**：项目根目录下的 `llm-protection-system-{版本号}-{平台}-{架构}-{时间戳}.zip`（Windows）或 `.tar.gz`（macOS/Linux）

## 平台特定说明

### Windows

在 Windows 上，构建过程会创建一个包含可执行文件和所有依赖项的目录。您可以通过双击 `llm-protection-system.exe` 启动应用程序。

### macOS

在 macOS 上，构建过程会创建一个 `.app` 包。您可以通过双击 `本地大模型防护系统.app` 启动应用程序，或者将其拖到 Applications 文件夹中安装。

注意：如果您收到"未识别的开发者"警告，请在 Finder 中右键点击应用程序，选择"打开"，然后在弹出的对话框中再次点击"打开"。

### Linux

在 Linux 上，构建过程会创建一个包含可执行文件和所有依赖项的目录。您可以通过运行 `./llm-protection-system` 启动应用程序。

## 故障排除

### 常见问题

1. **缺少模块错误**：如果构建过程报告缺少某些模块，请将它们添加到 `pyinstaller.spec` 文件的 `hiddenimports` 列表中。

2. **文件未包含在构建中**：如果某些文件（如配置文件或静态资源）未包含在构建中，请将它们添加到 `pyinstaller.spec` 文件的 `datas` 列表中。

3. **动态库加载错误**：如果应用程序在运行时报告无法加载某些动态库，请确保这些库已包含在构建中，或者在目标系统上安装这些库。

### 调试构建

如果您需要调试构建过程，可以使用以下选项：

```bash
# 生成详细的构建日志
pyinstaller pyinstaller.spec --clean --log-level DEBUG
```

## 自定义构建

如果您需要自定义构建过程，可以修改 `pyinstaller.spec` 文件。该文件包含了构建配置，如包含的文件、隐藏导入、图标等。

## 更多资源

- [PyInstaller 官方文档](https://pyinstaller.org/en/stable/)
- [PyInstaller GitHub 仓库](https://github.com/pyinstaller/pyinstaller)
