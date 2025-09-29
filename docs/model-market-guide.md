# 模型市场使用指南

## 概述

模型市场是一个Hugging Face风格的模型发现和管理平台，集成到LLM防护系统中。它允许用户浏览、搜索、下载和评价各种AI模型。

## 功能特性

### 1. 模型浏览
- **分类筛选**: 按框架(PyTorch、TensorFlow、ONNX)、领域(NLP、CV、Audio等)筛选
- **搜索功能**: 支持按名称、描述、标签搜索模型
- **排序选项**: 按下载量、评分、发布日期、名称排序

### 2. 模型详情
- **基本信息**: 模型名称、描述、作者、许可证、大小等
- **版本信息**: 支持多版本管理，包含下载链接和发布说明
- **性能指标**: 各基准测试的详细性能数据
- **社区评价**: 用户评分和评论系统

### 3. 交互功能
- **点赞系统**: 用户可以给喜欢的模型点赞
- **下载统计**: 自动记录模型下载次数
- **评价系统**: 用户可以对模型进行评分和评论

### 4. 统计信息
- **市场概况**: 总模型数、总下载量、总点赞数
- **分类统计**: 按框架和领域的分布统计
- **热门模型**: 下载量和点赞数排行榜

## 访问方式

### Web界面访问
1. 打开主界面: `http://localhost:8081/static/index.html`
2. 在侧边栏点击"模型市场"菜单
3. 或者直接访问: `http://localhost:8081/model-market`

### API访问
所有功能都提供RESTful API接口:

```bash
# 获取模型列表
GET /api/v1/models

# 获取模型详情
GET /api/v1/models/{model_id}

# 下载模型
POST /api/v1/models/{model_id}/download

# 点赞模型
POST /api/v1/models/{model_id}/like

# 添加评价
POST /api/v1/models/{model_id}/review?rating=5&comment=很好用

# 获取统计信息
GET /api/v1/models/stats/summary

# 搜索建议
GET /api/v1/models/search/suggestions?q=llama
```

## 当前支持的模型

系统预置了3个示例模型:

### 1. Llama 3 8B
- **类型**: 大语言模型
- **框架**: PyTorch
- **领域**: 自然语言处理
- **特点**: 多语言支持、代码生成能力

### 2. Stable Diffusion XL
- **类型**: 文本到图像生成
- **框架**: PyTorch
- **领域**: 计算机视觉
- **特点**: 高质量图像生成

### 3. Whisper Large v3
- **类型**: 语音识别
- **框架**: PyTorch
- **领域**: 音频处理
- **特点**: 支持99种语言

## 技术实现

### 后端架构
- **框架**: FastAPI
- **数据结构**: Pydantic模型验证
- **存储**: 内存数据库(可扩展为持久化存储)
- **API风格**: RESTful

### 前端界面
- **技术栈**: HTML5 + CSS3 + JavaScript
- **样式**: Apple设计风格
- **功能**: 响应式设计、实时搜索、分页加载

### 集成方式
- **路由注册**: 自动集成到主应用路由系统
- **静态文件**: 通过FastAPI静态文件服务提供
- **CORS支持**: 支持跨域访问

## 扩展开发

### 添加新模型
在 `src/web/model_market_api.py` 中的 `init_sample_data()` 函数添加新模型数据:

```python
{
    "metadata": {
        "id": "your-model-id",
        "name": "Your Model Name",
        "description": "模型描述",
        "author": "作者/机构",
        "license": "许可证",
        "framework": "pytorch",
        "domain": "nlp",
        "tags": ["tag1", "tag2"],
        "downloads": 0,
        "likes": 0,
        "created_at": "2024-01-01",
        "updated_at": "2024-01-01",
        "size": "1.0GB",
        "language": "en",
        "hardware_requirements": "硬件要求"
    },
    "versions": [
        {
            "version": "1.0.0",
            "download_url": "/api/v1/models/your-model-id/download",
            "checksum": "sha256:...",
            "release_notes": "发布说明",
            "created_at": "2024-01-01"
        }
    ],
    "performance_metrics": {
        "metric1": 95.0,
        "metric2": 88.5
    },
    "community_rating": 0.0
}
```

### 自定义界面
修改 `static/model-market.html` 文件来自定义前端界面:

- 修改CSS样式
- 添加新的交互功能
- 调整页面布局

## 故障排除

### 常见问题
1. **页面无法访问**: 检查服务器是否运行在8081端口
2. **API返回404**: 确认模型ID是否正确
3. **静态资源加载失败**: 检查静态文件目录权限

### 日志查看
查看应用日志获取详细错误信息:
```bash
tail -f logs/app.log
```

## 未来规划

- [ ] 持久化存储支持
- [ ] 用户认证系统
- [ ] 模型上传功能
- [ ] 实时通知系统
- [ ] 多语言支持
- [ ] 移动端适配

## 联系方式

如有问题或建议，请联系系统管理员或查看项目文档。