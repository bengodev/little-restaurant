from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponse

from .models import Menu
from .forms import BookingForm
# Create your views here.


def home(request):
    return render(request, 'index.html')


def about(request):
    return render(request, 'about.html')


def book(request):
    form = BookingForm()

    if request.method == 'POST':
        form = BookingForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, 'Your booking was successful!')
            return redirect('book')
    return render(request, 'book.html', {'form': form})


def menu(request):
    menu_data = Menu.objects.all()
    return render(request, 'menu.html', {'menu_items': menu_data})


def menu_item(request, item_id=None):
    if item_id:
        menu_item = Menu.objects.get(id=item_id)
    else:
        menu_item = ''

    return render(request, 'menu_item.html', {'menu_item': menu_item})
