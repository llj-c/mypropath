""" 基础数据模型 基类 """

from pydantic import BaseModel, ConfigDict


class BaseDataModel(BaseModel):
    """接口数据模型基类"""
    model_config = ConfigDict(
        extra="ignore",  # 忽略响应中多余的字段
        strict=False,    # 允许类型转换（如字符串数字转int）
        populate_by_name=True,  # 支持别名映射,
        arbitrary_types_allowed=True,  # 允许任意类型
        from_attributes=True  # 从属性映射
    )
