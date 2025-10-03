"""API密钥管理API路由。"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.auth.middleware import get_current_user
from src.auth.models.api_key import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
    APIKeyUpdate,
)
from src.auth.models.user import User
from src.auth.services.api_key_service import api_key_service
from src.logger import logger

router = APIRouter(prefix="/api/v1/api-keys", tags=["API密钥管理"])


@router.post("", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user)
) -> APIKeyCreateResponse:
    """创建新的API密钥。

    Args:
        key_data: 密钥创建数据
        current_user: 当前用户

    Returns:
        包含完整密钥的响应(仅在创建时返回一次)

    Raises:
        HTTPException: 创建失败
    """
    try:
        api_key_str, key_info = await api_key_service.create_api_key(
            current_user,
            key_data
        )

        return APIKeyCreateResponse(
            api_key=api_key_str,
            key_info=key_info
        )

    except Exception as e:
        logger.error(f"创建API密钥失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建API密钥失败"
        )


@router.get("", response_model=List[APIKeyResponse])
async def list_api_keys(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
) -> List[APIKeyResponse]:
    """获取当前用户的API密钥列表。

    Args:
        limit: 返回数量限制
        offset: 偏移量
        current_user: 当前用户

    Returns:
        API密钥列表
    """
    try:
        return await api_key_service.list_api_keys(current_user, limit, offset)
    except Exception as e:
        logger.error(f"获取API密钥列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取API密钥列表失败"
        )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user)
) -> APIKeyResponse:
    """获取API密钥详情。

    Args:
        key_id: 密钥ID
        current_user: 当前用户

    Returns:
        API密钥详情

    Raises:
        HTTPException: 密钥不存在或无权访问
    """
    try:
        key_info = await api_key_service.get_api_key(key_id, current_user)

        if not key_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API密钥不存在或无权访问"
            )

        return key_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取API密钥详情失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取API密钥详情失败"
        )


@router.put("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: str,
    key_update: APIKeyUpdate,
    current_user: User = Depends(get_current_user)
) -> APIKeyResponse:
    """更新API密钥信息。

    Args:
        key_id: 密钥ID
        key_update: 更新数据
        current_user: 当前用户

    Returns:
        更新后的API密钥信息

    Raises:
        HTTPException: 更新失败
    """
    try:
        key_info = await api_key_service.update_api_key(
            key_id,
            current_user,
            key_update
        )

        if not key_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API密钥不存在或无权访问"
            )

        return key_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新API密钥失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新API密钥失败"
        )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user)
) -> None:
    """删除API密钥。

    Args:
        key_id: 密钥ID
        current_user: 当前用户

    Raises:
        HTTPException: 删除失败
    """
    try:
        success = await api_key_service.delete_api_key(key_id, current_user)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API密钥不存在或无权访问"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除API密钥失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除API密钥失败"
        )


@router.post("/{key_id}/regenerate", response_model=APIKeyCreateResponse)
async def regenerate_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user)
) -> APIKeyCreateResponse:
    """重新生成API密钥。

    Args:
        key_id: 密钥ID
        current_user: 当前用户

    Returns:
        新的API密钥(完整密钥仅此一次显示)

    Raises:
        HTTPException: 重新生成失败
    """
    try:
        result = await api_key_service.regenerate_api_key(key_id, current_user)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API密钥不存在或无权访问"
            )

        new_key_str, key_info = result

        return APIKeyCreateResponse(
            api_key=new_key_str,
            key_info=key_info
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新生成API密钥失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重新生成API密钥失败"
        )
