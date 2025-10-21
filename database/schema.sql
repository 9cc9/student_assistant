-- 学习助手系统数据库表结构
-- 创建时间: 2024-01-15
-- 版本: 1.0

-- 设置字符集和排序规则
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 1. 学生基础信息表
CREATE TABLE `students` (
    `student_id` VARCHAR(50) NOT NULL COMMENT '学生ID',
    `name` VARCHAR(100) NOT NULL COMMENT '学生姓名',
    `email` VARCHAR(100) NOT NULL COMMENT '邮箱',
    `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号',
    `password_hash` VARCHAR(255) DEFAULT NULL COMMENT '密码哈希',
    `level` ENUM('L0', 'L1', 'L2', 'L3') NOT NULL DEFAULT 'L0' COMMENT '学习水平',
    `learning_style` ENUM('examples_first', 'theory_first', 'hands_on', 'visual') NOT NULL DEFAULT 'examples_first' COMMENT '学习风格',
    `time_budget_hours_per_week` INT NOT NULL DEFAULT 6 COMMENT '每周学习时间预算(小时)',
    `weak_skills` JSON DEFAULT NULL COMMENT '薄弱技能列表',
    `interests` JSON DEFAULT NULL COMMENT '兴趣方向列表',
    `goals` JSON DEFAULT NULL COMMENT '学习目标列表',
    `mastery_scores` JSON DEFAULT NULL COMMENT '各技能掌握度分数',
    `frustration_level` DECIMAL(3,2) NOT NULL DEFAULT 0.00 COMMENT '挫败感水平(0-1)',
    `retry_count` INT NOT NULL DEFAULT 0 COMMENT '总重试次数',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`student_id`),
    UNIQUE KEY `uk_email` (`email`),
    KEY `idx_level` (`level`),
    KEY `idx_created_at` (`created_at`),
    KEY `idx_password_hash` (`password_hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生基础信息表';

-- 2. 学生全局进度表
CREATE TABLE `student_progress` (
    `student_id` VARCHAR(50) NOT NULL COMMENT '学生ID',
    `current_node_id` VARCHAR(100) NOT NULL COMMENT '当前节点ID',
    `current_channel` ENUM('A', 'B', 'C') NOT NULL DEFAULT 'B' COMMENT '当前通道',
    `total_study_hours` DECIMAL(8,2) NOT NULL DEFAULT 0.00 COMMENT '总学习时长(小时)',
    `frustration_level` DECIMAL(3,2) NOT NULL DEFAULT 0.00 COMMENT '当前挫败感水平(0-1)',
    `started_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '开始学习时间',
    `last_activity_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '最后活动时间',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`student_id`),
    KEY `idx_current_node` (`current_node_id`),
    KEY `idx_last_activity` (`last_activity_at`),
    CONSTRAINT `fk_student_progress_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生全局进度表';

-- 3. 学生节点进度详情表
CREATE TABLE `student_progress_nodes` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `student_id` VARCHAR(50) NOT NULL COMMENT '学生ID',
    `node_id` VARCHAR(100) NOT NULL COMMENT '节点ID',
    `status` ENUM('locked', 'available', 'in_progress', 'completed', 'failed') NOT NULL DEFAULT 'locked' COMMENT '节点状态',
    `used_channel` ENUM('A', 'B', 'C') DEFAULT NULL COMMENT '使用的通道',
    `score` DECIMAL(5,2) DEFAULT NULL COMMENT '节点得分(0-100)',
    `attempt_count` INT NOT NULL DEFAULT 0 COMMENT '尝试次数',
    `started_at` TIMESTAMP NULL DEFAULT NULL COMMENT '开始时间',
    `completed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '完成时间',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_student_node` (`student_id`, `node_id`),
    KEY `idx_status` (`status`),
    KEY `idx_completed_at` (`completed_at`),
    CONSTRAINT `fk_progress_nodes_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生节点进度详情表';

-- 4. 诊断记录表
CREATE TABLE `diagnostics` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `student_id` VARCHAR(50) NOT NULL COMMENT '学生ID',
    `diagnostic_id` VARCHAR(100) NOT NULL COMMENT '诊断ID',
    `diagnostic_type` VARCHAR(50) NOT NULL COMMENT '诊断类型',
    `overall_score` DECIMAL(5,2) NOT NULL COMMENT '总体得分(0-100)',
    `concept_score` DECIMAL(5,2) DEFAULT NULL COMMENT '概念理解得分',
    `coding_score` DECIMAL(5,2) DEFAULT NULL COMMENT '编程能力得分',
    `tool_familiarity` DECIMAL(5,2) DEFAULT NULL COMMENT '工具熟悉度得分',
    `skill_scores` JSON DEFAULT NULL COMMENT '各技能详细得分',
    `learning_style_preference` VARCHAR(50) DEFAULT NULL COMMENT '学习风格偏好',
    `time_budget_hours_per_week` INT DEFAULT NULL COMMENT '每周学习时间预算',
    `goals` JSON DEFAULT NULL COMMENT '学习目标',
    `interests` JSON DEFAULT NULL COMMENT '兴趣方向',
    `recommendations` JSON DEFAULT NULL COMMENT '推荐建议',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_diagnostic_id` (`diagnostic_id`),
    KEY `idx_student_id` (`student_id`),
    KEY `idx_created_at` (`created_at`),
    CONSTRAINT `fk_diagnostics_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='诊断记录表';

-- 5. 诊断题目明细表
CREATE TABLE `diagnostic_items` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `diagnostic_id` VARCHAR(100) NOT NULL COMMENT '诊断ID',
    `item_id` VARCHAR(100) NOT NULL COMMENT '题目ID',
    `item_type` VARCHAR(50) NOT NULL COMMENT '题目类型',
    `question` TEXT NOT NULL COMMENT '题目内容',
    `answer` TEXT DEFAULT NULL COMMENT '学生答案',
    `correct_answer` TEXT DEFAULT NULL COMMENT '正确答案',
    `score` DECIMAL(5,2) DEFAULT NULL COMMENT '得分',
    `max_score` DECIMAL(5,2) NOT NULL DEFAULT 100.00 COMMENT '满分',
    `dimension` VARCHAR(100) DEFAULT NULL COMMENT '评价维度',
    `difficulty_level` INT DEFAULT NULL COMMENT '难度等级(1-10)',
    `time_spent_seconds` INT DEFAULT NULL COMMENT '答题用时(秒)',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_diagnostic_id` (`diagnostic_id`),
    KEY `idx_item_type` (`item_type`),
    KEY `idx_dimension` (`dimension`),
    CONSTRAINT `fk_diagnostic_items_diagnostic` FOREIGN KEY (`diagnostic_id`) REFERENCES `diagnostics` (`diagnostic_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='诊断题目明细表';

-- 6. 评分规则表
CREATE TABLE `assessments` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `assessment_id` VARCHAR(100) NOT NULL COMMENT '评分规则ID',
    `name` VARCHAR(200) NOT NULL COMMENT '评分规则名称',
    `description` TEXT DEFAULT NULL COMMENT '评分规则描述',
    `assessment_type` VARCHAR(50) NOT NULL COMMENT '评分类型',
    `node_id` VARCHAR(100) DEFAULT NULL COMMENT '关联节点ID',
    `channel` ENUM('A', 'B', 'C') DEFAULT NULL COMMENT '适用通道',
    `rubric` JSON NOT NULL COMMENT '评分细则',
    `weight_idea` DECIMAL(3,2) NOT NULL DEFAULT 0.30 COMMENT 'Idea权重',
    `weight_ui` DECIMAL(3,2) NOT NULL DEFAULT 0.30 COMMENT 'UI权重',
    `weight_code` DECIMAL(3,2) NOT NULL DEFAULT 0.40 COMMENT 'Code权重',
    `pass_threshold` DECIMAL(5,2) NOT NULL DEFAULT 60.00 COMMENT '通过阈值',
    `excellent_threshold` DECIMAL(5,2) NOT NULL DEFAULT 85.00 COMMENT '优秀阈值',
    `max_retries` INT NOT NULL DEFAULT 3 COMMENT '最大重试次数',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    `version` VARCHAR(20) NOT NULL DEFAULT '1.0' COMMENT '版本号',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_assessment_id` (`assessment_id`),
    KEY `idx_node_channel` (`node_id`, `channel`),
    KEY `idx_type` (`assessment_type`),
    KEY `idx_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评分规则表';

-- 7. 评分执行记录表
CREATE TABLE `assessment_runs` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `run_id` VARCHAR(100) NOT NULL COMMENT '评分执行ID',
    `student_id` VARCHAR(50) NOT NULL COMMENT '学生ID',
    `assessment_id` VARCHAR(100) NOT NULL COMMENT '评分规则ID',
    `node_id` VARCHAR(100) NOT NULL COMMENT '节点ID',
    `channel` ENUM('A', 'B', 'C') NOT NULL COMMENT '使用通道',
    `status` ENUM('queued', 'in_progress', 'completed', 'failed') NOT NULL DEFAULT 'queued' COMMENT '执行状态',
    `overall_score` DECIMAL(5,2) DEFAULT NULL COMMENT '总体得分',
    `idea_score` DECIMAL(5,2) DEFAULT NULL COMMENT 'Idea得分',
    `ui_score` DECIMAL(5,2) DEFAULT NULL COMMENT 'UI得分',
    `code_score` DECIMAL(5,2) DEFAULT NULL COMMENT 'Code得分',
    `detailed_scores` JSON DEFAULT NULL COMMENT '详细评分',
    `assessment_level` ENUM('pass', 'excellent', 'need_improvement') DEFAULT NULL COMMENT '评估等级',
    `diagnosis` JSON DEFAULT NULL COMMENT '诊断信息',
    `resources` JSON DEFAULT NULL COMMENT '推荐资源',
    `exit_rules` JSON DEFAULT NULL COMMENT '准出规则',
    `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
    `started_at` TIMESTAMP NULL DEFAULT NULL COMMENT '开始时间',
    `completed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '完成时间',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_run_id` (`run_id`),
    KEY `idx_student_id` (`student_id`),
    KEY `idx_assessment_id` (`assessment_id`),
    KEY `idx_node_id` (`node_id`),
    KEY `idx_status` (`status`),
    KEY `idx_created_at` (`created_at`),
    CONSTRAINT `fk_assessment_runs_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_assessment_runs_assessment` FOREIGN KEY (`assessment_id`) REFERENCES `assessments` (`assessment_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评分执行记录表';

-- 8. 提交记录表
CREATE TABLE `submissions` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `submission_id` VARCHAR(100) NOT NULL COMMENT '提交ID',
    `student_id` VARCHAR(50) NOT NULL COMMENT '学生ID',
    `node_id` VARCHAR(100) NOT NULL COMMENT '节点ID',
    `channel` ENUM('A', 'B', 'C') NOT NULL COMMENT '使用通道',
    `assessment_run_id` VARCHAR(100) DEFAULT NULL COMMENT '关联评分执行ID',
    `file_path` VARCHAR(500) NOT NULL COMMENT '文件路径',
    `file_type` VARCHAR(50) NOT NULL COMMENT '文件类型',
    `file_size` BIGINT DEFAULT NULL COMMENT '文件大小(字节)',
    `content_hash` VARCHAR(64) DEFAULT NULL COMMENT '内容哈希',
    `idea_text` TEXT DEFAULT NULL COMMENT 'Idea文本',
    `ui_images` JSON DEFAULT NULL COMMENT 'UI图片列表',
    `code_snippets` JSON DEFAULT NULL COMMENT '代码片段',
    `code_repo` VARCHAR(500) DEFAULT NULL COMMENT '代码仓库链接',
    `submission_type` VARCHAR(50) NOT NULL DEFAULT 'code' COMMENT '提交类型',
    `status` ENUM('pending', 'processing', 'completed', 'failed') NOT NULL DEFAULT 'pending' COMMENT '处理状态',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_submission_id` (`submission_id`),
    KEY `idx_student_node` (`student_id`, `node_id`),
    KEY `idx_assessment_run` (`assessment_run_id`),
    KEY `idx_created_at` (`created_at`),
    KEY `idx_status` (`status`),
    CONSTRAINT `fk_submissions_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_submissions_assessment_run` FOREIGN KEY (`assessment_run_id`) REFERENCES `assessment_runs` (`run_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='提交记录表';

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 创建索引优化查询性能
CREATE INDEX `idx_student_progress_completed` ON `student_progress_nodes` (`student_id`, `status`, `completed_at`);
CREATE INDEX `idx_assessment_runs_student_time` ON `assessment_runs` (`student_id`, `created_at`);
CREATE INDEX `idx_submissions_student_time` ON `submissions` (`student_id`, `created_at`);
CREATE INDEX `idx_diagnostics_student_time` ON `diagnostics` (`student_id`, `created_at`);
CREATE INDEX idx_students_email ON students(email);
CREATE INDEX idx_students_password_hash ON students(password_hash);
