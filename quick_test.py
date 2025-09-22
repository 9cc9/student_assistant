#!/usr/bin/env python3
"""
AI助教评估系统 - 快速测试
"""

import asyncio
import json
from src.services.assessment_service import AssessmentService

async def quick_test():
    """快速测试评估系统"""
    
    print("🚀 === 快速评估测试 ===")
    
    service = AssessmentService()
    
    # 简单项目数据
    test_data = {
        "idea_text": "开发一个待办事项管理APP，支持任务分类、提醒和进度跟踪功能。使用React Native开发，后端用Node.js，数据库用MongoDB。",
        "project_name": "TodoMaster",
        "technical_stack": ["React Native", "Node.js", "MongoDB"],
        "target_users": "学生和上班族",
        "core_features": ["任务管理", "分类标签", "提醒通知", "进度统计"],
        "ui_images": [],
        "design_tool": "Sketch", 
        "code_repo": "",
        "language": "JavaScript",
        "framework": "React Native",
        "lines_of_code": 800,
        "test_coverage": 60.0,
        "code_snippets": [
            """// App.js - 主应用组件
import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, TouchableOpacity } from 'react-native';
import TaskItem from './components/TaskItem';
import AddTaskModal from './components/AddTaskModal';

export default function App() {
  const [tasks, setTasks] = useState([]);
  const [modalVisible, setModalVisible] = useState(false);

  const addTask = (task) => {
    setTasks([...tasks, { ...task, id: Date.now(), completed: false }]);
    setModalVisible(false);
  };

  const toggleTask = (id) => {
    setTasks(tasks.map(task => 
      task.id === id ? { ...task, completed: !task.completed } : task
    ));
  };

  return (
    <View style={{flex: 1, padding: 20}}>
      <Text style={{fontSize: 24, fontWeight: 'bold', marginBottom: 20}}>
        我的任务
      </Text>
      
      <FlatList
        data={tasks}
        keyExtractor={item => item.id.toString()}
        renderItem={({item}) => (
          <TaskItem task={item} onToggle={toggleTask} />
        )}
      />
      
      <TouchableOpacity
        style={{
          backgroundColor: '#007AFF',
          padding: 15,
          borderRadius: 8,
          alignItems: 'center',
          marginTop: 20
        }}
        onPress={() => setModalVisible(true)}
      >
        <Text style={{color: 'white', fontSize: 16}}>添加任务</Text>
      </TouchableOpacity>
      
      <AddTaskModal
        visible={modalVisible}
        onClose={() => setModalVisible(false)}
        onAdd={addTask}
      />
    </View>
  );
}"""
        ]
    }
    
    print(f"📱 项目: {test_data['project_name']}")
    print(f"💻 技术: {', '.join(test_data['technical_stack'])}")
    print("⏳ 开始评估...")
    
    # 提交评估
    assessment_id = await service.submit_assessment("test_user", test_data)
    print(f"✅ 评估ID: {assessment_id}")
    
    # 等待结果
    for i in range(20):
        await asyncio.sleep(2)
        try:
            result = service.get_assessment_status(assessment_id)
            print(f"🔄 {result['status']}", end="")
            
            if result['status'] == 'completed':
                print("\n")
                print(f"🎯 总分: {result['overall_score']:.1f}/100")
                
                if 'breakdown' in result:
                    b = result['breakdown']
                    print(f"💡 创意: {b['idea']:.1f} | 🎨 UI: {b['ui']:.1f} | 💻 代码: {b['code']:.1f}")
                
                # 保存结果
                with open("quick_test_result.json", "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print("📄 结果已保存到 quick_test_result.json")
                break
            elif result['status'] == 'failed':
                print(f"\n❌ 评估失败")
                break
            else:
                print(".", end="")
                
        except Exception as e:
            print(f" ⚠️ {str(e)}")
    
    print("\n🎯 测试完成!")

if __name__ == "__main__":
    asyncio.run(quick_test())
