from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.deletion import CASCADE
from django.utils import timezone


class User(AbstractUser):
    pass


class Category(models.Model):
    Category = models.CharField(max_length=300)

    def __str__(self):
        return str(self.Category)


class Listing(models.Model):
    title = models.CharField(max_length=64)
    description = models.CharField(blank=True, max_length=500)
    active = models.BooleanField(default=True)
    #date = models.DateTimeField(default=timezone.now)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="similar", blank=True)
    startBid = models.FloatField()
    currentBid = models.FloatField(null=True, blank=True)
    currentlyWatching = models.ManyToManyField(
        User, blank=True, related_name="listingsWatched")
    # do not delete the user when deleting the buyer from this listing (models.Protect)
    buyer = models.ForeignKey(
        User, blank=True, on_delete=models.PROTECT, null=True)
    seller = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="sellerListings", null=True, blank=True)
    imageURL = models.CharField(blank=True, max_length=500)

    def __str__(self):
        return f"{self.title}- starting: {self.startBid}, current: {self.currentBid}"


class Comment(models.Model):
    text = models.CharField(blank=False, max_length=500)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="getComments")


class Bid(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="bid_user")
    listing = models.ForeignKey(
        Listing, on_delete=CASCADE, related_name="bid_listing")
    price = models.FloatField()
