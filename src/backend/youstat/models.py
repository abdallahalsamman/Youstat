# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from __future__ import unicode_literals

from django.db import models
from django.contrib.postgres.fields import JSONField

class Channels(models.Model):
    id = models.AutoField(primary_key=True)
    channel_id = models.TextField(unique=True, db_index=True)
    video_ids = JSONField(blank=True)
    words_count = JSONField(blank=True)

    class Meta:
        db_table = 'channels'


class Videos(models.Model):
    id = models.AutoField(primary_key=True)
    video_id = models.TextField(unique=True, db_index=True)
    subtitle_original = models.TextField(blank=True, null=True)
    subtitle_original_formatted = models.TextField(blank=True, null=True)
    subtitle_original_lang = models.TextField(blank=True, null=True)
    subtitle_translated = models.TextField(blank=True, null=True)
    subtitle_translated_formatted = models.TextField(blank=True, null=True)
    words_count = JSONField(blank=True)

    class Meta:
        db_table = 'videos'
