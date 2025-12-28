"""
数据库迁移脚本：将 student_id 设为必填，email 设为可选

由于 SQLite 不支持直接 ALTER COLUMN 修改 NOT NULL 约束，
本脚本通过重建表的方式完成迁移：
1. 创建新表 users_new（新约束）
2. 迁移数据（无 student_id 的记录用 email 填充）
3. 删除旧表，重命名新表
4. 重建索引
"""
import sqlite3
import uuid

DB_PATH = "buct_media.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("开始迁移...")
    
    # 1. 检查当前表结构
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"当前表列: {columns}")
    
    # 2. 检查是否有数据缺少 student_id
    cursor.execute("SELECT id, email, student_id FROM users WHERE student_id IS NULL OR student_id = ''")
    missing_student_id = cursor.fetchall()
    
    if missing_student_id:
        print(f"发现 {len(missing_student_id)} 条记录缺少 student_id，将使用 email 作为临时 student_id...")
        for row in missing_student_id:
            user_id, email, student_id = row
            # 使用 email 的用户名部分或生成 UUID 作为临时 student_id
            temp_student_id = email.split('@')[0] if email else f"temp_{uuid.uuid4().hex[:8]}"
            cursor.execute("UPDATE users SET student_id = ? WHERE id = ?", (temp_student_id, user_id))
            print(f"  用户 {email} -> student_id: {temp_student_id}")
        conn.commit()
    
    # 3. 创建新表（student_id NOT NULL, email NULL）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users_new (
            id VARCHAR(36) PRIMARY KEY,
            student_id VARCHAR(20) NOT NULL UNIQUE,
            email VARCHAR(255) UNIQUE,
            hashed_password VARCHAR(255) NOT NULL,
            full_name VARCHAR(100),
            role VARCHAR(20) NOT NULL DEFAULT 'user',
            is_active BOOLEAN NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 4. 迁移数据
    cursor.execute("""
        INSERT INTO users_new (id, student_id, email, hashed_password, full_name, role, is_active, created_at)
        SELECT id, student_id, email, hashed_password, full_name, role, is_active, created_at
        FROM users
    """)
    
    # 5. 删除旧表
    cursor.execute("DROP TABLE users")
    
    # 6. 重命名新表
    cursor.execute("ALTER TABLE users_new RENAME TO users")
    
    # 7. 重建索引
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_student_id ON users (student_id)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")
    
    conn.commit()
    
    # 验证
    cursor.execute("PRAGMA table_info(users)")
    new_columns = cursor.fetchall()
    print("\n迁移完成！新表结构:")
    for col in new_columns:
        print(f"  {col[1]}: {col[2]}, NOT NULL: {col[3]}")
    
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    print(f"\n用户总数: {count}")
    
    conn.close()
    print("\n✅ 迁移成功完成！")

if __name__ == "__main__":
    migrate()
