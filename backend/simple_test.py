#!/usr/bin/env python3
"""
简单测试修正后的API端点
"""
import requests
import json

BASE_URL = "http://localhost:8001"

def test_simple_question():
    """测试简单问题（直接回答）"""
    print("=== 测试简单问题 ===")
    
    data = {
        "topic": "你好，你是谁？",
        "locale": "zh-CN"
    }
    
    response = requests.post(f"{BASE_URL}/api/research/start", json=data)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"响应消息: {result.get('message', 'No message')}")
        print(f"需要计划: {result.get('need_plan', False)}")
        print("✅ 简单问题测试完成")
    else:
        print(f"❌ 请求失败: {response.text}")
    
    print()

def test_complex_question():
    """测试复杂问题（需要研究计划）"""
    print("=== 测试复杂问题 ===")
    
    data = {
        "topic": "请研究一下人工智能在医疗领域的应用现状",
        "locale": "zh-CN"
    }
    
    response = requests.post(f"{BASE_URL}/api/research/start", json=data)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"需要计划: {result.get('need_plan', False)}")
        print(f"状态: {result.get('status', 'Unknown')}")
        
        if result.get("need_plan", False):
            print("✅ 复杂问题正确识别为需要研究计划")
            
            # 测试确认计划
            plan_id = result.get("plan_id")
            if plan_id:
                confirm_data = {
                    "plan_id": plan_id,
                    "user_confirm": "confirm"
                }
                
                confirm_response = requests.post(f"{BASE_URL}/api/research/confirm-plan", json=confirm_data)
                print(f"确认计划状态码: {confirm_response.status_code}")
                
                if confirm_response.status_code == 200:
                    confirm_result = confirm_response.json()
                    print(f"确认响应状态: {confirm_result.get('status', 'Unknown')}")
                    print("✅ 研究计划确认流程测试完成")
                else:
                    print(f"❌ 确认计划失败: {confirm_response.text}")
            else:
                print("❌ 没有获取到plan_id")
        else:
            print("❌ 复杂问题被错误识别为简单问题")
    else:
        print(f"❌ 请求失败: {response.text}")
    
    print()

if __name__ == "__main__":
    print("开始简单测试修正后的API...\n")
    
    try:
        test_simple_question()
        test_complex_question()
        
        print("=== 测试完成 ===")
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        print("请确保服务器正在端口8001上运行")