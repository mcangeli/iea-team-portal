from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import SeasonClass, ShowClass


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
