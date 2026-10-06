"""种子数据脚本：基于公开信丰/赣南脐橙产销数据构建演示数据。

事实锚点（公开来源）:
- 信丰县脐橙面积/产量: 2020年21万亩/13.5万吨 → 2024年28.4万亩/26万吨, 2025年预计28.6万吨
  (信丰县政府《2024年国民经济和社会发展计划执行情况报告》等)
- 安远县 2024 年 27万亩/27.5万吨; 寻乌县果业 24.6万亩/26万吨 (县政府公开报道)
- 赣州市脐橙面积约194万亩 (央视《从156株到194万亩》)
- 批发价: 2023年前约3元/斤(6元/kg)以上, 2023年跌破1元/斤, 2024年上市回升至
  2.3元/斤后回落至1.5-1.8元/斤, 2025年产季持续低迷 (水果观察、南康区政府答复等)
- 病虫害: 黄龙病/溃疡病/炭疽病/树脂病、木虱/红蜘蛛/潜叶蛾/蚜虫等 (各地植保情报)

其余细粒度数据（逐月、逐产地）在上述锚点内合理插值。固定随机种子保证可复现。

用法: .venv/Scripts/python.exe -m scripts.seed
"""
import random
from datetime import date
from decimal import Decimal

import numpy as np
from sqlalchemy import delete

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    DecisionAdvice,
    MarketData,
    ModelInfo,
    PestDiseaseRecord,
    PestDiseaseType,
    Permission,
    PredictionResult,
    PriceData,
    ProductionArea,
    ProductionData,
    ProductionEvaluation,
    Product,
    RefreshToken,
    Region,
    Role,
    Role as RoleModel,
    SalesData,
    User,
    role_permission,
)
from app.models.system import OperationLog

random.seed(42)
np.random.seed(42)

TODAY = date(2026, 10, 5)
D = Decimal


# ============================================================
# 基础数据定义
# ============================================================

# (adcode, 名称, 经度, 纬度, 2020→2025年产量(万吨), 种植面积(万亩), 是否核心)
COUNTIES = [
    ("360722", "信丰县", 114.93, 25.39, [13.5, 21.0, 22.0, 26.0, 26.0, 28.6], 28.4, True),
    ("360726", "安远县", 115.39, 25.14, [20.0, 22.0, 24.5, 26.5, 27.5, 28.0], 27.0, True),
    ("360734", "寻乌县", 115.65, 24.95, [19.0, 20.5, 22.0, 24.0, 25.0, 26.0], 24.6, True),
    ("360730", "宁都县", 116.01, 26.47, [10.0, 11.0, 12.0, 13.5, 14.5, 15.0], 18.0, False),
    ("360731", "于都县", 115.41, 25.95, [8.0, 9.0, 10.0, 11.0, 12.0, 12.5], 16.0, False),
    ("360733", "会昌县", 115.79, 25.60, [7.0, 8.0, 8.5, 9.5, 10.0, 10.5], 14.0, False),
    ("360781", "瑞金市", 116.03, 25.89, [6.0, 7.0, 7.5, 8.0, 9.0, 9.5], 13.0, False),
    ("360703", "南康区", 114.76, 25.66, [5.0, 5.5, 6.0, 6.5, 7.0, 7.3], 11.0, False),
    ("360732", "兴国县", 115.36, 26.33, [4.0, 4.5, 5.0, 5.5, 6.0, 6.2], 9.0, False),
    ("360704", "赣县区", 115.00, 25.86, [3.5, 4.0, 4.5, 5.0, 5.5, 5.8], 8.0, False),
    ("360723", "大余县", 114.36, 25.40, [2.5, 3.0, 3.2, 3.5, 4.0, 4.2], 6.0, False),
    ("360724", "上犹县", 114.55, 25.79, [2.0, 2.3, 2.5, 2.8, 3.0, 3.2], 5.0, False),
    ("360783", "龙南市", 114.79, 24.91, [1.6, 1.8, 2.0, 2.2, 2.4, 2.5], 4.0, False),
    ("360735", "石城县", 116.34, 26.33, [1.3, 1.5, 1.6, 1.8, 2.0, 2.1], 3.5, False),
    ("360725", "崇义县", 114.30, 25.68, [1.5, 1.8, 2.0, 2.2, 2.5, 2.6], 3.5, False),
    ("360728", "定南县", 114.99, 24.78, [1.5, 1.7, 1.9, 2.0, 2.2, 2.3], 3.0, False),
    ("360729", "全南县", 114.53, 24.76, [1.2, 1.4, 1.5, 1.7, 1.9, 2.0], 2.8, False),
    ("360702", "章贡区", 114.92, 25.83, [0.8, 0.9, 1.0, 1.1, 1.2, 1.2], 2.0, False),
]

