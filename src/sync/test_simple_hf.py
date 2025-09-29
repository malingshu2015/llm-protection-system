"""
简单的HuggingFace API测试
"""

import asyncio
import aiohttp


async def test_simple_api():
    """测试简单的API调用"""
    print("测试简单的HuggingFace API调用...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ModelSync/1.0)",
    }
    
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        try:
            # 不带参数的请求
            print("1. 测试不带参数的请求...")
            async with session.get("https://huggingface.co/api/models") as response:
                print(f"状态码: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"返回数据类型: {type(data)}")
                    if isinstance(data, list) and len(data) > 0:
                        print(f"第一个模型: {data[0].get('id', 'unknown')}")
                        print("✓ 不带参数的请求成功")
                    else:
                        print("❌ 返回数据格式异常")
                else:
                    text = await response.text()
                    print(f"错误响应: {text[:200]}")
                    
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            
        try:
            # 带limit参数的请求
            print("\n2. 测试带limit参数的请求...")
            async with session.get("https://huggingface.co/api/models?limit=5") as response:
                print(f"状态码: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"返回模型数量: {len(data) if isinstance(data, list) else 'unknown'}")
                    print("✓ 带参数的请求成功")
                else:
                    text = await response.text()
                    print(f"错误响应: {text[:200]}")
                    
        except Exception as e:
            print(f"❌ 请求失败: {e}")


if __name__ == "__main__":
    asyncio.run(test_simple_api())