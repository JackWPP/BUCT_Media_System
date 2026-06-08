"""
Taxonomy service helpers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, with_loader_criteria

from app.models.photo import Photo
from app.models.taxonomy import PhotoClassification, TaxonomyAlias, TaxonomyFacet, TaxonomyNode

LEGACY_SEASON_MAP = {
    "春季": "Spring",
    "夏季": "Summer",
    "秋季": "Autumn",
    "冬季": "Winter",
}

LEGACY_PHOTO_TYPE_MAP = {
    "风光": "Landscape",
    "风光类": "Landscape",
    "校园风光": "Landscape",
    "建筑楼宇": "Landscape",
    "校区设施": "Landscape",
    "人像": "Portrait",
    "活动": "Activity",
    "纪实": "Documentary",
    "纪实类": "Documentary",
    "人文纪实": "Documentary",
    "自然生态": "Landscape",
}

LEGACY_CATEGORY_TO_PHOTO_TYPE = {
    "Landscape": "建筑楼宇",
    "风光": "建筑楼宇",
    "风光类": "建筑楼宇",
    "校园风光": "建筑楼宇",
    "建筑楼宇": "建筑楼宇",
    "校区设施": "校区设施",
    "自然生态": "自然生态",
}

PHOTO_TYPE_VALUES = {"建筑楼宇", "校区设施", "自然生态"}
PHOTO_TYPE_COMPAT_VALUES = PHOTO_TYPE_VALUES | {"风光类", "纪实类", "校园风光", "人文纪实", "风光", "纪实", "活动"}

LEGACY_SEASON_TO_TAXONOMY = {
    "Spring": "春季",
    "Summer": "夏季",
    "Autumn": "秋季",
    "Winter": "冬季",
    "春季": "春季",
    "夏季": "夏季",
    "秋季": "秋季",
    "冬季": "冬季",
}

CHANGPING_BUILDINGS = [
    "第一教学楼", "体育馆", "图书馆", "实验楼", "文理楼", "第二教学楼",
    "大学生活动中心", "校史博物馆", "工程训练中心", "机电信息楼A座",
    "学生公寓", "紫竹餐厅", "玉兰餐厅", "后勤服务楼", "新校区建设指挥部",
    "保卫处监控指挥中心", "樱花苑", "紫竹苑", "玉兰苑", "留学生公寓",
    "杏坛苑/青教公寓", "杏坛苑/短租公寓",
]

CHAOYANG_BUILDINGS = [
    "教学楼（朝阳校区）", "行政楼", "高精尖大厦", "科技大厦", "逸夫图书馆",
    "会议中心", "科学会堂", "母校之光", "运动场（朝阳校区）",
]

HAIDIAN_BUILDINGS = ["教学楼（海淀校区）", "军乐厅", "荣茂图书馆"]

CHANGPING_BUILDING_PHASE_1 = [
    "第一教学楼",
    "第二教学楼",
    "图书馆",
    "体育馆",
    "大学生活动中心",
    "校史博物馆",
    "文理楼",
    "工程训练中心",
    "机电信息楼A座",
    "后勤服务楼",
    "保卫处监控指挥中心",
]

CHANGPING_BUILDING_PHASE_2 = [
    "实验楼",
    "学生公寓",
    "紫竹餐厅",
    "玉兰餐厅",
    "新校区建设指挥部",
    "樱花苑",
    "紫竹苑",
    "玉兰苑",
    "留学生公寓",
    "杏坛苑/青教公寓",
    "杏坛苑/短租公寓",
]

CHANGPING_FACILITY_GROUPS = {
    "室外设施": ["运动场/风雨操场", "第二运动场", "足球场", "篮球场", "网球场", "排球场", "素质拓展基地"],
    "教学设施": ["教室（第一教学楼）", "教室（第二教学楼）", "求真讲堂（第二教学楼）", "励学讲堂（第二教学楼）", "教研室（大学生活动中心）"],
    "体育设施": ["比赛主场馆（体育馆）", "健身房（体育馆）", "篮球训练馆（体育馆）", "网球馆（体育馆）", "羽毛球馆（体育馆）", "乒乓球馆（体育馆）", "游泳馆（体育馆）", "健美操室（体育馆）", "舞蹈室（体育馆）", "跆拳道室（体育馆）", "形体室（体育馆）", "体测室（体育馆）"],
    "美育设施": ["蓝晒美育工坊（实验楼）", "人因工学美育工坊（实验楼）", "掐丝珐琅美育工坊（实验楼）", "滴胶艺术坊（实验楼）", "陶艺拉坯美育工坊（实验楼）", "陶艺彩绘美育工坊（实验楼）", "情绪串珠美育工坊（实验楼）", "永生绒花美育工坊（实验楼）", "木艺工坊（实验楼）"],
    "实验设施": ["数字化智能教学未来中心（实验楼）", "思政学习创新中心（实验楼）", "实践教学与创新培养未来中心（实验楼）"],
    "办公设施": ["一站式服务大厅（图书馆）", "马克思主义学院（文理楼）", "数理学院（文理楼）", "文法学院（文理楼）", "经济管理学院（文理楼）"],
    "会议设施": ["网络视频会议室（图书馆）", "共享研讨空间（图书馆）", "第一会议室（图书馆）", "第二会议室（图书馆）", "学术报告厅（图书馆）", "共享办公空间（图书馆）", "多功能厅（体育馆）", "会议室（第二教学楼）", "会议室（后勤服务楼）", "贵宾室（体育馆）", "贵宾室（第二教学楼）", "会议室（校史博物馆）"],
    "其他设施": ["小剧场（大学生活动中心）", "主题摄影展（图书馆）", "212大型视听室（图书馆）", "校史馆临时展厅（图书馆）", "智慧教学运行中心（第二教学楼）", "艺术展厅（大学生活动中心）", "琴房（大学生活动中心）", "活动室（大学生活动中心）", "排练厅（大学生活动中心）", "创享商圈（大学生活动中心）", "主题展厅（校史博物馆）", "藏品修复室（校史博物馆）", "数控仿真室（工程训练中心）", "创客空间（工程训练中心）", "游戏设计工坊（工程训练中心）", "寓建生活工坊（学生公寓）"],
}

CHANGPING_NATURAL_ECOLOGY = {
    "季节": ["春季", "夏季", "秋季", "冬季"],
    "自然现象": ["日出", "日落", "蓝天", "日食", "月食", "雨", "白云", "雾", "雷电", "彩虹", "晚霞", "星", "乌云", "雪", "星轨", "银河"],
    "动物": ["猫", "黑天鹅", "白鹅", "绿头鸭", "雌性绿头鸭", "苍鹭", "番鸭", "黑水鸡", "小天鹅"],
    "植物": ["迎春", "杏", "连翘", "芍药", "郁金香", "二月兰", "桃", "牡丹", "紫花地丁", "海棠", "樱花", "玉兰"],
}

CHANGPING_LANDSCAPE_MAINTENANCE = ["校名石", "荷塘", "柳湖", "玉屏山", "北化知行园", "静心亭（柳湖）", "师贤亭（荷塘）", "燕贺亭（玉屏山）", "钟塔（第二教学楼）", "文化墙（第二教学楼）", "质量文化（图书馆）", "中心广场（大学生活动中心）", "枫叶广场（玉屏山）", "校名标识字（玉屏山）", "化彩三台（北化八景）", "馆声凫影（北化八景）", "镜湖书柳（北化八景）", "小荷听书（北化八景）", "花海晴光（北化八景）", "平湖跃金（北化八景）", "花海聆淙（北化八景）", "烟雨玉屏（北化八景）"]

DEFAULT_TAXONOMY = [
    {
        "key": "season",
        "name": "季节",
        "is_system": True,
        "sort_order": 10,
        "nodes": ["春季", "夏季", "秋季", "冬季"],
        "aliases": {
            "春季": ["春天", "春日", "春"],
            "夏季": ["夏天", "夏日", "夏"],
            "秋季": ["秋天", "秋日", "秋", "金秋"],
            "冬季": ["冬天", "冬日", "冬"],
        },
    },
    {
        "key": "campus",
        "name": "校区",
        "is_system": True,
        "sort_order": 20,
        "nodes": ["朝阳校区", "昌平校区", "海淀校区"],
        "aliases": {
            "昌平校区": ["昌平", "北化昌平"],
            "朝阳校区": ["朝阳", "北化朝阳"],
            "海淀校区": ["海淀", "北化海淀"],
        },
    },
    {
        "key": "building",
        "name": "楼宇",
        "selection_mode": "multiple",
        "is_system": True,
        "sort_order": 30,
        "nodes": [
            {"name": "朝阳校区楼宇", "children": CHAOYANG_BUILDINGS},
            {"name": "昌平校区楼宇", "children": CHANGPING_BUILDINGS},
            {"name": "海淀校区楼宇", "children": HAIDIAN_BUILDINGS},
        ],
        "aliases": {
            "图书馆": ["北化图书馆", "新图书馆"],
            "大学生活动中心": ["学生活动中心", "活动中心", "学生中心"],
            "第一教学楼": ["一教"],
            "第二教学楼": ["二教"],
            "实验楼": ["实验中心", "综合实验楼"],
            "体育馆": ["体育中心", "室内体育馆"],
            "运动场": ["操场", "体育场"],
            "学生公寓": ["宿舍", "学生宿舍", "樱花苑学生公寓", "樱花苑", "樱花苑公寓"],
        },
    },
    {
        "key": "gallery_series",
        "name": "专区",
        "is_system": True,
        "sort_order": 40,
        "nodes": ["昌平校区摄影大赛", "投稿作品"],
        "aliases": {
            "昌平校区摄影大赛": ["摄影大赛", "摄影比赛", "摄影大赛作品", "昌平摄影大赛"],
            "投稿作品": ["师生投稿", "学生投稿", "教师投稿", "教职工投稿", "师生作品"],
        },
    },
    {
        "key": "source_type",
        "name": "来源",
        "is_system": True,
        "sort_order": 45,
        "nodes": ["教职工投稿", "学生投稿"],
        "aliases": {"教职工投稿": ["教师投稿", "教工投稿"], "学生投稿": ["同学投稿"]},
    },
    {
        "key": "gallery_year",
        "name": "届次/年份",
        "is_system": True,
        "sort_order": 50,
        "nodes": [
            "第一届获奖作品（2018年）",
            "第二届获奖作品（2019年）",
            "第三届获奖作品（2020年）",
            "第四届获奖作品（2021年）",
            "第五届获奖作品（2022年）",
            "第六届获奖作品（2023年）",
            "第七届获奖作品（2024年）",
            "第八届获奖作品（2025年）",
        ],
        "aliases": {
            "第一届获奖作品（2018年）": ["2018", "2018年", "第一届", "2018年第一届获奖作品"],
            "第二届获奖作品（2019年）": ["2019", "2019年", "第二届", "2019年第二届获奖作品"],
            "第三届获奖作品（2020年）": ["2020", "2020年", "第三届", "2020年第三届获奖作品"],
            "第四届获奖作品（2021年）": ["2021", "2021年", "第四届", "2021年第四届获奖作品"],
            "第五届获奖作品（2022年）": ["2022", "2022年", "第五届", "2022年第五届获奖作品"],
            "第六届获奖作品（2023年）": ["2023", "2023年", "第六届", "2023年第六届获奖作品"],
            "第七届获奖作品（2024年）": ["2024", "2024年", "第七届", "2024年第七届获奖作品"],
            "第八届获奖作品（2025年）": ["2025", "2025年", "第八届", "2025年第八届获奖作品"],
        },
    },
    {
        "key": "award_level",
        "name": "奖项",
        "is_system": True,
        "sort_order": 55,
        "nodes": ["特等奖", "一等奖", "二等奖", "优秀奖"],
        "aliases": {},
    },
    {
        "key": "photo_type",
        "name": "类别",
        "is_system": True,
        "sort_order": 60,
        "nodes": ["建筑楼宇", "校区设施", "自然生态"],
        "aliases": {
            "建筑楼宇": ["楼宇", "建筑", "建筑物", "建筑楼宇", "风光", "风光类", "校园风光", "Landscape"],
            "校区设施": ["设施", "校园设施", "校区设施", "室内设施", "户外设施"],
            "自然生态": ["自然", "生态", "动植物", "动物", "植物"],
        },
    },
    {
        "key": "facility",
        "name": "设施",
        "selection_mode": "multiple",
        "is_system": True,
        "sort_order": 80,
        "nodes": [
            {"name": "室外设施", "children": ["运动场/风雨操场", "第二运动场", "足球场", "篮球场", "网球场", "排球场", "素质拓展基地"]},
            {"name": "教学设施", "children": ["教室（第一教学楼）", "教室（第二教学楼）", "求真讲堂（第二教学楼）", "励学讲堂（第二教学楼）", "教研室（大学生活动中心）"]},
            {"name": "体育设施", "children": ["比赛主场馆（体育馆）", "健身房（体育馆）", "篮球训练馆（体育馆）", "网球馆（体育馆）", "羽毛球馆（体育馆）", "乒乓球馆（体育馆）", "游泳馆（体育馆）", "健美操室（体育馆）", "舞蹈室（体育馆）", "跆拳道室（体育馆）", "形体室（体育馆）", "体测室（体育馆）"]},
            {"name": "美育设施", "children": ["蓝晒美育工坊（实验楼）", "人因工学美育工坊（实验楼）", "掐丝珐琅美育工坊（实验楼）", "滴胶艺术坊（实验楼）", "陶艺拉坯美育工坊（实验楼）", "陶艺彩绘美育工坊（实验楼）", "情绪串珠美育工坊（实验楼）", "永生绒花美育工坊（实验楼）", "木艺工坊（实验楼）"]},
            {"name": "实验设施", "children": ["数字化智能教学未来中心（实验楼）", "思政学习创新中心（实验楼）", "实践教学与创新培养未来中心（实验楼）"]},
            {"name": "办公设施", "children": ["一站式服务大厅（图书馆）", "马克思主义学院（文理楼）", "数理学院（文理楼）", "文法学院（文理楼）", "经济管理学院（文理楼）"]},
            {"name": "会议设施", "children": ["网络视频会议室（图书馆）", "共享研讨空间（图书馆）", "第一会议室（图书馆）", "第二会议室（图书馆）", "学术报告厅（图书馆）", "共享办公空间（图书馆）", "多功能厅（体育馆）", "会议室（第二教学楼）", "会议室（后勤服务楼）", "贵宾室（体育馆）", "贵宾室（第二教学楼）", "会议室（校史博物馆）"]},
            {"name": "其他设施", "children": ["小剧场（大学生活动中心）", "主题摄影展（图书馆）", "212大型视听室（图书馆）", "校史馆临时展厅（图书馆）", "智慧教学运行中心（第二教学楼）", "艺术展厅（大学生活动中心）", "琴房（大学生活动中心）", "活动室（大学生活动中心）", "排练厅（大学生活动中心）", "创享商圈（大学生活动中心）", "主题展厅（校史博物馆）", "藏品修复室（校史博物馆）", "数控仿真室（工程训练中心）", "创客空间（工程训练中心）", "游戏设计工坊（工程训练中心）", "寓建生活工坊（学生公寓）"]},
        ],
        "aliases": {},
    },
    {
        "key": "landscape",
        "name": "景观",
        "selection_mode": "multiple",
        "is_system": True,
        "sort_order": 90,
        "nodes": ["校名石", "荷塘", "柳湖", "玉屏山", "北化知行园", "静心亭（柳湖）", "师贤亭（荷塘）", "燕贺亭（玉屏山）", "钟塔（第二教学楼）", "文化墙（第二教学楼）", "质量文化（图书馆）", "中心广场（大学生活动中心）", "枫叶广场（玉屏山）", "校名标识字（玉屏山）", "化彩三台（北化八景）", "馆声凫影（北化八景）", "镜湖书柳（北化八景）", "小荷听书（北化八景）", "花海晴光（北化八景）", "平湖跃金（北化八景）", "花海聆淙（北化八景）", "烟雨玉屏（北化八景）"],
        "aliases": {"柳湖": ["湖"], "玉屏山": ["山"]},
    },
    {
        "key": "natural_phenomenon",
        "name": "自然现象",
        "selection_mode": "multiple",
        "is_system": True,
        "sort_order": 100,
        "nodes": ["日出", "日落", "蓝天", "日食", "月食", "雨", "白云", "雾", "雷电", "彩虹", "晚霞", "星", "乌云", "雪", "星轨", "银河"],
        "aliases": {},
    },
    {
        "key": "technique",
        "name": "表现手法",
        "selection_mode": "multiple",
        "is_system": True,
        "sort_order": 110,
        "nodes": ["冷暖对比", "补色碰撞", "单色意境", "黑白"],
        "aliases": {},
    },
    {
        "key": "animal",
        "name": "动物",
        "selection_mode": "multiple",
        "is_system": True,
        "sort_order": 120,
        "nodes": ["猫", "黑天鹅", "白鹅", "绿头鸭", "雌性绿头鸭", "苍鹭", "番鸭", "黑水鸡", "小天鹅"],
        "aliases": {
            "雌性绿头鸭": ["麻鸭"],
        },
    },
    {
        "key": "plant",
        "name": "植物",
        "selection_mode": "multiple",
        "is_system": True,
        "sort_order": 130,
        "nodes": ["迎春", "杏", "连翘", "芍药", "郁金香", "二月兰", "桃", "牡丹", "紫花地丁", "海棠", "樱花", "玉兰"],
        "aliases": {},
    },
    {
        "key": "documentary_topic",
        "name": "纪实主题",
        "is_system": True,
        "sort_order": 70,
        "nodes": [
            "德育", "智育", "体育", "美育", "劳育",
            "春季百花节", "夏季荷花节", "秋季山楂节", "秋季枫叶节", "冬季冰雪节",
            "接待会议", "大型活动", "其他",
        ],
        "aliases": {
            "接待会议": ["会议", "接待"],
            "大型活动": ["校园活动"],
        },
    },
]

LEGACY_NODE_MERGES = {
    "building": {
        "一教": "第一教学楼",
        "二教": "第二教学楼",
        "三教": None,
        "主楼": None,
        "樱花苑学生公寓": "学生公寓",
        "学生活动中心": "大学生活动中心",
        "樱花大道": None,
        "操场": "运动场",
        "校门": None,
        "主楼广场": None,
    },
    "gallery_series": {
        "摄影大赛": "昌平校区摄影大赛",
        "师生投稿": "投稿作品",
        "校园风光": "投稿作品",
        "活动纪实": "投稿作品",
    },
    "gallery_year": {
        "2018": "第一届获奖作品（2018年）",
        "2018年第一届获奖作品": "第一届获奖作品（2018年）",
        "2019": "第二届获奖作品（2019年）",
        "2019年第二届获奖作品": "第二届获奖作品（2019年）",
        "2020": "第三届获奖作品（2020年）",
        "2020年第三届获奖作品": "第三届获奖作品（2020年）",
        "2021": "第四届获奖作品（2021年）",
        "2021年第四届获奖作品": "第四届获奖作品（2021年）",
        "2022": "第五届获奖作品（2022年）",
        "2022年第五届获奖作品": "第五届获奖作品（2022年）",
        "2023": "第六届获奖作品（2023年）",
        "2023年第六届获奖作品": "第六届获奖作品（2023年）",
        "2024": "第七届获奖作品（2024年）",
        "2024年第七届获奖作品": "第七届获奖作品（2024年）",
        "2025": "第八届获奖作品（2025年）",
        "2025年第八届获奖作品": "第八届获奖作品（2025年）",
    },
    "photo_type": {
        "风光": None,
        "风光类": None,
        "校园风光": None,
        "纪实": None,
        "纪实类": None,
        "活动": None,
        "人文纪实": None,
        "人像": None,
    },
    "animal": {
        "麻鸭": "雌性绿头鸭",
    },
}

TAXONOMY_GUIDE = {
    "primary": ["gallery_series", "campus", "photo_type"],
    "dependencies": {
        "campus": {
            "朝阳校区": ["building", "facility", "landscape"],
            "昌平校区": ["building", "facility", "landscape"],
            "海淀校区": ["building", "facility", "landscape"],
        },
        "gallery_series": {
            "昌平校区摄影大赛": ["gallery_year", "award_level"],
            "投稿作品": [],
        },
        "photo_type": {
            "建筑楼宇": ["building", "landscape", "season", "technique"],
            "校区设施": ["facility", "landscape", "season", "technique"],
            "自然生态": ["season", "natural_phenomenon", "landscape", "animal", "plant", "technique"],
        },
    },
    "campus_structure": {
        "昌平校区": {
            "building": {
                "一期项目": CHANGPING_BUILDING_PHASE_1,
                "二期项目": CHANGPING_BUILDING_PHASE_2,
            },
            "facility": CHANGPING_FACILITY_GROUPS,
            "natural_ecology": CHANGPING_NATURAL_ECOLOGY,
            "landscape": {
                "景观维持": CHANGPING_LANDSCAPE_MAINTENANCE,
            },
        },
        "朝阳校区": {
            "building": CHAOYANG_BUILDINGS,
        },
        "海淀校区": {
            "building": HAIDIAN_BUILDINGS,
        },
    },
    "campus_category_tree": {
        "昌平校区": {
            "建筑楼宇": [
                {"title": "一期项目", "facet_key": "building", "nodes": CHANGPING_BUILDING_PHASE_1},
                {"title": "二期项目", "facet_key": "building", "nodes": CHANGPING_BUILDING_PHASE_2},
            ],
            "校区设施": [
                {"title": title, "facet_key": "facility", "nodes": nodes}
                for title, nodes in CHANGPING_FACILITY_GROUPS.items()
            ] + [
                {"title": "景观", "facet_key": "landscape", "nodes": CHANGPING_LANDSCAPE_MAINTENANCE},
            ],
            "自然生态": [
                {"title": "季节", "facet_key": "season", "nodes": CHANGPING_NATURAL_ECOLOGY["季节"]},
                {"title": "自然现象", "facet_key": "natural_phenomenon", "nodes": CHANGPING_NATURAL_ECOLOGY["自然现象"]},
                {"title": "动物", "facet_key": "animal", "nodes": CHANGPING_NATURAL_ECOLOGY["动物"]},
                {"title": "植物", "facet_key": "plant", "nodes": CHANGPING_NATURAL_ECOLOGY["植物"]},
                {"title": "景观", "facet_key": "landscape", "nodes": CHANGPING_LANDSCAPE_MAINTENANCE},
            ],
        },
        "朝阳校区": {
            "建筑楼宇": [{"title": "朝阳校区楼宇", "facet_key": "building", "nodes": CHAOYANG_BUILDINGS}],
            "校区设施": [],
            "自然生态": [
                {"title": "季节", "facet_key": "season"},
                {"title": "自然现象", "facet_key": "natural_phenomenon"},
                {"title": "动物", "facet_key": "animal"},
                {"title": "植物", "facet_key": "plant"},
            ],
        },
        "海淀校区": {
            "建筑楼宇": [{"title": "海淀校区楼宇", "facet_key": "building", "nodes": HAIDIAN_BUILDINGS}],
            "校区设施": [],
            "自然生态": [
                {"title": "季节", "facet_key": "season"},
                {"title": "自然现象", "facet_key": "natural_phenomenon"},
                {"title": "动物", "facet_key": "animal"},
                {"title": "植物", "facet_key": "plant"},
            ],
        },
    },
    "legacy_query_aliases": {"landmark": "building"},
}


def _node_key(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def _flatten_seed_nodes(nodes: list) -> list[str]:
    names: list[str] = []
    for node in nodes:
        if isinstance(node, dict):
            names.append(node["name"])
            names.extend(_flatten_seed_nodes(node.get("children", [])))
        else:
            names.append(str(node))
    return names


async def _upsert_seed_nodes(
    db: AsyncSession,
    facet: TaxonomyFacet,
    nodes: list,
    existing_nodes: dict[str, TaxonomyNode],
    parent: TaxonomyNode | None = None,
) -> bool:
    changed = False
    for index, seed in enumerate(nodes, start=1):
        if isinstance(seed, dict):
            node_name = seed["name"]
            children = seed.get("children", [])
            is_selectable = bool(seed.get("is_selectable", False))
        else:
            node_name = str(seed)
            children = []
            is_selectable = True

        node = existing_nodes.get(node_name)
        if node is None:
            node = TaxonomyNode(
                facet_id=facet.id,
                parent_id=parent.id if parent else None,
                key=_node_key(node_name),
                name=node_name,
                sort_order=index,
                is_active=True,
                is_selectable=is_selectable,
            )
            db.add(node)
            await db.flush()
            existing_nodes[node.name] = node
            changed = True
        else:
            target_parent_id = parent.id if parent else None
            if node.parent_id != target_parent_id:
                node.parent_id = target_parent_id
                changed = True
            if node.sort_order != index:
                node.sort_order = index
                changed = True
            if not node.is_active:
                node.is_active = True
                changed = True
            if node.is_selectable != is_selectable:
                node.is_selectable = is_selectable
                changed = True

        if children:
            if await _upsert_seed_nodes(db, facet, children, existing_nodes, node):
                changed = True
    return changed


async def ensure_default_taxonomy(db: AsyncSession) -> None:
    """Seed system facets, base nodes, and aliases if they are missing.

    Uses flush instead of commit so the caller controls the transaction boundary.
    """
    created = False
    active_seed_keys = {facet_seed["key"] for facet_seed in DEFAULT_TAXONOMY}
    for facet_seed in DEFAULT_TAXONOMY:
        result = await db.execute(select(TaxonomyFacet).where(TaxonomyFacet.key == facet_seed["key"]))
        facet = result.scalar_one_or_none()
        if facet is None:
            facet = TaxonomyFacet(
                key=facet_seed["key"],
                name=facet_seed["name"],
                selection_mode=facet_seed.get("selection_mode", "single"),
                is_system=facet_seed.get("is_system", False),
                sort_order=facet_seed.get("sort_order", 0),
                is_active=True,
            )
            db.add(facet)
            await db.flush()
            created = True
        else:
            facet.name = facet_seed["name"]
            facet.selection_mode = facet_seed.get("selection_mode", "single")
            facet.is_system = facet_seed.get("is_system", facet.is_system)
            facet.sort_order = facet_seed.get("sort_order", facet.sort_order)
            facet.is_active = True

        existing_nodes_result = await db.execute(
            select(TaxonomyNode).where(TaxonomyNode.facet_id == facet.id)
        )
        existing_nodes = {node.name: node for node in existing_nodes_result.scalars().all()}
        if await _upsert_seed_nodes(db, facet, facet_seed.get("nodes", []), existing_nodes):
            created = True

        await db.flush()

        aliases_map = facet_seed.get("aliases", {})
        if aliases_map:
            nodes_result = await db.execute(
                select(TaxonomyNode).where(TaxonomyNode.facet_id == facet.id)
            )
            all_nodes = {node.name: node for node in nodes_result.scalars().all()}

            for node_name, alias_list in aliases_map.items():
                node = all_nodes.get(node_name)
                if node is None:
                    continue
                existing_aliases_result = await db.execute(
                    select(TaxonomyAlias.alias).where(TaxonomyAlias.node_id == node.id)
                )
                existing_aliases = {row[0] for row in existing_aliases_result.all()}
                for alias in alias_list:
                    clean = alias.strip()
                    if not clean or clean == node.name or clean in existing_aliases:
                        continue
                    alias_result = await db.execute(
                        select(TaxonomyAlias).where(TaxonomyAlias.alias == clean)
                    )
                    existing_alias = alias_result.scalar_one_or_none()
                    if existing_alias is None:
                        db.add(TaxonomyAlias(node_id=node.id, alias=clean))
                        created = True
                    elif existing_alias.node_id != node.id:
                        existing_alias.node_id = node.id
                        created = True

        if await reconcile_facet_to_seed(db, facet, facet_seed):
            created = True

    legacy_facets_result = await db.execute(
        select(TaxonomyFacet).where(
            TaxonomyFacet.is_system.is_(True),
            TaxonomyFacet.is_active.is_(True),
            TaxonomyFacet.key.notin_(active_seed_keys),
        )
    )
    for legacy_facet in legacy_facets_result.scalars().all():
        legacy_facet.is_active = False
        created = True

    if created:
        await db.flush()


async def reconcile_facet_to_seed(db: AsyncSession, facet: TaxonomyFacet, facet_seed: dict) -> bool:
    """Converge an existing facet to the new controlled vocabulary.

    Old nodes are not exposed publicly after this. Where a confident mapping
    exists, photo classifications are moved to the new node first.
    """
    changed = False
    allowed_names = set(_flatten_seed_nodes(facet_seed.get("nodes", [])))
    merge_map = LEGACY_NODE_MERGES.get(facet.key, {})

    result = await db.execute(select(TaxonomyNode).where(TaxonomyNode.facet_id == facet.id))
    nodes = list(result.scalars().all())
    nodes_by_name = {node.name: node for node in nodes}

    for source_name, target_name in merge_map.items():
        source = nodes_by_name.get(source_name)
        if source is None:
            continue
        if target_name is None:
            continue
        target = nodes_by_name.get(target_name)
        if target is None:
            continue
        classifications_result = await db.execute(
            select(PhotoClassification).where(PhotoClassification.node_id == source.id)
        )
        for classification in classifications_result.scalars().all():
            existing_result = await db.execute(
                select(PhotoClassification).where(
                    PhotoClassification.photo_id == classification.photo_id,
                    PhotoClassification.facet_id == classification.facet_id,
                    PhotoClassification.node_id == target.id,
                )
            )
            if existing_result.scalar_one_or_none() is None:
                classification.node_id = target.id
                classification.updated_at = datetime.utcnow()
            else:
                await db.delete(classification)
            changed = True

    for node in nodes:
        if node.name not in allowed_names and node.is_active:
            node.is_active = False
            changed = True

    return changed


async def get_facets(db: AsyncSession, active_only: bool = False) -> list[TaxonomyFacet]:
    options = [
        selectinload(TaxonomyFacet.nodes).options(
            selectinload(TaxonomyNode.aliases),
            selectinload(TaxonomyNode.children),
        )
    ]
    if active_only:
        options.append(
            with_loader_criteria(
                TaxonomyNode,
                TaxonomyNode.is_active.is_(True),
                include_aliases=True,
            )
        )
    query = select(TaxonomyFacet).options(*options).order_by(TaxonomyFacet.sort_order.asc(), TaxonomyFacet.id.asc())
    if active_only:
        query = query.where(TaxonomyFacet.is_active.is_(True))
    result = await db.execute(query)
    return list(result.scalars().all())


def build_node_tree(nodes: list[TaxonomyNode]) -> list[TaxonomyNode]:
    """Convert a flat node list into a nested tree in-memory."""
    node_map = {node.id: node for node in nodes}
    roots: list[TaxonomyNode] = []
    for node in nodes:
        node.children = []
    for node in nodes:
        if node.parent_id and node.parent_id in node_map:
            node_map[node.parent_id].children.append(node)
        else:
            roots.append(node)
    for node in node_map.values():
        node.children.sort(key=lambda child: (child.sort_order, child.id))
    roots.sort(key=lambda item: (item.sort_order, item.id))
    return roots


async def get_facet_by_id(db: AsyncSession, facet_id: int) -> Optional[TaxonomyFacet]:
    result = await db.execute(
        select(TaxonomyFacet)
        .options(selectinload(TaxonomyFacet.nodes).selectinload(TaxonomyNode.aliases))
        .where(TaxonomyFacet.id == facet_id)
    )
    return result.scalar_one_or_none()


async def get_facet_by_key(db: AsyncSession, facet_key: str) -> Optional[TaxonomyFacet]:
    result = await db.execute(select(TaxonomyFacet).where(TaxonomyFacet.key == facet_key))
    return result.scalar_one_or_none()


async def get_node_by_id(db: AsyncSession, node_id: int) -> Optional[TaxonomyNode]:
    result = await db.execute(
        select(TaxonomyNode)
        .options(selectinload(TaxonomyNode.aliases), selectinload(TaxonomyNode.facet))
        .where(TaxonomyNode.id == node_id)
    )
    return result.scalar_one_or_none()


def validate_selectable_node(node: TaxonomyNode, facet_key: str | None = None) -> None:
    if not node.is_active:
        raise ValueError(f"Inactive taxonomy node cannot be assigned: {node.name}")
    if not node.is_selectable:
        raise ValueError(f"Taxonomy group nodes cannot be submitted: {node.name}")
    if facet_key and node.facet and node.facet.key != facet_key:
        raise ValueError(f"Node {node.id} does not belong to facet: {facet_key}")


async def replace_node_aliases(db: AsyncSession, node: TaxonomyNode, aliases: list[str]) -> None:
    await db.execute(TaxonomyAlias.__table__.delete().where(TaxonomyAlias.node_id == node.id))
    for alias in aliases:
        clean = alias.strip()
        if clean:
            db.add(TaxonomyAlias(node_id=node.id, alias=clean))


async def resolve_taxonomy_node(
    db: AsyncSession,
    facet_key: str,
    raw_value: str,
) -> Optional[TaxonomyNode]:
    clean = raw_value.strip()
    facet = await get_facet_by_key(db, facet_key)
    if facet is None:
        return None

    result = await db.execute(
        select(TaxonomyNode)
        .options(selectinload(TaxonomyNode.facet))
        .where(
            TaxonomyNode.facet_id == facet.id,
            TaxonomyNode.is_active.is_(True),
            func.lower(TaxonomyNode.name) == clean.lower(),
        )
    )
    node = result.scalar_one_or_none()
    if node:
        return node

    result = await db.execute(
        select(TaxonomyNode)
        .options(selectinload(TaxonomyNode.facet))
        .where(
            TaxonomyNode.facet_id == facet.id,
            TaxonomyNode.is_active.is_(True),
            func.lower(TaxonomyNode.key) == _node_key(clean),
        )
    )
    node = result.scalar_one_or_none()
    if node:
        return node

    result = await db.execute(
        select(TaxonomyNode)
        .options(selectinload(TaxonomyNode.facet))
        .join(TaxonomyAlias)
        .where(
            TaxonomyNode.facet_id == facet.id,
            TaxonomyNode.is_active.is_(True),
            func.lower(TaxonomyAlias.alias) == clean.lower(),
        )
    )
    return result.scalar_one_or_none()


async def resolve_legacy_photo_classifications(
    db: AsyncSession,
    *,
    season: str | None = None,
    category: str | None = None,
    campus: str | None = None,
) -> dict[str, int]:
    """Resolve legacy photo fields into canonical taxonomy node ids.

    Portrait is intentionally skipped: it remains a compatibility/access-control
    value in photos.category and is not a new photo_type.
    """
    resolved: dict[str, int] = {}
    legacy_values = {
        "season": LEGACY_SEASON_TO_TAXONOMY.get(season or "", season),
        "campus": campus,
        "photo_type": LEGACY_CATEGORY_TO_PHOTO_TYPE.get(category or ""),
    }
    for facet_key, raw_value in legacy_values.items():
        if not raw_value:
            continue
        node = await resolve_taxonomy_node(db, facet_key, str(raw_value))
        if node is None:
            continue
        validate_selectable_node(node, facet_key)
        resolved[facet_key] = node.id
    return resolved


async def set_photo_classification(
    db: AsyncSession,
    photo: Photo,
    facet_key: str,
    node: TaxonomyNode,
) -> None:
    facet = await get_facet_by_key(db, facet_key)
    if facet is None:
        raise ValueError(f"Unknown facet: {facet_key}")
    if node.facet_id != facet.id:
        raise ValueError(f"Node {node.id} does not belong to facet: {facet_key}")
    validate_selectable_node(node, facet_key)

    now = datetime.utcnow()
    if facet.selection_mode == "single":
        result = await db.execute(
            select(PhotoClassification).where(
                PhotoClassification.photo_id == photo.id,
                PhotoClassification.facet_id == facet.id,
            )
        )
        existing = list(result.scalars().all())
        classification = existing[0] if existing else None
        for extra in existing[1:]:
            await db.delete(extra)
    else:
        result = await db.execute(
            select(PhotoClassification).where(
                PhotoClassification.photo_id == photo.id,
                PhotoClassification.facet_id == facet.id,
                PhotoClassification.node_id == node.id,
            )
        )
        classification = result.scalar_one_or_none()

    if classification is None:
        classification = PhotoClassification(
            photo_id=photo.id,
            facet_id=facet.id,
            node_id=node.id,
            created_at=now,
            updated_at=now,
        )
        db.add(classification)
    else:
        classification.node_id = node.id
        classification.updated_at = now

    if facet_key == "season":
        photo.season = LEGACY_SEASON_MAP.get(node.name, node.name)
    elif facet_key == "campus":
        photo.campus = node.name
    elif facet_key == "photo_type":
        photo.category = LEGACY_PHOTO_TYPE_MAP.get(node.name, node.name)


async def set_photo_classification_nodes(
    db: AsyncSession,
    photo: Photo,
    facet_key: str,
    node_ids: Iterable[int],
) -> None:
    facet = await get_facet_by_key(db, facet_key)
    if facet is None:
        raise ValueError(f"Unknown facet: {facet_key}")

    clean_ids = [int(node_id) for node_id in node_ids if node_id]
    if facet.selection_mode == "single":
        if not clean_ids:
            await delete_photo_classification(db, photo, facet_key)
            return
        node = await get_node_by_id(db, clean_ids[0])
        if node is None:
            raise ValueError(f"Unknown node id: {clean_ids[0]}")
        await set_photo_classification(db, photo, facet_key, node)
        return

    result = await db.execute(
        select(PhotoClassification).where(
            PhotoClassification.photo_id == photo.id,
            PhotoClassification.facet_id == facet.id,
        )
    )
    existing = {classification.node_id: classification for classification in result.scalars().all()}
    target_ids = set(clean_ids)
    for node_id in target_ids:
        node = await get_node_by_id(db, node_id)
        if node is None:
            raise ValueError(f"Unknown node id: {node_id}")
        await set_photo_classification(db, photo, facet_key, node)
    for node_id, classification in existing.items():
        if node_id not in target_ids:
            await db.delete(classification)


async def set_photo_classifications(
    db: AsyncSession,
    photo: Photo,
    classifications: dict[str, int | list[int]],
) -> None:
    """Batch set classifications for a photo: { facet_key: node_id | node_ids }."""
    for facet_key, value in classifications.items():
        if isinstance(value, list):
            await set_photo_classification_nodes(db, photo, facet_key, value)
        else:
            await set_photo_classification_nodes(db, photo, facet_key, [value])


async def delete_photo_classification(
    db: AsyncSession,
    photo: Photo,
    facet_key: str,
) -> None:
    """Remove a classification for a single facet from a photo."""
    facet = await get_facet_by_key(db, facet_key)
    if facet is None:
        raise HTTPException(status_code=404, detail=f"Unknown facet: {facet_key}")

    result = await db.execute(
        select(PhotoClassification).where(
            PhotoClassification.photo_id == photo.id,
            PhotoClassification.facet_id == facet.id,
        )
    )
    classifications = list(result.scalars().all())
    if not classifications:
        return

    for classification in classifications:
        await db.delete(classification)

    if facet_key == "season":
        photo.season = None
    elif facet_key == "campus":
        photo.campus = None
    elif facet_key == "photo_type":
        photo.category = None


def build_node_path(node: TaxonomyNode) -> list[str]:
    path: list[str] = []
    current = node
    while current is not None:
        path.insert(0, current.name)
        current = current.__dict__.get("parent")
    return path


def serialize_classifications(photo: Photo) -> dict[str, dict[str, object]]:
    values: dict[str, dict[str, object]] = {}
    for classification in getattr(photo, "classifications", []) or []:
        if not classification.facet or not classification.node:
            continue
        if (
            not classification.facet.is_active
            or not classification.node.is_active
            or not classification.node.is_selectable
        ):
            continue
        payload = {
            "facet_key": classification.facet.key,
            "facet_name": classification.facet.name,
            "node_id": classification.node.id,
            "node_key": classification.node.key,
            "node_name": classification.node.name,
            "path": build_node_path(classification.node),
        }
        if classification.facet.selection_mode == "multiple":
            values.setdefault(classification.facet.key, [])
            values[classification.facet.key].append(payload)
        else:
            values[classification.facet.key] = payload
    return values
