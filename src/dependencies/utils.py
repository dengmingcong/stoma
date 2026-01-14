"""参数依赖分析工具函数。"""

from pydantic.fields import FieldInfo

from src.params import Param


def get_param_info(field_info: FieldInfo) -> Param | None:
    """从字段的 FieldInfo 中提取参数标记信息。

    检查 FieldInfo 本身是否是 Param 类型的实例，或者检查其 metadata。

    :param field_info: Pydantic 字段信息对象。
    :type field_info: FieldInfo
    :return: 参数标记对象，如果没有找到则返回 None。
    :rtype: Param | None
    """
    # 首先检查 field_info 本身是否是 Param 的实例
    if isinstance(field_info, Param):
        return field_info

    # 然后检查 field_info 的 metadata 列表
    for metadata in field_info.metadata:
        if isinstance(metadata, Param):
            return metadata

    return None
