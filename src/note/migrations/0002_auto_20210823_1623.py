# Generated by Django 2.2 on 2021-08-23 16:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('note', '0001_initial'),
        ('researchhub_document', '0021_auto_20210804_1850'),
        ('user', '0060_organization'),
    ]

    operations = [
        migrations.AddField(
            model_name='note',
            name='organization',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_notes', to='user.Organization'),
        ),
        migrations.AddField(
            model_name='note',
            name='unified_document',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='note', to='researchhub_document.ResearchhubUnifiedDocument'),
        ),
    ]
