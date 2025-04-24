# 贡献指南

感谢您对本地大模型防护系统的关注！我们非常欢迎社区贡献，无论是代码贡献、问题报告还是功能建议。本文档将指导您如何参与项目开发。

## 行为准则

请保持尊重和专业，为所有参与者创造一个积极、包容的环境。

## 如何贡献

### 报告问题

如果您发现了bug或有功能建议，请通过GitHub Issues提交：

1. 在提交前，请先搜索现有issues，避免重复
2. 使用清晰的标题和详细描述
3. 对于bug报告，请包含：
   - 问题的详细描述
   - 复现步骤
   - 预期行为与实际行为
   - 系统环境（操作系统、Python版本等）
   - 相关日志或截图

### 提交代码

1. Fork项目仓库
2. 创建您的特性分支：`git checkout -b feature/amazing-feature`
3. 提交您的更改：`git commit -m 'Add some amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 提交Pull Request

### 代码风格

- 遵循PEP 8编码规范
- 使用类型注解
- 编写文档字符串
- 添加适当的测试

### 开发流程

1. 安装开发依赖：
   ```bash
   pip install -r requirements-dev.txt
   ```

2. 在本地运行测试：
   ```bash
   pytest
   ```

3. 格式化代码：
   ```bash
   black .
   isort .
   ```

4. 运行代码检查：
   ```bash
   flake8
   mypy .
   ```

## Pull Request流程

1. 确保PR描述清晰地说明了更改内容和原因
2. 确保所有自动化测试通过
3. 如果添加了新功能，请添加相应的测试
4. 如果修复了bug，请添加回归测试
5. 更新相关文档

## 版本发布流程

我们使用[语义化版本](https://semver.org/lang/zh-CN/)进行版本管理：

- 主版本号：不兼容的API变更
- 次版本号：向下兼容的功能性新增
- 修订号：向下兼容的问题修正

## 文档贡献

文档改进同样重要！您可以：

- 修复文档中的错误
- 添加缺失的信息
- 改进现有文档的清晰度
- 添加更多示例或教程

## 联系方式

如有任何问题，请通过以下方式联系我们：

- GitHub Issues
- 电子邮件：[your.email@example.com]

感谢您的贡献！
