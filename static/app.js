const { createApp } = Vue

createApp({
    data() {
        return {
            // 认证相关
            isLoggedIn: false,
            currentStudent: null,
            authToken: null,
            showLoginModal: false,
            showRegisterModal: false,
            loginForm: {
                student_id: '',
                password: ''
            },
            registerForm: {
                student_id: '',
                name: '',
                password: '',
                confirmPassword: '',
                email: ''
            },
            authError: '',
            
            activeTab: 'history', // 默认显示学习记录标签页
            loading: false,
            isDragging: false,
            selectedFiles: [],
            
            // 诊断相关数据
            diagnosticStarted: false,
            diagnosticCompleted: false,
            diagnosticForm: {
                studentId: ''
            },
            studentProfile: null,
            pathRecommendation: null,
            
            // 真实诊断测试数据（从JSON加载）
            diagnosticTest: null,           // 测试题目数据
            diagnosticQuestionsLoaded: false, // 题目加载状态
            currentSection: 0,              // 当前测试模块(0-3)
            studentAnswers: {               // 学生答案收集
                concepts: {},
                coding: {},
                tools: {},
                preferences: {
                    interests: [],
                    goals: []
                }
            },
            testStartTime: null,            // 测试开始时间
            sectionStartTime: null,         // 当前模块开始时间
            evaluationResult: null,         // 评估结果
            
            // 学习路径相关数据
            studentProgress: null,
            currentTask: null,
            learningNodes: [],
            latestRecommendation: null,
            selectedChannel: 'B', // 默认选中B通道
            
            // 作业提交数据
            uploadForm: {
                studentId: '',
                ideaText: ''
            },
            assessmentResult: null,
            
            // 历史记录数据
            historyData: [],
            historyLoading: false,
            historyFilter: {
                studentId: ''
            },
            
            // 诊断历史数据
            diagnosticHistory: [],
            diagnosticHistoryLoading: false
        }
    },
    computed: {
        filteredHistory() {
            let filtered = this.historyData
            if (this.historyFilter.studentId) {
                const studentId = this.historyFilter.studentId.toLowerCase().trim()
                filtered = filtered.filter(record => 
                    record.student_id.toLowerCase().includes(studentId)
                )
            }
            return filtered
        }
    },
    methods: {
        // ================ 诊断测试方法 ================
        
        // 预加载诊断测试题目（从JSON文件）
        async loadDiagnosticQuestions() {
            try {
                const response = await fetch('/static/diagnostic_questions.json')
                if (!response.ok) {
                    throw new Error('Failed to load diagnostic questions')
                }
                const data = await response.json()
                
                // 转换为API格式
                this.diagnosticTest = {
                    test_info: data.test_info,
                    sections: this.transformDiagnosticSections(data.sections)
                }
                this.diagnosticQuestionsLoaded = true
                console.log('✅ 成功从JSON加载诊断测试题目')
            } catch (error) {
                console.error('❌ 加载诊断题目失败:', error)
                this.diagnosticQuestionsLoaded = false
                // 不阻塞系统，用户点击开始测试时再尝试从API加载
            }
        },
        
        transformDiagnosticSections(sectionsData) {
            return sectionsData.map(section => {
                // 处理工具熟悉度模块
                if (section.id === 'tools' && section.survey) {
                    return {
                        id: section.id,
                        title: section.title,
                        description: section.description,
                        time_limit: section.time_limit,
                        questions: section.survey.map((surveyItem, index) => ({
                            id: `tools_${surveyItem.category}`,
                            question: `请评估您对以下${surveyItem.category}工具的熟悉程度`,
                            type: 'rating',
                            category: {
                                name: surveyItem.category,
                                tools: surveyItem.tools
                            }
                        }))
                    }
                }
                // 其他模块直接使用questions字段
                return {
                    id: section.id,
                    title: section.title,
                    description: section.description || '',
                    time_limit: section.time_limit,
                    questions: section.questions || []
                }
            })
        },
        
        async startDiagnostic() {
            if (!this.diagnosticForm.studentId.trim()) {
                alert('请输入学生ID')
                return
            }
            
            // 如果题目已从JSON加载，直接使用
            if (this.diagnosticQuestionsLoaded && this.diagnosticTest) {
                this.diagnosticStarted = true
                this.testStartTime = new Date()
                this.currentSection = 0
                this.sectionStartTime = new Date()
                console.log('使用预加载的诊断测试题目')
                return
            }
            
            // 否则，尝试从API加载（备用方案）
            this.loading = true
            try {
                const response = await fetch('/api/diagnostic/test')
                if (response.ok) {
                    this.diagnosticTest = await response.json()
                this.diagnosticStarted = true
                    this.testStartTime = new Date()
                    this.currentSection = 0
                    this.sectionStartTime = new Date()
                    console.log('从API加载诊断测试题目成功')
                } else {
                    throw new Error('获取测试题目失败')
                }
            } catch (error) {
                alert('启动诊断测试失败: ' + error.message + '\n请确保题目文件已正确配置')
                this.diagnosticStarted = false
            } finally {
                this.loading = false
            }
        },
        
        // 进入下一个测试模块
        nextSection() {
            if (this.currentSection < this.diagnosticTest.sections.length - 1) {
                this.currentSection++
                this.sectionStartTime = new Date()
                window.scrollTo({ top: 0, behavior: 'smooth' })
            } else {
                // 最后一个模块，准备提交
                if (confirm('确认提交诊断测试？提交后将生成您的学习画像。')) {
                    this.submitDiagnostic()
                }
            }
        },
        
        // 返回上一个测试模块
        previousSection() {
            if (this.currentSection > 0) {
                this.currentSection--
                this.sectionStartTime = new Date()
                window.scrollTo({ top: 0, behavior: 'smooth' })
            }
        },
        
        // 提交诊断测试
        async submitDiagnostic() {
            this.loading = true
            try {
                // 调用真实API提交测试答案
                const response = await fetch('/api/diagnostic/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        student_id: this.diagnosticForm.studentId,
                        responses: this.studentAnswers
                    })
                })
                
                if (response.ok) {
                    const result = await response.json()
                    this.evaluationResult = result.evaluation_results
                    this.studentProfile = result.student_profile
                    this.pathRecommendation = result.recommendations
                    this.diagnosticCompleted = true
                    this.diagnosticStarted = false
                    
                    console.log('诊断评估完成:', result)
                    
                    // 自动创建学习路径
                    await this.createLearningPathFromDiagnostic(result)
                } else {
                    const error = await response.json()
                    throw new Error(error.detail || '提交失败')
                }
            } catch (error) {
                alert('提交诊断测试失败: ' + error.message)
            } finally {
                this.loading = false
            }
        },
        
        // 从诊断结果创建学习路径
        async createLearningPathFromDiagnostic(diagnosticResult) {
            try {
                const response = await fetch('/api/learning-path/diagnostic', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        student_id: this.diagnosticForm.studentId,
                        diagnostic_results: {
                            concept_score: diagnosticResult.evaluation_results.concept_score,
                            coding_score: diagnosticResult.evaluation_results.coding_score,
                            tool_familiarity: diagnosticResult.evaluation_results.tool_familiarity,
                            interests: diagnosticResult.student_profile.interests,
                            learning_style_preference: diagnosticResult.student_profile.learning_style,
                            time_budget_hours_per_week: diagnosticResult.student_profile.time_budget_hours_per_week,
                            goals: diagnosticResult.student_profile.goals
                        }
                    })
                })
                
                if (response.ok) {
                    const pathData = await response.json()
                    console.log('学习路径创建成功:', pathData)
                    // 刷新学习路径显示
                    await this.loadStudentProgress()
                } else {
                    console.error('创建学习路径失败:', response.status, await response.text())
                }
            } catch (error) {
                console.error('创建学习路径失败:', error)
            }
        },
        
        resetDiagnostic() {
            this.diagnosticStarted = false
            this.diagnosticCompleted = false
            this.studentProfile = null
            this.pathRecommendation = null
            this.diagnosticForm.studentId = ''
            this.diagnosticTest = null
            this.currentSection = 0
            this.studentAnswers = {
                concepts: {},
                coding: {},
                tools: {},
                preferences: {
                    interests: [],
                    goals: []
                }
            }
            this.testStartTime = null
            this.sectionStartTime = null
            this.evaluationResult = null
        },
        
        // ================ 学习路径方法 ================
        async loadStudentProgress() {
            // 获取学生ID，优先使用当前登录用户，否则使用诊断表单中的ID
            const studentId = this.currentStudent?.student_id || this.diagnosticForm.studentId
            if (!studentId) return
            
            try {
                const response = await fetch(`/api/learning-path/progress/${studentId}`)
                if (response.ok) {
                    const data = await response.json()
                    this.studentProgress = {
                        ...data.progress_summary,
                        current_node_id: data.current_status.current_node_id,
                        current_channel: data.current_status.current_channel
                    }
                    this.currentTask = data.current_task
                    await this.loadLearningPath()
                }
            } catch (error) {
                console.error('加载学生进度失败:', error)
            }
        },
        
        async loadLearningPath() {
            try {
                const response = await fetch('/api/learning-path/path/info')
                if (response.ok) {
                    const data = await response.json()
                    this.learningNodes = data.nodes
                }
            } catch (error) {
                console.error('加载学习路径失败:', error)
            }
        },
        
        viewLearningPath() {
            this.activeTab = 'learning-path'
            this.loadStudentProgress()
        },
        
        async acceptPathRecommendation() {
            // 这里实现接受路径推荐的逻辑
            alert('路径推荐已应用到您的学习计划中！')
            this.viewLearningPath()
        },
        
        // 开始当前任务 - 跳转到作业提交页面
        startCurrentTask() {
            if (!this.currentTask) return
            
            // 切换到作业提交页面
            this.activeTab = 'upload'
            
            // 预填充任务相关信息
            this.uploadForm.ideaText = `我正在完成【${this.currentTask.node_name}】的${this.currentTask.channel}通道任务：\n\n${this.currentTask.task_description}\n\n任务要求：\n${this.currentTask.requirements.map(req => `• ${req}`).join('\n')}\n\n提交要求：\n${this.currentTask.deliverables.map(del => `• ${del}`).join('\n')}`
            
            // 滚动到页面顶部
            window.scrollTo({ top: 0, behavior: 'smooth' })
        },
        
        // 切换当前任务的通道难度
        async switchCurrentTaskChannel(channel) {
            if (!this.currentTask || !this.studentProgress) return
            
            // 如果已经是当前通道，不需要切换
            if (this.currentTask.channel === channel) return
            
            // 获取学生ID，优先使用当前登录用户，否则使用诊断表单中的ID
            const studentId = this.currentStudent?.student_id || this.diagnosticForm.studentId
            if (!studentId) {
                this.showErrorMessage('请先登录或完成诊断测试')
                return
            }
            
            try {
                // 调用后端API切换通道
                const response = await fetch('/api/learning-path/channel/switch', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        student_id: studentId,
                        node_id: this.studentProgress.current_node_id,
                        channel: channel
                    })
                })
                
                if (response.ok) {
                    const result = await response.json()
                    console.log('当前任务通道切换成功:', result)
                    
                    // 更新当前任务信息
                    if (result.current_task) {
                        this.currentTask = result.current_task
                    }
                    
                    // 重新加载学习进度以保持数据同步
                    await this.loadStudentProgress()
                    
                    // 显示成功提示
                    this.showSuccessMessage(`已切换到${channel}通道！`)
                } else {
                    const error = await response.json()
                    this.showErrorMessage('切换通道失败: ' + (error.detail || '未知错误'))
                }
            } catch (error) {
                console.error('切换当前任务通道失败:', error)
                this.showErrorMessage('切换通道失败: ' + error.message)
            }
        },
        
        // 显示成功消息
        showSuccessMessage(message) {
            // 创建临时提示元素
            const toast = document.createElement('div')
            toast.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-all duration-300'
            toast.textContent = message
            document.body.appendChild(toast)
            
            // 3秒后自动移除
            setTimeout(() => {
                toast.style.opacity = '0'
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast)
                    }
                }, 300)
            }, 3000)
        },
        
        // 显示错误消息
        showErrorMessage(message) {
            // 创建临时提示元素
            const toast = document.createElement('div')
            toast.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-all duration-300'
            toast.textContent = message
            document.body.appendChild(toast)
            
            // 5秒后自动移除
            setTimeout(() => {
                toast.style.opacity = '0'
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast)
                    }
                }, 300)
            }, 5000)
        },
        
        // 更新学习路径进度
        async updateLearningProgress(assessmentResult) {
            if (!this.studentProgress || !this.studentProgress.current_node_id) {
                console.warn('无法更新学习进度：缺少当前节点信息')
                return
            }
            
            try {
                // 获取学生ID
                const studentId = this.currentStudent?.student_id || this.diagnosticForm.studentId
                if (!studentId) {
                    console.warn('无法更新学习进度：缺少学生ID')
                    return
                }
                
                // 调用学习路径更新API
                const response = await fetch('/api/learning-path/progress/update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        student_id: studentId,
                        node_id: this.studentProgress.current_node_id,
                        status: 'completed',
                        assessment_result: {
                            overall_score: assessmentResult.overall_score || 0,
                            detailed_scores: assessmentResult.detailed_scores || {},
                            feedback: assessmentResult.feedback || ''
                        }
                    })
                })
                
                if (response.ok) {
                    const result = await response.json()
                    console.log('学习进度更新成功:', result)
                    
                    // 重新加载学习进度以获取最新的节点信息
                    await this.loadStudentProgress()
                    
                    // 检查是否有路径推荐
                    if (result.path_recommendation) {
                        // 将推荐信息保存到评估结果中
                        if (this.assessmentResult) {
                            this.assessmentResult.path_recommendation = result.path_recommendation
                        }
                        
                        // 应用路径推荐（但不自动切换，让用户选择）
                        console.log('收到路径推荐:', result.path_recommendation)
                    }
                    
                    // 显示成功提示
                    this.showSuccessMessage('恭喜！您已完成当前学习节点，已解锁下一个节点！')
                } else {
                    const error = await response.json()
                    console.error('学习进度更新失败:', error)
                    this.showErrorMessage('学习进度更新失败: ' + (error.detail || '未知错误'))
                }
            } catch (error) {
                console.error('更新学习进度异常:', error)
                this.showErrorMessage('更新学习进度失败: ' + error.message)
            }
        },
        
        // 应用路径推荐
        async applyPathRecommendation(recommendation) {
            try {
                console.log('收到路径推荐:', recommendation)
                
                const { recommended_channel, next_node_id, decision_type, reasoning } = recommendation
                
                // 如果推荐了不同的通道，自动切换
                if (recommended_channel && this.studentProgress && this.studentProgress.current_channel !== recommended_channel) {
                    console.log(`系统推荐切换到${recommended_channel}通道`)
                    
                    // 调用通道切换API
                    const studentId = this.currentStudent?.student_id || this.diagnosticForm.studentId
                    const response = await fetch('/api/learning-path/channel/switch', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            student_id: studentId,
                            node_id: this.studentProgress.current_node_id,
                            channel: recommended_channel
                        })
                    })
                    
                    if (response.ok) {
                        const result = await response.json()
                        console.log('通道切换成功:', result)
                        
                        // 重新加载学习进度
                        await this.loadStudentProgress()
                        
                        // 显示推荐信息
                        this.showRecommendationMessage(recommendation)
                    } else {
                        console.warn('通道切换失败，但推荐信息已显示')
                        this.showRecommendationMessage(recommendation)
                    }
                } else {
                    // 直接显示推荐信息
                    this.showRecommendationMessage(recommendation)
                }
            } catch (error) {
                console.error('应用路径推荐失败:', error)
                this.showErrorMessage('应用学习推荐失败: ' + error.message)
            }
        },
        
        // 显示推荐信息
        showRecommendationMessage(recommendation) {
            const { recommended_channel, decision_type, reasoning } = recommendation
            
            // 创建推荐信息弹窗
            const modal = document.createElement('div')
            modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50'
            modal.innerHTML = `
                <div class="bg-white rounded-lg p-6 max-w-md mx-4">
                    <div class="flex items-center mb-4">
                        <i class="fas fa-lightbulb text-yellow-500 text-2xl mr-3"></i>
                        <h3 class="text-xl font-semibold text-gray-800">学习路径推荐</h3>
                    </div>
                    <div class="mb-4">
                        <p class="text-gray-700 mb-2"><strong>推荐通道：</strong>${recommended_channel}通道</p>
                        <p class="text-gray-700 mb-2"><strong>推荐类型：</strong>${this.getDecisionTypeText(decision_type)}</p>
                        <p class="text-gray-600 text-sm">${reasoning}</p>
                    </div>
                    <div class="flex justify-end">
                        <button onclick="this.closest('.fixed').remove()" 
                                class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition">
                            知道了
                        </button>
                    </div>
                </div>
            `
            
            document.body.appendChild(modal)
            
            // 5秒后自动关闭
            setTimeout(() => {
                if (modal.parentNode) {
                    modal.remove()
                }
            }, 10000)
        },
        
        // 获取决策类型文本
        getDecisionTypeText(decisionType) {
            const typeMap = {
                'keep': '保持当前通道',
                'upgrade': '升级到更高难度',
                'downgrade': '降级到基础难度',
                'downgrade_with_scaffold': '降级并提供辅导'
            }
            return typeMap[decisionType] || decisionType
        },
        
        // 获取决策类型显示文本（用于HTML显示）
        getDecisionText(decisionType) {
            return this.getDecisionTypeText(decisionType)
        },
        
        // 获取决策类型样式类
        getDecisionClass(decisionType) {
            const classMap = {
                'keep': 'text-blue-600 font-medium',
                'upgrade': 'text-green-600 font-medium',
                'downgrade': 'text-orange-600 font-medium',
                'downgrade_with_scaffold': 'text-red-600 font-medium'
            }
            return classMap[decisionType] || 'text-gray-600 font-medium'
        },
        
        // 获取通道样式类
        getChannelClass(channel) {
            const classMap = {
                'A': 'text-green-600 font-medium',
                'B': 'text-blue-600 font-medium',
                'C': 'text-purple-600 font-medium'
            }
            return classMap[channel] || 'text-gray-600 font-medium'
        },
        
        // 获取节点名称
        getNodeName(nodeId) {
            const nodeNames = {
                'api_calling': 'API调用',
                'model_deployment': '模型部署',
                'no_code_ai': '零代码AI',
                'rag_system': 'RAG系统',
                'ui_design': 'UI设计',
                'frontend_dev': '前端开发',
                'backend_dev': '后端开发'
            }
            return nodeNames[nodeId] || nodeId
        },
        
        // 接受路径推荐
        async acceptPathRecommendation() {
            if (!this.assessmentResult.path_recommendation) return
            
            try {
                const recommendation = this.assessmentResult.path_recommendation
                await this.applyPathRecommendation(recommendation)
                
                // 显示成功提示
                this.showSuccessMessage('已接受路径推荐，学习路径已更新！')
                
                // 切换到学习路径标签页
                this.viewLearningPath()
            } catch (error) {
                console.error('接受路径推荐失败:', error)
                this.showErrorMessage('接受路径推荐失败: ' + error.message)
            }
        },
        
        // ================ 作业提交方法 ================
        async submitAssignment() {
            if (!this.uploadForm.studentId || !this.uploadForm.ideaText || this.selectedFiles.length === 0) {
                alert('请填写所有必填信息并选择文件')
                return
            }

            this.loading = true
            try {
                const formData = new FormData()
                formData.append('student_id', this.uploadForm.studentId)
                formData.append('idea_text', this.uploadForm.ideaText)
                
                this.selectedFiles.forEach(file => {
                    formData.append('files', file)
                })

                const response = await fetch('/api/upload/files', {
                    method: 'POST',
                    body: formData
                })

                if (response.ok) {
                    const result = await response.json()
                    
                    // 设置初始评估结果（显示处理中状态）
                    this.assessmentResult = {
                        assessment_id: result.assessment_id,
                        status: 'processing',
                        message: result.message,
                        submission_id: result.submission_id,
                        project_path: result.project_path
                    }
                    
                    // 切换到学习记录标签页显示结果
                    this.activeTab = 'history'
                    this.scrollToResult()
                    
                    // 延迟 500ms 开始查询，确保初始状态已渲染
                    setTimeout(async () => {
                        await this.checkAssessmentWithPath(result.assessment_id)
                    }, 500)
                } else {
                    const error = await response.json()
                    alert('提交失败: ' + (error.detail || '未知错误'))
                }
            } catch (error) {
                alert('提交失败: ' + error.message)
            } finally {
                this.loading = false
            }
        },
        
        async checkAssessmentWithPath(assessmentId, maxRetries = 20) {
            try {
                const response = await fetch(`/api/assessment/${assessmentId}`)
                if (response.ok) {
                    const result = await response.json()
                    
                    if (result.status === 'completed') {
                        // 评估完成，创建全新对象以触发响应式更新
                        const newResult = {
                            ...result,
                            _updateTime: Date.now() // 添加时间戳确保对象引用变化
                        }
                        
                        // 更新评估结果
                        this.assessmentResult = newResult
                        
                        // 更新学习路径进度
                        await this.updateLearningProgress(result)
                    } else if ((result.status === 'processing' || result.status === 'in_progress') && maxRetries > 0) {
                        // 仍在处理中，继续轮询
                        setTimeout(() => {
                            this.checkAssessmentWithPath(assessmentId, maxRetries - 1)
                        }, 2000)
                    } else if (result.status === 'failed') {
                        // 评估失败
                        this.assessmentResult = { ...result }
                        alert('评估失败: ' + (result.error_message || '未知错误'))
                    } else if (maxRetries === 0) {
                        alert('评估处理时间较长，请稍后手动刷新页面查看结果')
                    }
                }
            } catch (error) {
                console.error('检查评估状态异常:', error)
            }
        },
        
        // ================ 历史记录方法 ================
        async loadHistory() {
            this.historyLoading = true
            try {
                let url = '/api/assessment/history'
                const params = new URLSearchParams()
                
                if (this.historyFilter.studentId.trim()) {
                    params.append('student_id', this.historyFilter.studentId.trim())
                }
                
                if (params.toString()) {
                    url += '?' + params.toString()
                }
                
                const response = await fetch(url)
                if (response.ok) {
                    const data = await response.json()
                    this.historyData = data.assessments || []
                }
            } catch (error) {
                console.error('加载历史记录失败:', error)
            } finally {
                this.historyLoading = false
            }
        },
        
        viewHistoryDetail(record) {
            // 查看历史记录详情
            this.assessmentResult = record
            this.activeTab = 'history'  // 确保切换到学习记录标签页
            this.scrollToResult()
        },
        
        // ================ 工具方法 ================
        handleFileSelect(event) {
            this.selectedFiles = Array.from(event.target.files)
        },
        
        handleFileDrop(event) {
            this.isDragging = false
            this.selectedFiles = Array.from(event.dataTransfer.files)
        },
        
        clearFiles() {
            this.selectedFiles = []
            if (this.$refs.fileInput) {
                this.$refs.fileInput.value = ''
            }
        },
        
        formatFileSize(bytes) {
            if (bytes === 0) return '0 B'
            const k = 1024
            const sizes = ['B', 'KB', 'MB', 'GB']
            const i = Math.floor(Math.log(bytes) / Math.log(k))
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
        },
        
        resetForm() {
            this.assessmentResult = null
            this.selectedFiles = []
            this.uploadForm = { studentId: '', ideaText: '' }
            if (this.$refs.fileInput) {
                this.$refs.fileInput.value = ''
            }
            window.scrollTo({ top: 0, behavior: 'smooth' })
        },
        
        scrollToResult() {
            this.$nextTick(() => {
                const element = document.querySelector('.result-card')
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth' })
                }
            })
        },
        
        // ================ 样式方法 ================
        getStyleText(style) {
            const styleMap = {
                'examples_first': '示例优先学习',
                'theory_first': '理论优先学习',
                'hands_on': '动手实践学习',
                'visual': '可视化学习'
            }
            return styleMap[style] || style
        },
        
        getChannelClass(channel) {
            const classMap = {
                'A': 'bg-green-100 text-green-800 px-2 py-1 rounded text-sm',
                'B': 'bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm',
                'C': 'bg-purple-100 text-purple-800 px-2 py-1 rounded text-sm'
            }
            return classMap[channel] || 'bg-gray-100 text-gray-800 px-2 py-1 rounded text-sm'
        },
        
        getDecisionClass(decision) {
            const classMap = {
                'upgrade': 'bg-green-100 text-green-800 px-2 py-1 rounded text-sm',
                'keep': 'bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm', 
                'downgrade_with_scaffold': 'bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-sm'
            }
            return classMap[decision] || 'bg-gray-100 text-gray-800 px-2 py-1 rounded text-sm'
        },
        
        getDecisionText(decision) {
            const textMap = {
                'upgrade': '升级通道',
                'keep': '保持当前',
                'downgrade_with_scaffold': '降级辅导'
            }
            return textMap[decision] || decision
        },
        
        getNodeClass(node, index) {
            // 根据节点状态返回样式类
            if (!this.studentProgress) {
                return 'border-gray-200 bg-gray-50 hover:border-gray-300'
            }
            
            const nodeId = node.id
            const completedNodes = this.studentProgress.completed_nodes || []
            const currentNodeId = this.studentProgress.current_node_id
            
            // 已完成的节点 - 绿色边框
            if (completedNodes.includes(nodeId)) {
                return 'border-green-300 bg-green-50 hover:border-green-400'
            }
            
            // 当前正在学习的节点 - 蓝色边框
            if (nodeId === currentNodeId) {
                return 'border-blue-300 bg-blue-50 hover:border-blue-400'
            }
            
            // 未解锁的节点 - 灰色边框
            return 'border-gray-200 bg-gray-50 hover:border-gray-300'
        },
        
        getNodeIconClass(node, index) {
            // 根据节点状态返回图标样式
            if (!this.studentProgress) {
                return 'bg-gray-400'
            }
            
            const nodeId = node.id
            const completedNodes = this.studentProgress.completed_nodes || []
            const currentNodeId = this.studentProgress.current_node_id
            
            // 已完成的节点 - 绿色
            if (completedNodes.includes(nodeId)) {
                return 'bg-green-500'
            }
            
            // 当前正在学习的节点 - 蓝色
            if (nodeId === currentNodeId) {
                return 'bg-blue-500'
            }
            
            // 未解锁的节点 - 灰色
            return 'bg-gray-400'
        },
        
        getNodeStatusIcon(node) {
            // 根据节点状态返回状态图标
            if (!this.studentProgress) {
                return 'fas fa-lock text-gray-400'
            }
            
            const nodeId = node.id
            const completedNodes = this.studentProgress.completed_nodes || []
            const currentNodeId = this.studentProgress.current_node_id
            
            // 已完成的节点
            if (completedNodes.includes(nodeId)) {
                return 'fas fa-check-circle text-green-500'
            }
            
            // 当前正在学习的节点
            if (nodeId === currentNodeId) {
                return 'fas fa-play-circle text-blue-500'
            }
            
            // 未解锁的节点
            return 'fas fa-lock text-gray-400'
        },
        
        getEstimatedHours(node) {
            // 获取节点预估时间
            return node.estimated_hours?.B || 8
        },
        
        getNodeName(nodeId) {
            const nodeNames = {
                'api_calling': 'API调用',
                'model_deployment': '模型部署', 
                'no_code_ai': '零代码配置AI应用',
                'rag_system': 'RAG系统',
                'ui_design': 'UI设计',
                'frontend_dev': '前端开发',
                'backend_dev': '后端开发'
            }
            return nodeNames[nodeId] || nodeId
        },
        
        // 获取通道任务信息
        getChannelTask(node, channel) {
            if (!node.channels || !node.channels[channel]) {
                return { task: '任务信息不可用' }
            }
            return node.channels[channel]
        },
        
        // 获取通道预估时间
        getChannelHours(node, channel) {
            if (!node.channels || !node.channels[channel]) {
                return 0
            }
            return node.channels[channel].estimated_hours || 0
        },
        
        // 获取通道难度
        getChannelDifficulty(node, channel) {
            if (!node.channels || !node.channels[channel]) {
                return 0
            }
            return node.channels[channel].difficulty || 0
        },
        
        // 判断是否为当前节点
        isCurrentNode(node) {
            const isCurrent = this.studentProgress && this.studentProgress.current_node_id === node.id
            console.log(`🔍 isCurrentNode(${node.id}):`, isCurrent, 'current_node_id:', this.studentProgress?.current_node_id)
            return isCurrent
        },
        
        // 判断是否为已完成的节点
        isCompletedNode(node) {
            const isCompleted = this.studentProgress && this.studentProgress.completed_nodes && this.studentProgress.completed_nodes.includes(node.id)
            console.log(`🔍 isCompletedNode(${node.id}):`, isCompleted, 'completed_nodes:', this.studentProgress?.completed_nodes)
            return isCompleted
        },
        
        // 获取当前通道
        getCurrentChannel(node) {
            if (!this.studentProgress || this.studentProgress.current_node_id !== node.id) {
                return null
            }
            return this.studentProgress.current_channel
        },
        
        // 获取已完成的通道
        getCompletedChannel(node) {
            if (!this.studentProgress || !this.studentProgress.completed_nodes || !this.studentProgress.completed_nodes.includes(node.id)) {
                console.log(`🔍 getCompletedChannel(${node.id}): null (node not completed)`)
                return null
            }
            
            // 从学生进度中获取该节点完成的通道信息
            const completedChannel = this.studentProgress.completed_channels?.[node.id] || 'B'
            console.log(`🔍 getCompletedChannel(${node.id}):`, completedChannel, 'completed_channels:', this.studentProgress.completed_channels)
            return completedChannel
        },
        
        // 获取通道按钮样式
        getChannelButtonClass(channel) {
            const classMap = {
                'A': 'bg-green-500 text-white',
                'B': 'bg-blue-500 text-white',
                'C': 'bg-purple-500 text-white'
            }
            return classMap[channel] || 'bg-gray-500 text-white'
        },
        
        // 切换通道
        async switchToChannel(nodeId, channel) {
            // 获取学生ID，优先使用当前登录用户，否则使用诊断表单中的ID
            const studentId = this.currentStudent?.student_id || this.diagnosticForm.studentId
            if (!studentId) {
                this.showErrorMessage('请先登录或完成诊断测试')
                return
            }
            
            try {
                // 调用后端API切换通道
                const response = await fetch('/api/learning-path/channel/switch', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        student_id: studentId,
                        node_id: nodeId,
                        channel: channel
                    })
                })
                
                if (response.ok) {
                    const result = await response.json()
                    console.log('通道切换成功:', result)
                    
                    // 重新加载学习进度
                    await this.loadStudentProgress()
                    
                    alert(`已切换到${channel}通道！`)
                } else {
                    const error = await response.json()
                    alert('切换通道失败: ' + (error.detail || '未知错误'))
                }
            } catch (error) {
                console.error('切换通道失败:', error)
                alert('切换通道失败: ' + error.message)
            }
        },
        
        getStatusText(status) {
            const statusMap = {
                'completed': '已完成',
                'in_progress': '进行中',
                'queued': '排队中',
                'failed': '失败'
            }
            return statusMap[status] || status
        },
        
        getStatusBadgeClass(status) {
            const classMap = {
                'completed': 'bg-green-100 text-green-800',
                'in_progress': 'bg-orange-100 text-orange-800',
                'queued': 'bg-blue-100 text-blue-800',
                'failed': 'bg-red-100 text-red-800'
            }
            return classMap[status] || 'bg-gray-100 text-gray-800'
        },
        
        formatDateTime(dateTimeStr) {
            if (!dateTimeStr) return ''
            try {
                const date = new Date(dateTimeStr)
                return date.toLocaleString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                })
            } catch {
                return dateTimeStr
            }
        },
        
        // ============ 认证相关方法 ============
        
        async login() {
            this.authError = ''
            this.loading = true
            
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        student_id: this.loginForm.student_id,
                        password: this.loginForm.password
                    })
                })
                
                const data = await response.json()
                
                if (!response.ok) {
                    throw new Error(data.detail || '登录失败')
                }
                
                if (data.success) {
                    // 保存Token和用户信息
                    this.authToken = data.token
                    this.currentStudent = data.student
                    this.isLoggedIn = true
                    
                    // 保存到localStorage
                    localStorage.setItem('authToken', data.token)
                    localStorage.setItem('currentStudent', JSON.stringify(data.student))
                    
                    // 自动填充学生ID
                    this.diagnosticForm.studentId = data.student.student_id
                    this.uploadForm.studentId = data.student.student_id
                    this.historyFilter.studentId = data.student.student_id
                    
                    // 关闭模态框
                    this.showLoginModal = false
                    
                    // 切换到个人中心标签页
                    this.activeTab = 'profile'
                    
                    // 加载学生数据
                    await this.loadStudentData()
                    
                    alert('登录成功！')
                }
            } catch (error) {
                console.error('登录失败:', error)
                this.authError = error.message || '登录失败，请检查学生ID和密码'
            } finally {
                this.loading = false
            }
        },
        
        async register() {
            this.authError = ''
            
            // 验证密码
            if (this.registerForm.password !== this.registerForm.confirmPassword) {
                this.authError = '两次输入的密码不一致'
                return
            }
            
            if (this.registerForm.password.length < 6) {
                this.authError = '密码长度至少6位'
                return
            }
            
            this.loading = true
            
            try {
                const response = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        student_id: this.registerForm.student_id,
                        name: this.registerForm.name,
                        password: this.registerForm.password,
                        email: this.registerForm.email || undefined
                    })
                })
                
                const data = await response.json()
                
                if (!response.ok) {
                    throw new Error(data.detail || '注册失败')
                }
                
                if (data.success) {
                    alert('注册成功！请登录')
                    // 切换到登录模态框
                    this.showRegisterModal = false
                    this.showLoginModal = true
                    // 预填充学生ID
                    this.loginForm.student_id = this.registerForm.student_id
                    this.loginForm.password = ''
                    // 重置注册表单
                    this.registerForm = {
                        student_id: '',
                        name: '',
                        password: '',
                        confirmPassword: '',
                        email: ''
                    }
                }
            } catch (error) {
                console.error('注册失败:', error)
                this.authError = error.message || '注册失败，请重试'
            } finally {
                this.loading = false
            }
        },
        
        async logout() {
            try {
                if (this.authToken) {
                    await fetch('/api/auth/logout', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${this.authToken}`
                        }
                    })
                }
            } catch (error) {
                console.error('登出请求失败:', error)
            } finally {
                // 清除本地数据
                this.isLoggedIn = false
                this.currentStudent = null
                this.authToken = null
                localStorage.removeItem('authToken')
                localStorage.removeItem('currentStudent')
                
                // 重置表单
                this.diagnosticForm.studentId = ''
                this.uploadForm.studentId = ''
                this.historyFilter.studentId = ''
                
                alert('已登出')
            }
        },
        
        async checkLoginStatus() {
            // 检查localStorage中的登录状态
            const token = localStorage.getItem('authToken')
            const studentData = localStorage.getItem('currentStudent')
            
            if (token && studentData) {
                try {
                    // 验证Token是否有效
                    const response = await fetch('/api/auth/verify', {
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    })
                    
                    const data = await response.json()
                    
                    if (data.valid) {
                        this.authToken = token
                        this.currentStudent = JSON.parse(studentData)
                        this.isLoggedIn = true
                        
                        // 切换到个人中心标签页
                        this.activeTab = 'profile'
                        
                        // 自动填充学生ID
                        this.diagnosticForm.studentId = this.currentStudent.student_id
                        this.uploadForm.studentId = this.currentStudent.student_id
                        this.historyFilter.studentId = this.currentStudent.student_id
                        
                        // 加载学生数据
                        await this.loadStudentData()
                    } else {
                        // Token无效，清除
                        localStorage.removeItem('authToken')
                        localStorage.removeItem('currentStudent')
                    }
                } catch (error) {
                    console.error('验证登录状态失败:', error)
                    localStorage.removeItem('authToken')
                    localStorage.removeItem('currentStudent')
                }
            }
        },
        
        async loadStudentData() {
            if (!this.authToken) return
            
            try {
                // 加载诊断历史
                this.diagnosticHistoryLoading = true
                const diagnosticResponse = await fetch('/api/student/diagnostic-history?limit=5', {
                    headers: {
                        'Authorization': `Bearer ${this.authToken}`
                    }
                })
                
                if (diagnosticResponse.ok) {
                    const diagnosticData = await diagnosticResponse.json()
                    this.diagnosticHistory = diagnosticData.history || []
                    console.log('诊断历史已加载:', diagnosticData.count, '条记录')
                }
                this.diagnosticHistoryLoading = false
                
                // 加载学习历史
                const learningResponse = await fetch('/api/student/learning-history?limit=20', {
                    headers: {
                        'Authorization': `Bearer ${this.authToken}`
                    }
                })
                
                if (learningResponse.ok) {
                    const learningData = await learningResponse.json()
                    this.historyData = learningData.records || []
                    console.log('学习历史已加载:', learningData.count, '条记录')
                }
            } catch (error) {
                console.error('加载学生数据失败:', error)
                this.diagnosticHistoryLoading = false
            }
        },
        
        getAuthHeaders() {
            if (this.authToken) {
                return {
                    'Authorization': `Bearer ${this.authToken}`,
                    'Content-Type': 'application/json'
                }
            }
            return {
                'Content-Type': 'application/json'
            }
        }
    },
    watch: {
        // 监听标签页切换
        activeTab(newTab) {
            if (newTab === 'history' && this.historyData.length === 0) {
                this.loadHistory()
            } else if (newTab === 'learning-path' && this.diagnosticForm.studentId) {
                this.loadStudentProgress()
            } else if (newTab === 'profile' && this.isLoggedIn) {
                // 切换到个人中心时重新加载诊断历史
                this.loadStudentData()
            }
        }
    },
    async mounted() {
        
        // 检查登录状态
        await this.checkLoginStatus()
        
        // 预加载诊断测试题目
        await this.loadDiagnosticQuestions()
    }
}).mount('#app')