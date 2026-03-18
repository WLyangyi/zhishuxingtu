"""
测试数据初始化脚本
用于测试双向链接功能：
- 创建多条相互链接的笔记
- 包含正常链接和断链测试数据
"""
import sys
import os
import json
import re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.models.note import Note
from app.models.folder import Folder
from app.models.tag import Tag
from app.core.security import get_password_hash

LINK_PATTERN = re.compile(r'\[\[([^\]]+)\]\]')

def parse_links(content: str) -> list:
    if not content:
        return []
    matches = LINK_PATTERN.findall(content)
    return [title.strip() for title in matches]

def resolve_links(db: Session, content: str) -> list:
    try:
        titles = parse_links(content)
        linked_ids = []
        for title in titles:
            note = db.query(Note).filter(Note.title == title).first()
            if note:
                linked_ids.append(note.id)
        return linked_ids
    except Exception as e:
        print(f"Error resolving links: {e}")
        return []

def init_test_data(force: bool = False):
    db: Session = SessionLocal()
    
    try:
        user = db.query(User).first()
        if not user:
            user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123")
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"创建测试用户: {user.username}")
        
        existing_notes = db.query(Note).filter(Note.user_id == user.id).count()
        if existing_notes > 0 and not force:
            print(f"用户已有 {existing_notes} 条笔记，跳过测试数据创建")
            print("如需强制创建，请运行: python init_test_data.py --force")
            return
        
        if force and existing_notes > 0:
            print(f"强制模式：将创建测试笔记（现有 {existing_notes} 条笔记保留）")
        
        test_notes = [
            {
                "title": "Vue3学习笔记",
                "content": """# Vue3 学习笔记

## 基础概念

Vue3 是一个渐进式 JavaScript 框架，主要特点包括：

- Composition API
- 更好的 TypeScript 支持
- 更小的打包体积

## 相关笔记

- [[React对比分析]] - Vue与React的对比
- [[前端框架选型]] - 如何选择前端框架

## 进阶内容

参见 [[Vue3进阶技巧]] 了解更多高级用法。
"""
            },
            {
                "title": "React对比分析",
                "content": """# React 对比分析

## Vue vs React

这篇文章对比 Vue3 和 React 的异同。

### 相似点
- 组件化开发
- 虚拟DOM
- 响应式更新

### 差异点
- 模板语法 vs JSX
- Options API vs Hooks
- 响应式实现原理

## 相关阅读

- [[Vue3学习笔记]] - Vue3基础教程
- [[前端框架选型]] - 选型指南
- [[TypeScript最佳实践]] - TS使用技巧
"""
            },
            {
                "title": "前端框架选型",
                "content": """# 前端框架选型指南

## 主流框架对比

| 框架 | 优势 | 劣势 |
|------|------|------|
| Vue3 | 易上手、文档友好 | 生态相对较小 |
| React | 生态丰富、社区活跃 | 学习曲线陡峭 |
| Angular | 企业级方案完整 | 过于臃肿 |

## 选型建议

- 小型项目：[[Vue3学习笔记]]
- 中大型项目：React 或 Vue3
- 企业级应用：Angular

## 参考资料

- [[Vue3学习笔记]]
- [[React对比分析]]
"""
            },
            {
                "title": "Vue3进阶技巧",
                "content": """# Vue3 进阶技巧

## 自定义 Hooks

```typescript
function useCounter() {
  const count = ref(0)
  const increment = () => count.value++
  return { count, increment }
}
```

## 性能优化

1. 使用 `shallowRef` 减少响应式开销
2. 合理使用 `computed` 和 `watch`
3. 虚拟列表处理大数据

## 前置知识

需要先阅读 [[Vue3学习笔记]] 掌握基础概念。

## 断链测试

这里链接到一个不存在的笔记：[[不存在的笔记标题]]
这个也是断链：[[已删除的笔记]]
"""
            },
            {
                "title": "TypeScript最佳实践",
                "content": """# TypeScript 最佳实践

## 类型定义

```typescript
interface User {
  id: string
  name: string
  email: string
}
```

## 泛型使用

```typescript
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key]
}
```

## 相关笔记

- [[前端框架选型]] - 框架选型时考虑TS支持
- [[Vue3学习笔记]] - Vue3的TS支持很好

## 断链测试

链接到 [[这个笔记不存在]] 用于测试断链显示。
"""
            },
            {
                "title": "测试笔记-断链集合",
                "content": """# 断链测试集合

这篇笔记专门用于测试断链显示效果。

## 各种断链情况

1. 普通断链：[[不存在的笔记A]]
2. 带空格的断链：[[这是一个 不存在的笔记]]
3. 特殊字符断链：[[笔记@#$%]]
4. 英文断链：[[Non Existent Note]]

## 正常链接

- [[Vue3学习笔记]] - 这个链接是正常的
- [[前端框架选型]] - 这个也是正常的

## 混合测试

这段文字中有正常链接 [[Vue3学习笔记]] 和断链 [[不存在的笔记B]] 混合出现。
"""
            }
        ]
        
        for note_data in test_notes:
            note = Note(
                title=note_data["title"],
                content=note_data["content"],
                user_id=user.id
            )
            db.add(note)
        
        db.commit()
        
        for note_data in test_notes:
            note = db.query(Note).filter(Note.title == note_data["title"]).first()
            if note:
                linked_ids = resolve_links(db, note_data["content"])
                note.linked_note_ids = json.dumps(linked_ids)
        
        db.commit()
        print(f"成功创建 {len(test_notes)} 条测试笔记")
        
        print("\n=== 测试说明 ===")
        print("1. 正常链接测试：")
        print("   - 打开「Vue3学习笔记」，预览模式下点击 [[React对比分析]] 应跳转到对应笔记")
        print("   - 链接应显示为蓝色可点击状态")
        print("")
        print("2. 断链测试：")
        print("   - 打开「Vue3进阶技巧」，预览模式下查看 [[不存在的笔记标题]]")
        print("   - 断链应显示为红色删除线样式")
        print("")
        print("3. 反向链接测试：")
        print("   - 打开「Vue3学习笔记」，右侧边栏应显示「反向链接」列表")
        print("   - 列表中应包含链接到当前笔记的其他笔记")
        
    except Exception as e:
        print(f"错误: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    force = "--force" in sys.argv or "-f" in sys.argv
    init_test_data(force)
