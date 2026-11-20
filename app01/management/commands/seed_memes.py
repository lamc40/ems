""" 批量导入梗知识库到 500 条以上

用法：
  python manage.py seed_memes                # 直接导入（保留已有）
  python manage.py seed_memes --reset        # 先清空再重建
  python manage.py seed_memes --limit 500    # 只导入前 N 条（测试用）
"""
from django.core.management.base import BaseCommand

from app01.models import Meme


# 导入三批种子数据
from app01.management.commands.meme_seed.batch1_internet import MEMES as BATCH1
from app01.management.commands.meme_seed.batch2_workplace_gaming import MEMES as BATCH2
from app01.management.commands.meme_seed.batch3_anime_variety_other import MEMES as BATCH3

ALL_MEMES = BATCH1 + BATCH2 + BATCH3


class Command(BaseCommand):
    help = "批量扩充网络梗知识库（目标 500+ 条）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="先清空所有 Meme 记录再重建（谨慎！）",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="只导入前 N 条（0 表示全部）",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = Meme.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"已清空 {deleted} 条旧记录"))

        limit = options["limit"]
        memes = ALL_MEMES if limit <= 0 else ALL_MEMES[:limit]

        total = len(memes)
        self.stdout.write(f"📦 准备导入 {total} 条梗数据...")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for idx, (name, keywords, explanation, origin, category) in enumerate(memes, 1):
            try:
                obj, created = Meme.objects.update_or_create(
                    name=name,
                    defaults={
                        "keywords": keywords,
                        "explanation": explanation,
                        "origin": origin,
                        "category": category,
                        "is_active": True,
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            except Exception as e:
                skipped_count += 1
                if skipped_count <= 3:  # 只打印前 3 条跳过的
                    self.stdout.write(
                        self.style.WARNING(f"  ⏭ 跳过 [{name}]: {e}")
                    )

            # 每 50 条打印进度
            if idx % 50 == 0 or idx == total:
                self.stdout.write(f"  📊 进度 {idx}/{total}  新增:{created_count} 更新:{updated_count} 跳过:{skipped_count}")

        final_count = Meme.objects.count()
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"✅ 种子导入完成！\n"
            f"   本次新增: {created_count} 条\n"
            f"   本次更新: {updated_count} 条\n"
            f"   本次跳过: {skipped_count} 条\n"
            f"   Meme 表总计: {final_count} 条"
        ))
