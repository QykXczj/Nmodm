# 贡献指南

[返回主页](../../README.md) | [English](../en/CONTRIBUTING.md)

感谢你考虑为 Nmodm 做出贡献！

## 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [提交规范](#提交规范)

---

## 行为准则

### 我们的承诺

为了营造开放和友好的环境，我们承诺：

- 使用友好和包容的语言
- 尊重不同的观点和经验
- 优雅地接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员表示同理心

### 不可接受的行为

- 使用性化的语言或图像
- 侮辱/贬损的评论，人身攻击
- 公开或私下的骚扰
- 未经许可发布他人的私人信息
- 其他不道德或不专业的行为

---

## 如何贡献

### 报告 Bug

**提交 Bug 前**:
1. 检查 [Issues](https://github.com/your-repo/Nmodm/issues) 确认未被报告
2. 确认使用的是最新版本
3. 收集相关信息

**Bug 报告应包含**:
- 清晰的标题和描述
- 复现步骤
- 预期行为和实际行为
- 截图（如适用）
- 环境信息：
  - 操作系统版本
  - Python 版本（如从源码运行）
  - Nmodm 版本

**示例**:
```markdown
**描述**
点击"启动游戏"后程序崩溃

**复现步骤**
1. 打开 Nmodm
2. 配置游戏路径
3. 点击"启动游戏"
4. 程序崩溃

**预期行为**
游戏应该正常启动

**环境**
- OS: Windows 11 64-bit
- Nmodm: v3.1.2
- Python: 3.11.0 (如适用)

**截图**
[附加截图]
```

### 功能建议

**提交建议前**:
1. 确认功能尚未存在
2. 检查是否有类似建议
3. 考虑功能的实用性

**功能建议应包含**:
- 清晰的功能描述
- 使用场景
- 可能的实现方案
- 替代方案

### 改进文档

文档改进包括：
- 修正错误或过时信息
- 添加缺失的说明
- 改进示例代码
- 翻译文档

---

## 开发流程

### 1. Fork 项目

点击 GitHub 页面右上角的 "Fork" 按钮

### 2. 克隆仓库

```bash
git clone https://github.com/your-username/Nmodm.git
cd Nmodm
```

### 3. 创建分支

```bash
# 功能分支
git checkout -b feature/amazing-feature

# 修复分支
git checkout -b fix/bug-description

# 文档分支
git checkout -b docs/improve-readme
```

### 4. 设置开发环境

```bash
# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 安装开发工具
pip install black flake8 mypy pytest
```

### 5. 进行开发

- 编写代码
- 添加测试
- 更新文档
- 遵循代码规范

### 6. 测试代码

```bash
# 运行测试
pytest tests/

# 代码格式化
black src/

# 代码检查
flake8 src/

# 类型检查
mypy src/
```

### 7. 提交更改

```bash
git add .
git commit -m "feat: add amazing feature"
```

### 8. 推送分支

```bash
git push origin feature/amazing-feature
```

### 9. 创建 Pull Request

1. 访问你的 Fork 页面
2. 点击 "New Pull Request"
3. 填写 PR 描述
4. 提交 PR

---

## 代码规范

### Python 风格

遵循 [PEP 8](https://pep8.org/) 规范：

```python
# 好的示例
def calculate_total_price(items: list, tax_rate: float) -> float:
    """计算总价（含税）
    
    Args:
        items: 商品列表
        tax_rate: 税率
        
    Returns:
        总价
    """
    subtotal = sum(item.price for item in items)
    return subtotal * (1 + tax_rate)


# 不好的示例
def calc(i,t):
    s=sum(x.p for x in i)
    return s*(1+t)
```

### 命名规范

```python
# 类名：PascalCase
class ConfigManager:
    pass

# 函数名：snake_case
def get_game_path():
    pass

# 常量：UPPER_CASE
MAX_RETRY_COUNT = 3

# 私有方法：前缀下划线
def _internal_method():
    pass
```

### 文档字符串

```python
def download_file(url: str, save_path: str, timeout: int = 30) -> bool:
    """下载文件到指定路径
    
    Args:
        url: 文件下载链接
        save_path: 保存路径
        timeout: 超时时间（秒），默认 30
        
    Returns:
        下载是否成功
        
    Raises:
        ValueError: URL 格式无效
        IOError: 文件写入失败
        
    Example:
        >>> download_file("https://example.com/file.zip", "file.zip")
        True
    """
    pass
```

### 类型注解

```python
from typing import List, Dict, Optional

def process_mods(
    mod_list: List[str],
    config: Dict[str, any],
    output_path: Optional[str] = None
) -> bool:
    pass
```

---

## 提交规范

### Conventional Commits

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型（Type）

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具相关

### 范围（Scope）

可选，表示影响的模块：

- `mod`: Mod 管理
- `config`: 配置管理
- `ui`: 用户界面
- `network`: 网络功能
- `build`: 构建系统

### 主题（Subject）

- 使用祈使句
- 不要大写首字母
- 不要句号结尾
- 限制在 50 字符内

### 正文（Body）

- 详细说明改动
- 说明改动原因
- 与之前行为的对比

### 页脚（Footer）

- 关联 Issue: `Closes #123`
- 破坏性变更: `BREAKING CHANGE: ...`

### 示例

```
feat(mod): 添加 Mod 自动更新功能

实现了以下功能：
- 检测 Mod 新版本
- 自动下载更新
- 备份旧版本

Closes #123
```

```
fix(ui): 修复窗口最小化后无法恢复的问题

在 Windows 11 上，点击任务栏图标无法恢复窗口。
通过处理 WM_SYSCOMMAND 消息解决。

Fixes #456
```

---

## Pull Request 指南

### PR 标题

使用与提交信息相同的格式：

```
feat(mod): 添加 Mod 自动更新功能
```

### PR 描述

包含以下内容：

```markdown
## 改动说明
简要描述这个 PR 做了什么

## 改动类型
- [ ] Bug 修复
- [x] 新功能
- [ ] 文档更新
- [ ] 代码重构

## 测试
描述如何测试这些改动

## 截图
如果有 UI 改动，添加截图

## 相关 Issue
Closes #123
```

### PR 检查清单

提交前确认：

- [ ] 代码遵循项目规范
- [ ] 已添加必要的测试
- [ ] 所有测试通过
- [ ] 已更新相关文档
- [ ] 提交信息符合规范
- [ ] 已自我审查代码

---

## 代码审查

### 审查者职责

- 检查代码质量
- 验证功能正确性
- 提供建设性反馈
- 及时响应

### 被审查者职责

- 响应审查意见
- 进行必要修改
- 保持礼貌和专业

---

## 获取帮助

如有疑问：

- 📖 查看 [开发者指南](DEVELOPER_GUIDE.md)
- 💬 在 [Discussions](https://github.com/your-repo/Nmodm/discussions) 提问
- 📧 联系维护者

---

## 许可证

贡献的代码将采用与项目相同的 [MIT 许可证](../../LICENSE)。

---

**感谢你的贡献！** 🎉

**最后更新**: 2025-01-20