# 产地（镇级）: (县adcode, 产地名, 面积占比, 品种, 特点描述)
AREAS = [
    ("360722", "安西镇脐橙基地", 0.20, "纽荷尔", "百里脐橙带核心区，万亩优质脐橙基地，标准化示范区"),
    ("360722", "大塘埠镇脐橙基地", 0.16, "纽荷尔", "万亩优质脐橙基地，富硒高标准示范基地"),
    ("360722", "油山镇脐橙基地", 0.13, "朋娜", "红色文化与脐橙产业融合示范区"),
    ("360722", "古陂镇脐橙基地", 0.11, "纽荷尔", "农伯乐合作社集聚区，绿色食品原料基地"),
    ("360722", "铁石口镇脐橙基地", 0.09, "纽贺尔", "早熟品种试点区域"),
    ("360722", "新田镇脐橙基地", 0.09, "纽荷尔", "乌饭节文旅融合产区"),
    ("360722", "嘉定镇脐橙基地", 0.12, "赣橙5号", "城郊精品果园，采摘体验基地"),
    ("360722", "西牛镇脐橙基地", 0.10, "纽荷尔", "冷链物流节点产区"),
    ("360726", "版石镇脐橙基地", 0.18, "纽荷尔", "安远最早建园的脐橙产区之一，20年以上树龄"),
    ("360726", "镇岗乡脐橙基地", 0.15, "纽荷尔", "三百山生态核心区，出口示范基地"),
    ("360726", "孔田镇脐橙基地", 0.14, "朋娜", "智慧果园示范区，水肥一体化"),
    ("360726", "车头镇脐橙基地", 0.12, "纽荷尔", "橙皇现代农业产业园所在地"),
    ("360726", "欣山镇脐橙基地", 0.11, "赣橙5号", "无公害脐橙出口示范基地"),
    ("360734", "文峰乡脐橙基地", 0.18, "纽荷尔", "寻乌富硒土壤核心产区"),
    ("360734", "吉潭镇脐橙基地", 0.15, "纽荷尔", "国家级出口食品质量安全示范区"),
    ("360734", "澄江镇脐橙基地", 0.14, "朋娜", "传统优势产区，果品加工集聚"),
    ("360730", "梅江镇脐橙基地", 0.16, "纽荷尔", "宁都脐橙主产区，气候温和无霜期长"),
    ("360730", "长胜镇脐橙基地", 0.13, "纽荷尔", "果大色艳脆嫩爽口产区"),
    ("360731", "梓山镇脐橙基地", 0.15, "纽荷尔", "于都富硒产业园区"),
    ("360731", "禾丰镇脐橙基地", 0.12, "朋娜", "丘陵标准化果园"),
    ("360733", "文武坝镇脐橙基地", 0.14, "纽荷尔", "会昌富硒脐橙主产区"),
    ("360733", "麻州镇脐橙基地", 0.11, "纽荷尔", "合作社联营产区"),
    ("360781", "叶坪乡脐橙基地", 0.13, "纽荷尔", "红色旅游融合产区"),
    ("360781", "武阳镇脐橙基地", 0.12, "纽荷尔", "瑞金脐橙示范带"),
    ("360703", "龙回镇脐橙基地", 0.12, "纽荷尔", "南康甜柚脐橙混栽区"),
    ("360703", "朱坊乡脐橙基地", 0.10, "赣橙5号", "农夫山泉收购基地之一"),
    ("360732", "潋江镇脐橙基地", 0.09, "纽荷尔", "将军县果业基地"),
    ("360704", "田村镇脐橙基地", 0.09, "纽荷尔", "赣县山地果园"),
    ("360723", "新城镇脐橙基地", 0.07, "纽荷尔", "大余平原果园"),
    ("360724", "东山镇脐橙基地", 0.06, "纽荷尔", "上犹生态果园"),
    ("360783", "龙南镇脐橙基地", 0.06, "纽荷尔", "龙南丘陵标准化果园"),
    ("360735", "琴江镇脐橙基地", 0.06, "纽荷尔", "石城赣江源头生态产区"),
    ("360725", "横水镇脐橙基地", 0.06, "朋娜", "崇义高山生态果园"),
    ("360728", "历市镇脐橙基地", 0.06, "纽荷尔", "定南东江源头产区"),
    ("360729", "城厢镇脐橙基地", 0.06, "纽荷尔", "全南高山晚熟产区"),
    ("360702", "沙石镇脐橙基地", 0.05, "纽荷尔", "章贡城郊精品采摘园"),
]

