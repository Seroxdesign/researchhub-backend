# Generated by Django 2.2 on 2022-07-05 22:02

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import reputation.related_models.bounty
import reputation.related_models.escrow


def migrate_author_rsc_to_escrow(apps, schema_editor):
    User = apps.get_model('user', 'user')
    AuthorRSC = apps.get_model('reputation', 'authorrsc')
    Escrow = apps.get_model('reputation', 'escrow')
    Paper = apps.get_model('paper', 'paper')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    bank_user = User.objects.filter(email="bank@researchhub.com")
    if bank_user.exists():
        user = bank_user.first()
    else:
        user = User.objects.first()

    for author_rsc in AuthorRSC.objects.all().iterator():
        Escrow.objects.create(
            created_by=user,
            content_type=ContentType.objects.get_for_model(Paper),
            object_id=author_rsc.paper.id,
            amount=author_rsc.amount
        )


def create_default_term(apps, schema_editor):
    reputation.related_models.escrow.get_current_bounty_fee()


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reputation', '0055_auto_20220628_2135'),
    ]

    operations = [
        migrations.CreateModel(
            name='Term',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
                ('expiration_date', models.DateTimeField(null=True)),
                ('rh_pct', models.DecimalField(decimal_places=2, max_digits=5)),
                ('dao_pct', models.DecimalField(decimal_places=2, max_digits=5)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Escrow',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
                ('hold_type', models.CharField(choices=[('BOUNTY', 'BOUNTY'), ('AUTHOR_RSC', 'AUTHOR_RSC')], max_length=16)),
                ('amount', models.DecimalField(decimal_places=10, default=0, max_digits=19)),
                ('object_id', models.PositiveIntegerField()),
                ('status', models.CharField(choices=[('PAID', 'PAID'), ('PARTIALLY_PAID', 'PARTIALLY_PAID'), ('PENDING', 'PENDING'), ('CANCELLED', 'CANCELLED')], default='PENDING', max_length=16)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_escrows', to=settings.AUTH_USER_MODEL)),
                ('recipient', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='target_escrows', to=settings.AUTH_USER_MODEL)),
                ('term', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='reputation.Term')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Bounty',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
                ('expiration_date', models.DateTimeField(default=reputation.related_models.bounty.get_default_expiration_date, null=True)),
                ('item_object_id', models.PositiveIntegerField()),
                ('solution_object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('amount', models.DecimalField(decimal_places=10, default=0, max_digits=19)),
                ('status', models.CharField(choices=[('OPEN', 'OPEN'), ('CLOSED', 'CLOSED'), ('CANCELLED', 'CANCELLED'), ('EXPIRED', 'EXPIRED')], default='OPEN', max_length=16)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bounties', to=settings.AUTH_USER_MODEL)),
                ('escrow', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='bounty', to='reputation.Escrow')),
                ('item_content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='item_bounty', to='contenttypes.ContentType')),
                ('solution_content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='solution_bounty', to='contenttypes.ContentType')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RunPython(migrate_author_rsc_to_escrow),
    ]
