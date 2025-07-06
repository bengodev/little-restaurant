from django.db import models

# Create your models here.


class Menu(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.IntegerField()
    picture = models.ImageField(
        upload_to='menu_images/', blank=True, null=True)
    available = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    date = models.DateField(auto_now=True)
    guests = models.IntegerField()
    comments = models.CharField(max_length=1000, blank=True, null=True)

    def __str__(self):
        return f"Booking for {self.name} on {self.date}"
