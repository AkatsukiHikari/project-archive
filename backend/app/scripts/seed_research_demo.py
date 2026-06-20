"""档案编研 demo：项目 + 选材 + 成果（富文档 HTML）+ 成果档案库。

- 2 个项目：一个「大事记」、一个「专题汇编」
- 每个项目从正式库挑选若干档案作为素材
- 产出成果：一份大事记（draft，正文含大事记表格）、一份专题汇编（finalized）
- 每份成果建立自己的"成果档案库"（从项目素材导入）

幂等：先清除旧的 [DEMO] 编研数据再重建。
运行：cd backend && PYTHONPATH=. uv run python app/scripts/seed_research_demo.py
"""

import asyncio
import html
import sys

sys.path.insert(0, ".")

from sqlalchemy import delete, select

import app.modules.iam.models.tenant  # noqa: F401
import app.modules.iam.models.user  # noqa: F401
from app.infra.db.session import AsyncSessionLocal
from app.modules.repository.models.archive import (Archive,  # noqa: F401
                                                   ArchiveAttachment)
from app.modules.repository.models.category import \
    ArchiveCategory  # noqa: F401
from app.modules.repository.models.fonds import Fonds  # noqa: F401
from app.modules.research.models import (ResearchMaterial, ResearchProject,
                                         ResearchResult, ResearchResultArchive)

TITLE_PREFIX = "[DEMO]"


def _snapshot(a) -> dict:
    return {
        "archive_id": a.id,
        "DH": a.DH,
        "TM": a.TM,
        "RZZ": a.RZZ,
        "ND": a.ND,
        "WJRQ": a.WJRQ,
        "QZH": a.QZH,
    }


