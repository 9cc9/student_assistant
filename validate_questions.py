#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断测试题目验证工具

用于验证 diagnostic_questions.json 文件的格式和内容是否正确
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

def validate_test_info(test_info: Dict[str, Any]) -> List[str]:
    """验证测试基本信息"""
    errors = []
    required_fields = ['title', 'description', 'version']
    
    for field in required_fields:
        if field not in test_info:
            errors.append(f"❌ test_info 缺少必需字段: {field}")
    
    return errors

def validate_question(question: Dict[str, Any], section_id: str, q_index: int) -> List[str]:
    """验证单个题目"""
    errors = []
    
    # 基本字段验证
    if 'id' not in question:
        errors.append(f"❌ {section_id} 第 {q_index + 1} 题缺少 id 字段")
    
    if 'question' not in question:
        errors.append(f"❌ {section_id} 第 {q_index + 1} 题缺少 question 字段")
    
    if 'type' not in question:
        errors.append(f"❌ {section_id} 第 {q_index + 1} 题缺少 type 字段")
        return errors
    
    # 根据题目类型验证特定字段
    q_type = question['type']
    q_id = question.get('id', f'question_{q_index}')
    
    if q_type == 'multiple_choice':
        if 'options' not in question:
            errors.append(f"❌ {section_id}/{q_id}: 选择题缺少 options 字段")
        elif not isinstance(question['options'], list):
            errors.append(f"❌ {section_id}/{q_id}: options 必须是数组")
        elif len(question['options']) < 2:
            errors.append(f"⚠️  {section_id}/{q_id}: 选择题至少需要2个选项")
    
    elif q_type == 'short_answer':
        if 'placeholder' not in question:
            errors.append(f"⚠️  {section_id}/{q_id}: 简答题建议添加 placeholder 字段")
    
    elif q_type == 'coding':
        if 'template' not in question:
            errors.append(f"⚠️  {section_id}/{q_id}: 编程题建议添加 template 字段")
    
    elif q_type == 'code_analysis':
        if 'code' not in question:
            errors.append(f"❌ {section_id}/{q_id}: 代码分析题缺少 code 字段")
    
    elif q_type == 'single_choice':
        if 'options' not in question:
            errors.append(f"❌ {section_id}/{q_id}: 单选题缺少 options 字段")
        else:
            for opt_idx, opt in enumerate(question['options']):
                if not isinstance(opt, dict):
                    errors.append(f"❌ {section_id}/{q_id}: 选项 {opt_idx + 1} 必须是对象")
                elif 'value' not in opt or 'label' not in opt:
                    errors.append(f"❌ {section_id}/{q_id}: 选项 {opt_idx + 1} 缺少 value 或 label")
    
    elif q_type == 'rating':
        if 'category' not in question:
            errors.append(f"❌ {section_id}/{q_id}: 评级题缺少 category 字段")
    
    else:
        errors.append(f"⚠️  {section_id}/{q_id}: 未知题目类型 '{q_type}'")
    
    return errors

def validate_tools_section(section: Dict[str, Any]) -> List[str]:
    """验证工具熟悉度模块"""
    errors = []
    
    if 'survey' not in section:
        errors.append(f"❌ 工具模块必须包含 survey 字段")
        return errors
    
    survey = section['survey']
    if not isinstance(survey, list):
        errors.append(f"❌ survey 必须是数组")
        return errors
    
    for idx, category in enumerate(survey):
        if 'category' not in category:
            errors.append(f"❌ survey 第 {idx + 1} 项缺少 category 字段")
        
        if 'tools' not in category:
            errors.append(f"❌ survey 第 {idx + 1} 项缺少 tools 字段")
        else:
            tools = category['tools']
            if not isinstance(tools, list):
                errors.append(f"❌ survey 第 {idx + 1} 项的 tools 必须是数组")
            else:
                for tool_idx, tool in enumerate(tools):
                    if 'name' not in tool:
                        errors.append(f"❌ survey 第 {idx + 1} 项工具 {tool_idx + 1} 缺少 name")
                    if 'description' not in tool:
                        errors.append(f"⚠️  survey 第 {idx + 1} 项工具 {tool_idx + 1} 建议添加 description")
    
    return errors

