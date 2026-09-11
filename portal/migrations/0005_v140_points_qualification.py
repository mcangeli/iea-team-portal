from django.db import migrations, models
import django.db.models.deletion


def preserve_existing_points(apps, schema_editor):
    ShowResult = apps.get_model('portal', 'ShowResult')
    ShowResult.objects.filter(points__isnull=False).update(manual_points=True)


def seed_scoring_configs(apps, schema_editor):
    Season = apps.get_model('portal', 'Season')
    SeasonScoringConfig = apps.get_model('portal', 'SeasonScoringConfig')
    for season in Season.objects.all():
        SeasonScoringConfig.objects.get_or_create(season=season)


class Migration(migrations.Migration):
    dependencies = [('portal', '0004_v130_workflow')]

    operations = [
        migrations.AddField(
            model_name='showresult',
            name='manual_points',
            field=models.BooleanField(default=False, help_text='Keep the entered points instead of calculating from placing.'),
        ),
        migrations.CreateModel(
            name='SeasonScoringConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_points', models.DecimalField(decimal_places=1, default=7, max_digits=4)),
                ('second_points', models.DecimalField(decimal_places=1, default=5, max_digits=4)),
                ('third_points', models.DecimalField(decimal_places=1, default=4, max_digits=4)),
                ('fourth_points', models.DecimalField(decimal_places=1, default=3, max_digits=4)),
                ('fifth_points', models.DecimalField(decimal_places=1, default=2, max_digits=4)),
                ('sixth_points', models.DecimalField(decimal_places=1, default=1, max_digits=4)),
                ('individual_qualification_points', models.DecimalField(decimal_places=1, default=18, max_digits=5)),
                ('team_qualification_points', models.DecimalField(decimal_places=1, default=20, max_digits=5)),
                ('season', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='scoring_config', to='portal.season')),
            ],
        ),
        migrations.CreateModel(
            name='QualificationOverride',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('auto', 'Automatic'), ('qualified', 'Qualified'), ('not_qualified', 'Not qualified')], default='auto', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('membership', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='qualification_overrides', to='portal.seasonmembership')),
                ('season_class', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='qualification_overrides', to='portal.seasonclass')),
            ],
        ),
        migrations.AddConstraint(
            model_name='qualificationoverride',
            constraint=models.UniqueConstraint(fields=('membership', 'season_class'), name='unique_qualification_override'),
        ),
        migrations.RunPython(preserve_existing_points, migrations.RunPython.noop),
        migrations.RunPython(seed_scoring_configs, migrations.RunPython.noop),
    ]
