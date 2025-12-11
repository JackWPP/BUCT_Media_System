"""
测试批量导入功能
"""
import asyncio
import sys
import os
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.import_service import import_service, scan_and_parse_json_files


def test_scan_json_files():
    """测试 JSON 文件扫描"""
    print("=" * 50)
    print("测试 JSON 文件扫描")
    print("=" * 50)
    
    # 测试目录扫描
    test_dir = os.path.join(os.path.dirname(__file__), 'test_data')
    
    if not os.path.exists(test_dir):
        print(f"⚠️  测试目录不存在: {test_dir}")
        print("   请创建测试目录并添加 JSON 文件")
        return
    
    json_files = import_service.scan_json_files(test_dir)
    print(f"\n找到 {len(json_files)} 个 JSON 文件:")
    for f in json_files:
        print(f"  - {f}")


def test_parse_json():
    """测试 JSON 解析"""
    print("\n" + "=" * 50)
    print("测试 JSON 解析")
    print("=" * 50)
    
    # 创建测试 JSON 数据
    test_data = [
        {
            "uuid": "test-uuid-001",
            "filename": "test_photo_1.jpg",
            "original_path": "/path/to/test_photo_1.jpg",
            "width": 1920,
            "height": 1080,
            "tags": {
                "attributes": {
                    "season": "Spring",
                    "category": "Landscape"
                },
                "keywords": ["建筑", "樱花", "蓝天"],
                "meta": {
                    "camera": "Canon EOS R5",
                    "lens": "RF 24-105mm"
                }
            }
        },
        {
            "uuid": "test-uuid-002",
            "filename": "test_photo_2.jpg",
            "tags": {
                "keywords": ["人物", "活动"]
            }
        }
    ]
    
    # 保存为临时 JSON 文件
    temp_json = os.path.join(os.path.dirname(__file__), 'temp_test.json')
    with open(temp_json, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n创建测试 JSON: {temp_json}")
    
    # 解析 JSON
    photos = import_service.parse_json_file(temp_json)
    
    if photos:
        print(f"✅ 成功解析 {len(photos)} 条照片数据")
        for i, photo in enumerate(photos, 1):
            print(f"\n照片 {i}:")
            print(f"  UUID: {photo.get('uuid')}")
            print(f"  文件名: {photo.get('filename')}")
            
            # 提取标签信息
            season, category, keywords = import_service.extract_tags_from_data(photo)
            print(f"  季节: {season}")
            print(f"  分类: {category}")
            print(f"  关键词: {keywords}")
    else:
        print("❌ 解析失败")
    
    # 清理临时文件
    if os.path.exists(temp_json):
        os.remove(temp_json)
        print(f"\n清理临时文件: {temp_json}")


def test_validate_photo_data():
    """测试数据验证"""
    print("\n" + "=" * 50)
    print("测试数据验证")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "有效数据",
            "data": {"uuid": "test-001", "filename": "test.jpg"},
            "expected": True
        },
        {
            "name": "缺少 uuid",
            "data": {"filename": "test.jpg"},
            "expected": False
        },
        {
            "name": "缺少 filename",
            "data": {"uuid": "test-001"},
            "expected": False
        }
    ]
    
    for test_case in test_cases:
        print(f"\n测试用例: {test_case['name']}")
        result = import_service.validate_photo_data(test_case['data'])
        expected = test_case['expected']
        
        if result == expected:
            print(f"  ✅ 验证通过 (结果: {result})")
        else:
            print(f"  ❌ 验证失败 (期望: {expected}, 实际: {result})")


def test_find_image_file():
    """测试图片文件查找"""
    print("\n" + "=" * 50)
    print("测试图片文件查找")
    print("=" * 50)
    
    # 查找已上传的测试图片
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'originals')
    
    if not os.path.exists(uploads_dir):
        print(f"⚠️  上传目录不存在: {uploads_dir}")
        return
    
    # 获取第一个图片文件
    images = [f for f in os.listdir(uploads_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    
    if not images:
        print(f"⚠️  未找到测试图片")
        return
    
    test_image = images[0]
    print(f"\n使用测试图片: {test_image}")
    
    # 测试查找
    photo_data = {
        "filename": test_image,
        "original_path": os.path.join(uploads_dir, test_image)
    }
    
    found_path = import_service.find_image_file(
        photo_data,
        uploads_dir
    )
    
    if found_path:
        print(f"✅ 找到图片: {found_path}")
        print(f"   文件存在: {os.path.exists(found_path)}")
    else:
        print(f"❌ 未找到图片")


def test_extract_tags():
    """测试标签提取"""
    print("\n" + "=" * 50)
    print("测试标签提取")
    print("=" * 50)
    
    test_data = {
        "tags": {
            "attributes": {
                "season": "Winter",
                "category": "Landscape"
            },
            "keywords": ["建筑", "雪", "天空", "树木"],
            "meta": {
                "camera": "Canon EOS R5",
                "iso": 100
            }
        }
    }
    
    # 提取标签
    season, category, keywords = import_service.extract_tags_from_data(test_data)
    print(f"\n提取结果:")
    print(f"  季节: {season}")
    print(f"  分类: {category}")
    print(f"  关键词 ({len(keywords)} 个): {keywords}")
    
    # 提取 EXIF
    exif = import_service.extract_exif_from_data(test_data)
    print(f"\nEXIF 数据:")
    for key, value in exif.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    print("\n🚀 开始测试批量导入功能\n")
    
    # 运行所有测试
    test_parse_json()
    test_validate_photo_data()
    test_extract_tags()
    test_find_image_file()
    test_scan_json_files()
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)
    print("\n提示: 要测试完整导入功能,请:")
    print("  1. 启动后端服务: uvicorn app.main:app --reload --port 8002")
    print("  2. 准备测试 JSON 文件")
    print("  3. 调用 API: POST /api/v1/photos/import")
