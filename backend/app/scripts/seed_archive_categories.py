"""
初始化内置档案门类（DA/T 18-2022 档案著录规则 + 各门类专项规范）。

设计原则
─────────
1. 字段 name 统一使用汉语拼音大写缩写（DA/T 惯例）。
   - 同名消歧：男方 NF / 女方 NV；全宗 QZ / 权利 QL；面积 MJ → 地块面积 DKMJ（避免与密级 MJ 混淆）。
2. 所有门类的 field_schema 均以 COMMON_FIELDS（通用著录项）开头，inherited=True。
   这些通用项对应 Archive 表列字段，在门类字段设计视图中作"系统字段"展示，
   用户不可删改，数据保存到 Archive 列而非 ext_fields。
3. 各门类的私有著录项（inherited=False）追加在通用项之后，
   数据保存到 Archive.ext_fields (JSONB)。

字段来源
─────────
通用项   DA/T 18-2022 档案著录规则（全 15 项）
文书     DA/T 18-2022 § 5 / 原 DA/T 22-2015 归档文件整理规则
科技     DA/T 28-2018 建设项目档案管理规范 / 科技档案著录规则
会计     DA/T 94-2022 电子会计档案管理规范 / 财会[2015]43号
照片     DA/T 69-2018 照片类档案著录规范（拟）
声像     DA/T 63-2017 录音录像类电子档案元数据方案
电子     DA/T 31-2017 / GB/T 39362-2020 电子档案管理系统通用功能要求
实物     《实物类档案整理与著录规则》（送审稿）
专业     民政部、退役军人事务部、国家医保局相关规范

幂等：已存在的 code 跳过，不重复插入。
更新：见 update_categories.py；或直接运行本脚本后 UPDATE。
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.core.config import settings

import app.modules.iam.models.user  # noqa: F401
import app.modules.iam.models.permission  # noqa: F401
from app.modules.repository.models.category import ArchiveCategory


# ─── 字段定义辅助 ─────────────────────────────────────────────────────────────

def f(name: str, label: str, ftype: str = "text",
      required: bool = False, options: list | None = None,
      inherited: bool = False, default_value=None,
      sort_order: int = 0) -> dict:
    d: dict = {
        "name": name, "label": label, "type": ftype,
        "required": required, "inherited": inherited,
        "sort_order": sort_order,
    }
    if options:
        d["options"] = options
    if default_value is not None:
        d["default_value"] = default_value
    return d


def base(name: str, label: str, ftype: str = "text",
         required: bool = False, options: list | None = None,
         default_value=None, sort_order: int = 0) -> dict:
    """通用著录项（inherited=True，对应 Archive 表列，仅展示不可编辑）。"""
    return f(name, label, ftype, required, options,
             inherited=True, default_value=default_value, sort_order=sort_order)


# ─── DA/T 18-2022 通用著录项（15项，所有门类共用）────────────────────────────

_MJ_OPTIONS  = ["公开", "内部", "秘密", "机密", "绝密"]
_BGQX_OPTIONS = ["永久", "30年", "10年"]

COMMON_FIELDS = [
    # 标识符组（MLH/AJH/JH 已移除，层级关系通过档号 DH 命名约定体现）
    base("DH",   "档号",     "text",   True,  sort_order=1),
    base("QZH",  "全宗号",   "text",   True,  sort_order=2),
    # 内容描述组
    base("TM",   "题名",     "textarea", True, sort_order=3),
    base("RZZ",  "责任者",   "text",          sort_order=4),
    base("ND",   "年度",     "number",        sort_order=5, default_value="$currentYear"),
    base("WJRQ", "文件日期", "text",          sort_order=6),
    base("YS",   "页数",     "number",        sort_order=7),
    # 管理控制组
    base("MJ",   "密级",     "select", True,  _MJ_OPTIONS,  "公开",  sort_order=8),
    base("BGQX", "保管期限", "select", True,  _BGQX_OPTIONS, "30年", sort_order=9),
    # 检索组
    base("ZTC",  "主题词",   "text",          sort_order=10),
    base("ZY",   "摘要",     "textarea",      sort_order=11),
    base("FZ",   "附注",     "textarea",      sort_order=12),
]


# ─── 文书档案 WS（DA/T 18-2022 / DA/T 22-2015）────────────────────────────────

WS_FIELDS = [
    f("WZ",    "文种",     "select", options=[
        "命令（令）", "决定", "决议", "公告", "通告", "意见",
        "通知", "通报", "报告", "请示", "批复", "议案", "函", "纪要", "其他",
    ]),
    f("JJCD",  "紧急程度", "select", options=["特急", "加急", "急", "平"]),
    f("FWBH",  "发文编号", "text"),   # 机关发文字号，如"国办发〔2024〕1号"
    f("FWJG",  "发文机关", "text"),
    f("ZSJG",  "主送机关", "text"),
    f("CSJG",  "抄送机关", "text"),
    f("BGR",   "拟稿人",   "text"),
    f("HGR",   "核稿人",   "text"),
    f("QFR",   "签发人",   "text",   True),
    f("GDDW",  "归档单位", "text"),
    f("DJDW",  "定稿单位", "text"),
]

# ─── 科技档案 KJ（DA/T 28-2018 / 科技档案著录规则）──────────────────────────

KJ_FIELDS = [
    f("ZYLB",  "专业类别", "select", options=[
        "基建工程", "工业生产", "农业科技", "科学研究",
        "测绘勘探", "环境监测", "医疗卫生", "其他",
    ]),
    f("XMBH",  "项目编号", "text"),
    f("XMMC",  "项目名称", "text"),
    f("ZY",    "专业",     "select", options=[
        "建筑", "结构", "给排水", "暖通空调", "电气", "弱电智能化",
        "道路", "桥梁", "岩土", "工艺", "其他",
    ]),
    f("TZLB",  "图纸类别", "select", options=["设计图", "施工图", "竣工图", "草图", "示意图"]),
    f("TH",    "图号",     "text"),
    f("BBH",   "版本号",   "text"),
    f("BLC",   "比例尺",   "text"),
    f("SJJD",  "设计阶段", "select", options=["方案设计", "初步设计", "施工图设计", "竣工"]),
    f("SJDW",  "设计单位", "text"),
    f("SPJG",  "审批机关", "text"),
    f("ZTXS",  "载体形式", "select", options=["纸质", "CAD电子", "BIM模型", "其他"]),
]

# ─── 会计档案 HJ（DA/T 94-2022 / 财会[2015]43号）─────────────────────────────

HJ_FIELDS = [
    f("DALB",  "档案类别", "select", True, [
        "会计凭证", "会计账簿", "财务报告", "其他会计资料",
    ]),
    f("HJND",  "会计年度", "text",   True),   # 如 "2024"
    f("HJQJ",  "会计期间", "text",   True),   # 如 "2024年1月"
    f("PZZL",  "凭证种类", "select", options=["原始凭证", "记账凭证", "银行单据", "报销凭证"]),
    f("PZH",   "凭证号",   "text"),
    f("ZBZL",  "账簿种类", "select", options=["总账", "明细账", "日记账", "固定资产台账", "备查账"]),
    f("BBZL",  "报表种类", "select", options=[
        "资产负债表", "利润表", "现金流量表", "所有者权益变动表", "附注",
    ]),
    f("KMMC",  "科目名称", "text"),
    f("JE",    "金额（元）","number"),
    f("KPZDW", "开票/制单单位", "text"),
]

# ─── 照片档案 ZP（照片类档案著录规范）────────────────────────────────────────

ZP_FIELDS = [
    f("SYZ",   "摄影者",       "text",   True),
    f("SYSJ",  "摄影时间",     "text"),   # YYYY-MM-DD 或 YYYY-MM
    f("SYDD",  "摄影地点",     "text"),
    f("SL",    "照片数量",     "number"),
    f("ZPGG",  "照片规格",     "select", options=[
        "1寸", "2寸", "4寸", "5寸", "6寸", "8寸", "10寸", "A4", "A3", "其他",
    ]),
    f("TXGS",  "图像格式",     "select", options=["JPEG", "TIFF", "RAW", "PNG", "其他"]),
    f("SCMS",  "色彩模式",     "select", options=["彩色", "黑白", "灰度"]),
    f("FBL",   "分辨率（DPI）","number"),
    f("ZTLX",  "载体类型",     "select", options=["纸质照片", "胶片底片", "数字文件"]),
    f("YBCFDD","原版存放地点", "text"),
]

# ─── 声像档案 SX（DA/T 63-2017 录音录像类电子档案元数据方案）─────────────────

SX_FIELDS = [
    f("MTLX",  "媒体类型",     "select", True, ["录音", "录像", "影片", "其他"]),
    f("LZRQ",  "录制日期",     "text"),
    f("LZDD",  "录制地点",     "text"),
    f("LZZ",   "录制者",       "text"),
    f("LZDW",  "录制单位",     "text"),
    f("SC",    "时长（分钟）", "number"),
    f("WJGS",  "文件格式",     "select", options=[
        "MP4", "AVI", "MOV", "MKV", "MP3", "WAV", "FLAC", "其他",
    ]),
    f("FBL",   "分辨率",       "select", options=["4K（2160P）", "1080P", "720P", "标清", "其他"]),
    f("ML",    "码率（kbps）", "number"),
    f("ZTGG",  "载体规格",     "text"),
    f("BFSB",  "播放设备",     "text"),
]

# ─── 电子档案 DZ（DA/T 31-2017 / GB/T 39362-2020）───────────────────────────
# 注：file_format、file_size、sha256_hash 已为 Archive 表独立列，此处补充元数据著录项

DZ_FIELDS = [
    f("WJGSBZ", "文件格式标准", "select", options=[
        "PDF/A", "OFD", "DOCX", "XLSX", "XML", "TXT", "其他",
    ]),
    f("XCRJ",   "形成软件",     "text"),
    f("RJBB",   "软件版本",     "text"),
    f("CZXTHJ", "操作系统环境", "text"),
    f("CGJZ",   "存储介质",     "select", options=[
        "光盘（CD）", "光盘（DVD）", "蓝光光盘", "硬盘", "U盘", "云存储", "其他",
    ]),
    f("JYSL",   "校验算法",     "select", options=["MD5", "SHA-256", "SHA-512", "SM3"]),
    f("SZQM",   "数字签名",     "text"),
    f("JMFS",   "加密方式",     "select", options=["不加密", "SM4", "AES-256", "其他"]),
    f("BBH",    "版本号",       "text"),
    f("QYJL",   "迁移记录",     "textarea"),
]

# ─── 实物档案 SW（《实物类档案整理与著录规则》送审稿）─────────────────────────

SW_FIELDS = [
    f("SWMC",  "实物名称",   "text",   True),
    f("SWLB",  "实物类别",   "select", options=[
        "奖章奖杯", "纪念品", "文物", "样品标本", "设备模型", "印章证照", "其他",
    ]),
    f("CZ",    "材质",       "text"),
    f("GGCC",  "规格尺寸",   "text"),
    f("SL",    "数量",       "number", True),
    f("JLDW",  "计量单位",   "text"),
    f("CFWZ",  "存放位置",   "text"),
    f("XZ",    "现状",       "select", options=["完好", "轻微损坏", "严重损坏", "修复中"]),
    f("LY",    "来源",       "text"),
    f("JDR",   "鉴定人",     "text"),
    f("PGJZ",  "评估价值",   "text"),
]

# ─── 专业档案子类 ─────────────────────────────────────────────────────────────

# 人事档案（民政/组织部规范）
ZY_RS_FIELDS = [
    f("XM",    "姓名",       "text",   True),
    f("XB",    "性别",       "select", True,  ["男", "女"]),
    f("CSRQ",  "出生日期",   "text",   True),
    f("SFZH",  "身份证号",   "text",   True),
    f("MZ",    "民族",       "text"),
    f("ZZMM",  "政治面貌",   "select", options=["中共党员", "中共预备党员", "共青团员", "民主党派", "群众"]),
    f("ZGXL",  "最高学历",   "select", options=["博士研究生", "硕士研究生", "本科", "大专", "中专/高中", "初中及以下"]),
    f("ZW",    "职务",       "text"),
    f("ZC",    "职称",       "text"),
    f("GZDW",  "工作单位",   "text"),
    f("DALB",  "档案类别",   "select", options=["干部档案", "工人档案", "学籍档案", "流动人员档案"]),
]

# 婚姻档案（民政部婚姻登记规范）
ZY_HY_FIELDS = [
    f("NFXM",  "男方姓名",   "text",   True),   # 男方 NF（Nán Fāng）
    f("NFZJH", "男方证件号", "text",   True),
    f("NVXM",  "女方姓名",   "text",   True),   # 女方 NV（Nǚ Fāng）
    f("NVZJH", "女方证件号", "text",   True),
    f("HYZT",  "婚姻状态",   "select", True,  ["结婚", "离婚", "补领证"]),
    f("HYXZ",  "婚姻性质",   "select", options=["初婚", "再婚", "复婚"]),
    f("DJRQ",  "登记日期",   "text",   True),
    f("DJJG",  "登记机关",   "text",   True),
    f("ZSBH",  "证书编号",   "text"),
]

# 扶贫档案（国务院扶贫办规范）
ZY_FP_FIELDS = [
    f("HZXM",  "户主姓名",   "text",   True),
    f("HZZJH", "户主证件号", "text",   True),
    f("JTRKS", "家庭人口数", "number"),
    f("ZPYY",  "致贫原因",   "select", options=["因病", "因残", "因学", "因灾", "缺劳力", "缺技术", "其他"]),
    f("PKDJ",  "贫困等级",   "select", options=["建档立卡贫困户", "边缘易致贫户", "突发严重困难户"]),
    f("BFCS",  "帮扶措施",   "textarea"),
    f("BFZRR", "帮扶责任人", "text"),
    f("BFDW",  "帮扶单位",   "text"),
    f("TPRQ",  "脱贫日期",   "text"),
    f("TCYY",  "退出原因",   "text"),
]

# 土地确权档案（自然资源部规范）
ZY_TQ_FIELDS = [
    f("QLRXM",  "权利人姓名",   "text",   True),
    f("QLRZJH", "权利人证件号", "text",   True),
    f("DKBH",   "地块编号",     "text",   True),
    f("DKLX",   "地块类型",     "select", options=["耕地", "林地", "草地", "建设用地", "其他"]),
    f("DKMJ",   "地块面积（亩）","number"),   # 用 DKMJ 而非 MJ，避免与密级混淆
    f("WZMS",   "位置描述",     "text"),
    f("ZSBH",   "证书编号",     "text"),
    f("FZRQ",   "发证日期",     "text"),
    f("FZJG",   "发证机关",     "text"),
]

# 出生医学证明（国家卫健委规范）
ZY_SC_FIELDS = [
    f("XSEXM",  "新生儿姓名",   "text",   True),   # 新生儿 XSE
    f("XB",     "性别",         "select", True,  ["男", "女", "待定"]),
    f("CSRQ",   "出生日期",     "text",   True),
    f("CSYY",   "出生医院",     "text",   True),
    f("MQXM",   "母亲姓名",     "text",   True),
    f("MQZJH",  "母亲证件号",   "text",   True),
    f("FQXM",   "父亲姓名",     "text"),
    f("FQZJH",  "父亲证件号",   "text"),
    f("ZJBH",   "证件编号",     "text"),
    f("CSTZ",   "出生体重（克）","number"),
]

# 退役军人档案（退役军人事务部规范）
ZY_TY_FIELDS = [
    f("XM",    "姓名",         "text",   True),
    f("XB",    "性别",         "select", True,  ["男", "女"]),
    f("CSRQ",  "出生日期",     "text"),
    f("SFZH",  "身份证号",     "text",   True),
    f("RWRQ",  "入伍日期",     "text",   True),
    f("TYRQ",  "退役日期",     "text",   True),
    f("FYNX",  "服役年限",     "number"),
    f("BDFH",  "部队番号",     "text"),
    f("JXZJ",  "军衔/职级",    "text"),
    f("TYFS",  "退役方式",     "select", options=["安置", "自主就业", "退休", "供养"]),
    f("AZD",   "安置地",       "text"),
    f("LGJL",  "立功记录",     "text"),
]

# 低保档案（国家民政部规范）
ZY_DB_FIELDS = [
    f("HZXM",   "户主姓名",     "text",   True),
    f("HZZJH",  "户主证件号",   "text",   True),
    f("JTRK",   "家庭人口",     "number"),
    f("DBLB",   "低保类别",     "select", True, ["城市低保", "农村低保"]),
    f("YBZJE",  "月保障金额（元）","number"),
    f("SPJG",   "审批机关",     "text"),
    f("QSRQ",   "起始日期",     "text"),
    f("FHZQ",   "复核周期",     "select", options=["每月", "每季度", "每半年", "每年"]),
    f("ZJFHRQ", "最近复核日期", "text"),
    f("TZYY",   "停止原因",     "text"),
]


# ─── 门类定义（通用项 + 私有项）──────────────────────────────────────────────

def schema(*specific: dict) -> list:
    """合并通用著录项与门类私有著录项。"""
    return list(COMMON_FIELDS) + list(specific)


BUILTIN_CATEGORIES = [
    {
        "code": "WS", "name": "文书档案", "parent_id_code": None,
        "requires_privacy_guard": False,
        "field_schema": schema(*WS_FIELDS),
    },
    {
        "code": "KJ", "name": "科技档案", "parent_id_code": None,
        "requires_privacy_guard": False,
        "field_schema": schema(*KJ_FIELDS),
    },
    {
        "code": "HJ", "name": "会计档案", "parent_id_code": None,
        "requires_privacy_guard": False,
        "field_schema": schema(*HJ_FIELDS),
    },
    {
        "code": "ZP", "name": "照片档案", "parent_id_code": None,
        "requires_privacy_guard": False,
        "field_schema": schema(*ZP_FIELDS),
    },
    {
        "code": "SX", "name": "声像档案", "parent_id_code": None,
        "requires_privacy_guard": False,
        "field_schema": schema(*SX_FIELDS),
    },
    {
        "code": "DZ", "name": "电子档案", "parent_id_code": None,
        "requires_privacy_guard": False,
        "field_schema": schema(*DZ_FIELDS),
    },
    {
        "code": "SW", "name": "实物档案", "parent_id_code": None,
        "requires_privacy_guard": False,
        "field_schema": schema(*SW_FIELDS),
    },
    {
        "code": "ZY", "name": "专业档案", "parent_id_code": None,
        "requires_privacy_guard": False,
        "field_schema": list(COMMON_FIELDS),   # 父类仅通用项，子类自行扩展
    },
    # ── 专业档案子类 ──────────────────────────────────────────────────────
    {
        "code": "ZY_RS", "name": "人事档案", "parent_id_code": "ZY",
        "requires_privacy_guard": True,
        "field_schema": schema(*ZY_RS_FIELDS),
    },
    {
        "code": "ZY_HY", "name": "婚姻档案", "parent_id_code": "ZY",
        "requires_privacy_guard": True,
        "field_schema": schema(*ZY_HY_FIELDS),
    },
    {
        "code": "ZY_FP", "name": "扶贫档案", "parent_id_code": "ZY",
        "requires_privacy_guard": True,
        "field_schema": schema(*ZY_FP_FIELDS),
    },
    {
        "code": "ZY_TQ", "name": "土地确权档案", "parent_id_code": "ZY",
        "requires_privacy_guard": True,
        "field_schema": schema(*ZY_TQ_FIELDS),
    },
    {
        "code": "ZY_SC", "name": "出生医学证明", "parent_id_code": "ZY",
        "requires_privacy_guard": True,
        "field_schema": schema(*ZY_SC_FIELDS),
    },
    {
        "code": "ZY_TY", "name": "退役军人档案", "parent_id_code": "ZY",
        "requires_privacy_guard": True,
        "field_schema": schema(*ZY_TY_FIELDS),
    },
    {
        "code": "ZY_DB", "name": "低保档案", "parent_id_code": "ZY",
        "requires_privacy_guard": True,
        "field_schema": schema(*ZY_DB_FIELDS),
    },
]


# ─── 种子逻辑 ─────────────────────────────────────────────────────────────────

async def seed(db: AsyncSession) -> None:
    code_to_id: dict[str, object] = {}

    for pass_no in [1, 2]:   # pass 1: 顶级；pass 2: 子类
        for item in BUILTIN_CATEGORIES:
            is_top = item["parent_id_code"] is None
            if (pass_no == 1) != is_top:
                continue

            result = await db.execute(
                select(ArchiveCategory).where(ArchiveCategory.code == item["code"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                code_to_id[item["code"]] = existing.id
                print(f"  skip existing: {item['code']}")
                continue

            cat = ArchiveCategory(
                code=item["code"],
                name=item["name"],
                is_builtin=True,
                requires_privacy_guard=item["requires_privacy_guard"],
                parent_id=code_to_id.get(item["parent_id_code"]) if item["parent_id_code"] else None,
                field_schema=item["field_schema"] or None,
            )
            db.add(cat)
            await db.flush()
            code_to_id[item["code"]] = cat.id
            n = len(item["field_schema"])
            print(f"  inserted: {item['code']} {item['name']} ({n} fields)")

    await db.commit()
    print("Done.")


async def main() -> None:
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        await seed(db)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
