from django.urls import path

from . import inventory_views

urlpatterns = [
    path("inventory/", inventory_views.inventory_list, name="inventory_list"),
    path("inventory/items/add/", inventory_views.inventory_item_create, name="inventory_item_create"),
    path("inventory/items/<int:pk>/", inventory_views.inventory_item_detail, name="inventory_item_detail"),
    path("inventory/items/<int:pk>/edit/", inventory_views.inventory_item_edit, name="inventory_item_edit"),
    path("inventory/items/<int:pk>/receive/", inventory_views.inventory_receive, name="inventory_receive"),
    path("inventory/items/<int:pk>/use/", inventory_views.inventory_use, name="inventory_use"),
    path("inventory/items/<int:pk>/adjust/", inventory_views.inventory_adjust, name="inventory_adjust"),
    path("inventory/items/<int:pk>/transfer/", inventory_views.inventory_transfer, name="inventory_transfer"),
    path("inventory/categories/add/", inventory_views.inventory_category_create, name="inventory_category_create"),
]
