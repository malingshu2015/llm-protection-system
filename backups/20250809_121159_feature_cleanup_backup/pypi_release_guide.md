# PyPI发布指南

本文档提供了将本地大模型防护系统发布到PyPI的详细步骤。

## 前提条件

1. 已安装Python和pip
2. 已安装twine和build工具：`pip install twine build`
3. 拥有PyPI账号
4. 已配置PyPI API令牌

## 发布步骤

### 1. 准备发布环境

创建并激活一个干净的虚拟环境：

```bash
python -m venv pypi_release_env
source pypi_release_env/bin/activate  # Linux/macOS
# 或
pypi_release_env\Scripts\activate  # Windows
```

安装必要的工具：

```bash
pip install --upgrade pip
pip install --upgrade twine build
```

### 2. 更新版本号

确保`VERSION`文件中的版本号正确：

```bash
echo "1.0.0" > VERSION
```

### 3. 构建分发包

在项目根目录下运行：

```bash
python -m build
```

这将在`dist/`目录下创建源码分发包(`.tar.gz`)和wheel分发包(`.whl`)。

### 4. 检查分发包

使用twine检查分发包是否符合PyPI的要求：

```bash
twine check dist/*
```

### 5. 上传到TestPyPI（可选但推荐）

先上传到TestPyPI进行测试：

```bash
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

然后测试安装：

```bash
pip install --index-url https://test.pypi.org/simple/ llm-protection-system
```

### 6. 上传到PyPI

确认一切正常后，上传到正式的PyPI：

```bash
twine upload dist/*
```

### 7. 验证发布

验证包是否已成功发布并可安装：

```bash
pip install llm-protection-system
```

## 自动化发布脚本

为了简化发布过程，我们提供了一个自动化发布脚本：

```bash
./scripts/publish_to_pypi.sh
```

该脚本会自动执行上述所有步骤，包括版本检查、构建和上传。

## 发布后检查清单

- [ ] 确认包可以通过pip安装
- [ ] 确认包的版本号正确
- [ ] 确认包的元数据（描述、作者、许可证等）正确
- [ ] 确认包的依赖项正确
- [ ] 确认包的文档链接有效
- [ ] 确认PyPI页面上的README正确显示

## 故障排除

### 常见问题

1. **上传失败**：确保您的PyPI凭据正确，并且包名称未被占用。
2. **构建错误**：检查`setup.py`和`MANIFEST.in`文件是否正确配置。
3. **安装错误**：检查依赖项是否正确声明。

### 有用的命令

- 查看包信息：`pip show llm-protection-system`
- 卸载包：`pip uninstall llm-protection-system`
- 查看PyPI上的包历史：访问`https://pypi.org/project/llm-protection-system/#history`

## 参考资源

- [PyPI官方文档](https://packaging.python.org/tutorials/packaging-projects/)
- [Twine文档](https://twine.readthedocs.io/en/latest/)
- [TestPyPI](https://test.pypi.org/)
