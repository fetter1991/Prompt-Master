import os
import json
import zipfile
import time
from werkzeug.utils import secure_filename
from flask import current_app
from extensions import db
from models import Image, Tag, ReferenceImage, MainImage


class DataService:
    @staticmethod
    def import_zip_stream(zip_path):
        """流式处理 ZIP 导入，返回生成器"""
        yield "🚀 [System] 开始处理数据包...\n"

        stats = {'processed': 0, 'skipped': 0, 'errors': 0}
        upload_root = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
        if not os.path.exists(upload_root): os.makedirs(upload_root)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                if 'data.json' not in zf.namelist():
                    yield "❌ 错误：未找到 data.json\n"
                    return

                with zf.open('data.json') as f:
                    data = json.load(f)
                    items = data.get('images', [])

                yield f"📦 发现 {len(items)} 条记录，开始导入...\n"

                for item in items:
                    try:
                        # 查重：标题和作者相同则跳过
                        if Image.query.filter_by(title=item['title'], author=item.get('author', '')).first():
                            yield f"   ⏭️ [跳过] {item['title']}\n"
                            stats['skipped'] += 1
                            continue

                        yield f"   📥 [导入] {item['title']}... "

                        # 1. 提取主图，兼容旧版单主图与新版多主图
                        raw_main_images = item.get('main_images') or []
                        if raw_main_images:
                            main_items = raw_main_images
                        else:
                            main_items = [{
                                'file_path': item.get('zip_image_path'),
                                'thumbnail_path': item.get('zip_thumb_path'),
                                'position': 0
                            }]

                        extracted_main_images = []
                        web_folder = current_app.config['UPLOAD_FOLDER']

                        for index, main_item in enumerate(main_items):
                            zip_img = main_item.get('zip_image_path') or main_item.get('file_path')
                            if zip_img and zip_img not in zf.namelist():
                                zip_img = f"images/{os.path.basename(zip_img)}"
                            if not zip_img or zip_img not in zf.namelist():
                                if index == 0:
                                    raise FileNotFoundError("主图缺失")
                                continue

                            safe_name = secure_filename(os.path.basename(zip_img))
                            with zf.open(zip_img) as src, open(os.path.join(upload_root, safe_name), "wb") as dst:
                                dst.write(src.read())

                            safe_thumb = None
                            zip_thumb = main_item.get('zip_thumb_path') or main_item.get('thumbnail_path')
                            if zip_thumb and zip_thumb not in zf.namelist():
                                zip_thumb = f"images/{os.path.basename(zip_thumb)}"
                            if zip_thumb and zip_thumb in zf.namelist():
                                safe_thumb = secure_filename(os.path.basename(zip_thumb))
                                with zf.open(zip_thumb) as src, open(os.path.join(upload_root, safe_thumb), "wb") as dst:
                                    dst.write(src.read())

                            extracted_main_images.append({
                                'file_path': f"/{web_folder}/{safe_name}",
                                'thumbnail_path': f"/{web_folder}/{safe_thumb}" if safe_thumb else None,
                                'position': main_item.get('position', index)
                            })

                        if not extracted_main_images:
                            raise FileNotFoundError("主图缺失")

                        first_main_image = sorted(extracted_main_images, key=lambda x: x.get('position', 0))[0]
                        img = Image(
                            title=item['title'],
                            author=item.get('author', ''),
                            prompt=item.get('prompt', ''),
                            description=item.get('description', ''),
                            type=item.get('type', 'txt2img'),
                            model_type=item.get('model_type', ''),
                            category=item.get('category', 'gallery'),  # 读取分类
                            file_path=first_main_image['file_path'],
                            thumbnail_path=first_main_image.get('thumbnail_path'),
                            status='pending',  # 导入后默认为待审核，需管理员确认
                            heat_score=item.get('heat_score', 0)
                        )

                        for main_item in extracted_main_images:
                            img.main_images.append(MainImage(
                                file_path=main_item['file_path'],
                                thumbnail_path=main_item.get('thumbnail_path'),
                                position=main_item.get('position', 0)
                            ))
                        # ---------------------------------

                        # 3. 处理标签
                        for t in item.get('tags', []):
                            tag = Tag.query.filter_by(name=t).first() or Tag(name=t)
                            db.session.add(tag)
                            img.tags.append(tag)

                        # 4. 处理参考图
                        for ref_path in item.get('refs', []):
                            # 兼容旧版本 JSON
                            if isinstance(ref_path, str):
                                if ref_path in zf.namelist():
                                    safe_ref = secure_filename(os.path.basename(ref_path))
                                    with zf.open(ref_path) as src, open(os.path.join(upload_root, safe_ref),
                                                                        "wb") as dst:
                                        dst.write(src.read())
                                    ref_obj = ReferenceImage(file_path=f"/{web_folder}/{safe_ref}")
                                    img.refs.append(ref_obj)
                            # 兼容新版本 JSON
                            elif isinstance(ref_path, dict):
                                if not ref_path.get('is_placeholder') and ref_path.get('file_path'):
                                    fname = os.path.basename(ref_path['file_path'])
                                    zip_ref_path = f"images/{fname}"

                                    if zip_ref_path in zf.namelist():
                                        with zf.open(zip_ref_path) as src, open(os.path.join(upload_root, fname),
                                                                                "wb") as dst:
                                            dst.write(src.read())
                                        ref_obj = ReferenceImage(
                                            file_path=f"/{web_folder}/{fname}",
                                            position=ref_path.get('position', 0)
                                        )
                                        img.refs.append(ref_obj)

                        db.session.add(img)
                        db.session.commit()
                        stats['processed'] += 1
                        yield "✅ OK\n"

                    except Exception as e:
                        db.session.rollback()
                        stats['errors'] += 1
                        yield f"❌ {str(e)}\n"

                    # 避免阻塞 IO
                    time.sleep(0.01)

        except Exception as e:
            yield f"\n❌ ZIP 读取失败: {str(e)}\n"
        finally:
            # 清理临时上传文件
            if os.path.exists(zip_path): os.remove(zip_path)

        yield f"\n🎉 完成：成功 {stats['processed']}，跳过 {stats['skipped']}，错误 {stats['errors']}"