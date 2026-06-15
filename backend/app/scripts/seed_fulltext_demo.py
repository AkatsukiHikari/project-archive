"""全文检索 demo：给部分正式库档案写入 OCR 全文，并重建 ES 索引。

刻意让全文里出现题名中没有的关键词（如"防汛""征地补偿""疫苗接种"），
演示"题名著录不准、按字段查不到，但全文能命中"的场景。

运行：cd backend && PYTHONPATH=. uv run python app/scripts/seed_fulltext_demo.py
"""

import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy import select

from app.infra.db.session import AsyncSessionLocal
import app.modules.iam.models.tenant  # noqa: F401
from app.modules.repository.models.category import ArchiveCategory  # noqa: F401
from app.modules.repository.models.fonds import Fonds  # noqa: F401
from app.modules.repository.models.archive import Archive

# 关键词刻意不出现在题名中，只在全文里
OCR_SAMPLES = [
    "本文件记录了二〇〇三年度防汛抗洪应急预案的执行情况，包括河堤加固、物资储备与人员调度安排。",
    "关于城北片区征地补偿标准的会议决定，明确每亩补偿金额及安置房分配办法，涉及农户三百二十户。",
    "全县适龄儿童疫苗接种工作总结，含麻疹、脊髓灰质炎等疫苗的接种率统计与冷链管理记录。",
    "国有土地使用权出让合同，地块位于开发区东侧，出让年限五十年，约定容积率与绿化率指标。",
    "招商引资项目环境影响评价报告，评估废水废气排放对周边水源地的潜在影响及防治措施。",
    "老干部离退休待遇调整通知，涉及医疗报销比例、住房补贴标准及节日慰问金发放细则。",
    "全市中小学校舍安全排查记录，对危房等级、加固方案与师生疏散预案逐校登记。",
    "城市供水管网改造工程竣工验收材料，含管材检测、压力测试与水质化验报告。",
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        archives = (
            (
                await db.execute(
                    select(Archive)
                    .where(Archive.is_deleted.is_(False), Archive.full_text.is_(None))
                    .limit(len(OCR_SAMPLES))
                )
            )
            .scalars()
            .all()
        )
        if not archives:
            print("没有可写入的正式库档案（或都已有全文）")
            return
        for a, text in zip(archives, OCR_SAMPLES):
            a.full_text = text
        await db.commit()
        n = len(archives)
        samples = [(a.DH, a.TM) for a in archives[:3]]

    # 重建 ES 索引，让 full_text 进入检索
    from app.modules.repository.tasks.es_rebuild import rebuild_archive_index

    print(f"已为 {n} 件档案写入 OCR 全文，样例档号：{samples}")
    print("触发 ES 全量重建…")
    try:
        rebuild_archive_index.delay(None)
        print("已提交 Celery 重建任务（异步）")
    except Exception as exc:
        print(f"Celery 不可用（{exc}），改为同步重建")
        await _sync_reindex()


async def _sync_reindex() -> None:
    from app.infra.search.archive_index import index_item
    from app.modules.repository.models.archive import ArchiveStaging

    async with AsyncSessionLocal() as db:
        for model in (ArchiveStaging, Archive):
            rows = (
                (await db.execute(select(model).where(model.is_deleted.is_(False))))
                .scalars()
                .all()
            )
            for r in rows:
                await index_item(r)
        print("同步重建完成")


if __name__ == "__main__":
    asyncio.run(seed())
