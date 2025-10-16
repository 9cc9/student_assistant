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
            if (!this.diagnosticForm.studentId) return
            
            try {
                const response = await fetch(`/api/learning-path/progress/${this.diagnosticForm.studentId}`)
                if (response.ok) {
                    const data = await response.json()
                    this.studentProgress = data.progress_summary
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
                            _updateTime: Date.now(), // 添加时间戳确保对象引用变化
                            // 确保有路径推荐（如果后端没有返回）
                            path_recommendation: result.path_recommendation || {
                                decision_type: 'keep',
                                channel: 'B',
                                next_node_id: 'model_deployment',
                                reasoning: '基于您的优秀表现，建议继续在B通道学习下一个节点'
                            }
                        }
                        
                        // 更新评估结果
                        this.assessmentResult = newResult
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
            return 'border-gray-200 bg-white hover:border-blue-300'
        },
        
        getNodeIconClass(node, index) {
            // 根据节点状态返回图标样式
            return 'bg-blue-500'
        },
        
        getNodeStatusIcon(node) {
            // 根据节点状态返回状态图标
            return 'fas fa-clock text-gray-400'
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