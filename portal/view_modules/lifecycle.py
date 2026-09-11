"""Rider lifecycle and former-rider archive views for v2.0 Preview 4."""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from ..lifecycle_models import RiderLifecycle
from ..models import Rider
from .common import _require_manage, _team


class RiderLifecycleForm(forms.ModelForm):
    class Meta:
        model = RiderLifecycle
        fields = ["status", "graduation_year", "ended_on"]
        widgets = {
            "ended_on": forms.DateInput(attrs={"type": "date"}),
        }
        help_texts = {
            "status": (
                "Active riders appear in current team operations. Graduated, "
                "Left Team, and Inactive riders remain in the historical archive."
            ),
            "graduation_year": "Optional. Used only when the rider is marked Graduated.",
        }

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        graduation_year = cleaned.get("graduation_year")
        ended_on = cleaned.get("ended_on")

        if status != RiderLifecycle.Status.GRADUATED and graduation_year:
            self.add_error(
                "graduation_year",
                "Graduation year is only used when the rider is marked Graduated.",
            )
        if status == RiderLifecycle.Status.ACTIVE and ended_on:
            self.add_error("ended_on", "An active rider cannot have an end date.")
        return cleaned


@login_required
def former_rider_list(request):
    _require_manage(request.user)
    team = _team(request.user)
    selected_status = request.GET.get("status", "all")
    former_statuses = {
        RiderLifecycle.Status.GRADUATED,
        RiderLifecycle.Status.LEFT_TEAM,
        RiderLifecycle.Status.INACTIVE,
    }

    qs = (
        team.riders.exclude(lifecycle__status=RiderLifecycle.Status.ACTIVE)
        .select_related("lifecycle")
        .prefetch_related("memberships__season")
        .order_by("last_name", "first_name")
    )
    if selected_status in former_statuses:
        qs = qs.filter(lifecycle__status=selected_status)
    else:
        selected_status = "all"

    counts = {
        "all": team.riders.exclude(
            lifecycle__status=RiderLifecycle.Status.ACTIVE
        ).count(),
        "graduated": team.riders.filter(
            lifecycle__status=RiderLifecycle.Status.GRADUATED
        ).count(),
        "left_team": team.riders.filter(
            lifecycle__status=RiderLifecycle.Status.LEFT_TEAM
        ).count(),
        "inactive": team.riders.filter(
            lifecycle__status=RiderLifecycle.Status.INACTIVE
        ).count(),
    }

    return render(
        request,
        "portal/former_rider_list.html",
        {
            "former_riders": qs,
            "selected_status": selected_status,
            "status_counts": counts,
        },
    )


@login_required
def rider_lifecycle_edit(request, pk):
    _require_manage(request.user)
    team = _team(request.user)
    rider = get_object_or_404(Rider, pk=pk, team=team)
    lifecycle, _ = RiderLifecycle.objects.get_or_create(
        rider=rider,
        defaults={
            "status": (
                RiderLifecycle.Status.ACTIVE
                if rider.active
                else RiderLifecycle.Status.INACTIVE
            )
        },
    )

    form = RiderLifecycleForm(request.POST or None, instance=lifecycle)
    if form.is_valid():
        with transaction.atomic():
            lifecycle = form.save()
            should_be_active = lifecycle.status == RiderLifecycle.Status.ACTIVE
            Rider.objects.filter(pk=rider.pk).update(active=should_be_active)

        if should_be_active:
            messages.success(
                request,
                f"{rider.display_name} is active again and will appear in current team operations.",
            )
        else:
            messages.success(
                request,
                f"{rider.display_name} moved to Alumni / Former Riders. Historical records were preserved.",
            )
        return redirect("rider_detail", pk=rider.pk)

    return render(
        request,
        "portal/rider_lifecycle_form.html",
        {
            "form": form,
            "rider": rider,
            "title": f"{rider.display_name} {rider.last_name}",
        },
    )
