from .models import User, Category, Listing, Comment, Bid
from django.forms import ModelForm
from typing import KeysView, Text
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.db.models.base import Model
from django.forms.widgets import FileInput, Input, NumberInput, Select, TextInput, Textarea
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.forms import HiddenInput
from django import forms

import os

from decouple import config


def index(request):
    listings = Listing.objects.filter(active=True).order_by("-id")

    for l in listings:
        if request.user in l.currentlyWatching.all():
            l.watched = True  # used for when the user clicks on the listing
        else:
            l.watched = False

    return render(request, "auctions/index.html", {
        "listings": listings
    })


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")


class ListingForm(ModelForm):
    class Meta:
        model = Listing
        fields = ['title', 'description', 'category',
                  'startBid', 'imageURL', 'auction_image']

        widgets = {'seller': HiddenInput(attrs={'style': "display:block"}),
                   'description': Textarea(attrs={'cols': 100, 'rows': 3, 'class': "descriptionTextBox"}),
                   'title': TextInput(attrs={'class': "descriptionTextBox", 'style': 'border-radius:3px, width:90vw'}),
                   'startBid': NumberInput(attrs={'class': "descriptionTextBox", 'style': 'border-radius:3px, width:90vw'}),
                   'imageURL': TextInput(attrs={'class': "descriptionTextBox", 'style': 'border-radius:3px, width:90vw'}),
                   'auction_image': FileInput(),
                   'category': Select(attrs={'class': "dropdownCategory"})
                   }


class BidForm(ModelForm):
    class Meta:
        model = Bid
        fields = ['price']


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': Textarea(attrs={'cols': 100, 'rows': 3, 'style': "box-sizing:border-box; width: 100%;", 'class': "commentBox"}),
        }


def newListing(request):

    listing = ListingForm()

    if request.method == "POST":

        listing = ListingForm(request.POST, request.FILES)
        print(request.POST)
        if listing.is_valid():

            listing = listing.save(commit=False)
            listing.seller = request.user
            listing.save()
            listing.currentBid = -1
            listing.save()

        return render(request, "auctions/createListing.html", {
            "form": ListingForm(),
            "created": True
        })
    else:
        return render(request, "auctions/createListing.html", {
            "form": ListingForm(),
            "created": False
        })


def listing(request, id):

    listing = Listing.objects.get(pk=id)

    bids = Bid.objects.all()

    if request.user in listing.currentlyWatching.all():
        listing.watched = True
    else:
        listing.watched = False

    if request.method == "POST":
        if request.POST.get('formType') == "comment":
            comment = CommentForm(request.POST)
            if comment.is_valid():
                comment = comment.save(commit=False)
                comment.user = request.user
                comment.listing = Listing.objects.get(pk=id)
                comment.save()

        elif request.POST.get('formType') == "watchlist":
            # current listing
            if listing.watched:
                listing.currentlyWatching.remove(request.user)
                listing.watched = False
            else:
                listing.currentlyWatching.add(request.user)
                listing.watched = True

        elif request.POST.get('formType') == "bid":
            price = float(request.POST['price'])
            if priceIsEnough(price, listing):
                listing.currentBid = price
                Listing.objects.get(pk=id).currentBid = price
                form = BidForm(request.POST)
                bid = form.save(commit=False)
                bid.listing = listing
                bid.user = request.user

                # delete all old bids
                Bid.objects.filter(user=request.user).delete()

                bid.save()
                listing.save()
                return render(request, "auctions/listing.html", {
                    "listing": listing,
                    "comments": Listing.objects.get(pk=id).getComments.all(),
                    "commentForm": CommentForm(),
                    "bidForm": BidForm(),
                    "bidSuccess": 1
                })
                # bidsuccess 1 is success
                # bidsuccess 2 is false
                # bidsuccess 0 is did not bid
            else:
                return render(request, "auctions/listing.html", {
                    "listing": listing,
                    "comments": Listing.objects.get(pk=id).getComments.all(),
                    "commentForm": CommentForm(),
                    "bidForm": BidForm(),
                    "bidSuccess": 2
                })

        elif request.POST.get('formType') == "close":
            # close bid
            if request.user == listing.seller:
                listing.active = False
                bid = Bid.objects.filter(listing=listing).last()
                if not bid is None:
                    listing.buyer = bid.user
                listing.save()

    return render(request, "auctions/listing.html", {
        "listing": listing,
        "comments": Listing.objects.get(pk=id).getComments.all(),
        "commentForm": CommentForm(),
        "bidForm": BidForm(),
        "bidSuccess": 0
    })


def priceIsEnough(price, listing):
    if price >= listing.startBid and price > listing.currentBid:
        return True
    return False


def watchlist(request):
    if not request.user.is_anonymous:
        listings = request.user.listingsWatched.all().order_by("-id")

        return render(request, "auctions/watchlist.html", {
            "listings": listings,
        })
    else:
        return render(request, "auctions/watchlist.html")


def categories(request):

    categories = Category.objects.all()

    return render(request, "auctions/categories.html", {
        "categories": categories,
    })


def findWithCategory(request, c):

    list = Listing.objects.all()

    listings = []

    for l in list:
        if l.category.Category == c and l.active:
            listings.append(l)

    return render(request, "auctions/index.html", {
        "listings": listings,
    })
