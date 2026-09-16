from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portal", "0087_v340_lesson_model_state_alignment")]

    operations = [
        migrations.AddField(
            model_name="lessonparticipantmove",
            name="carry_horse",
            field=models.BooleanField(default=False),
        ),
    ]
