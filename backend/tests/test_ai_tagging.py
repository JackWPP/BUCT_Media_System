"""
测试 AI 打标功能
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai_tagging import AITaggingService


async def _test_ai_service():
    """测试 AI 服务"""
    print("=" * 50)
    print("AI 打标服务测试")
    print("=" * 50)
    
    ai_service = AITaggingService()
    
    print(f"\n配置信息:")
    print(f"  Ollama URL: {ai_service.ollama_url}")
    print(f"  模型名称: {ai_service.model_name}")
    print(f"  AI 已启用: {ai_service.enabled}")
    
    if not ai_service.enabled:
        print("\n⚠️  AI 服务已禁用,跳过测试")
        return
    
    # 测试图片压缩和编码
    print("\n" + "=" * 50)
    print("测试图片压缩和编码")
    print("=" * 50)
    
    # 查找测试图片
    test_image = None
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'originals')
    
    if os.path.exists(uploads_dir):
        images = [f for f in os.listdir(uploads_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        if images:
            test_image = os.path.join(uploads_dir, images[0])
            print(f"找到测试图片: {images[0]}")
    
    if not test_image or not os.path.exists(test_image):
        print("❌ 未找到测试图片,请先上传一张照片")
        print(f"   查找路径: {uploads_dir}")
        return
    
    try:
        # 测试图片编码
        print("\n正在压缩和编码图片...")
        image_base64 = ai_service._compress_and_encode_image(test_image, max_size=1024)
        print(f"✅ 图片编码成功")
        print(f"   Base64 长度: {len(image_base64)} 字符")
        
        # 测试 Prompt 构建
        print("\n" + "=" * 50)
        print("测试 Prompt 构建")
        print("=" * 50)
        prompt = ai_service._build_prompt()
        print(prompt)
        
        # 测试 AI 分析 (如果 Ollama 可用)
        print("\n" + "=" * 50)
        print("测试 AI 分析")
        print("=" * 50)
        print("正在调用 Ollama API...")
        print("⚠️  注意: 这需要 Ollama 服务正在运行")
        
        try:
            result = await ai_service.analyze_image(test_image)
            
            if result:
                print("\n✅ AI 分析成功!")
                print(f"\n分析结果:")
                print(f"  季节 (season): {result.get('season')}")
                print(f"  分类 (category): {result.get('category')}")
                print(f"  标签 (objects): {', '.join(result.get('objects', []))}")
            else:
                print("\n❌ AI 分析返回空结果")
                
        except Exception as e:
            print(f"\n❌ AI 分析失败: {str(e)}")
            print("\n可能的原因:")
            print("  1. Ollama 服务未运行 (启动命令: ollama serve)")
            print("  2. llava 模型未安装 (安装命令: ollama pull llava)")
            print("  3. Ollama 端口配置错误")
            print(f"\n当前配置的 Ollama URL: {ai_service.ollama_url}")
            
    except Exception as e:
        print(f"\n❌ 测试过程出错: {str(e)}")
        import traceback
        traceback.print_exc()


async def _test_response_parsing():
    """测试响应解析"""
    print("\n" + "=" * 50)
    print("测试响应解析")
    print("=" * 50)
    
    ai_service = AITaggingService()
    
    # 测试标准 JSON
    test_cases = [
        {
            "name": "标准 JSON",
            "response": '{"season": "Winter", "category": "Landscape", "objects": ["建筑", "雪", "天空"]}',
            "expected": True
        },
        {
            "name": "带 Markdown 代码块",
            "response": '```json\n{"season": "Spring", "category": "Portrait", "objects": ["人物", "花朵"]}\n```',
            "expected": True
        },
        {
            "name": "无效的 season",
            "response": '{"season": "Invalid", "category": "Landscape", "objects": ["建筑"]}',
            "expected": True  # 会使用默认值
        },
        {
            "name": "缺少字段",
            "response": '{"season": "Summer"}',
            "expected": False  # 会使用默认值但仍能解析
        }
    ]
    
    for test_case in test_cases:
        print(f"\n测试用例: {test_case['name']}")
        print(f"输入: {test_case['response'][:100]}...")
        
        try:
            result = ai_service._parse_response(test_case['response'])
            print(f"✅ 解析成功")
            print(f"   结果: season={result['season']}, category={result['category']}, objects={result['objects']}")
        except Exception as e:
            print(f"❌ 解析失败: {str(e)}")


def test_ai_service():
    asyncio.run(_test_ai_service())


def test_response_parsing():
    asyncio.run(_test_response_parsing())


if __name__ == "__main__":
    print("\n🚀 开始测试 AI 打标服务\n")
    
    # 运行响应解析测试
    asyncio.run(_test_response_parsing())
    
    # 运行完整 AI 服务测试
    asyncio.run(_test_ai_service())
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)
