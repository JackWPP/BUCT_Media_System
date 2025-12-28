"""
User CRUD operations

用户相关的数据库操作。
"""
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.models.user import User
from app.schemas.user import UserCreate, UserCreateByAdmin, UserUpdateByAdmin
from app.core.security import get_password_hash, verify_password


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Get user by email
    
    通过邮箱查询用户。
    """
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_student_id(db: AsyncSession, student_id: str) -> Optional[User]:
    """
    Get user by student_id
    
    通过学号/工号查询用户。
    """
    result = await db.execute(select(User).filter(User.student_id == student_id))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """
    Get user by ID
    
    通过 ID 查询用户。
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user: UserCreate, role: str = "user") -> User:
    """
    Create a new user
    
    创建新用户（普通注册）。
    必须包含 student_id。
    """
    hashed_password = get_password_hash(user.password)
    db_user = User(
        student_id=user.student_id,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=role,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def create_user_by_admin(db: AsyncSession, user_data: UserCreateByAdmin) -> User:
    """
    管理员创建用户
    
    支持指定角色和学号。
    """
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role.value,  # 从枚举获取字符串值
        student_id=user_data.student_id,  # 学号
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def authenticate_user(db: AsyncSession, identifier: str, password: str) -> Optional[User]:
    """
    Authenticate user by email/student_id and password
    
    支持邮箱或学号登录。
    
    Args:
        db: 数据库会话
        identifier: 邮箱或学号
        password: 密码
    """
    # 先尝试邮箱查找
    user = await get_user_by_email(db, identifier)
    if not user:
        # 再尝试学号查找
        user = await get_user_by_student_id(db, identifier)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    role: Optional[str] = None
) -> Tuple[List[User], int]:
    """
    获取用户列表（支持分页和搜索）

    Args:
        db: 数据库会话
        skip: 跳过记录数
        limit: 返回记录数
        search: 搜索关键词（邮箱或姓名）
        role: 按角色过滤

    Returns:
        (用户列表, 总数)
    """
    query = select(User)
    count_query = select(func.count(User.id))
    
    # 搜索过滤
    if search:
        # 支持搜索邮箱、姓名或学号
        search_filter = (
            (User.email.ilike(f"%{search}%")) | 
            (User.full_name.ilike(f"%{search}%")) |
            (User.student_id.ilike(f"%{search}%"))
        )
        query = query.filter(search_filter)
        count_query = count_query.filter(search_filter)
    
    # 角色过滤
    if role:
        query = query.filter(User.role == role)
        count_query = count_query.filter(User.role == role)
    
    # 排序和分页
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    
    # 执行查询
    result = await db.execute(query)
    users = result.scalars().all()
    
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    return list(users), total


async def update_user_by_admin(
    db: AsyncSession,
    user_id: str,
    user_data: UserUpdateByAdmin
) -> Optional[User]:
    """
    管理员更新用户信息

    支持修改邮箱、姓名、密码、激活状态和角色。
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    update_data = user_data.model_dump(exclude_unset=True)
    
    # 处理密码
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    elif "password" in update_data:
        del update_data["password"]
    
    # 处理角色枚举
    if "role" in update_data and update_data["role"]:
        update_data["role"] = update_data["role"].value
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_role(db: AsyncSession, user_id: str, new_role: str) -> Optional[User]:
    """
    更新用户角色

    Args:
        db: 数据库会话
        user_id: 用户 ID
        new_role: 新角色
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    user.role = new_role
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: str) -> bool:
    """
    删除用户

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        是否删除成功
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    
    await db.delete(user)
    await db.commit()
    return True