# 销售省份: (adcode, 名称, 经度, 纬度, 市场权重, 等级)
PROVINCES = [
    ("440000", "广东省", 113.27, 23.13, 0.16, "core"),
    ("330000", "浙江省", 120.16, 30.29, 0.11, "core"),
    ("320000", "江苏省", 118.78, 32.06, 0.10, "core"),
    ("310000", "上海市", 121.47, 31.23, 0.08, "core"),
    ("110000", "北京市", 116.40, 39.90, 0.07, "main"),
    ("350000", "福建省", 119.30, 26.08, 0.06, "main"),
    ("430000", "湖南省", 112.94, 28.23, 0.055, "main"),
    ("420000", "湖北省", 114.31, 30.59, 0.05, "main"),
    ("510000", "四川省", 104.07, 30.57, 0.045, "main"),
    ("370000", "山东省", 117.12, 36.65, 0.04, "main"),
    ("410000", "河南省", 113.63, 34.75, 0.04, "main"),
    ("340000", "安徽省", 117.28, 31.86, 0.035, "potential"),
    ("360000", "江西省", 115.89, 28.68, 0.03, "potential"),
    ("130000", "河北省", 114.51, 38.04, 0.025, "potential"),
    ("120000", "天津市", 117.20, 39.13, 0.02, "potential"),
    ("610000", "陕西省", 108.94, 34.34, 0.02, "potential"),
    ("210000", "辽宁省", 123.43, 41.80, 0.018, "potential"),
    ("500000", "重庆市", 106.55, 29.56, 0.018, "potential"),
    ("520000", "贵州省", 106.63, 26.65, 0.015, "potential"),
    ("530000", "云南省", 102.83, 24.88, 0.015, "potential"),
    ("450000", "广西壮族自治区", 108.37, 22.82, 0.02, "potential"),
]

# 病虫害类型: (名称, 类型, 描述, 防治措施) —— 来自各地植保部门公开技术资料
PEST_TYPES = [
    ("柑橘黄龙病", "disease",
     "毁灭性病害，由韧皮部杆菌引起，柑橘木虱传播，病树出现黄梢、斑驳黄化，可防可控不可治",
     "贯彻「防木虱、砍病树、种无病苗」策略：统一时间防治木虱（螺虫乙酯、噻虫嗪等）；发现病株按五步法清除（喷药→砍树→划十字→涂药→覆膜）；栽植无病苗木"),
    ("柑橘溃疡病", "disease",
     "细菌性病害，危害叶片、枝梢和果实，病叶率一般0.3%~6%，橙类发病较重",
     "嫩梢期与大风暴雨前后喷药保护：噻唑锌、春雷·喹啉铜、氢氧化铜等；幼树夏梢萌发后15/25天各喷1次；及时剪除病枝清园"),
    ("柑橘炭疽病", "disease",
     "普发性真菌病害，气温回升遇多雨天气易流行，一般病叶率0.1%~2.9%",
     "谢花三分之二时防治：咪鲜胺、吡唑醚菌酯、代森锰锌等；加强栽培管理增施有机肥，及时排水"),
    ("柑橘树脂病", "disease",
     "又称砂皮病，危害枝干与果实，弱树与冻害后易发",
     "剪除病枝，刮除病组织后涂药；春季萌芽前喷代森锰锌预防"),
    ("柑橘红蜘蛛", "pest",
     "主要害螨，虫口密度一般15~60头/百叶，高的可达600~800头/百叶，春秋两季为害盛期",
     "果园生草释放捕食螨以螨治螨；药剂轮换使用：乙螨唑、螺螨酯、联肼·乙螨唑、矿物油等，注意喷施叶背"),
    ("柑橘木虱", "pest",
     "黄龙病唯一传播媒介，嫩梢期产卵繁殖，百梢虫量0~8头，失管果园更高",
     "黄板诱杀+统一时间用药：螺虫·噻虫啉、噻虫嗪·虱螨脲等；及时控梢抹除夏梢；失管果园强制联防"),
    ("柑橘潜叶蛾", "pest",
     "以幼虫潜入嫩叶表皮下取食，形成弯曲虫道，秋梢期受害最重",
     "统一放秋梢避开产卵高峰；性信息素诱捕；嫩梢期喷阿维菌素、灭幼脲等"),
    ("柑橘蚜虫", "pest",
     "群集嫩梢吸食汁液，一般1~8头/梢，可诱发煤污病",
     "悬挂黄板；保护瓢虫草蛉等天敌；达到防治指标时选用噻虫嗪、啶虫脒等"),
    ("柑橘蓟马", "pest",
     "为害嫩梢花蕾幼果，是「花皮果」的主要成因之一",
     "现蕾期与幼果期防治：多杀霉素、乙基多杀菌素等，注意保护蜜蜂"),
    ("柑橘花蕾蛆", "pest",
     "成虫产卵于花蕾内，幼虫蛀食致花蕾不能开放",
     "花蕾露白前树冠喷施高效氯氰菊酯，抓住成虫羽化出土关键窗口期"),
]

