# Generated by Django 5.0.3 on 2024-03-11 16:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0005_delete_recomment'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='view_count',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
