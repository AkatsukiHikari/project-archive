"""年报指标体系定义（依据《全国档案事业统计调查制度》档案馆基本情况年报 DA-2 表整理）。

source:
  auto    系统自动计算（generate 时实时统计，定稿前可重算）
  manual  系统无数据源，人工填报

指标 key 全局唯一；前端按 group 分组渲染。
"""

INDICATOR_GROUPS: list[dict] = [
    {
        "key": "personnel",
        "name": "一、人员情况",
        "items": [
            {
                "key": "staff_quota",
                "label": "定编人数",
                "unit": "人",
                "source": "manual",
            },
            {
                "key": "staff_actual",
                "label": "实有专职人员",
                "unit": "人",
                "source": "manual",
            },
            {
                "key": "staff_college",
                "label": "其中：大专以上学历",
                "unit": "人",
                "source": "manual",
            },
            {
                "key": "staff_training",
                "label": "本年接受在职业务培训",
                "unit": "人次",
                "source": "manual",
            },
        ],
    },
    {
        "key": "holdings",
        "name": "二、馆藏档案情况",
        "items": [
            {
                "key": "fonds_count",
                "label": "全宗数",
                "unit": "个",
                "source": "auto",
                "hint": "全宗管理中未删除的全宗",
            },
            {
                "key": "holdings_volume",
                "label": "以卷为保管单位档案",
                "unit": "卷",
                "source": "auto",
                "hint": "正式库中案卷目录下的档案",
            },
            {
                "key": "holdings_piece",
                "label": "以件为保管单位档案",
                "unit": "件",
                "source": "auto",
                "hint": "正式库中一文一件/卷内档案",
            },
            {
                "key": "shelf_length",
                "label": "总排架长度",
                "unit": "米",
                "source": "manual",
            },
            {
                "key": "pre_1949",
                "label": "其中：建国前档案",
                "unit": "卷/件",
                "source": "auto",
                "hint": "年度早于 1949 的馆藏",
            },
        ],
    },
    {
        "key": "electronic",
        "name": "三、电子档案情况",
        "items": [
            {
                "key": "e_archive_count",
                "label": "电子档案（含数字副本）",
                "unit": "件",
                "source": "auto",
                "hint": "挂接了电子原文的馆藏档案",
            },
            {
                "key": "e_capacity_gb",
                "label": "电子档案总容量",
                "unit": "GB",
                "source": "auto",
                "hint": "全部电子原文文件容量合计",
            },
        ],
    },
    {
        "key": "digitization",
        "name": "四、传统载体档案数字化情况",
        "items": [
            {
                "key": "digitized_count",
                "label": "已数字化档案数量",
                "unit": "件",
                "source": "auto",
                "hint": "正式库中已挂接数字化成果的档案",
            },
            {
                "key": "digitized_gb",
                "label": "数字化成果容量",
                "unit": "GB",
                "source": "auto",
            },
            {
                "key": "digitized_rate",
                "label": "馆藏数字化率",
                "unit": "%",
                "source": "auto",
                "hint": "已数字化 / 馆藏总量",
            },
            {
                "key": "digitized_frames",
                "label": "数字化画幅数量",
                "unit": "画幅",
                "source": "auto",
                "hint": "按电子原文 PDF 页数合计",
            },
        ],
    },
    {
        "key": "other_carriers",
        "name": "五、其他载体档案",
        "items": [
            {
                "key": "photo_archives",
                "label": "照片档案",
                "unit": "张",
                "source": "manual",
            },
            {
                "key": "audio_tapes",
                "label": "录音档案",
                "unit": "盘",
                "source": "manual",
            },
            {
                "key": "video_tapes",
                "label": "录像档案",
                "unit": "盘",
                "source": "manual",
            },
            {"key": "microfilm", "label": "缩微胶片", "unit": "卷", "source": "manual"},
            {
                "key": "physical_items",
                "label": "实物档案",
                "unit": "件",
                "source": "manual",
            },
        ],
    },
    {
        "key": "catalog",
        "name": "六、档案编目与检索",
        "items": [
            {
                "key": "catalog_file_level",
                "label": "文件级机读目录",
                "unit": "条",
                "source": "auto",
                "hint": "暂存库 + 正式库著录条目合计",
            },
            {
                "key": "catalog_volume_level",
                "label": "案卷级机读目录",
                "unit": "条",
                "source": "auto",
            },
            {
                "key": "search_tools",
                "label": "检索工具",
                "unit": "种",
                "source": "manual",
            },
        ],
    },
    {
        "key": "receive",
        "name": "七、本年接收情况",
        "items": [
            {
                "key": "year_received",
                "label": "本年接收档案",
                "unit": "件",
                "source": "auto",
                "hint": "本年度接收入库的移交清单条目",
            },
            {
                "key": "year_archived",
                "label": "本年归档入正式库",
                "unit": "件",
                "source": "auto",
            },
            {
                "key": "year_imported",
                "label": "本年批量导入",
                "unit": "件",
                "source": "auto",
                "hint": "批量导入任务成功条数",
            },
        ],
    },
    {
        "key": "appraisal",
        "name": "八、本年鉴定与销毁",
        "items": [
            {
                "key": "year_appraised",
                "label": "本年完成开放鉴定",
                "unit": "件",
                "source": "auto",
                "hint": "审核通过的开放鉴定明细",
            },
            {
                "key": "year_opened",
                "label": "其中：划定开放",
                "unit": "件",
                "source": "auto",
            },
            {
                "key": "year_destroyed",
                "label": "本年销毁档案",
                "unit": "件",
                "source": "manual",
                "hint": "销毁流程上线前人工填报",
            },
        ],
    },
    {
        "key": "utilization",
        "name": "九、档案资料利用情况",
        "items": [
            {
                "key": "year_util_visits",
                "label": "本年利用人次",
                "unit": "人次",
                "source": "auto",
            },
            {
                "key": "year_util_items",
                "label": "本年利用卷件次",
                "unit": "卷件次",
                "source": "auto",
            },
            {
                "key": "year_research",
                "label": "本年编研成果",
                "unit": "部",
                "source": "manual",
            },
            {
                "key": "year_exhibitions",
                "label": "举办展览",
                "unit": "个",
                "source": "manual",
            },
        ],
    },
    {
        "key": "building",
        "name": "十、馆库建设情况",
        "items": [
            {
                "key": "building_total_area",
                "label": "总建筑面积",
                "unit": "㎡",
                "source": "manual",
            },
            {
                "key": "building_storage_area",
                "label": "档案库房面积",
                "unit": "㎡",
                "source": "manual",
            },
            {
                "key": "building_reading_area",
                "label": "阅览用房面积",
                "unit": "㎡",
                "source": "manual",
            },
            {
                "key": "building_office_area",
                "label": "办公用房面积",
                "unit": "㎡",
                "source": "manual",
            },
        ],
    },
    {
        "key": "equipment",
        "name": "十一、设施设备情况",
        "items": [
            {
                "key": "equip_hvac",
                "label": "恒温恒湿设备",
                "unit": "台",
                "source": "manual",
            },
            {
                "key": "equip_security",
                "label": "安防监控系统",
                "unit": "套",
                "source": "manual",
            },
            {
                "key": "equip_fire",
                "label": "消防设备",
                "unit": "套",
                "source": "manual",
            },
            {
                "key": "equip_computer",
                "label": "计算机",
                "unit": "台",
                "source": "manual",
            },
        ],
    },
    {
        "key": "finance",
        "name": "十二、经费情况",
        "items": [
            {
                "key": "budget_total",
                "label": "本年经费总额",
                "unit": "万元",
                "source": "manual",
            },
            {
                "key": "budget_it",
                "label": "其中：信息化建设经费",
                "unit": "万元",
                "source": "manual",
            },
        ],
    },
]

AUTO_KEYS: set[str] = {
    item["key"]
    for group in INDICATOR_GROUPS
    for item in group["items"]
    if item["source"] == "auto"
}

MANUAL_KEYS: set[str] = {
    item["key"]
    for group in INDICATOR_GROUPS
    for item in group["items"]
    if item["source"] == "manual"
}
