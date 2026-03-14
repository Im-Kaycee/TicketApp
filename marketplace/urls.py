from django.urls import path
from .views import (
    CancelListingView,
    CreateListingView,
    MarketplaceListView,
    PurchaseListingView,
)

urlpatterns = [
    path("", MarketplaceListView.as_view(), name="marketplace-list"),
    path("list/", CreateListingView.as_view(), name="create-listing"),
    path("purchase/", PurchaseListingView.as_view(), name="purchase-listing"),
    path("<int:listing_id>/cancel/", CancelListingView.as_view(), name="cancel-listing"),
    #path("webhook/", MarketplaceWebhookView.as_view(), name="marketplace-webhook"),
]