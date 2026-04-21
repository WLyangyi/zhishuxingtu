import asyncio
from app.db.session import get_db
from app.models.few_shot import FewShotExample
from app.models.prompt import Prompt
from sqlalchemy.orm import Session

DEFAULT_FEW_SHOT_EXAMPLES = [
    {
        "scenario": "conversation_summary",
        "input_example": """用户：我想学习Vue3
AI：Vue3是渐进式JavaScript框架，相比Vue2有组合式API、更好的TypeScript支持等特性。
用户：和Vue2有什么区别？
AI：主要区别包括：1. 组合式API替代选项式API 2. 更好的TypeScript支持 3. 更快的渲染性能 4. 更小的打包体积
用户：学习路线是什么？
AI：建议先掌握Vue2基础，然后学习组合式API，最后深入响应式原理和源码。""",
        "output_example": """## 主题
Vue3学习讨论

## 关键要点
1. Vue3是渐进式JavaScript框架
2. 与Vue2主要区别：组合式API、更好的TypeScript支持、更快性能
3. 学习路线：Vue2基础 → 组合式API → 响应式原理

## 待办事项
- [ ] 学习Vue2基础知识
- [ ] 掌握组合式API
- [ ] 深入响应式原理

## 总结
用户对Vue3感兴趣，讨论了基础概念、与Vue2的区别以及学习路线建议。""",
        "quality_score": 9.0
    },
    {
        "scenario": "conversation_summary",
        "input_example": """用户：Python怎么读取JSON文件？
AI：使用json模块的load方法，示例代码：import json; data = json.load(open('file.json'))
用户：写入呢？
AI：使用json.dump方法，示例：json.dump(data, open('output.json', 'w'))
用户：如何格式化输出？
AI：添加indent参数：json.dump(data, file, indent=2, ensure_ascii=False)""",
        "output_example": """## 主题
Python JSON文件操作

## 关键要点
1. 读取：json.load(file)
2. 写入：json.dump(data, file)
3. 格式化：indent参数控制缩进，ensure_ascii=False支持中文

## 待办事项
- [ ] 练习JSON文件读写
- [ ] 测试格式化参数

## 总结
讨论了Python中JSON文件的读取、写入和格式化输出方法。""",
        "quality_score": 8.5
    },
    {
        "scenario": "knowledge_extraction",
        "input_example": """文章标题：深度学习在NLP中的应用

深度学习技术已经彻底改变了自然语言处理领域。Transformer架构通过自注意力机制实现了对长距离依赖的有效建模，成为现代NLP的基础。

关键技术包括：
1. BERT：双向编码器，擅长理解任务
2. GPT：单向解码器，擅长生成任务
3. Transformer-XL：支持更长上下文

应用场景涵盖机器翻译、文本摘要、问答系统、情感分析等。预训练+微调的范式大幅降低了下游任务的数据需求。""",
        "output_example": """## 核心知识点
1. **Transformer架构**：基于自注意力机制的神经网络结构，能建模长距离依赖
2. **预训练+微调范式**：先在大规模数据上预训练，再在特定任务上微调

## 关键技术点
- **BERT**：双向编码器，理解任务（分类、NER等）
- **GPT**：单向解码器，生成任务（文本生成、对话等）
- **Transformer-XL**：支持更长上下文窗口

## 应用场景
- 机器翻译
- 文本摘要
- 问答系统
- 情感分析

## 技术优势
- 降低下游任务数据需求
- 统一的架构范式
- 强大的迁移学习能力""",
        "quality_score": 9.5
    },
    {
        "scenario": "knowledge_extraction",
        "input_example": """文章标题：Vue3响应式原理详解

Vue3使用Proxy替代了Vue2的Object.defineProperty来实现响应式系统。Proxy可以拦截对象的所有操作，包括属性添加、删除等，解决了Vue2无法检测属性添加/删除的问题。

核心API：
- reactive()：返回对象的响应式代理
- ref()：将基本类型包装为响应式对象
- computed()：计算属性，自动追踪依赖

响应式原理：
1. 依赖收集：在getter中收集依赖
2. 触发更新：在setter中触发依赖执行
3. 副作用：effect函数自动追踪响应式依赖""",
        "output_example": """## 核心知识点
1. **Proxy响应式**：Vue3用Proxy替代Object.defineProperty，可拦截所有操作
2. **依赖收集与触发**：getter收集依赖，setter触发更新

## 关键技术点
- **reactive()**：返回对象的响应式代理
- **ref()**：将基本类型包装为响应式对象
- **computed()**：计算属性，自动追踪依赖
- **effect()**：副作用函数，自动追踪响应式依赖

## 技术优势
- 可检测属性添加/删除
- 支持Map/Set等数据结构
- 性能更好（惰性响应）

## 应用场景
- 状态管理
- 数据绑定
- 计算属性""",
        "quality_score": 9.0
    },
    {
        "scenario": "knowledge_qa",
        "input_example": """问题：Vue3和React的区别是什么？

知识库内容：
【笔记: Vue3核心特性】
Vue3使用模板语法，提供组合式API，学习曲线相对平缓。响应式系统基于Proxy实现。

【笔记: React核心特性】
React使用JSX语法，提供Hooks API，学习曲线较陡峭。状态管理需要额外库支持。

【笔记: 框架对比分析】
Vue3适合快速开发，React适合大型团队协作。Vue3文档更友好，React生态更丰富。""",
        "output_example": """## 推理过程
1. **语法层面**：Vue3使用模板，React使用JSX
2. **响应式原理**：Vue3用Proxy，React用虚拟DOM diff
3. **学习曲线**：Vue更平缓，React更陡峭
4. **生态对比**：Vue文档友好，React生态丰富

## 核心区别

| 维度 | Vue3 | React |
|------|------|-------|
| 语法 | 模板 | JSX |
| 响应式 | Proxy | 虚拟DOM diff |
| 学习曲线 | 平缓 | 陡峭 |
| 文档 | 友好 | 完善 |
| 生态 | 完善 | 丰富 |

## 建议
- **新手**：推荐Vue3，学习曲线平缓，文档友好
- **大型团队**：推荐React，生态丰富，社区活跃
- **快速原型**：推荐Vue3，开发效率高
- **企业级应用**：两者都适合，根据团队技术栈选择""",
        "quality_score": 9.5
    },
    {
        "scenario": "knowledge_qa",
        "input_example": """问题：Python如何实现单例模式？

知识库内容：
【笔记: Python设计模式】
单例模式确保一个类只有一个实例。Python实现方式包括：装饰器、元类、模块导入。

【笔记: 单例模式代码示例】
使用装饰器实现：
def singleton(cls):
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance

【笔记: 单例最佳实践】
推荐使用模块导入方式，Python模块天然单例。""",
        "output_example": """## 推理过程
1. **分析需求**：需要确保类只有一个实例
2. **评估方案**：装饰器、元类、模块导入三种方式
3. **对比优劣**：模块导入最简单，装饰器最灵活

## 实现方式

### 方式1：装饰器（推荐）
```python
def singleton(cls):
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance

@singleton
class Database:
    pass
```

### 方式2：模块导入（最简单）
```python
# singleton.py
class _Singleton:
    pass

instance = _Singleton()

# 使用
from singleton import instance
```

### 方式3：元类
```python
class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Database(metaclass=SingletonMeta):
    pass
```

## 建议
- **简单场景**：使用模块导入
- **需要延迟初始化**：使用装饰器
- **复杂需求**：使用元类""",
        "quality_score": 9.0
    }
]

async def init_few_shot_examples():
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        for example_data in DEFAULT_FEW_SHOT_EXAMPLES:
            existing = db.query(FewShotExample).filter(
                FewShotExample.scenario == example_data["scenario"],
                FewShotExample.input_example == example_data["input_example"]
            ).first()
            
            if not existing:
                example = FewShotExample(**example_data)
                db.add(example)
        
        db.commit()
        print("Few-Shot示例初始化完成")
        
        total = db.query(FewShotExample).count()
        print(f"总计 {total} 个示例")
        
    except Exception as e:
        print(f"初始化失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(init_few_shot_examples())
