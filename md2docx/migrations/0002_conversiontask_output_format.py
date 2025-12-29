from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('md2docx', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversiontask',
            name='output_format',
            field=models.CharField(default='docx', max_length=32),
        ),
    ]
