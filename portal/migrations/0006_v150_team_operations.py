from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('portal', '0005_v140_points_qualification'),
    ]

    operations = [
        migrations.AddField(
            model_name='season',
            name='futures_volunteer_hours_required',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name='season',
            name='upper_volunteer_hours_required',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.CreateModel(
            name='LessonGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('team_level', models.CharField(choices=[('futures', 'Futures Team'), ('upper', 'Upper School Team'), ('both', 'Both teams')], default='both', max_length=20)),
                ('default_location', models.CharField(blank=True, max_length=180)),
                ('active', models.BooleanField(default=True)),
                ('coach', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lesson_groups_coached', to=settings.AUTH_USER_MODEL)),
                ('riders', models.ManyToManyField(blank=True, related_name='lesson_groups', to='portal.rider')),
                ('season', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lesson_groups', to='portal.season')),
            ],
            options={'ordering': ['team_level', 'name']},
        ),
        migrations.AddConstraint(
            model_name='lessongroup',
            constraint=models.UniqueConstraint(fields=('season', 'name'), name='unique_lesson_group_season'),
        ),
        migrations.CreateModel(
            name='Lesson',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='Team lesson', max_length=160)),
                ('starts_at', models.DateTimeField()),
                ('ends_at', models.DateTimeField(blank=True, null=True)),
                ('location', models.CharField(blank=True, max_length=180)),
                ('notes', models.TextField(blank=True)),
                ('cancelled', models.BooleanField(default=False)),
                ('coach', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lessons_coached', to=settings.AUTH_USER_MODEL)),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lessons', to='portal.lessongroup')),
                ('season', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lessons', to='portal.season')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lessons', to='portal.team')),
            ],
            options={'ordering': ['starts_at']},
        ),
        migrations.AddField(
            model_name='calendarevent',
            name='lesson',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='calendar_event', to='portal.lesson'),
        ),
        migrations.CreateModel(
            name='LessonAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('expected', 'Expected'), ('present', 'Present'), ('absent', 'Absent'), ('excused', 'Excused'), ('makeup', 'Makeup')], default='expected', max_length=20)),
                ('horse_name', models.CharField(blank=True, max_length=100)),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance', to='portal.lesson')),
                ('rider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lesson_attendance', to='portal.rider')),
            ],
            options={'ordering': ['rider__last_name', 'rider__first_name']},
        ),
        migrations.AddConstraint(
            model_name='lessonattendance',
            constraint=models.UniqueConstraint(fields=('lesson', 'rider'), name='unique_lesson_rider_attendance'),
        ),
        migrations.CreateModel(
            name='ShowAvailability',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'No response'), ('available', 'Available'), ('conditional', 'Available with conditions'), ('unavailable', 'Unavailable')], default='pending', max_length=20)),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('responded_at', models.DateTimeField(blank=True, null=True)),
                ('responded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='show_availability_responses', to=settings.AUTH_USER_MODEL)),
                ('rider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='show_availability', to='portal.rider')),
                ('show', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='availability', to='portal.show')),
            ],
            options={'ordering': ['rider__last_name', 'rider__first_name']},
        ),
        migrations.AddConstraint(
            model_name='showavailability',
            constraint=models.UniqueConstraint(fields=('show', 'rider'), name='unique_show_rider_availability'),
        ),
        migrations.CreateModel(
            name='VolunteerLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_date', models.DateField()),
                ('hours', models.DecimalField(decimal_places=2, max_digits=5)),
                ('category', models.CharField(choices=[('show', 'Show support'), ('barn', 'Barn/team support'), ('fundraising', 'Fundraising'), ('team', 'Team event'), ('other', 'Other')], default='team', max_length=30)),
                ('performed_by', models.CharField(blank=True, help_text='Name of the family member/person who completed the hours.', max_length=160)),
                ('description', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('pending', 'Pending approval'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('coach_notes', models.CharField(blank=True, max_length=255)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='volunteer_logs_approved', to=settings.AUTH_USER_MODEL)),
                ('rider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='volunteer_logs', to='portal.rider')),
                ('season', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='volunteer_logs', to='portal.season')),
                ('submitted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='volunteer_logs_submitted', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-service_date', '-submitted_at']},
        ),
    ]