# 产品（品种）
PRODUCTS = [
    ("纽荷尔脐橙（信丰）", "纽荷尔", "特级", "果径80-85mm", "11月中下旬",
     "果皮橙色光滑，大而无核，肉质脆嫩，甜酸适中"),
    ("纽荷尔脐橙（精品装）", "纽荷尔", "一级", "果径75-80mm", "11月中下旬",
     "标准化分级精品果，可食率85%以上"),
    ("朋娜脐橙", "朋娜", "一级", "果径70-80mm", "11月上旬",
     "果大形正，橙红鲜艳，较早熟"),
    ("赣橙5号", "赣橙5号", "一级", "果径75-80mm", "10月下旬",
     "比纽荷尔早熟7-15天，错峰上市"),
    ("富硒脐橙", "纽荷尔", "特级", "果径80mm+", "11月中下旬",
     "信丰富硒高标准示范基地产出，硒元素含量达标"),
    ("脐橙加工原料果", "混合", "统货", "-", "11月-次年1月",
     "用于脐橙汁、橙皮丁、橙脯等精深加工"),
]

# 产季（11月→次年10月）月度价格基线（元/kg，批发口径）
# 锚点：2020-2022 约6-7元/kg；2023 产季断崖下跌；2024 回升后回落；2025-2026 低迷
SEASON_BASELINE = {
    "2019-20": 6.3,
    "2020-21": 6.5, "2021-22": 6.6, "2022-23": 6.2,
    "2023-24": 2.8, "2024-25": 3.8, "2025-26": 2.9,
}
# 产季内月度形状（11月起12个月）
SEASON_SHAPE = [0.92, 0.95, 1.08, 1.05, 1.10, 1.12, 1.10, 1.05, 1.02, 1.00, 0.98, 0.95]
# 产量采收月度分布（产季内：11月40%、12月32%、1月15%、2月5%、3月3%、4月2%）
HARVEST_DIST = {11: 0.40, 12: 0.32, 1: 0.15, 2: 0.05, 3: 0.03, 4: 0.02}
# 产销率（按年）
SALES_RATE = {2020: 0.90, 2021: 0.92, 2022: 0.93, 2023: 0.86, 2024: 0.89, 2025: 0.91}


def season_of(y: int, m: int) -> tuple[str, int]:
    """返回 (产季key, 产季内第几月0-11)。产季从11月开始。"""
    if m >= 11:
        return f"{y}-{str(y + 1)[-2:]}", m - 11
    return f"{y - 1}-{str(y)[-2:]}", m + 1


def baseline_price(y: int, m: int) -> float:
    season, idx = season_of(y, m)
    base = SEASON_BASELINE[season]
    # 2023产季断崖：11月上市3.6元 → 后期跌破2.0
    if season == "2023-24":
        base_path = [3.6, 3.0, 2.6, 2.2, 2.0, 2.2, 2.4, 2.6, 2.8, 2.9, 3.0, 3.2]
        return base_path[idx]
    # 2024产季：上市4.6回升 → 11月底回落3.2-3.6
    if season == "2024-25":
        base_path = [4.6, 3.9, 3.6, 3.4, 3.5, 3.7, 3.9, 4.0, 4.1, 4.2, 4.3, 4.4]
        return base_path[idx]
    # 2025产季：低迷 3.4 → 2.4
    if season == "2025-26":
        base_path = [3.4, 3.0, 2.8, 2.6, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.1, 3.2]
        return base_path[idx]
    return base * SEASON_SHAPE[idx]


