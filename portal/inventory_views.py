from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render

from .inventory_forms import (
    InventoryAdjustmentForm, InventoryCategoryForm, InventoryItemForm,
    InventoryMovementForm, InventoryTransferForm,
)
from .model_modules.inventory import InventoryCategory, InventoryItem, InventoryStock
from .platform import can_manage_organization, organization_for_view_user
from .services.inventory_operations import (
    adjust_inventory, consume_inventory, receive_inventory, transfer_inventory,
)


def _team(user):
    team = organization_for_view_user(user)
    if team is None:
        raise PermissionDenied
    return team


def _manager(user):
    if not can_manage_organization(user):
        raise PermissionDenied


@login_required
def inventory_list(request):
    team = _team(request.user)
    items = InventoryItem.objects.filter(team=team).select_related("category").prefetch_related(
        Prefetch("stock_balances", queryset=InventoryStock.objects.select_related("space__facility"))
    )
    return render(request, "portal/inventory_list.html", {
        "items": items, "can_manage": can_manage_organization(request.user),
    })


@login_required
def inventory_item_detail(request, pk):
    team = _team(request.user)
    item = get_object_or_404(
        InventoryItem.objects.select_related("category"), pk=pk, team=team
    )
    return render(request, "portal/inventory_item_detail.html", {
        "item": item,
        "stock": item.stock_balances.select_related("space__facility").order_by("space__facility__name", "space__name"),
        "history": item.transactions.select_related("space__facility").all()[:50],
        "location_count": item.stock_balances.filter(quantity__gt=0).count(),
        "can_manage": can_manage_organization(request.user),
    })


@login_required
def inventory_item_create(request):
    _manager(request.user)
    team = _team(request.user)
    form = InventoryItemForm(request.POST or None, team=team)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(request, f"{item.name} added to inventory.")
        return redirect("inventory_item_detail", pk=item.pk)
    return render(request, "portal/inventory_form.html", {"form": form, "title": "Add inventory item"})


@login_required
def inventory_item_edit(request, pk):
    _manager(request.user)
    team = _team(request.user)
    item = get_object_or_404(InventoryItem, pk=pk, team=team)
    form = InventoryItemForm(request.POST or None, instance=item, team=team)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(request, f"{item.name} updated.")
        return redirect("inventory_item_detail", pk=item.pk)
    return render(request, "portal/inventory_form.html", {"form": form, "item": item, "title": f"Edit {item.name}"})


@login_required
def inventory_category_create(request):
    _manager(request.user)
    team = _team(request.user)
    form = InventoryCategoryForm(request.POST or None, team=team)
    if request.method == "POST" and form.is_valid():
        category = form.save()
        messages.success(request, f"{category.name} category added.")
        return redirect("inventory_list")
    return render(request, "portal/inventory_form.html", {"form": form, "title": "Add inventory category"})


def _movement(request, pk, *, title, form_class, operation, success):
    _manager(request.user)
    team = _team(request.user)
    item = get_object_or_404(InventoryItem, pk=pk, team=team)
    form = form_class(request.POST or None, team=team, item=item)
    if request.method == "POST" and form.is_valid():
        try:
            operation(
                item=item,
                space=form.cleaned_data["space"],
                quantity=form.cleaned_data["quantity"],
                reference=form.cleaned_data.get("reference", ""),
                notes=form.cleaned_data.get("notes", ""),
            )
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
        else:
            messages.success(request, success.format(item=item))
            return redirect("inventory_item_detail", pk=item.pk)
    return render(request, "portal/inventory_movement_form.html", {
        "form": form, "item": item, "title": title.format(item=item),
    })


@login_required
def inventory_receive(request, pk):
    return _movement(request, pk, title="Receive {item.name}", form_class=InventoryMovementForm,
                     operation=receive_inventory, success="Stock received for {item.name}.")


@login_required
def inventory_use(request, pk):
    return _movement(request, pk, title="Use {item.name}", form_class=InventoryMovementForm,
                     operation=consume_inventory, success="Inventory use recorded for {item.name}.")


@login_required
def inventory_adjust(request, pk):
    return _movement(request, pk, title="Adjust {item.name}", form_class=InventoryAdjustmentForm,
                     operation=adjust_inventory, success="Physical count updated for {item.name}.")


@login_required
def inventory_transfer(request, pk):
    _manager(request.user)
    team = _team(request.user)
    item = get_object_or_404(InventoryItem, pk=pk, team=team)
    form = InventoryTransferForm(request.POST or None, team=team)
    if request.method == "POST" and form.is_valid():
        try:
            transfer_inventory(
                item=item,
                source_space=form.cleaned_data["source_space"],
                destination_space=form.cleaned_data["destination_space"],
                quantity=form.cleaned_data["quantity"],
                reference=form.cleaned_data.get("reference", ""),
                notes=form.cleaned_data.get("notes", ""),
            )
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
        else:
            messages.success(request, f"{item.name} transferred.")
            return redirect("inventory_item_detail", pk=item.pk)
    return render(request, "portal/inventory_movement_form.html", {
        "form": form, "item": item, "title": f"Transfer {item.name}",
    })
