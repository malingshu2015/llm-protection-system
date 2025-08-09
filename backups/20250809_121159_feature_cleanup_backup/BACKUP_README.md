# LLM防护系统备份说明

## 备份信息
- **备份时间**: 2025年8月9日 12:11:59
- **备份类型**: 功能清理前完整备份
- **备份目的**: 在进行重复功能清理和代码优化前保存当前状态

## 备份内容

### 核心目录
- `src/` - 所有源代码文件
- `static/` - 前端页面和静态资源
- `rules/` - 安全规则配置文件
- `docs/` - 项目文档
- `tests/` - 测试文件
- `tools/` - 工具和脚本
- `scripts/` - 构建和发布脚本
- `examples/` - 示例配置

### 配置文件
- `requirements.txt` - Python依赖
- `pyproject.toml` - 项目配置
- `docker-compose.yml` - Docker配置
- `Dockerfile` - Docker镜像配置
- `setup.py` - 安装配置
- `VERSION` - 版本文件
- `CHANGELOG.md` - 更新日志
- `README.md` - 项目说明
- `LICENSE` - 许可证文件

## 发现的重复功能

### HTML页面重复
1. **模型管理**: `models.html` vs `models_v2.html`
2. **事件管理**: `events_old.html` vs `events.html` vs `events_v2.html`
3. **监控中心**: `monitor.html` vs `monitor_v2.html`
4. **规则管理**: `rules.html` vs `rules_v2.html`

### API功能重复
1. **模型API**: `api.py` vs `enhanced_models_api.py`
2. **健康检查**: 多个模块中重复实现
3. **Ollama代理**: `api.py` vs `ollama_proxy_api.py`

### CSS样式重复
1. **Apple风格**: 14个相关CSS文件
2. **重复变量**: 每个页面都重新定义相同的CSS变量
3. **未使用样式**: 多个标记为"不使用"的CSS引用

### JavaScript功能重复
1. **UI组件**: 相同的侧边栏和图表逻辑
2. **API调用**: 重复的封装和错误处理
3. **配置管理**: 多套模型和规则配置逻辑

## 计划的清理工作

### 短期优化
- [ ] 删除备份文件(.bak)和旧版本页面(_old)
- [ ] 统一页面版本到v2
- [ ] 整合重复的CSS文件

### 中期重构
- [ ] 合并重复的API端点
- [ ] 组件化重复的UI元素
- [ ] 统一配置管理界面

### 长期架构
- [ ] 前后端分离重构
- [ ] 微服务架构拆分
- [ ] 自动化构建流程

## 恢复说明

如果需要恢复备份，请按以下步骤操作：

1. 停止当前运行的服务
2. 备份当前状态（可选）
3. 将此备份目录下的文件复制回项目根目录
4. 重新安装依赖：`pip install -r requirements.txt`
5. 重启服务

## 注意事项

- 此备份不包含虚拟环境目录
- 不包含数据目录中的运行时数据
- 不包含生成的构建文件
- Git历史信息需要单独备份

---
**备份创建者**: AI助手  
**联系方式**: 通过项目维护者  
**备份有效期**: 建议保留至功能清理完成并验证稳定后