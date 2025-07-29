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


# INSERT INTO app_book(name, phone, date, violation_image)
# VALUES(1, '2025-07-28', '20:00:00',
#        '/media/human_detection/2025-06-22-22-20-19_human_detection.jpg');

# Create postgresql Trigger function
# CREATE OR REPLACE FUNCTION notify_booking_change()
# RETURNS TRIGGER AS $$
# BEGIN
#     PERFORM pg_notify(
#         'booking_channel',
#         json_build_object(
#             'table', TG_TABLE_NAME,
#             'op',    TG_OP,
#             'data',  row_to_json(NEW)
#         )::text
#     );
#     RETURN NEW;
# END;
# $$ LANGUAGE plpgsql;

# To attach a table
# CREATE TRIGGER trg_booking_notify
# AFTER INSERT ON app_book
# FOR EACH ROW EXECUTE FUNCTION notify_booking_change();
