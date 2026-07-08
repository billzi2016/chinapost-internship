"""向量索引占位迁移。

当前旧 H5 embedding 是 4096 维，pgvector ivfflat 对 vector 维度有限制，因此暂时保留精确搜索。
保留这个迁移文件是为了记录设计决策，并为未来更换低维 embedding 后增加索引留出位置。
"""

from __future__ import annotations

from django.db import migrations


def create_vector_index(apps, schema_editor) -> None:
    """当前不创建索引，原因见文件级注释。"""
    # 当前导入的 H5 向量是 4096 维；pgvector ivfflat 对 vector 列维度有上限。
    # 查询代码使用 pgvector.django 的距离表达式做精确搜索。
    return


def drop_vector_index(apps, schema_editor) -> None:
    """没有创建索引，因此回滚时也不需要删除索引。"""
    return


class Migration(migrations.Migration):
    """记录暂不创建向量索引的迁移节点。"""

    dependencies = [
        ("core", "0003_postalembedding"),
    ]

    operations = [
        migrations.RunPython(create_vector_index, drop_vector_index),
    ]