def validate_section(section: Dict[str, Any], idx: int) -> List[str]:
    """验证测试模块"""
    errors = []
    
    # 基本字段验证
    if 'id' not in section:
        errors.append(f"❌ Section {idx + 1} 缺少 id 字段")
        return errors
    
    section_id = section['id']
    
    if 'title' not in section:
        errors.append(f"❌ {section_id} 缺少 title 字段")
    
    # 工具模块特殊处理
    if section_id == 'tools':
        errors.extend(validate_tools_section(section))
    else:
        if 'questions' not in section:
            errors.append(f"❌ {section_id} 缺少 questions 字段")
        else:
            questions = section['questions']
            if not isinstance(questions, list):
                errors.append(f"❌ {section_id} 的 questions 必须是数组")
            else:
                for q_idx, question in enumerate(questions):
                    errors.extend(validate_question(question, section_id, q_idx))
    
    return errors

def validate_diagnostic_questions(file_path: str) -> bool:
    """验证诊断测试题目文件"""
    print(f"🔍 正在验证: {file_path}\n")
    
    # 检查文件是否存在
    if not Path(file_path).exists():
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    # 读取并解析JSON
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON格式错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return False
    
    all_errors = []
    warnings = []
    
    # 验证顶层结构
    if 'test_info' not in data:
        all_errors.append("❌ 缺少 test_info 字段")
    else:
        errors = validate_test_info(data['test_info'])
        all_errors.extend(errors)
    
    if 'sections' not in data:
        all_errors.append("❌ 缺少 sections 字段")
        print("\n".join(all_errors))
        return False
    
    sections = data['sections']
    if not isinstance(sections, list):
        all_errors.append("❌ sections 必须是数组")
        print("\n".join(all_errors))
        return False
    
    # 验证每个section
    section_ids = set()
    for idx, section in enumerate(sections):
        errors = validate_section(section, idx)
        
        # 分离错误和警告
        for error in errors:
            if error.startswith('⚠️'):
                warnings.append(error)
            else:
                all_errors.append(error)
        
        # 检查ID重复
        if 'id' in section:
            if section['id'] in section_ids:
                all_errors.append(f"❌ Section ID '{section['id']}' 重复")
            section_ids.add(section['id'])
    
    # 输出结果
    print("=" * 60)
    
    if all_errors:
        print(f"\n❌ 发现 {len(all_errors)} 个错误:\n")
        for error in all_errors:
            print(error)
    
    if warnings:
        print(f"\n⚠️  发现 {len(warnings)} 个警告:\n")
        for warning in warnings:
            print(warning)
    
    if not all_errors:
        print("✅ 验证通过！题目文件格式正确\n")
        
        # 输出统计信息
        print("=" * 60)
        print(f"📊 统计信息:")
        print(f"  - 测试标题: {data['test_info'].get('title', 'N/A')}")
        print(f"  - 版本: {data['test_info'].get('version', 'N/A')}")
        print(f"  - 测试模块数: {len(sections)}")
        
        total_questions = 0
        for section in sections:
            section_id = section.get('id', 'unknown')
            if 'questions' in section:
                q_count = len(section['questions'])
                total_questions += q_count
                print(f"    • {section.get('title', section_id)}: {q_count} 题")
            elif 'survey' in section:
                s_count = len(section['survey'])
                total_questions += s_count
                print(f"    • {section.get('title', section_id)}: {s_count} 个调查类别")
        
        print(f"  - 总计题目数: {total_questions}")
        print("=" * 60)
        
        if warnings:
            print("\n💡 提示: 虽然有警告，但不影响使用。建议根据警告优化题目质量。")
        
        return True
    else:
        print("\n" + "=" * 60)
        print("❌ 验证失败，请修复上述错误后重试")
        return False

def main():
    """主函数"""
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = 'static/diagnostic_questions.json'
    
    success = validate_diagnostic_questions(file_path)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
