"""编研模板内置数据：4 类常用体裁的文档骨架（系统内置，全局可见）。

幂等：按 (name, is_builtin=True) 判断，已存在即跳过。
运行：cd backend && PYTHONPATH=. uv run python app/scripts/seed_research_templates.py
"""

import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy import select

import app.modules.iam.models.tenant  # noqa: F401
import app.modules.iam.models.user  # noqa: F401
from app.infra.db.session import AsyncSessionLocal
from app.modules.research.models import ResearchTemplate

CHRONICLE = """
<h1 style="text-align:center">XX大事记</h1>
<p style="text-align:center">（XXXX年—XXXX年）</p>
<h2>编纂说明</h2>
<p>本大事记按时间顺序记述本单位重要事件，资料来源于馆藏档案，力求准确、简明。</p>
<h2>大事记事</h2>
<table>
<thead><tr><th>日期</th><th>大事记事</th><th>来源档号</th></tr></thead>
<tbody>
<tr><td>XXXX-XX-XX</td><td>（在此填写事件，或用"按档案库生成大事记表格"一键生成）</td><td></td></tr>
</tbody>
</table>
<h2>引用档案目录</h2>
<p>（编纂完成后，可用工具栏右侧"生成引用档案目录"自动列出所引档案）</p>
"""

ORG_HISTORY = """
<h1 style="text-align:center">XX单位组织沿革</h1>
<h2>一、机构概况</h2>
<p>简述本单位的性质、职能、隶属关系。</p>
<h2>二、历史沿革</h2>
<p>按时间脉络记述机构的设立、更名、合并、撤销等重大变动。</p>
<h2>三、内设机构</h2>
<p>列述各时期内设机构及其职责。</p>
<h2>四、历任领导</h2>
<table>
<thead><tr><th>姓名</th><th>职务</th><th>任职起止</th></tr></thead>
<tbody><tr><td></td><td></td><td></td></tr></tbody>
</table>
<h2>五、引用档案目录</h2>
<p></p>
"""

COMPILATION = """
<h1 style="text-align:center">XX专题档案汇编</h1>
<h2>一、编纂说明</h2>
<p>说明本汇编的编纂目的、收录范围、时间断限与编排体例。</p>
<h2>二、专题综述</h2>
<p>对专题背景、发展脉络作综合叙述。</p>
<h2>三、档案选编</h2>
<p>（按主题/时间分目编排所选档案，可在正文中插入"档案引用"标记）</p>
<h2>四、引用档案目录</h2>
<p></p>
"""

FONDS_GUIDE = """
<h1 style="text-align:center">XX全宗指南</h1>
<h2>一、全宗概况</h2>
<p>全宗名称、全宗号、档案数量、起止年代、密级开放情况。</p>
<h2>二、立档单位历史</h2>
<p>立档单位的建立、职能与变迁。</p>
<h2>三、档案内容与成分</h2>
<p>按类别概述全宗内档案的主要内容、载体形式与成分。</p>
<h2>四、检索与利用</h2>
<p>检索工具、查阅方式与利用须知。</p>
"""

TEMPLATES = [
    (
        "大事记模板",
        "大事记",
        "按时间顺序记述重要事件，含大事记表格与引用目录骨架。",
        CHRONICLE,
        1,
    ),
    (
        "组织沿革模板",
        "组织沿革",
        "机构概况、历史沿革、内设机构、历任领导骨架。",
        ORG_HISTORY,
        2,
    ),
    (
        "专题汇编模板",
        "专题汇编",
        "编纂说明、专题综述、档案选编、引用目录骨架。",
        COMPILATION,
        3,
    ),
    (
        "全宗指南模板",
        "全宗指南",
        "全宗概况、立档单位历史、档案成分、检索利用骨架。",
        FONDS_GUIDE,
        4,
    ),
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing = set(
            (
                await db.execute(
                    select(ResearchTemplate.name).where(
                        ResearchTemplate.is_builtin.is_(True),
                        ResearchTemplate.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        made = 0
        for name, rtype, desc, content, order in TEMPLATES:
            if name in existing:
                continue
            db.add(
                ResearchTemplate(
                    name=name,
                    result_type=rtype,
                    description=desc,
                    content=content.strip(),
                    is_builtin=True,
                    sort_order=order,
                    tenant_id=None,
                )
            )
            made += 1
        await db.commit()
        print(f"完成：内置编研模板新增 {made} 个（已存在 {len(existing)} 个）")


if __name__ == "__main__":
    asyncio.run(seed())
