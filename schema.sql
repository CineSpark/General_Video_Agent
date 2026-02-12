CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(128) NOT NULL PRIMARY KEY COMMENT '会话唯一标识符',
    user_id VARCHAR(128) NOT NULL COMMENT '用户标识符',
    session_state LONGTEXT COMMENT '会话状态数据，JSON格式',
    created_at datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
    updated_at datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新时间',

    INDEX idx_user_id (user_id),
    INDEX idx_updated_at (updated_at)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话信息表';

-- 事件表
-- 存储会话中的所有事件，包括用户消息、模型响应、工具调用等
CREATE TABLE IF NOT EXISTS events (
    event_type VARCHAR(128) NOT NULL COMMENT '事件类型',
    event_id VARCHAR(128) NOT NULL PRIMARY KEY COMMENT '事件唯一标识符',
    user_id VARCHAR(128) NOT NULL COMMENT '用户标识符',
    session_id VARCHAR(128) NOT NULL COMMENT '所属会话ID',
    invocation_id VARCHAR(128) DEFAULT NULL COMMENT '对话标识符',
    author VARCHAR(128) NOT NULL COMMENT '代理名称',
    timestamp DATETIME(6) NOT NULL COMMENT '事件时间戳，支持微秒精度',
    content LONGTEXT COMMENT '消息内容',
    tool_calls JSON DEFAULT NULL COMMENT '工具调用列表，JSON格式',
    tool_result JSON DEFAULT NULL COMMENT '工具调用结果，JSON格式',
    finish_reason VARCHAR(128) DEFAULT NULL COMMENT '结束原因',
    model VARCHAR(128) DEFAULT NULL COMMENT '使用的模型名称',
    error TEXT DEFAULT NULL COMMENT '错误信息',

    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_invocation_id (invocation_id)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件记录表';
