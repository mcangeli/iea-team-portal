from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import SeasonClass, ShowClass


# Keep the field definition isolated from the large legacy models module while
# still making class_code a real SeasonClass model field at runtime.
if not any(field.name == "class_code" for field in SeasonClass._meta.fields):
    class_code_field = models.CharField(
        max_length=30,
        blank=True,
        help_text="Short IEA class identifier, such as H1, H2, H8, or H14.",
    )
    class_code_field.contribute_to_class(SeasonClass, "class_code")


@receiver(pre_save, sender=ShowClass)
def inherit_season_class_code(sender, instance, **kwargs):
    """Use the SeasonClass code as the default/canonical show class number."""
    if not instance.season_class_id:
        return
    code = (getattr(instance.season_class, "class_code", "") or "").strip().upper()
    if code:
        instance.class_number = code


@receiver(post_save, sender=SeasonClass)
def sync_show_class_codes(sender, instance, **kwargs):
    """Propagate a changed canonical class code to linked show classes."""
    code = (getattr(instance, "class_code", "") or "").strip().upper()
    if code and instance.class_code != code:
        SeasonClass.objects.filter(pk=instance.pk).update(class_code=code)
        instance.class_code = code
    if code:
        ShowClass.objects.filter(season_class=instance).exclude(class_number=code).update(class_number=code)
