"""初始化开放鉴定标准条款 + 敏感词库（全局，tenant_id=NULL）。

运行方式：
    uv run python app/scripts/seed_appraisal.py

初始条款依据《中华人民共和国档案法》（2020 修订）与
《国家档案馆档案开放办法》（国家档案局令第 19 号，2022）整理，
客户有自己的划控标准时可在「鉴定标准」页面替换。

幂等：已存在的条款编码 / 敏感词跳过。
"""

import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.modules.appraisal.models import (AppraisalSensitiveWord,
                                          AppraisalStandard)
from app.modules.iam import \
    models as iam_models  # noqa: F401  注册 iam_tenant 等被 FK 引用的表

# ── 标准条款 ──────────────────────────────────────────────────────────────────

STANDARDS: list[dict] = [
    {
        "code": "KF-01",
        "title": "形成满二十五年开放",
        "content": "档案自形成之日起满二十五年，不涉及国家安全、重大利益及其他不宜开放情形的，应当向社会开放。",
        "target_kfzt": "开放",
        "source": "《档案法》第二十七条",
        "sort_order": 10,
    },
    {
        "code": "KF-02",
        "title": "经济教育科技文化类档案提前开放",
        "content": "经济、教育、科学、技术、文化等类档案，可以少于二十五年向社会开放。",
        "target_kfzt": "开放",
        "source": "《档案法》第二十七条",
        "sort_order": 20,
    },
    {
        "code": "KZ-01",
        "title": "涉密档案不予开放",
        "content": "属于国家秘密或者未依法解密的档案，不得开放。",
        "target_kfzt": "不开放",
        "keywords": ["国家秘密", "涉密", "保密期限"],
        "source": "《国家档案馆档案开放办法》第十一条",
        "sort_order": 30,
    },
    {
        "code": "KZ-02",
        "title": "危害国家安全和利益",
        "content": "开放后可能危害国家主权、安全和发展利益的档案（含国防、军事内容），划入控制范围。",
        "target_kfzt": "不开放",
        "keywords": ["国防", "军事部署", "武器装备", "作战"],
        "source": "《国家档案馆档案开放办法》第十二条",
        "sort_order": 40,
    },
    {
        "code": "KZ-03",
        "title": "涉及外交外事",
        "content": "涉及外交、外事活动，开放后可能影响国家对外关系的档案，划入控制范围。",
        "target_kfzt": "控制使用",
        "keywords": ["外交", "涉外谈判", "领事"],
        "source": "《国家档案馆档案开放办法》第十二条",
        "sort_order": 50,
    },
    {
        "code": "KZ-04",
        "title": "影响公共安全与社会稳定",
        "content": "开放后可能影响公共安全、社会稳定或者民族宗教关系的档案，划入控制范围。",
        "target_kfzt": "控制使用",
        "keywords": ["群体性事件", "维稳", "民族纠纷", "宗教冲突"],
        "source": "《国家档案馆档案开放办法》第十二条",
        "sort_order": 60,
    },
    {
        "code": "KZ-05",
        "title": "涉及个人隐私与个人信息",
        "content": "涉及个人隐私、个人信息，开放后可能损害个人合法权益的档案（婚姻、收养、病历、身份信息等），划入控制范围。",
        "target_kfzt": "控制使用",
        "keywords": ["个人隐私", "身份证号", "病历", "收养", "婚姻登记"],
        "source": "《国家档案馆档案开放办法》第十二条",
        "sort_order": 70,
    },
    {
        "code": "KZ-06",
        "title": "涉及商业秘密与知识产权",
        "content": "涉及商业秘密、知识产权，开放后可能损害有关单位合法权益的档案，划入控制范围。",
        "target_kfzt": "控制使用",
        "keywords": ["商业秘密", "技术秘密", "专利申请", "配方"],
        "source": "《国家档案馆档案开放办法》第十二条",
        "sort_order": 80,
    },
    {
        "code": "KZ-07",
        "title": "移交单位明确暂缓开放",
        "content": "档案形成单位或者移交单位明确要求暂缓开放且理由正当的档案，可以延期开放，期满后重新鉴定。",
        "target_kfzt": "延期开放",
        "keywords": ["暂缓开放", "暂不开放"],
        "source": "《国家档案馆档案开放办法》第十三条",
        "sort_order": 90,
    },
]

# ── 敏感词 ────────────────────────────────────────────────────────────────────

SENSITIVE_WORDS: list[dict] = [
    {"word": "国家秘密", "category": "国家安全", "suggest_kfzt": "不开放"},
    {"word": "绝密", "category": "国家安全", "suggest_kfzt": "不开放"},
    {"word": "机密", "category": "国家安全", "suggest_kfzt": "不开放"},
    {"word": "国防工程", "category": "国防军事", "suggest_kfzt": "不开放"},
    {"word": "军事设施", "category": "国防军事", "suggest_kfzt": "不开放"},
    {"word": "武器装备", "category": "国防军事", "suggest_kfzt": "不开放"},
    {"word": "外交谈判", "category": "外交外事", "suggest_kfzt": "控制使用"},
    {"word": "涉外纠纷", "category": "外交外事", "suggest_kfzt": "控制使用"},
    {"word": "群体性事件", "category": "社会稳定", "suggest_kfzt": "控制使用"},
    {"word": "信访", "category": "社会稳定", "suggest_kfzt": "控制使用"},
    {"word": "民族纠纷", "category": "社会稳定", "suggest_kfzt": "控制使用"},
    {"word": "身份证号", "category": "个人隐私", "suggest_kfzt": "控制使用"},
    {"word": "病历", "category": "个人隐私", "suggest_kfzt": "控制使用"},
    {"word": "收养登记", "category": "个人隐私", "suggest_kfzt": "控制使用"},
    {"word": "离婚调解", "category": "个人隐私", "suggest_kfzt": "控制使用"},
    {"word": "纪律处分", "category": "个人隐私", "suggest_kfzt": "控制使用"},
    {"word": "商业秘密", "category": "商业秘密", "suggest_kfzt": "控制使用"},
    {"word": "技术配方", "category": "商业秘密", "suggest_kfzt": "控制使用"},
    {"word": "专利申请", "category": "知识产权", "suggest_kfzt": "控制使用"},
    {"word": "暂缓开放", "category": "移交要求", "suggest_kfzt": "延期开放"},
]


async def seed() -> None:
    engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        inserted_std = 0
        for s in STANDARDS:
            exists = (
                await session.execute(
                    select(AppraisalStandard.id).where(
                        AppraisalStandard.code == s["code"],
                        AppraisalStandard.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if exists:
                print(f"  SKIP   标准 {s['code']} {s['title']}")
                continue
            session.add(AppraisalStandard(**s, is_enabled=True, tenant_id=None))
            inserted_std += 1
            print(f"  INSERT 标准 {s['code']} {s['title']} → {s['target_kfzt']}")

        inserted_word = 0
        for w in SENSITIVE_WORDS:
            exists = (
                await session.execute(
                    select(AppraisalSensitiveWord.id).where(
                        AppraisalSensitiveWord.word == w["word"],
                        AppraisalSensitiveWord.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if exists:
                print(f"  SKIP   敏感词 {w['word']}")
                continue
            session.add(AppraisalSensitiveWord(**w, is_enabled=True, tenant_id=None))
            inserted_word += 1
            print(
                f"  INSERT 敏感词 {w['word']} ({w['category']}) → {w['suggest_kfzt']}"
            )

        await session.commit()
        print(f"\n完成：新增 {inserted_std} 条标准，{inserted_word} 个敏感词")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
