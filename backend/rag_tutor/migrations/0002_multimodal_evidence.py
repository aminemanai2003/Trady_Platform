from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rag_tutor", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tutordocument",
            name="file_type",
            field=models.CharField(max_length=20),
        ),
        migrations.AddField(
            model_name="tutordocument",
            name="modality",
            field=models.CharField(db_index=True, default="text", max_length=20),
        ),
        migrations.AddField(
            model_name="tutordocument",
            name="extraction_metadata_json",
            field=models.TextField(blank=True, default="{}"),
        ),
        migrations.AddField(
            model_name="documentchunk",
            name="modality",
            field=models.CharField(db_index=True, default="text", max_length=20),
        ),
        migrations.AddField(
            model_name="documentchunk",
            name="source_label",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="documentchunk",
            name="page_number",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="documentchunk",
            name="timestamp_start",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="documentchunk",
            name="timestamp_end",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="documentchunk",
            name="metadata_json",
            field=models.TextField(blank=True, default="{}"),
        ),
    ]
