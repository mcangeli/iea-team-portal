from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("portal", "0082_v340_lesson_participant_move"),
    ]
    operations = [
        migrations.AddField(
            model_name="lessonparticipantmove",
            name="initiated_by",
            field=models.CharField(choices=[("staff", "Staff"), ("rider", "Rider")], default="staff", max_length=12),
        ),
        migrations.AddField(
            model_name="lessonparticipantmove",
            name="created_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="lesson_participant_moves_created", to=settings.AUTH_USER_MODEL),
        ),
    ]
