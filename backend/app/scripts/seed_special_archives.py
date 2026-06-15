"""专业档案 demo：婚姻档案 + 人事档案（验证无题名/扩展字段的处理）。

婚姻档案没有题名，只有男女方姓名等扩展字段；题名按档案馆惯例合成为
"<男方>与<女方>婚姻登记"，真实可查字段（姓名/证件号/登记日期等）落 ext_fields。
婚姻档案是民政领域最高频被查询的档案类型，密级=无，供社会公众查档。

幂等：以 DH 前缀 HYDEMO / RSDEMO 为标记，已存在即跳过。
运行：cd backend && PYTHONPATH=. uv run python app/scripts/seed_special_archives.py
"""
import asyncio
import random
import sys

sys.path.insert(0, ".")

from sqlalchemy import func, select

from app.infra.db.session import AsyncSessionLocal
import app.modules.iam.models.tenant  # noqa: F401
from app.modules.repository.models.archive import ArchiveStaging, Catalog
from app.modules.repository.models.category import ArchiveCategory
from app.modules.repository.models.fonds import Fonds

XING = list("王李张刘陈杨黄赵周吴徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘")
NAN_MING = ["伟", "强", "磊", "军", "勇", "杰", "涛", "明", "超", "鹏", "斌", "波", "辉", "刚", "建国", "志强", "晓东"]
NV_MING = ["芳", "娜", "敏", "静", "丽", "燕", "娟", "霞", "秀英", "桂英", "玉兰", "婷婷", "晓燕", "梅", "颖", "雪"]
DJJG = ["南京市玄武区民政局", "南京市秦淮区民政局", "南京市鼓楼区民政局", "南京市建邺区民政局"]
HYZT = ["结婚", "结婚", "结婚", "离婚", "补领证"]
HYXZ = ["初婚", "初婚", "再婚", "复婚"]


def _idcard() -> str:
    return f"32010{random.randint(1,4)}{random.randint(1960,2000)}{random.randint(1,12):02d}{random.randint(1,28):02d}{random.randint(1000,9999)}"


async def _ensure_catalog(db, fonds, category, tenant_id) -> Catalog:
    cat = (await db.execute(
        select(Catalog).where(
            Catalog.fonds_id == fonds.id, Catalog.category_id == category.id,
            Catalog.is_deleted.is_(False),
        ).limit(1)
    )).scalars().first()
    if cat:
        return cat
    cat = Catalog(
        fonds_id=fonds.id, category_id=category.id,
        catalog_no=f"{fonds.fonds_code}-{category.code}-001",
        name=f"{category.name}目录", catalog_type="一文一件", tenant_id=tenant_id,
    )
    db.add(cat)
    await db.flush()
    return cat


async def seed() -> None:
    random.seed(2026)
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(
            select(func.count()).select_from(ArchiveStaging).where(
                ArchiveStaging.DH.like("HYDEMO%")
            )
        )).scalar_one()
        if existing:
            print(f"SKIP：已有 {existing} 条婚姻档案演示数据")
            return

        fonds_minzheng = (await db.execute(
            select(Fonds).where(Fonds.fonds_code == "A001", Fonds.is_deleted.is_(False))
        )).scalars().first()
        fonds_any = (await db.execute(
            select(Fonds).where(Fonds.is_deleted.is_(False)).order_by(Fonds.fonds_code)
        )).scalars().first()
        cat_hy = (await db.execute(
            select(ArchiveCategory).where(ArchiveCategory.code == "ZY_HY")
        )).scalars().first()
        cat_rs = (await db.execute(
            select(ArchiveCategory).where(ArchiveCategory.code == "ZY_RS")
        )).scalars().first()
        if not (cat_hy and cat_rs and (fonds_minzheng or fonds_any)):
            print("缺少婚姻/人事门类或全宗，先跑基础 seed")
            return
        fonds_hy = fonds_minzheng or fonds_any
        tenant_id = fonds_hy.tenant_id

        cat_obj_hy = await _ensure_catalog(db, fonds_hy, cat_hy, tenant_id)
        cat_obj_rs = await _ensure_catalog(db, fonds_any, cat_rs, tenant_id)

        # ── 婚姻档案 40 件 ──
        n_hy = 0
        for i in range(40):
            nf = random.choice(XING) + random.choice(NAN_MING)
            nv = random.choice(XING) + random.choice(NV_MING)
            zt = random.choice(HYZT)
            year = random.randint(2008, 2024)
            djrq = f"{year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
            ext = {
                "NFXM": nf, "NFZJH": _idcard(),
                "NVXM": nv, "NVZJH": _idcard(),
                "HYZT": zt, "HYXZ": random.choice(HYXZ),
                "DJRQ": djrq, "DJJG": random.choice(DJJG),
                "ZSBH": f"J{random.randint(320100000000, 320199999999)}",
            }
            db.add(ArchiveStaging(
                fonds_id=fonds_hy.id, catalog_id=cat_obj_hy.id, category_id=cat_hy.id,
                QZH=fonds_hy.fonds_code, DH=f"HYDEMO-{fonds_hy.fonds_code}-{year}-{i+1:04d}",
                # 婚姻档案题名按惯例合成（男方与女方+婚姻状态登记）
                TM=f"{nf}与{nv}{zt}登记", RZZ=None, ND=year, WJRQ=djrq,
                YS=random.randint(2, 6), MJ="无", BGQX="long",
                status="pending_review", ext_fields=ext, tenant_id=tenant_id,
                full_text=f"{nf}（{ext['NFZJH']}）与{nv}（{ext['NVZJH']}）于{djrq}在{ext['DJJG']}办理{zt}登记，"
                          f"婚姻性质{ext['HYXZ']}，结婚证字号{ext['ZSBH']}。",
            ))
            n_hy += 1

        # ── 人事档案 15 件 ──
        n_rs = 0
        for i in range(15):
            xm = random.choice(XING) + random.choice(NAN_MING + NV_MING)
            year = random.randint(2010, 2023)
            ext = {
                "XM": xm, "XB": random.choice(["男", "女"]),
                "CSRQ": f"{random.randint(1965,1998)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "SFZH": _idcard(), "MZ": "汉族",
                "ZZMM": random.choice(["中共党员", "共青团员", "群众"]),
                "ZGXL": random.choice(["本科", "硕士研究生", "大专"]),
                "ZW": random.choice(["科员", "副科长", "科长", "主任科员"]),
                "GZDW": "坤爵人力资源服务中心",
                "DALB": "干部档案",
            }
            db.add(ArchiveStaging(
                fonds_id=fonds_any.id, catalog_id=cat_obj_rs.id, category_id=cat_rs.id,
                QZH=fonds_any.fonds_code, DH=f"RSDEMO-{fonds_any.fonds_code}-{year}-{i+1:04d}",
                TM=f"{xm}人事档案", RZZ=xm, ND=year, WJRQ=f"{year}-06-30",
                YS=random.randint(10, 40), MJ="秘密", BGQX="permanent",
                status="pending_review", ext_fields=ext, tenant_id=tenant_id,
            ))
            n_rs += 1

        await db.commit()
        print(f"完成：婚姻档案 {n_hy} 件（无题名，按男女方合成）、人事档案 {n_rs} 件")
        print("提示：写完后请触发 ES 重建以纳入全文检索："
              "POST /api/v1/archive/admin/rebuild-es-index?sync=true")


if __name__ == "__main__":
    asyncio.run(seed())
