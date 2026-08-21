# Keeps the historical primary-key state aligned with Django's BigAutoField default.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_signupemailotp'),
    ]

    operations = [
        migrations.AlterField(model_name='customer_signup', name='id', field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        migrations.AlterField(model_name='service', name='id', field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        migrations.AlterField(model_name='serviceaddress', name='id', field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        migrations.AlterField(model_name='servicedetail', name='id', field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        migrations.AlterField(model_name='servicerequest', name='id', field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        migrations.AlterField(model_name='technician_signup', name='id', field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        migrations.AlterField(model_name='techniciannotification', name='id', field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
    ]
