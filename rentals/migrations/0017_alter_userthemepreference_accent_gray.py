from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0016_trigram_search_indexes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userthemepreference',
            name='accent',
            field=models.CharField(choices=[('purple', 'Blue + Purple'), ('orange', 'Orange'), ('gray', 'Grayscale')], default='purple', max_length=10, verbose_name='Aksen tema'),
        ),
    ]