def months_range(start: date, end: date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


# ============================================================
# 主流程
# ============================================================

def clear_all(db) -> None:
    """清空业务数据（幂等）。按外键依赖顺序删除。"""
    for table in [
        DecisionAdvice, PredictionResult, ModelInfo, OperationLog, RefreshToken,
        ProductionEvaluation, PestDiseaseRecord, MarketData, PriceData, SalesData,
        ProductionData, Product, ProductionArea, PestDiseaseType, Region,
        role_permission, Permission, User, RoleModel,
    ]:
        db.execute(delete(table))
    db.flush()


def seed_regions(db) -> dict[str, Region]:
    """全国 → 省(销售) + 江西省 → 赣州市 → 县区。返回 adcode→Region 映射。"""
    cache: dict[str, Region] = {}

    def add(name, type_, parent, adcode, lng, lat) -> Region:
        r = Region(
            name=name, type=type_, parent_id=parent.id if parent else None,
            adcode=adcode, longitude=D(str(lng)) if lng else None,
            latitude=D(str(lat)) if lat else None,
        )
        db.add(r)
        db.flush()
        if adcode:
            cache[adcode] = r
        return r

    country = add("全国", "country", None, "100000", None, None)
    for adcode, name, lng, lat, _, _ in PROVINCES:
        add(name, "province", country, adcode, lng, lat)
    jiangxi = cache.get("360000")
    ganzhou = add("赣州市", "city", jiangxi, "360700", 114.93, 25.83)
    for adcode, name, lng, lat, _, _, _ in COUNTIES:
        add(name, "county", ganzhou, adcode, lng, lat)
    db.flush()
    return cache


def seed_areas(db, regions: dict[str, Region]) -> list[ProductionArea]:
    """各县产地 + 四维能力分。返回产地列表。"""
    areas = []
    # 同县产地共享县产量，面积按占比分配
    for adcode, name, share, variety, desc in AREAS:
        county = regions[adcode]
        county_area = next(c[5] for c in COUNTIES if c[0] == adcode)
        core = next(c[6] for c in COUNTIES if c[0] == adcode)
        planting = county_area * share * 10000  # 亩
        base = 88 if core else 78
        rng = lambda lo, hi: D(str(round(random.uniform(lo, hi), 1)))  # noqa: E731
        a = ProductionArea(
            name=name,
            region_id=county.id,
            longitude=D(str(round(float(county.longitude) + random.uniform(-0.12, 0.12), 4))),
            latitude=D(str(round(float(county.latitude) + random.uniform(-0.10, 0.10), 4))),
            planting_area=D(str(round(planting, 0))),
            main_variety=variety,
            production_technology_score=rng(base - 4, base + 8),
            transport_score=rng(base - 6, base + 5),
            supply_score=rng(base - 3, base + 8),
            benefit_score=rng(base - 5, base + 7),
            description=desc,
        )
        db.add(a)
        areas.append(a)
    db.flush()
    return areas


def seed_products(db, areas: list[ProductionArea]) -> list[Product]:
    products = []
    xinfeng_areas = [a for a in areas if "信丰" in (a.region_name or "") or a.name in
                     ("安西镇脐橙基地", "大塘埠镇脐橙基地", "油山镇脐橙基地")]
    for i, (name, variety, grade, spec, listing, desc) in enumerate(PRODUCTS):
        p = Product(
            name=name, variety=variety, grade=grade, specification=spec,
            listing_time=listing, description=desc,
            production_area_id=(xinfeng_areas[i % len(xinfeng_areas)].id
                                if i < 5 else None),
        )
        db.add(p)
        products.append(p)
    db.flush()
    return products


def seed_production(db, areas: list[ProductionArea], regions: dict[str, Region]) -> None:
    """产量数据：2020-2025，按采收月度分布。"""
    county_production: dict[int, dict[int, float]] = {}  # county_id -> year -> 万吨
    for adcode, name, _, _, prod_list, _, _ in COUNTIES:
        county = regions[adcode]
        county_production[county.id] = {
            2020 + i: p * 10000 for i, p in enumerate(prod_list)  # 吨
        }

    for area in areas:
        county_total = county_production[area.region_id]
        # 该产地占县面积的近似比例
        share = float(area.planting_area) / next(
            float(a.planting_area) for a in areas if a.region_id == area.region_id
        ) if area.planting_area else 0
        # 用列表一次性算出该县全部产地面积和，避免多次扫描
        for year in range(2020, 2026):
            total_tons = county_total[year]
            for m, dist in HARVEST_DIST.items():
                y = year if m >= 11 else year + 1
                if y > 2026 or (y == 2026 and m > 9):
                    continue
                vol = total_tons * dist
                # 面积占比近似均分到各产地
                area_tons = vol * _area_share(areas, area, county_total, year)
                if area_tons < 1:
                    continue
                db.add(ProductionData(
                    production_area_id=area.id,
                    date=date(y, m, 15),
                    planting_area=area.planting_area,
                    production=D(str(round(area_tons, 2))),
                    yield_per_area=D(str(round(total_tons / float(area.planting_area), 3)))
                    if m == 11 else None,
                ))
    db.flush()


def _area_share(areas, area, county_total, year) -> float:
    """产地当年产量份额（按面积占县比重）。"""
    same_county = [a for a in areas if a.region_id == area.region_id]
    total_planting = sum(float(a.planting_area or 0) for a in same_county)
    if total_planting <= 0:
        return 0
    return float(area.planting_area or 0) / total_planting


def seed_prices(db, areas: list[ProductionArea]) -> None:
    """价格数据：2020-01 ~ 2026-09，产地因子 × 基线 × 噪声。"""
    # 产地价格因子：信丰品牌溢价，安远寻乌次之
    factor_map: dict[int, float] = {}
    for a in areas:
        if a.name.startswith(("安西", "大塘埠", "嘉定", "西牛")):
            factor_map[a.id] = random.uniform(1.03, 1.08)
        elif a.name.startswith(("版石", "镇岗", "文峰", "吉潭")):
            factor_map[a.id] = random.uniform(0.99, 1.04)
        else:
            factor_map[a.id] = random.uniform(0.93, 1.00)

    for y, m in months_range(date(2020, 1, 1), date(2026, 9, 1)):
        base = baseline_price(y, m)
        for a in areas:
            avg = base * factor_map[a.id] * random.uniform(0.97, 1.03)
            avg = round(avg, 2)
            db.add(PriceData(
                production_area_id=a.id,
                date=date(y, m, 15),
                average_price=D(str(avg)),
                highest_price=D(str(round(avg * random.uniform(1.15, 1.30), 2))),
                lowest_price=D(str(round(avg * random.uniform(0.78, 0.88), 2))),
                wholesale_price=D(str(round(avg * random.uniform(0.98, 1.06), 2))),
            ))
    db.flush()


def seed_sales(db, regions: dict[str, Region]) -> None:
    """销量数据：按省月度 + 渠道拆分。总销量 = 当年产量 × 产销率。"""
    county_production: dict[int, dict[int, float]] = {}
    for adcode, _, _, _, prod_list, _, _ in COUNTIES:
        county = regions[adcode]
        county_production[county.id] = {2020 + i: p for i, p in enumerate(prod_list)}

    year_total = {
        year: sum(v[year] for v in county_production.values()) for year in range(2020, 2026)
    }
    # 月度销售形状（产季内，11月—次年9月；与采收分布同属产季口径）
    month_shape = {11: 0.20, 12: 0.24, 1: 0.18, 2: 0.10, 3: 0.08, 4: 0.05,
                   5: 0.04, 6: 0.03, 7: 0.025, 8: 0.025, 9: 0.03}
    weight_sum = sum(p[4] for p in PROVINCES) or 1.0

    for adcode, name, _, _, weight, level in PROVINCES:
        province = regions[adcode]
        for year in range(2020, 2026):
            vol_year = year_total[year] * SALES_RATE[year] * (weight / weight_sum) * 10000  # 吨
            drift = random.uniform(0.92, 1.08)
            for m, shape in month_shape.items():
                y2 = year if m >= 11 else year + 1
                if y2 > 2026 or (y2 == 2026 and m > 9):
                    continue
                vol = vol_year * shape * drift
                if vol < 1:
                    continue
                price = baseline_price(y2, m)
                amount = vol * price * 1.18 / 10  # 吨×元/kg→万元（含流通加价18%）
                ecom_share = min(0.45, 0.25 + (year - 2020) * 0.04)
                for channel, share in (("批发", 1 - ecom_share), ("电商", ecom_share)):
                    cv = vol * share
                    if cv < 0.5:
                        continue
                    db.add(SalesData(
                        region_id=province.id,
                        date=date(y2, m, 15),
                        sales_volume=D(str(round(cv, 2))),
                        sales_amount=D(str(round(amount * share, 2))),
                        sales_channel=channel,
                    ))
    db.flush()


def seed_markets(db, regions: dict[str, Region]) -> None:
    """市场数据：省份年度汇总（与 sales 对齐）。"""
    prov_rows = db.query(SalesData).all()
    agg: dict[int, dict[int, dict]] = {}
    region_names = {r.id: r.name for r in db.query(Region).all()}
    for s in prov_rows:
        key = s.region_id
        # 产季年：11月—次年10月归属于起始自然年
        year = s.date.year if s.date.month >= 11 else s.date.year - 1
        agg.setdefault(key, {}).setdefault(year, {"v": 0.0, "a": 0.0})
        agg[key][year]["v"] += float(s.sales_volume)
        agg[key][year]["a"] += float(s.sales_amount)

    level_map = {ad: lv for ad, _, _, _, _, lv in PROVINCES}
    adcode_map = {regions[ad].id: ad for ad in regions}
    for rid, years in agg.items():
        adcode = adcode_map.get(rid)
        level = level_map.get(adcode, "potential")
        prev_v = None
        for year in sorted(years):
            v = years[year]["v"]
            a = years[year]["a"]
            growth = (
                round((v - prev_v) / prev_v * 100, 2) if prev_v else None
            )
            db.add(MarketData(
                region_id=rid,
                date=date(year, 12, 31),
                sales_volume=D(str(round(v, 2))),
                sales_amount=D(str(round(a, 2))),
                market_level=level,
                growth_rate=D(str(growth)) if growth is not None else None,
            ))
            prev_v = v
    db.flush()


def seed_pests(db, areas: list[ProductionArea]) -> None:
    """病虫害记录：按各病虫害真实发生季节生成。"""
    type_objs = []
    for name, kind, desc, prevention in PEST_TYPES:
        t = PestDiseaseType(name=name, type=kind, description=desc, prevention_method=prevention)
        db.add(t)
        type_objs.append(t)
    db.flush()

    # (类型索引, 高发月份, 高发县adcode列表或None=全部, 概率)
    patterns = [
        (0, [6, 7, 8, 9], ["360722", "360726", "360734", "360730"], 0.35),  # 黄龙病 夏秋木虱期
        (1, [4, 5, 7, 8], None, 0.45),   # 溃疡病 春梢+台风季
        (2, [5, 6], None, 0.40),         # 炭疽病 雨季
        (3, [3, 4], None, 0.25),         # 树脂病 春季
        (4, [3, 4, 5, 9, 10], None, 0.65),  # 红蜘蛛 春秋
        (5, [8, 9, 10], None, 0.55),     # 木虱 秋梢
        (6, [7, 8], None, 0.50),         # 潜叶蛾 秋梢
        (7, [3, 4], None, 0.45),         # 蚜虫 春梢
        (8, [4, 5], None, 0.35),         # 蓟马 花期
        (9, [3], None, 0.30),            # 花蕾蛆 花蕾期
    ]
    county_of_area = {a.id: a.region_id for a in areas}
    adcode_of_county = {}
    for a in areas:
        pass  # 由 region 查询填充，见下

    regions = {r.id: r for r in db.query(Region).filter(Region.type == "county").all()}
    adcode_of_county = {rid: r.adcode for rid, r in regions.items()}

    for year in range(2020, 2026):
        for ti, months_, targets, prob in patterns:
            for m in months_:
                for area in areas:
                    adcode = adcode_of_county.get(county_of_area[area.id])
                    if targets and adcode not in targets:
                        continue
                    p = prob * (0.25 if adcode not in [
                        "360722", "360726", "360734", "360730", "360731"] else 1.0)
                    if random.random() > p:
                        continue
                    severity = random.choices(
                        ["mild", "moderate", "severe"],
                        weights=[0.55, 0.33, 0.12] if ti != 0 else [0.25, 0.45, 0.30],
                    )[0]
                    planting = float(area.planting_area or 3000)
                    affected = planting * random.uniform(0.01, 0.12) * (
                        1.8 if severity == "severe" else 1.0)
                    impact = affected / 1000 * random.uniform(0.3, 0.9)  # 吨
                    db.add(PestDiseaseRecord(
                        production_area_id=area.id,
                        pest_disease_type_id=type_objs[ti].id,
                        date=date(year, m, random.randint(5, 25)),
                        affected_area=D(str(round(affected, 1))),
                        severity=severity,
                        production_impact=D(str(round(impact, 2))),
                        prevention_cost=D(str(round(affected * random.uniform(0.8, 1.6), 2))),
                    ))
    db.flush()


def seed_evaluations(db, areas: list[ProductionArea]) -> None:
    for year in (2024, 2025):
        for a in areas:
            price_score = random.uniform(72, 92)
            if a.name.startswith(("安西", "大塘埠")):
                price_score += 5
            scores = [
                round(price_score, 1),
                float(a.production_technology_score),
                float(a.transport_score),
                float(a.supply_score),
                float(a.benefit_score),
            ]
            total = round(sum(scores) / 5, 1)
            db.add(ProductionEvaluation(
                production_area_id=a.id,
                evaluation_date=date(year, 12, 31),
                price_score=D(str(scores[0])),
                technology_score=D(str(scores[1])),
                transport_score=D(str(scores[2])),
                supply_score=D(str(scores[3])),
                benefit_score=D(str(scores[4])),
                total_score=D(str(total)),
            ))
    db.flush()


def seed_users(db) -> None:
    admin_role = Role(name="管理员", code="admin", description="全部权限")
    op_role = Role(name="操作员", code="operator", description="数据管理与模型运行")
    viewer_role = Role(name="访客", code="viewer", description="只读")
    db.add_all([admin_role, op_role, viewer_role])
    db.flush()

    perms = [
        ("数据查看", "data:view"), ("数据管理", "data:manage"),
        ("模型运行", "model:run"), ("系统管理", "system:manage"),
        ("分析查看", "analysis:view"),
    ]
    perm_objs = [Permission(name=n, code=c) for n, c in perms]
    db.add_all(perm_objs)
    db.flush()
    admin_role.permissions = perm_objs
    op_role.permissions = [p for p in perm_objs if p.code != "system:manage"]
    viewer_role.permissions = [p for p in perm_objs if p.code in ("data:view", "analysis:view")]

    db.add(User(
        username="admin", password_hash=hash_password("admin123"),
        nickname="系统管理员", role_id=admin_role.id, status=True,
    ))
    db.add(User(
        username="operator", password_hash=hash_password("operator123"),
        nickname="数据操作员", role_id=op_role.id, status=True,
    ))
    db.flush()


def main() -> None:
    db = SessionLocal()
    try:
        print("[1/8] 清空旧数据 ...")
        clear_all(db)
        print("[2/8] 区域数据（全国/省/赣州18县区）...")
        regions = seed_regions(db)
        print("[3/8] 产地与产品数据 ...")
        areas = seed_areas(db, regions)
        products = seed_products(db, areas)
        print(f"      产地 {len(areas)} 个, 产品 {len(products)} 个")
        print("[4/8] 产量数据（2020-2025）...")
        seed_production(db, areas, regions)
        print("[5/8] 价格数据（2020-01 ~ 2026-09）...")
        seed_prices(db, areas)
        print("[6/8] 销量与市场数据 ...")
        seed_sales(db, regions)
        seed_markets(db, regions)
        print("[7/8] 病虫害与评价数据 ...")
        seed_pests(db, areas)
        seed_evaluations(db, areas)
        seed_users(db)
        db.commit()
        print("[8/8] 训练模型并生成预测与决策建议 ...")
        from app.services import decision_service, ml_service
        ml_service.train_price_model(db)
        ml_service.predict_price(db, months=6)
        ml_service.train_pest_model(db)
        ml_service.predict_pest(db, months=3)
        decision_service.refresh(db)
        db.commit()
        print("[OK] 种子数据全部完成")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
