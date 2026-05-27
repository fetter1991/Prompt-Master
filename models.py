from flask_login import UserMixin
from datetime import datetime
from extensions import db
from flask import request

image_tags = db.Table('image_tags',
                      db.Column('image_id', db.Integer, db.ForeignKey('image.id')),
                      db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
                      )


class User(UserMixin, db.Model):
    """用户模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))


class SystemSetting(db.Model):
    """系统配置表 (Key-Value 存储)"""
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(255))  # 存储 '1'/'0' 或其他字符串

    @staticmethod
    def get_bool(key, default=True):
        """获取布尔值设置"""
        setting = db.session.get(SystemSetting, key)
        if not setting:
            return default
        return setting.value == '1'

    @staticmethod
    def set_bool(key, value):
        """设置布尔值"""
        setting = db.session.get(SystemSetting, key)
        if not setting:
            setting = SystemSetting(key=key)
            db.session.add(setting)
        # 将 Python bool 转换为 '1' 或 '0'
        setting.value = '1' if value else '0'
        db.session.commit()

    @staticmethod
    def get_str(key, default=''):
        """获取字符串设置"""
        setting = db.session.get(SystemSetting, key)
        if not setting or setting.value is None:
            return default
        return setting.value

    @staticmethod
    def set_str(key, value):
        """设置字符串值"""
        setting = db.session.get(SystemSetting, key)
        if not setting:
            setting = SystemSetting(key=key)
            db.session.add(setting)
        setting.value = str(value) if value is not None else ''
        db.session.commit()

    @staticmethod
    def get_int(key, default=0):
        """获取整数设置"""
        setting = db.session.get(SystemSetting, key)
        if not setting or setting.value is None:
            return default
        try:
            return int(setting.value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def set_int(key, value):
        """设置整数值"""
        setting = db.session.get(SystemSetting, key)
        if not setting:
            setting = SystemSetting(key=key)
            db.session.add(setting)
        setting.value = str(int(value))
        db.session.commit()


class Image(db.Model):
    """核心作品模型"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(50), default='匿名')
    file_path = db.Column(db.String(255), nullable=False)
    thumbnail_path = db.Column(db.String(255))
    prompt = db.Column(db.Text)
    description = db.Column(db.Text)
    type = db.Column(db.String(50))  # txt2img / img2img
    model_type = db.Column(db.String(50), default='', index=True)  # 模型类型，如 SDXL / Flux / Midjourney
    status = db.Column(db.String(20), default='pending', index=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 作品分类: gallery / template
    category = db.Column(db.String(20), default='gallery', index=True)

    # 统计数据
    views_count = db.Column(db.Integer, default=0)
    copies_count = db.Column(db.Integer, default=0)
    heat_score = db.Column(db.Integer, default=0, index=True)

    # 关联
    tags = db.relationship('Tag', secondary=image_tags, backref='images')
    main_images = db.relationship('MainImage', backref='image', cascade="all, delete-orphan",
                                  order_by="MainImage.position")
    refs = db.relationship('ReferenceImage', backref='image', cascade="all, delete-orphan",
                           order_by="ReferenceImage.position")

    def to_dict(self):
        """序列化为字典，用于 API 或导出"""

        def _get_full_url(path):
            """辅助函数：确保返回的是带域名的完整 URL"""
            if not path:
                return None
            if path.startswith(('http://', 'https://')):
                return path
            # 本地路径，拼接当前请求的域名
            return request.url_root.rstrip('/') + path

        # 构造主作品图片列表；旧数据没有 main_images 时使用 file_path 兜底
        main_images_data = []
        main_images = self.main_images or []
        if main_images:
            for item in main_images:
                main_images_data.append({
                    "id": item.id,
                    "file_path": _get_full_url(item.file_path),
                    "thumbnail_path": _get_full_url(item.thumbnail_path),
                    "position": item.position
                })
        else:
            main_images_data.append({
                "id": None,
                "file_path": _get_full_url(self.file_path),
                "thumbnail_path": _get_full_url(self.thumbnail_path),
                "position": 0
            })

        # 构造参考图列表
        refs_data = []
        for r in self.refs:
            # 处理占位符逻辑，如果是占位符，返回特定标记 {{userText}}
            if r.is_placeholder:
                final_path = "{{userText}}"
            else:
                final_path = _get_full_url(r.file_path) if r.file_path else ""

            refs_data.append({
                "id": r.id,
                "file_path": final_path,
                "is_placeholder": r.is_placeholder,
                "position": r.position
            })

        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "prompt": self.prompt,
            "description": self.description,
            "type": self.type,
            "model_type": self.model_type or '',
            "category": self.category,

            # 主图和缩略图都处理成绝对路径
            "file_path": _get_full_url(self.file_path),
            "thumbnail_path": _get_full_url(self.thumbnail_path),
            "main_images": main_images_data,

            "tags": [t.name for t in self.tags],

            # 参考图列表
            "refs": refs_data,

            "heat_score": self.heat_score,
            "created_at": self.created_at.isoformat()
        }


class MainImage(db.Model):
    """主作品图片模型，支持一个作品关联多张主图"""
    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False, index=True)
    file_path = db.Column(db.String(255), nullable=False)
    thumbnail_path = db.Column(db.String(255))
    position = db.Column(db.Integer, default=0)


class ReferenceImage(db.Model):
    """参考图模型"""
    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=True)
    position = db.Column(db.Integer, default=0)
    is_placeholder = db.Column(db.Boolean, default=False)


class Tag(db.Model):
    """标签模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    is_sensitive = db.Column(db.Boolean, default=False)