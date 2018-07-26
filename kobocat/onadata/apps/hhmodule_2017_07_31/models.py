from django.db import models
from django.contrib.auth.models import User
#from __future__ import unicode_literals

# Create your models here.


# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Remove `managed = False` lines if you wish to allow Django to create and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [appname]'
# into your database.


#************Household Module Models Start***************

from django.utils.encoding import python_2_unicode_compatible



class HhMember(models.Model):
    #id = models.BigIntegerField(primary_key=True)
    highest_education_level = models.ForeignKey('HighestEducationLevel')
    occupation = models.ForeignKey('Occupation', blank=True, null=True)
    member_relationship = models.ForeignKey('MemberRelationship')
    member_status = models.ForeignKey('MemberStatus', blank=True, null=True)
    household = models.ForeignKey('Household', blank=True, null=True)
    name = models.CharField(max_length=150)
    age = models.IntegerField()
    gender = models.IntegerField()
    member_id = models.CharField(max_length=19)
    disability = models.IntegerField()
    regular_attendence = models.IntegerField(blank=True, null=True)
    profile_photo = models.CharField(max_length=250, blank=True)
    mobile_no = models.CharField(max_length=20, blank=True)
    work_for_cash = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'hh_member'


class HhStatus(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=150)
    code = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.name
    class Meta:
        managed = False
        db_table = 'hh_status'

@python_2_unicode_compatible
class HhUseAssetGrant(models.Model):
    #id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=150)
    code = models.IntegerField(blank=True, null=True)
    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'hh_use_asset_grant'

@python_2_unicode_compatible
class HighestEducationLevel(models.Model):
    #id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=150)
    code = models.IntegerField(blank=True, null=True)
    def __str__(self):
        return self.name
    class Meta:
        managed = False
        db_table = 'highest_education_level'

@python_2_unicode_compatible
class MemberRelationship(models.Model):
    #id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=150)
    code = models.IntegerField(blank=True, null=True)
    def __str__(self):
        return self.name
    class Meta:
        managed = False
        db_table = 'member_relationship'

@python_2_unicode_compatible
class MemberStatus(models.Model):
    #id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=150)
    code = models.IntegerField(blank=True, null=True)
    def __str__(self):
        return self.name
    class Meta:
        managed = False
        db_table = 'member_status'

@python_2_unicode_compatible
class Occupation(models.Model):
    ##id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=150)
    code = models.IntegerField(blank=True, null=True)
    def __str__(self):
        return self.name
    class Meta:
        managed = False
        db_table = 'occupation'


@python_2_unicode_compatible
class GeoWard(models.Model):
    ##id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=150)
    code = models.IntegerField(blank=True, null=True)
    def __str__(self):
        return self.name
    class Meta:
        managed = False
        db_table = 'geo_ward'


class Household(models.Model):
    #id = models.BigIntegerField(primary_key=True)
    geo_ward = models.ForeignKey(GeoWard)
    hh_use_asset_grant = models.ForeignKey(HhUseAssetGrant, blank=True, null=True)
    hh_status = models.ForeignKey(HhStatus, blank=True, null=True)
    #hh_member_head = models.ForeignKey(HhMember, blank=True, null=True)
    holding_no = models.CharField(max_length=150)
    hh_member_number = models.IntegerField(blank=True, null=True)
    hh_serial = models.CharField(max_length=25, null=True)
    hh_id = models.CharField(max_length=17)
    hh_phone=models.CharField(max_length=20,null=True)
    class Meta:
        managed = False
        db_table = 'household'