# Generated by Django 2.2.16 on 2023-04-28 14:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0007_follow'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='comment',
            options={'verbose_name': 'Пост', 'verbose_name_plural': 'Посты'},
        ),
        migrations.AlterModelOptions(
            name='follow',
            options={'verbose_name': 'Подписка', 'verbose_name_plural': 'Подписки'},
        ),
    ]