def _chronicle_html(archives: list) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(a.WJRQ or (str(a.ND) if a.ND else ''))}</td>"
        f"<td>{html.escape(a.TM)}</td>"
        f"<td>{html.escape(a.DH or '')}</td>"
        "</tr>"
        for a in archives
    )
    return (
        '<h1 style="text-align:center">建市发展大事记</h1>'
        "<h2>编纂说明</h2><p>本大事记按时间顺序记述建市以来重要事件，资料来源于馆藏档案。</p>"
        "<h2>大事记事</h2>"
        "<table><thead><tr><th>日期</th><th>大事记事</th><th>来源档号</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _compilation_html(archives: list) -> str:
    lis = "".join(
        f"<li>{html.escape(a.TM)}（{html.escape(a.WJRQ or str(a.ND or '不详'))}）"
        f"，档号 {html.escape(a.DH or '')}</li>"
        for a in archives
    )
    return (
        '<h1 style="text-align:center">重点基建工程专题汇编</h1>'
        "<h2>一、编纂说明</h2><p>本汇编收录重点基建工程相关档案，按工程进度脉络组织。</p>"
        "<h2>二、专题综述</h2><p>（综述正文，可在编辑器中续写并插入档案引用）</p>"
        f"<h2>三、档案选编</h2><ul>{lis}</ul>"
        "<h2>四、引用档案目录</h2><p>（可用工具栏生成）</p>"
    )


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # 清除旧 [DEMO] 数据（项目级联删素材；成果与成果档案库单独清）
        old_results = (
            (
                await db.execute(
                    select(ResearchResult.id).where(
                        ResearchResult.title.like(f"{TITLE_PREFIX}%")
                    )
                )
            )
            .scalars()
            .all()
        )
        if old_results:
            await db.execute(
                delete(ResearchResultArchive).where(
                    ResearchResultArchive.result_id.in_(old_results)
                )
            )
            await db.execute(
                delete(ResearchResult).where(ResearchResult.id.in_(old_results))
            )
        old_projects = (
            (
                await db.execute(
                    select(ResearchProject.id).where(
                        ResearchProject.title.like(f"{TITLE_PREFIX}%")
                    )
                )
            )
            .scalars()
            .all()
        )
        if old_projects:
            await db.execute(
                delete(ResearchMaterial).where(
                    ResearchMaterial.project_id.in_(old_projects)
                )
            )
            await db.execute(
                delete(ResearchProject).where(ResearchProject.id.in_(old_projects))
            )
        await db.flush()

        # 优先选有数字化原文(PDF/OFD 附件)的档案，便于演示"查看原文"对照写作
        with_att_ids = (
            (
                await db.execute(
                    select(ArchiveAttachment.archive_id)
                    .where(ArchiveAttachment.is_deleted.is_(False))
                    .distinct()
                )
            )
            .scalars()
            .all()
        )
        att_set = set(with_att_ids)

        archives = (
            (
                await db.execute(
                    select(Archive)
                    .where(Archive.is_deleted.is_(False))
                    .order_by(Archive.ND.asc().nulls_last(), Archive.DH)
                    .limit(200)
                )
            )
            .scalars()
            .all()
        )
        if not archives:
            print("正式库为空，先跑档案 seed（如 seed_appraisal_demo.py）")
            return

        tenant_id = archives[0].tenant_id
        # 让两份成果都纳入"有数字化原文"的档案，便于演示查看原文/OCR
        att_archives = [a for a in archives if a.id in att_set][:8]
        other = [a for a in archives if a.id not in att_set]
        fill = max(0, 12 - len(att_archives))
        chron_src = att_archives + other[:fill]
        comp_src = att_archives + other[fill : fill + fill] or chron_src

        p_chron = ResearchProject(
            title=f"{TITLE_PREFIX}建市发展大事记编研",
            project_type="大事记",
            members=["张编研", "李审校"],
            purpose="梳理建市以来重大事件，形成可供查考的大事记成果。",
            status="in_progress",
            tenant_id=tenant_id,
        )
        p_comp = ResearchProject(
            title=f"{TITLE_PREFIX}重点基建工程专题汇编",
            project_type="专题汇编",
            members=["王编研"],
            purpose="围绕重点基建工程，汇编相关档案与背景资料。",
            status="in_progress",
            tenant_id=tenant_id,
        )
        db.add_all([p_chron, p_comp])
        await db.flush()

        for a in chron_src:
            db.add(
                ResearchMaterial(
                    project_id=p_chron.id, tenant_id=tenant_id, **_snapshot(a)
                )
            )
        for a in comp_src:
            db.add(
                ResearchMaterial(
                    project_id=p_comp.id, tenant_id=tenant_id, **_snapshot(a)
                )
            )

        r_chron = ResearchResult(
            project_id=p_chron.id,
            title=f"{TITLE_PREFIX}建市发展大事记（初稿）",
            result_type="大事记",
            summary="按时间顺序整理的建市发展重要事件。",
            content=_chronicle_html(chron_src),
            status="draft",
            tenant_id=tenant_id,
        )
        r_comp = ResearchResult(
            project_id=p_comp.id,
            title=f"{TITLE_PREFIX}重点基建工程专题汇编",
            result_type="专题汇编",
            summary="收录重点基建工程相关档案，按工程进度脉络组织。",
            content=_compilation_html(comp_src),
            status="finalized",
            tenant_id=tenant_id,
        )
        db.add_all([r_chron, r_comp])
        await db.flush()

        for i, a in enumerate(chron_src, 1):
            db.add(
                ResearchResultArchive(
                    result_id=r_chron.id,
                    sort_order=i,
                    tenant_id=tenant_id,
                    **_snapshot(a),
                )
            )
        for i, a in enumerate(comp_src, 1):
            db.add(
                ResearchResultArchive(
                    result_id=r_comp.id,
                    sort_order=i,
                    tenant_id=tenant_id,
                    **_snapshot(a),
                )
            )

        await db.commit()
        print(
            "完成：2 个编研项目、"
            f"{len(chron_src) + len(comp_src)} 件素材、2 份成果（富文档）、"
            f"{len(chron_src) + len(comp_src)} 条成果档案库引用"
        )


if __name__ == "__main__":
    asyncio.run(seed())
