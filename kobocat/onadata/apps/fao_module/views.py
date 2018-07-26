from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.db.models import Count, Q
from django.http import (
    HttpResponseRedirect, HttpResponse)
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, loader
from django.contrib.auth.models import User
from datetime import date, timedelta, datetime
# from django.utils import simplejson
import json
import logging
import sys
import operator
import pandas
from django.shortcuts import render
import numpy
import time
import datetime
from django.core.files.storage import FileSystemStorage
from django.core.urlresolvers import reverse
from django.db import (IntegrityError, transaction)
from django.db.models import ProtectedError
from django.shortcuts import redirect
from onadata.apps.main.models.user_profile import UserProfile
from onadata.apps.usermodule.forms import UserForm, UserProfileForm, ChangePasswordForm, UserEditForm, OrganizationForm, \
    OrganizationDataAccessForm, ResetPasswordForm
from onadata.apps.usermodule.models import UserModuleProfile, UserPasswordHistory, UserFailedLogin, Organizations, \
    OrganizationDataAccess
from django.contrib.auth.decorators import login_required, user_passes_test
from django import forms
# Menu imports
from onadata.apps.usermodule.forms import MenuForm
from onadata.apps.usermodule.models import MenuItem
# Unicef Imports
from onadata.apps.logger.models import Instance, XForm
# Organization Roles Import
from onadata.apps.usermodule.models import OrganizationRole, MenuRoleMap, UserRoleMap
from onadata.apps.usermodule.forms import OrganizationRoleForm, RoleMenuMapForm, UserRoleMapForm, UserRoleMapfForm
from django.forms.models import inlineformset_factory, modelformset_factory
from django.forms.formsets import formset_factory

from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from collections import OrderedDict
import os
from django.contrib.auth.models import User
from django.utils import *
import decimal

def __db_fetch_values(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = cursor.fetchall()
    cursor.close()
    return fetchVal


def __db_fetch_single_value(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = cursor.fetchone()
    cursor.close()
    return fetchVal[0]


def __db_fetch_values_dict(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = dictfetchall(cursor)
    cursor.close()
    return fetchVal


def __db_commit_query(query):
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    cursor.close()


def dictfetchall(cursor):
    desc = cursor.description
    return [
        OrderedDict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()]


def decimal_date_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        return obj
    raise TypeError


def getDistricts(request):
    division = request.POST.get('div')
    district_query = "select value,name from geo_cluster where loc_type = 2 and parent = " + str(division)
    district_data = json.dumps(__db_fetch_values_dict(district_query))
    return HttpResponse(district_data)


def getUpazilas(request):
    district = request.POST.get('dist')
    upazila_query = "select value,name from geo_cluster where loc_type = 3 and parent = " + str(district)
    upazila_data = json.dumps(__db_fetch_values_dict(upazila_query))
    return HttpResponse(upazila_data)



@login_required
def add_patients_disease_file_form(request):
    select_query = "select * from species"
    df = pandas.DataFrame()
    df = pandas.read_sql(select_query, connection)
    species_id = df.species_id.tolist()
    species_name = df.species_name.tolist()
    species = zip(species_id, species_name)
    return render(request, 'fao_module/add_patients_disease_file_form.html', {'species': species})


@login_required
def insert_patients_disease_file_form(request):
    if request.POST:
        myfile = request.FILES['patients_disease_file_name']
        url = "onadata/media/uploaded_files/"
        fs = FileSystemStorage(location=url)
        myfile.name = str(datetime.datetime.now()) + "_" + str(myfile.name)
        filename = fs.save(myfile.name, myfile)
        full_file_path = "onadata/media/uploaded_files/" + myfile.name
        df = pandas.DataFrame()
        xlsx = pandas.ExcelFile(full_file_path)
        df = xlsx.parse(0)
        for each in df.index:
            if str(df.loc[each]['species_id']) != "nan" and str(df.loc[each]['disease_name']) != "nan" and str(
                    int(df.loc[each]['species_id'])).isdigit() and not (str(df.loc[each]['disease_name'])[0].isdigit()):
                select_query = "select * from patients_disease where species_id=" + str(
                    int(df.loc[each]['species_id'])) + " and disease_name = '" + str(
                    df.loc[each]['disease_name'].replace("'", "''")) + "'"
                sf = pandas.DataFrame()
                sf = pandas.read_sql(select_query, connection)
                if sf.empty:
                    insert_query = "INSERT INTO patients_disease (species_id, disease_name) VALUES(" + str(
                        int(df.loc[each]['species_id'])) + ", '" + str(
                        df.loc[each]['disease_name'].replace("'", "''")) + "')"
                    __db_commit_query(insert_query)
        messages.success(request, '<i class="fa fa-check-circle"></i> Disease File has been uploaded successfully!',
                         extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/disease_list/")


@login_required
def disease_list(request):
    query = "select id,species_id,(select species_name from species where species_id = t.species_id),disease_name from patients_disease t"
    disease_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return render(request, 'fao_module/disease_list.html', {
        'disease_list': disease_list
    })


@login_required
def insert_patients_disease_form(request):
    if request.POST:
        insert_query = "INSERT INTO public.patients_disease(species_id, disease_name)VALUES("+str(request.POST.get('species'))+", '"+str(request.POST.get('disease_name'))+"')"
        __db_commit_query(insert_query)
    return HttpResponseRedirect("/fao_module/disease_list/")


@login_required
def edit_disease_list_form(request, disease_id):
    query = "select id,species_id,(select species_name from species where species_id = t.species_id),disease_name from patients_disease t where  id = " + str(disease_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    set_species_id = df.species_id.tolist()[0]
    set_species_name = df.species_name.tolist()[0]
    set_disease_name = df.disease_name.tolist()[0]
    select_query = "select * from species"
    df = pandas.DataFrame()
    df = pandas.read_sql(select_query, connection)
    species_id = df.species_id.tolist()
    species_name = df.species_name.tolist()
    species = zip(species_id, species_name)
    return render(request, 'fao_module/edit_disease_list_form.html',
                  {'set_species_id': set_species_id, 'set_species_name': set_species_name,
                   'set_disease_name': set_disease_name,
                   'species': species,'disease_id':int(disease_id)})


@login_required
def update_disease_list_form(request):
    if request.POST:
        update_query = "UPDATE public.patients_disease SET species_id="+str(request.POST.get('species'))+", disease_name='"+str(request.POST.get('disease_name'))+"' WHERE id="+str(request.POST.get('disease_id'))
        __db_commit_query(update_query)
        messages.success(request, '<i class="fa fa-check-circle"></i> Disease Info has been updated successfully!',
                     extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/disease_list/")


@login_required
def delete_disease_list_form(request, disease_id):
    # print("DS "+str(disease_id))
    delete_query = "delete from patients_disease where id = " + str(disease_id)
    __db_commit_query(delete_query)
    messages.success(request, '<i class="fa fa-check-circle"></i> Disease Info has been deleted successfully!',
                     extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/disease_list/")


@login_required
def add_patients_symptoms_file_form(request):
    select_query = "select * from species"
    df = pandas.DataFrame()
    df = pandas.read_sql(select_query, connection)
    species_id = df.species_id.tolist()
    species_name = df.species_name.tolist()
    species = zip(species_id, species_name)
    return render(request, 'fao_module/add_patients_symptoms_file_form.html',{'species':species})


@login_required
def insert_patients_symptoms_file_form(request):
    if request.POST:
        myfile = request.FILES['patients_symptoms_file_name']
        url = "onadata/media/uploaded_files/"
        fs = FileSystemStorage(location=url)
        myfile.name = str(datetime.datetime.now()) + "_" + str(myfile.name)
        filename = fs.save(myfile.name, myfile)
        full_file_path = "onadata/media/uploaded_files/" + myfile.name
        df = pandas.DataFrame()
        xlsx = pandas.ExcelFile(full_file_path)
        df = xlsx.parse(0)
        for each in df.index:
            if str(df.loc[each]['species_type']) != "nan" and str(df.loc[each]['symptoms']) != "nan" and str(
                    int(df.loc[each]['species_type'])).isdigit() and not (str(df.loc[each]['symptoms'])[0].isdigit()):
                select_query = "select * from patients_symptoms where species_type=" + str(
                    int(df.loc[each]['species_type'])) + " and symptoms = '" + str(df.loc[each]['symptoms'].replace("'", "''")) + "'"
                sf = pandas.DataFrame()
                sf = pandas.read_sql(select_query, connection)
                if sf.empty:
                    insert_query = "INSERT INTO patients_symptoms (species_type, symptoms) VALUES(" + str(
                        int(df.loc[each]['species_type'])) + ", '" + str(df.loc[each]['symptoms'].replace("'", "''")) + "')"
                    __db_commit_query(insert_query)
        messages.success(request, '<i class="fa fa-check-circle"></i> Symptom File has been uploaded successfully!',
                         extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/symptom_list/")


@login_required
def add_medicine_list_file_form(request):
    return render(request, 'fao_module/add_medicine_list_file_form.html')


@login_required
def insert_medicine_list_file_form(request):
    if request.POST:
        myfile = request.FILES['medicine_list_file_name']
        url = "onadata/media/uploaded_files/"
        fs = FileSystemStorage(location=url)
        myfile.name = str(datetime.datetime.now()) + "_" + str(myfile.name)
        filename = fs.save(myfile.name, myfile)
        full_file_path = "onadata/media/uploaded_files/" + myfile.name
        df = pandas.DataFrame()
        xlsx = pandas.ExcelFile(full_file_path)
        df = xlsx.parse(0)
        for each in df.index:
            if str(df.loc[each]['Type']) != "nan" and str(df.loc[each]['Trade Name']) != "nan":
            # if str(df.loc[each]['Broad Medicine Group']) != "nan" and str(df.loc[each]['Sub-Group']) != "nan" and str(
            #         df.loc[each]['Pharmacological Group']) != "nan" and str(df.loc[each]['Type']) != "nan" and str(
            #     df.loc[each]['Trade Name']) != "nan" and str(df.loc[each]['Generic composition']) != "nan" and str(
            #     df.loc[each]['Company']) != "nan" and str(df.loc[each]['Pharmacopia']) != "nan" and str(
            #     df.loc[each]['Dosage']) != "nan":
                if str(df.loc[each]['Pac size 1']) != "nan":
                    try:
                        insert_query = "INSERT INTO public.medicine_list (broad_medicine_group, sub_group, pharmacological_group, medicine_type, trade_name, pac_size, generic_composition, company_name, pharmacopia_name, dosage)VALUES('" + str(
                            df.loc[each]['Broad Medicine Group']).replace("'", "''") + "', '" + str(df.loc[each]['Sub-Group']).replace("'", "''") + "', '" + str(
                            df.loc[each]['Pharmacological Group']).replace("'", "''") + "', '" + str(df.loc[each]['Type']).replace("'", "''") + "', '" + str(
                            df.loc[each]['Trade Name']).replace("'", "''") + "', '" + str(df.loc[each]['Pac size 1']).replace("'", "''") + "', '" + str(
                            df.loc[each]['Generic composition']).replace("'", "''") + "', '" + str(df.loc[each]['Company']).replace("'", "''") + "', '" + str(
                            df.loc[each]['Pharmacopia']).replace("'", "''") + "', '" + str(df.loc[each]['Dosage']).replace("'", "''") + "')"
                        __db_commit_query(insert_query)
                    except:
                        continue
                if str(df.loc[each]['Pac size 2']) != "nan":
                    try:
                        insert_query = "INSERT INTO public.medicine_list (broad_medicine_group, sub_group, pharmacological_group, medicine_type, trade_name, pac_size, generic_composition, company_name, pharmacopia_name, dosage)VALUES('" + str(
                            df.loc[each]['Broad Medicine Group']).replace("'", "''") + "', '" + str(df.loc[each]['Sub-Group']).replace("'", "''") + "', '" + str(
                            df.loc[each]['Pharmacological Group']).replace("'", "''") + "', '" + str(df.loc[each]['Type']).replace("'", "''") + "', '" + str(
                            df.loc[each]['Trade Name']).replace("'", "''") + "', '" + str(df.loc[each]['Pac size 2']).replace("'", "''") + "', '" + str(
                            df.loc[each]['Generic composition']).replace("'", "''") + "', '" + str(df.loc[each]['Company']).replace("'", "''") + "', '" + str(
                            df.loc[each]['Pharmacopia']).replace("'", "''") + "', '" + str(df.loc[each]['Dosage']).replace("'", "''") + "')"
                        __db_commit_query(insert_query)
                    except:
                        continue
                if str(df.loc[each]['Pac size 3']) != "nan":
                    try:
                        insert_query = "INSERT INTO public.medicine_list (broad_medicine_group, sub_group, pharmacological_group, medicine_type, trade_name, pac_size, generic_composition, company_name, pharmacopia_name, dosage)VALUES('" + str(
                            df.loc[each]['Broad Medicine Group']).replace("'", "''") + "', '" + str(df.loc[each]['Sub-Group']).replace("'", "''") + "', '" + str(
                            df.loc[each]['Pharmacological Group']).replace("'", "''") + "', '" + str(df.loc[each]['Type']).replace("'", "''") + "', '" + str(
                            df.loc[each]['Trade Name']).replace("'", "''") + "', '" + str(df.loc[each]['Pac size 3']).replace("'", "''") + "', '" + str(
                            df.loc[each]['Generic composition']).replace("'", "''") + "', '" + str(df.loc[each]['Company']).replace("'", "''") + "', '" + str(
                            df.loc[each]['Pharmacopia']).replace("'", "''") + "', '" + str(df.loc[each]['Dosage']).replace("'", "''") + "')"
                        __db_commit_query(insert_query)
                    except:
                        continue
        messages.success(request,
                         '<i class="fa fa-check-circle"></i> Medicine List File has been uploaded successfully!',
                         extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/medicine_list/")


@login_required
def insert_medicine_list_form(request):
    if request.POST:
        if len(str(request.POST['pac_size_1'])):
            insert_query = "INSERT INTO public.medicine_list (broad_medicine_group, sub_group, pharmacological_group, medicine_type, trade_name, pac_size, generic_composition, company_name, pharmacopia_name, dosage)VALUES('" + str(
            request.POST['broad_medicine_group']) + "', '" + str(request.POST['sub_group']) + "', '" + str(
            request.POST['pharmacological_group']) + "', '" + str(request.POST['medicine_type']) + "', '" + str(
            request.POST['trade_name']) + "', '" + str(request.POST['pac_size_1']) + "', '" + str(
            request.POST['generic_composition']) + "', '" + str(request.POST['company_name']) + "', '" + str(
            request.POST['pharmacopia_name']) + "', '" + str(request.POST['dosage']) + "')"
            __db_commit_query(insert_query)
        if len(str(request.POST['pac_size_2'])):
            insert_query = "INSERT INTO public.medicine_list (broad_medicine_group, sub_group, pharmacological_group, medicine_type, trade_name, pac_size, generic_composition, company_name, pharmacopia_name, dosage)VALUES('" + str(
                request.POST['broad_medicine_group']) + "', '" + str(request.POST['sub_group']) + "', '" + str(
                request.POST['pharmacological_group']) + "', '" + str(request.POST['medicine_type']) + "', '" + str(
                request.POST['trade_name']) + "', '" + str(request.POST['pac_size_2'].replace("'", "''")) + "', '" + str(
                request.POST['generic_composition']) + "', '" + str(request.POST['company_name']) + "', '" + str(
                request.POST['pharmacopia_name']) + "', '" + str(request.POST['dosage']) + "')"
            __db_commit_query(insert_query)
        if len(str(request.POST['pac_size_3'])):
            insert_query = "INSERT INTO public.medicine_list (broad_medicine_group, sub_group, pharmacological_group, medicine_type, trade_name, pac_size, generic_composition, company_name, pharmacopia_name, dosage)VALUES('" + str(
                request.POST['broad_medicine_group']) + "', '" + str(request.POST['sub_group']) + "', '" + str(
                request.POST['pharmacological_group']) + "', '" + str(request.POST['medicine_type']) + "', '" + str(
                request.POST['trade_name']) + "', '" + str(request.POST['pac_size_3']) + "', '" + str(
                request.POST['generic_composition']) + "', '" + str(request.POST['company_name']) + "', '" + str(
                request.POST['pharmacopia_name']) + "', '" + str(request.POST['dosage']) + "')"
            __db_commit_query(insert_query)
        messages.success(request, '<i class="fa fa-check-circle"></i> New Medicine Info has been added successfully!',
                         extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/medicine_list/")


@login_required
def medicine_list(request):
    query = "select * from medicine_list"
    result = __db_fetch_values_dict(query)
    medicine_list = []
    for each in result:
        medicine_list.append(handle_nan(json.loads(json.dumps(each))))
    return render(request, 'fao_module/medicine_list.html', {
        'medicine_list': json.dumps(medicine_list)
    })


@login_required
def edit_medicine_list_form(request, medicine_id):
    query = "select * from medicine_list where  id = " + str(medicine_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    broad_medicine_group = set_nan_to_space(df.broad_medicine_group.tolist()[0])
    sub_group = set_nan_to_space(df.sub_group.tolist()[0])
    pharmacological_group = set_nan_to_space(df.pharmacological_group.tolist()[0])
    medicine_type = set_nan_to_space(df.medicine_type.tolist()[0])
    trade_name = set_nan_to_space(df.trade_name.tolist()[0])
    pac_size = set_nan_to_space(df.pac_size.tolist()[0])
    generic_composition = set_nan_to_space(df.generic_composition.tolist()[0])
    company_name = set_nan_to_space(df.company_name.tolist()[0])
    pharmacopia_name = set_nan_to_space(df.pharmacopia_name.tolist()[0])
    dosage = set_nan_to_space(df.dosage.tolist()[0])
    return render(request, 'fao_module/edit_medicine_list_form.html',
                  {'medicine_id': medicine_id, 'broad_medicine_group': broad_medicine_group,
                   'sub_group': sub_group,
                   'pharmacological_group': pharmacological_group,
                   'medicine_type': medicine_type,
                   'trade_name': trade_name,
                   'pac_size': pac_size,
                   'generic_composition': generic_composition,
                   'company_name': company_name,
                   'pharmacopia_name': pharmacopia_name,
                   'dosage': dosage})

@login_required
def update_medicine_list_form(request):
    if request.POST:
        delete_query = "delete from medicine_list where id = " + str(request.POST.get('medicine_id'))
        __db_commit_query(delete_query)
        insert_query = "INSERT INTO public.medicine_list (id,broad_medicine_group, sub_group, pharmacological_group, medicine_type, trade_name, pac_size, generic_composition, company_name, pharmacopia_name, dosage)VALUES(" + str(
            request.POST.get('medicine_id')) + ",'" + str(
            request.POST['broad_medicine_group'].replace("'", "''")) + "', '" + str(request.POST['sub_group'].replace("'", "''")) + "', '" + str(
            request.POST['pharmacological_group'].replace("'", "''")) + "', '" + str(request.POST['medicine_type'].replace("'", "''")) + "', '" + str(
            request.POST['trade_name'].replace("'", "''")) + "', '" + str(request.POST['pac_size'].replace("'", "''")) + "', '" + str(
            request.POST['generic_composition'].replace("'", "''")) + "', '" + str(request.POST['company_name'].replace("'", "''")) + "', '" + str(
            request.POST['pharmacopia_name'].replace("'", "''")) + "', '" + str(request.POST['dosage'].replace("'", "''")) + "')"
        __db_commit_query(insert_query)
        messages.success(request, '<i class="fa fa-check-circle"></i> Medicine Info has been updated successfully!',
                         extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/medicine_list/")


@login_required
def delete_medicine_list_form(request, medicine_id):
    delete_query = "delete from medicine_list where id = " + str(medicine_id)
    __db_commit_query(delete_query)
    messages.success(request, '<i class="fa fa-check-circle"></i> Medicine Info has been deleted successfully!',
                     extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/medicine_list/")


@login_required
def designations_list(request):
    query = "select id,designations_name,(select designations_name from fao_designations  where id = t.supervisor_id) as supervisor_name  from fao_designations t"
    designations_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return render(request, 'fao_module/designations_list.html', {
        'designations_list': designations_list
    })


@login_required
def add_designations_form(request):
    query = "select * from fao_designations"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    supervisor_id = df.id.tolist()
    supervisor_name = df.designations_name.tolist()
    supervisor = zip(supervisor_id, supervisor_name)
    return render(request, 'fao_module/add_designations_form.html', {'supervisor': supervisor})


@login_required
def insert_designations_form(request):
    if request.POST:
        if str(request.POST.get('supervisor_id')) != "No Parent":
            insert_query = "INSERT INTO public.fao_designations(designations_name,supervisor_id) VALUES('" + str(
                request.POST.get('designations_name')) + "'," + str(request.POST.get('supervisor_id')) + ")"
        else:
            insert_query = "INSERT INTO public.fao_designations(designations_name) VALUES('" + str(
                request.POST.get('designations_name')) + "')"
        __db_commit_query(insert_query)
        messages.success(request, '<i class="fa fa-check-circle"></i> New Designation has been added successfully!',
                         extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/designations_list/")


@login_required
def edit_designations_form(request, designations_id):
    query = "select designations_name,(select designations_name from fao_designations  where id = t.supervisor_id) as supervisor_name,supervisor_id  from fao_designations t where id=" + str(
        designations_id) + ""
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    set_designations_name = df.designations_name.tolist()[0]
    set_supervisor_name = df.supervisor_name.tolist()[0]
    set_supervisor_id = df.supervisor_id.tolist()[0]
    query = "select * from fao_designations"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    supervisor_id = df.id.tolist()
    supervisor_name = df.designations_name.tolist()
    supervisor = zip(supervisor_id, supervisor_name)
    return render(request, 'fao_module/edit_designations_form.html',
                  {'designations_id': int(designations_id), 'set_supervisor_name': set_supervisor_name,
                   'set_supervisor_id': set_supervisor_id, 'supervisor': supervisor,
                   'set_designations_name': set_designations_name})


@login_required
def update_designations_form(request):
    if request.POST:
        delete_query = "delete from fao_designations where id = " + str(request.POST.get('designations_id')) + ""
        __db_commit_query(delete_query)
        insert_query = "INSERT INTO public.fao_designations(id,designations_name,supervisor_id) VALUES(" + str(
            request.POST.get('designations_id')) + ",'" + str(
            request.POST.get('designations_name')) + "',"+str(request.POST.get('set_supervisor_id'))+")"
        __db_commit_query(insert_query)
        messages.success(request, '<i class="fa fa-check-circle"></i> Designation Info has been updated successfully!',
                         extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/designations_list/")


@login_required
def add_disaster_file_form(request):
    if request.POST:
        myfile = request.FILES['disaster_file_name']
        url = "onadata/media/uploaded_files/"
        fs = FileSystemStorage(location=url)
        myfile.name = str(datetime.datetime.now()) + "_" + str(myfile.name)
        filename = fs.save(myfile.name, myfile)
        full_file_path = "onadata/media/uploaded_files/" + myfile.name
        file = open(full_file_path, 'r')
        content = file.read()
        file.close()
        content = json.dumps({'content': content})
        return render(request, 'fao_module/disaster_clustering.html', {'content': content})
    return render(request, 'fao_module/add_disaster_file_form.html')


@login_required
def user_resource_map_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]
    all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
    org_id_list = [org.pk for org in all_organizations]
    organization_id = []
    organization_name = []
    for each in org_id_list:
        select_org_query = "select * from usermodule_organizations where id = "+str(each)
        df = pandas.DataFrame()
        df = pandas.read_sql(select_org_query,connection)
        organization_id.append(df.id.tolist()[0])
        organization_name.append(df.organization.tolist()[0])
    organization = zip(organization_id,organization_name)
    if request.POST:
        if len(request.POST.get('user_id_list')):
            new_menu = request.POST.getlist('menu_id')
            user_id_list = request.POST.get('user_id_list').split(',')
            for each in user_id_list:
                delete_query = "delete from user_resource_map where user_id = "+str(int(each))
                __db_commit_query(delete_query)
            for val in new_menu:
                splitVal = val.split("_")
                insert_query = "INSERT INTO public.user_resource_map(user_id, resource_id)VALUES("+str(int(splitVal[1]))+","+str(int(splitVal[0]))+")"
                __db_commit_query(insert_query)
            messages.success(request, '<i class="fa fa-check-circle"></i> User Resource Access List has been updated successfully!',
                         extra_tags='alert-success crop-both-side')
        return render(request, 'fao_module/user_resource_map_list.html', {'organization': organization,'set_org_id':int(request.POST.get('set_org_id'))})
    return render(request,'fao_module/user_resource_map_list.html',{'organization':organization,'set_org_id':-1})


def load_user_resource_data(request):
    select_user_id_query = "select (select username from auth_user where id = t.user_id), user_id from usermodule_usermoduleprofile t where organisation_name_id = " +str(request.POST.get('org_id'))
    user_list = json.dumps(__db_fetch_values_dict(select_user_id_query), default=decimal_date_default)
    user_list1 = json.loads(user_list)
    for each in user_list1:
        select_resource_id_query = "select resource_id from user_resource_map where user_id = " + str(each['user_id'])
        sf = pandas.DataFrame()
        sf = pandas.read_sql(select_resource_id_query, connection)
        resource_id = sf.resource_id.tolist()
        if len(resource_id):
            each['list']= resource_id
        else:
            each['list'] = []
    return HttpResponse(json.dumps({'user_list':user_list1}))

@login_required
def affected_area(request):
    content = []
    khulna_file = open("onadata/media/all_geojson/Khulna_div.geojson", 'r')
    khulna_content = khulna_file.read()
    khulna_file.close()
    chittagong_file = open("onadata/media/all_geojson/Chittagong_div.geojson", 'r')
    chittagong_content = chittagong_file.read()
    khulna_file.close()
    content.append(khulna_content)
    content.append(chittagong_content)
    json_content = json.dumps({'content':content})
    percentage = []
    query = "select * from geo_cluster where loc_type = 1"
    df = pandas.read_sql(query,connection)
    division = df.value.tolist()
    for each in division:
        query = "select * from organization_catchment_area_percentage where geoid = " + str(each)
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        if df.empty:
            continue
        percentage.append(df.percentage.tolist()[0])
    return render(request,'fao_module/affected_area.html',{'id':id,'json_content':json_content,'percentage':percentage})


def json_data_fetch(request):
    query = "select * from geo_cluster where loc_type = " + str(request.POST.get('loc_type')) + " and  parent = "+ str(request.POST.get('id'))
    df =pandas.DataFrame()
    df = pandas.read_sql(query,connection)
    children_list = df.value.tolist()
    content = []
    percentage = []
    for each in children_list:
        query = "select geojson_file_path from organization_catchment_area_geojson where geoid = " + str(each)
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        if df.empty:
            continue
        path = df.geojson_file_path.tolist()[0]
        file = open(path,'r')
        file_content = file.read()
        file.close()
        content.append(file_content)
        query = "select * from organization_catchment_area_percentage where geoid = " +str(each)
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        percentage.append(df.percentage.tolist()[0])
    return HttpResponse(json.dumps({'content': content,'percentage':percentage}))


@login_required
def disease_stat_chart(request):
    query = "with t as( select substring(date,4,char_length(date)-2) date,unnest(string_to_array(overlay(tentative_diagnosis placing '' from char_length(tentative_diagnosis)-1 for 2), '@@')) disease from public.vw_patient_registry), alldate as ( select distinct date from t limit 12),alldisease as ( select distinct disease from t ),res1 as (select date,disease from alldate,alldisease ), res2 as (select date ,disease,count(disease) as data from t group by date,disease) select distinct res1.date as month,res1.disease,coalesce(res2.data,0) as count from res1 left join res2 on res1.disease = res2.disease and res1.date = res2.date order by disease asc,res1.date asc"
    df = pandas.DataFrame()
    df = pandas.read_sql(query,connection)
    # xlsx = pandas.ExcelFile("onadata/media/uploaded_files/disease_highcharts_data.xlsx")
    # df = xlsx.parse(0)
    data = []
    name = []
    categories = []
    if not df.empty:
        for each in df['disease'].unique().tolist():
            data.append(df['count'][df['disease'] == each].tolist())
        categories = json.dumps(df['month'].unique().tolist(),default=decimal_date_default)
        name = json.dumps(df['disease'].unique().tolist(),default=decimal_date_default)
        data = json.dumps(data,default=decimal_date_default)
    # print "Categories"
    # print categories
    # print "Name"
    # print name
    # print "Data"
    # print data
    return render(request,'fao_module/disease_stat_chart.html',{'categories':categories,'name':name,'data':data})



def get_recursive_organization_children(organization, organization_list=[]):
    organization_list.append(organization)
    observables = Organizations.objects.filter(parent_organization=organization)
    for org in observables:
        if org not in organization_list:
            organization_list = list((set(get_recursive_organization_children(org, organization_list))))
    return list(set(organization_list))


@login_required
def symptom_list(request):
    query = "select id,species_type,(select species_name from species where species_id = t.species_type),symptoms from patients_symptoms t"
    symptom_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return render(request, 'fao_module/symptom_list.html', {
        'symptom_list': symptom_list
    })


@login_required
def insert_patients_symptom_form(request):
    if request.POST:
        insert_query = "INSERT INTO public.patients_symptoms(species_type, symptoms)VALUES("+str(request.POST.get('species'))+", '"+str(request.POST.get('symptom_name'))+"')"
        __db_commit_query(insert_query)
    return HttpResponseRedirect("/fao_module/symptom_list/")


@login_required
def edit_symptom_list_form(request, symptom_id):
    query = "select id,species_type,(select species_name from species where species_id = t.species_type),symptoms from patients_symptoms t where  id = " + str(symptom_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    set_species_id = df.species_type.tolist()[0]
    set_species_name = df.species_name.tolist()[0]
    set_symptom_name = df.symptoms.tolist()[0]
    select_query = "select * from species"
    df = pandas.DataFrame()
    df = pandas.read_sql(select_query, connection)
    species_id = df.species_id.tolist()
    species_name = df.species_name.tolist()
    species = zip(species_id, species_name)
    return render(request, 'fao_module/edit_symptom_list_form.html',
                  {'set_species_id': set_species_id, 'set_species_name': set_species_name,
                   'set_symptom_name': set_symptom_name,
                   'species': species,'symptom_id':int(symptom_id)})


@login_required
def update_symptom_list_form(request):
    if request.POST:
        update_query = "UPDATE public.patients_symptoms SET species_type="+str(request.POST.get('species'))+", symptoms='"+str(request.POST.get('symptom_name'))+"' WHERE id="+str(request.POST.get('symptom_id'))
        __db_commit_query(update_query)
        messages.success(request, '<i class="fa fa-check-circle"></i> Symptom Info has been updated successfully!',
                     extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/symptom_list/")


@login_required
def delete_symptom_list_form(request, symptom_id):
    delete_query = "delete from patients_symptoms where id = " + str(symptom_id)
    __db_commit_query(delete_query)
    messages.success(request, '<i class="fa fa-check-circle"></i> Symptom Info has been deleted successfully!',
                     extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/symptom_list/")

@login_required
def designation_resource_map_list(request):
    select_designation_query = "WITH RECURSIVE rec_d(id, designations_name,supervisor_id) AS ( SELECT fao_designations.id, fao_designations.designations_name,fao_designations.supervisor_id FROM fao_designations WHERE designations_name = 'DD' UNION ALL SELECT fao_designations.id, fao_designations.designations_name,fao_designations.supervisor_id FROM rec_d, fao_designations where fao_designations.supervisor_id = rec_d.id) SELECT id, designations_name,supervisor_id FROM rec_d"
    designations_list = json.loads(json.dumps(__db_fetch_values_dict(select_designation_query)))
    for each in designations_list:
        select_resource_query = "select * from designations_resource_map where designation_id = "+ str(each['id'])
        df = pandas.DataFrame()
        df = pandas.read_sql(select_resource_query,connection)
        each['list'] = df.resource_id.tolist()
    if request.POST:
        delete_query = "delete from designations_resource_map "
        __db_commit_query(delete_query)
        new_menu = request.POST.getlist('menu_id')
        # print(new_menu[1])
        for val in new_menu:
            splitVal = val.split("_")
            # print(val)
            insert_query = "INSERT INTO public.designations_resource_map(designation_id, resource_id)VALUES("+str(int(splitVal[1]))+","+str(int(splitVal[0]))+")"
            __db_commit_query(insert_query)
        messages.success(request, '<i class="fa fa-check-circle"></i> Designation Resource Access List has been updated successfully!',
                             extra_tags='alert-success crop-both-side')
        return HttpResponseRedirect("/fao_module/designation_resource_map_list/")
    return render(request,'fao_module/designation_resource_map_list.html',{'designations_list': json.dumps(designations_list)})


@login_required
def farm_assessment_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    # fetching all organization recursively of current_user
    all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
    org_id_list = [org.pk for org in all_organizations]

    # this geo_data is the variable for storing all geo location for current_user
    all_geo_id = []
    col_name = []
    json_data = []

    org_type_query = "select * from usermodule_organizations where id = " + str(current_user.organisation_name_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(org_type_query, connection)
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 1:
        select_query = "SELECT data_id, farm_id, CASE report_type WHEN '1' THEN 'First Assessment Report' WHEN '2' THEN 'Follow-up Report' END   AS report_type, date_initial_visit, (SELECT NAME  FROM geo_cluster  WHERE  value::text = division) AS division, (SELECT NAME  FROM geo_cluster  WHERE  value::text = district) AS district, (SELECT NAME  FROM geo_cluster  WHERE  value::text = upazila)  AS upazila, (SELECT NAME  FROM geo_cluster  WHERE  value::text = xunion) AS xunion, mouza, village, address, owner_name, mobile_owner FROM vw_farm_assessment"
        data = __db_fetch_values_dict(select_query)
        for each1 in data:
                json_data.append(handle_none(each1))
                # each1 contains a json dictionary.
                # each1.items() create (key,value) pair
                for key, value in each1.items():
                    if key not in col_name and key != "data_id":
                        # unique column name insert in col_name list
                        col_name.append(key)
        all_geo_id.append(1)
        return render(request, 'fao_module/farm_assessment_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})

    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 2:
        for each in org_id_list:
            query = "select geoid from organization_catchment_area where organization_id = " + str(each)
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
            if not df.empty:
                # check for duplicate geoid
                # every time a unique geoid is pushed in all_geo_id
                if df.geoid.tolist()[0] in all_geo_id:
                    continue
                # fetching data from forms_data
                select_query = "SELECT data_id, farm_id, CASE report_type WHEN '1' THEN 'First Assessment Report' WHEN '2' THEN 'Follow-up Report' END   AS report_type, date_initial_visit, (SELECT NAME  FROM geo_cluster  WHERE  value::text = division) AS division, (SELECT NAME  FROM geo_cluster  WHERE  value::text = district) AS district, (SELECT NAME  FROM geo_cluster  WHERE  value::text = upazila)  AS upazila, (SELECT NAME  FROM geo_cluster  WHERE  value::text = xunion) AS xunion, mouza, village, address, owner_name, mobile_owner FROM vw_farm_assessment where working_upazila_id = " + str(
                    df.geoid.tolist()[0])
                data = __db_fetch_values_dict(select_query)
                for each1 in data:
                    json_data.append(handle_none(each1))
                    # each1 contains a json dictionary.
                    # each1.items() create (key,value) pair
                    for key, value in each1.items():
                        if key not in col_name and key != "data_id":
                            # unique column name insert in col_name list
                            col_name.append(key)
                all_geo_id.append(df.geoid.tolist()[0])
        return render(request, 'fao_module/farm_assessment_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})
    message = "You have no access to this page"    
    return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def xls_report_creator_for_farm_assessment(request):
    all_geo_id = request.POST.getlist('all_geo_id')
    if len(all_geo_id):
        if int(all_geo_id[0]) == 1:
            query = "SELECT farm_id, CASE report_type WHEN '1' THEN 'First Assessment Report' WHEN '2' THEN 'Follow-up Report' END  AS report_type, date_initial_visit, (SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila)  AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion)  AS xunion, mouza, village, address, owner_name, mobile_owner, CASE farm_ownership_type WHEN '4' THEN 'Rental' WHEN '3' THEN 'Personal contract' WHEN '2' THEN 'Independent' WHEN '1' THEN 'Corporate contract' END  AS farm_ownership_type, CASE type_person_interviewed WHEN '1' THEN 'Owner' WHEN '2' THEN 'Farm manager' WHEN '3' THEN 'Farm worker' WHEN '4' THEN 'Dealer' END  AS type_person_interviewed, gps_lattitude, gps_longitude, Replace(type_species, '@@', ',')  AS type_species, Replace(type_chicken, '@@', ',')  AS type_chicken, standing_population_birds, maximum_farm_capacity_birds, CASE birds_production_purpose WHEN '1' THEN 'Egg' WHEN '2' THEN 'Meat' WHEN '3' THEN 'Egg & Meat' WHEN '4' THEN 'Breeder' WHEN '5' THEN 'Sport' WHEN '6' THEN 'Pet' END  AS birds_production_purpose, CASE age_arrival_farm WHEN '1' THEN 'DOC' WHEN '2' THEN 'Pullet' WHEN '3' THEN 'Adult' END  AS age_arrival_farm, CASE previously_avian_influenza_investigate WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS previously_avian_influenza_investigate, date_previously_avian_influenza_investigate, vaccine1_ai_vaccination_used, CASE schedule_vaccine1 WHEN '1' THEN 'Age basis:' WHEN '2' THEN 'Calendar basis' WHEN '3' THEN 'After outbreak' WHEN '4' THEN 'No schedule (farmer doesn''t know)' END  AS schedule_vaccine1, Replace(schedule_vaccine1_before_production, '@@', ',') AS schedule_vaccine1_before_production, Replace(schedule_vaccine1_after_production, '@@', ',') AS schedule_vaccine1_after_production, date1_last3_ai_vaccination1, date2_last3_ai_vaccination1, date3_last3_ai_vaccination1, vaccine2_ai_vaccination_used, CASE schedule_vaccine2 WHEN '1' THEN 'Age basis:' WHEN '2' THEN 'Calendar basis' WHEN '3' THEN 'After outbreak' WHEN '4' THEN 'No schedule (farmer doesn''t know)' END  AS schedule_vaccine2, Replace(schedule_vaccine2_before_production, '@@', ',') AS schedule_vaccine2_before_production, Replace(schedule_vaccine2_after_production, '@@', ',') AS schedule_vaccine2_after_production, date1_last3_ai_vaccination2, date2_last3_ai_vaccination2, date3_last3_ai_vaccination2, CASE vaccination_given_by WHEN '1' THEN 'Outside vaccinator' WHEN '2' THEN 'Farm Staff' WHEN '3' THEN 'Both' END  AS vaccination_given_by, CASE vaccine_means_verification WHEN '1' THEN 'Vaccination record' WHEN '2' THEN 'Semi-structure interview' END  AS vaccine_means_verification, CASE outside_worker_do_not_enter_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS outside_worker_do_not_enter_farm, CASE only_workers_approved_visitor_enter_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS only_workers_approved_visitor_enter_farm, CASE no_manure_collector_enter_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS no_manure_collector_enter_farm, CASE fenced_duck_chicken_proof WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS fenced_duck_chicken_proof, CASE dead_birds_disposed_safely WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS dead_birds_disposed_safely, CASE sign_posted WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS sign_posted, CASE no_vehical_in_out_production_area WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS no_vehical_in_out_production_area, CASE only_workers_enter_production_area WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS only_workers_enter_production_area, CASE visitors_enter_production_if_approve_manager WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS visitors_enter_production_if_approve_manager, CASE access_control_loading_production_sign_posted WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS access_control_loading_production_sign_posted, CASE footwear_left_outside WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS footwear_left_outside, CASE change_clothes_entering_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS change_clothes_entering_farm, CASE uses_dedicated_footwear WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS uses_dedicated_footwear, CASE shower_entering_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS shower_entering_farm, CASE returning_materials_cleaned WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS returning_materials_cleaned, CASE returning_materials_disinfect WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS returning_materials_disinfect, CASE dead_bird_management_practice WHEN '1' THEN 'buried' WHEN '2' THEN 'river' WHEN '3' THEN 'rubbish pit' WHEN '4' THEN 'pond' WHEN '5' THEN 'open place/bush' WHEN '6' THEN 'rubbish container' WHEN '7' THEN 'food/feed' END  AS dead_bird_management_practice, Replace(farm_entrance_means_verification, '@@', ',') AS farm_entrance_means_verification, antibacterial_usages_product1, CASE antibacterial_usage_salesman_product1 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Govt' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END  AS antibacterial_usage_salesman_product1, CASE antibacterial_usage_prevention_product1 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END  AS antibacterial_usage_prevention_product1, CASE antibacterial_usage_drinking_water_product1 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END  AS antibacterial_usage_drinking_water_product1, CASE antibacterial_frequency_product1 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' END  AS antibacterial_frequency_product1, antibacterial_usages_product2, CASE antibacterial_usage_salesman_product2 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Govt' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END  AS antibacterial_usage_salesman_product2, CASE antibacterial_usage_prevention_product2 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END  AS antibacterial_usage_prevention_product2, CASE antibacterial_usage_drinking_water_product2 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END  AS antibacterial_usage_drinking_water_product2, CASE antibacterial_frequency_product2 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' END  AS antibacterial_frequency_product2, antibacterial_usages_product3, CASE antibacterial_usage_salesman_product3 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Govt' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END  AS antibacterial_usage_salesman_product3, CASE antibacterial_usage_prevention_product3 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END antibacterial_usage_prevention_product3, CASE antibacterial_usage_drinking_water_product3 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END  AS antibacterial_usage_drinking_water_product3, CASE antibacterial_frequency_product3 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' END  AS antibacterial_frequency_product3, antibacterial_usages_product4, CASE antibacterial_usage_salesman_product4 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Govt' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END  AS antibacterial_usage_salesman_product4, CASE antibacterial_usage_prevention_product4 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END  AS antibacterial_usage_prevention_product4, CASE antibacterial_usage_drinking_water_product4 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END  AS antibacterial_usage_drinking_water_product4, CASE antibacterial_frequency_product4 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' END  AS antibacterial_frequency_product4, antibacterial_usages_product5, CASE antibacterial_usage_salesman_product5 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Govt' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END  AS antibacterial_usage_salesman_product5, CASE antibacterial_usage_prevention_product5 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END  AS antibacterial_usage_prevention_product5, CASE antibacterial_usage_drinking_water_product5 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END  AS antibacterial_usage_drinking_water_product5, CASE antibacterial_frequency_product5 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' END  AS antibacterial_frequency_product5, farmer_concern, image, (select username from auth_user where id::text = field_staff1) as field_staff1, (select username from auth_user where id::text = field_staff2) as field_staff2, (select username from auth_user where id::text = ackknowlwdge_by) as ackknowlwdge_by, (select username from auth_user where id::text = approved_by) as approved_by FROM vw_farm_assessment"
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
        else:
            df = pandas.DataFrame()
            for each in all_geo_id:
                query = "SELECT farm_id, CASE report_type WHEN '1' THEN 'First Assessment Report' WHEN '2' THEN 'Follow-up Report' END AS report_type, date_initial_visit,(SELECT name FROM geo_cluster WHERE value :: text = division) AS division, (SELECT name FROM geo_cluster WHERE value :: text = district) AS district, (SELECT name FROM geo_cluster WHERE value :: text = upazila) AS upazila, (SELECT name FROM geo_cluster WHERE value :: text = xunion) AS xunion, mouza, village, address, owner_name, mobile_owner, CASE farm_ownership_type WHEN '4' THEN 'Rental' WHEN '3' THEN 'Personal contract' WHEN '2' THEN 'Independent' WHEN '1' THEN 'Corporate contract' END AS farm_ownership_type, CASE type_person_interviewed WHEN '1' THEN 'Owner' WHEN '2' THEN 'Farm manager' WHEN '3' THEN 'Farm worker' WHEN '4' THEN 'Dealer' END AS type_person_interviewed, gps_lattitude, gps_longitude, Replace(type_species, '@@', ',') AS type_species, Replace(type_chicken, '@@', ',') AS type_chicken, standing_population_birds, maximum_farm_capacity_birds, CASE birds_production_purpose WHEN '1' THEN 'Egg' WHEN '2' THEN 'Meat' WHEN '3' THEN 'Egg & Meat' WHEN '4' THEN 'Breeder' WHEN '5' THEN 'Sport' WHEN '6' THEN 'Pet' END AS birds_production_purpose, CASE age_arrival_farm WHEN '1' THEN 'DOC' WHEN '2' THEN 'Pullet' WHEN '3' THEN 'Adult' END AS age_arrival_farm, CASE previously_avian_influenza_investigate WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS previously_avian_influenza_investigate, date_previously_avian_influenza_investigate, vaccine1_ai_vaccination_used, CASE schedule_vaccine1 WHEN '1' THEN 'Age basis:' WHEN '2' THEN 'Calendar basis' WHEN '3' THEN 'After outbreak' WHEN '4' THEN 'No schedule (farmer doesn''t know)' END AS schedule_vaccine1, Replace(schedule_vaccine1_before_production, '@@', ',') AS schedule_vaccine1_before_production, Replace(schedule_vaccine1_after_production, '@@', ',') AS schedule_vaccine1_after_production, date1_last3_ai_vaccination1, date2_last3_ai_vaccination1, date3_last3_ai_vaccination1, vaccine2_ai_vaccination_used, CASE schedule_vaccine2 WHEN '1' THEN 'Age basis:' WHEN '2' THEN 'Calendar basis' WHEN '3' THEN 'After outbreak' WHEN '4' THEN 'No schedule (farmer doesn''t know)' END AS schedule_vaccine2, Replace(schedule_vaccine2_before_production, '@@', ',') AS schedule_vaccine2_before_production, Replace(schedule_vaccine2_after_production, '@@', ',') AS schedule_vaccine2_after_production, date1_last3_ai_vaccination2, date2_last3_ai_vaccination2, date3_last3_ai_vaccination2, CASE vaccination_given_by WHEN '1' THEN 'Outside vaccinator' WHEN '2' THEN 'Farm Staff' WHEN '3' THEN 'Both' END AS vaccination_given_by, Replace(vaccine_means_verification, '@@', ',') AS vaccine_means_verification, CASE outside_worker_do_not_enter_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS outside_worker_do_not_enter_farm, CASE only_workers_approved_visitor_enter_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS only_workers_approved_visitor_enter_farm, CASE no_manure_collector_enter_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS no_manure_collector_enter_farm, CASE fenced_duck_chicken_proof WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS fenced_duck_chicken_proof, CASE dead_birds_disposed_safely WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS dead_birds_disposed_safely, CASE sign_posted WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS sign_posted, CASE no_vehical_in_out_production_area WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS no_vehical_in_out_production_area, CASE only_workers_enter_production_area WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS only_workers_enter_production_area, CASE visitors_enter_production_if_approve_manager WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS visitors_enter_production_if_approve_manager, CASE access_control_loading_production_sign_posted WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS access_control_loading_production_sign_posted, CASE footwear_left_outside WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS footwear_left_outside, CASE change_clothes_entering_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS change_clothes_entering_farm, CASE uses_dedicated_footwear WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS uses_dedicated_footwear, CASE shower_entering_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS shower_entering_farm, CASE returning_materials_cleaned WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS returning_materials_cleaned, CASE returning_materials_disinfect WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS returning_materials_disinfect, CASE dead_bird_management_practice WHEN '1' THEN 'buried' WHEN '2' THEN 'river' WHEN '3' THEN 'rubbish pit' WHEN '4' THEN 'pond' WHEN '5' THEN 'open place/bush' WHEN '6' THEN 'rubbish container' WHEN '7' THEN 'food/feed' END AS dead_bird_management_practice, Replace(farm_entrance_means_verification, '@@', ',') AS farm_entrance_means_verification, antibacterial_usages_product1, CASE antibacterial_usage_salesman_product1 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Upazila Vet Hosp' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END AS antibacterial_usage_salesman_product1, CASE antibacterial_usage_prevention_product1 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END AS antibacterial_usage_prevention_product1, CASE antibacterial_usage_drinking_water_product1 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END AS antibacterial_usage_drinking_water_product1, CASE antibacterial_frequency_product1 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' WHEN '7' THEN '3 Times a Day' END AS antibacterial_frequency_product1, antibacterial_usages_product2, CASE antibacterial_usage_salesman_product2 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Upazila Vet Hosp' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END AS antibacterial_usage_salesman_product2, CASE antibacterial_usage_prevention_product2 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END AS antibacterial_usage_prevention_product2, CASE antibacterial_usage_drinking_water_product2 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END AS antibacterial_usage_drinking_water_product2, CASE antibacterial_frequency_product2 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' WHEN '7' THEN '3 Times a Day' END AS antibacterial_frequency_product2, antibacterial_usages_product3, CASE antibacterial_usage_salesman_product3 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Upazila Vet Hosp' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END AS antibacterial_usage_salesman_product3, CASE antibacterial_usage_prevention_product3 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END antibacterial_usage_prevention_product3, CASE antibacterial_usage_drinking_water_product3 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END AS antibacterial_usage_drinking_water_product3, CASE antibacterial_frequency_product3 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' WHEN '7' THEN '3 Times a Day' END AS antibacterial_frequency_product3, antibacterial_usages_product4, CASE antibacterial_usage_salesman_product4 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Upazila Vet Hosp' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END AS antibacterial_usage_salesman_product4, CASE antibacterial_usage_prevention_product4 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END AS antibacterial_usage_prevention_product4, CASE antibacterial_usage_drinking_water_product4 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END AS antibacterial_usage_drinking_water_product4, CASE antibacterial_frequency_product4 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' WHEN '7' THEN '3 Times a Day' END AS antibacterial_frequency_product4, antibacterial_usages_product5, CASE antibacterial_usage_salesman_product5 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Upazila Vet Hosp' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END AS antibacterial_usage_salesman_product5, CASE antibacterial_usage_prevention_product5 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END AS antibacterial_usage_prevention_product5, CASE antibacterial_usage_drinking_water_product5 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END AS antibacterial_usage_drinking_water_product5, CASE antibacterial_frequency_product5 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' WHEN '7' THEN '3 Times a Day' END AS antibacterial_frequency_product5, farmer_concern, image, (select username from auth_user where id::text = field_staff1) as field_staff1, (select username from auth_user where id::text = field_staff2) as field_staff2, (select username from auth_user where id::text = ackknowlwdge_by) as ackknowlwdge_by, (select username from auth_user where id::text = approved_by) as approved_by FROM vw_farm_assessment where working_upazila_id = " + str(each)
                temp_df = pandas.DataFrame()
                temp_df = pandas.read_sql(query, connection)
                if not temp_df.empty:
                    df = df.append(temp_df, ignore_index=True)
        writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        writer.save()
        f = open('onadata/media/uploaded_files/output.xlsx', 'r')
        response = HttpResponse(f, mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=Farm Assessment.xls'
        return response
    else:
        message = "You have no access to this page"    
        return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def avian_influenza_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    # fetching all organization recursively of current_user
    all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
    org_id_list = [org.pk for org in all_organizations]

    # this geo_data is the variable for storing all geo location for current_user
    all_geo_id = []
    col_name = []
    json_data = []

    org_type_query = "select * from usermodule_organizations where id = " + str(current_user.organisation_name_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(org_type_query, connection)

    # For CO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 1:
        select_query = "SELECT data_id,investigation_id, date_sample_collected, (SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, mouza, village, contact_person_name, title_position, contact_person_mobile, CASE sex WHEN '1' THEN 'Male' WHEN '2' THEN 'Female' END AS sex, laboratory_name_sample_sent_to, sample_collected_by_name FROM vw_ai_sample_submission"
        data = __db_fetch_values_dict(select_query)
        for each1 in data:
                json_data.append(handle_none(each1))
                # each1 contains a json dictionary.
                # each1.items() create (key,value) pair
                for key, value in each1.items():
                    if key not in col_name and key != "data_id":
                        # unique column name insert in col_name list
                        col_name.append(key)
        all_geo_id.append(1)
        return render(request, 'fao_module/avian_influenza_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})

    # For ULO/LO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 2:
        for each in org_id_list:
            query = "select geoid from organization_catchment_area where organization_id = " + str(each)
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
            if not df.empty:
                # check for duplicate geoid
                # every time a unique geoid is pushed in all_geo_id
                if df.geoid.tolist()[0] in all_geo_id:
                    continue
                # fetching data from forms_data
                select_query = "SELECT data_id,investigation_id, date_sample_collected, (SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, mouza, village, contact_person_name, title_position, contact_person_mobile, CASE sex WHEN '1' THEN 'Male' WHEN '2' THEN 'Female' END AS sex, laboratory_name_sample_sent_to, sample_collected_by_name FROM vw_ai_sample_submission where working_upazila_id = " + str(
                    df.geoid.tolist()[0])
                data = __db_fetch_values_dict(select_query)
                for each1 in data:
                    json_data.append(handle_none(each1))
                    # each1 contains a json dictionary.
                    # each1.items() create (key,value) pair
                    for key, value in each1.items():
                        if key not in col_name and key != "data_id":
                            # unique column name insert in col_name list
                            col_name.append(key)
                all_geo_id.append(df.geoid.tolist()[0])
        return render(request, 'fao_module/avian_influenza_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})
    message = "You have no access to this page"    
    return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def xls_report_creator_for_avian_influenza(request):
    all_geo_id = request.POST.getlist('all_geo_id')
    if len(all_geo_id):
        if int(all_geo_id[0]) == 1:
            # for CO users
            query = "SELECT investigation_id, date_sample_collected, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = division) AS division, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = district) AS district, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = upazila)  AS upazila, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = xunion)   AS xunion, mouza, village, contact_person_name, title_position, contact_person_mobile, sex, gps_lattitude, gps_longitude, cases_occur_production_system, other_cases_occur_production_system, has_farm_previously_assessed, date_previously_assessed, deshi_chicken_sample_number, deshi_chicken_sample_type_description, deshi_chicken_sample_ID, sonali_chicken_sample_number, sonali_chicken_sample_type_description, sonali_chicken_sample_ID, brown_comm_chicken_sample_number, brown_comm_chicken_sample_type_description, brown_comm_sample_ID, white_comm_chicken_sample_number, white_comm_chicken_sample_type_description, white_comm_sample_ID, duck_number_sample, duck_sample_type_description, duck_sample_ID, environment, environment_sample_number, environment_sample_type_description, environment_sample_ID, other, other_sample_number, other_sample_type_description, other_sample_ID, laboratory_name_sample_sent_to, sample_collected_by_name, sample_received_by, sample_received_date, laboratory_sample_ID, (select organization from usermodule_organizations where id::text = lab_info) as lab_name, species_name_id FROM  vw_ai_sample_submission"
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
        else:
            # for ULO/LO users
            df = pandas.DataFrame()
            for each in all_geo_id:
                query = "SELECT investigation_id, date_sample_collected, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = division) AS division, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = district) AS district, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = upazila)  AS upazila, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = xunion)   AS xunion, mouza, village, contact_person_name, title_position, contact_person_mobile, sex, gps_lattitude, gps_longitude, cases_occur_production_system, other_cases_occur_production_system, has_farm_previously_assessed, date_previously_assessed, deshi_chicken_sample_number, deshi_chicken_sample_type_description, deshi_chicken_sample_ID, sonali_chicken_sample_number, sonali_chicken_sample_type_description, sonali_chicken_sample_ID, brown_comm_chicken_sample_number, brown_comm_chicken_sample_type_description, brown_comm_sample_ID, white_comm_chicken_sample_number, white_comm_chicken_sample_type_description, white_comm_sample_ID, duck_number_sample, duck_sample_type_description, duck_sample_ID, environment, environment_sample_number, environment_sample_type_description, environment_sample_ID, other, other_sample_number, other_sample_type_description, other_sample_ID, laboratory_name_sample_sent_to, sample_collected_by_name, sample_received_by, sample_received_date, laboratory_sample_ID, (select organization from usermodule_organizations where id::text = lab_info) as lab_name, species_name_id FROM  vw_ai_sample_submission where working_upazila_id = " + str(each)
                temp_df = pandas.DataFrame()
                temp_df = pandas.read_sql(query, connection)
                if not temp_df.empty:
                    df = df.append(temp_df, ignore_index=True)
        writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        writer.save()
        f = open('onadata/media/uploaded_files/output.xlsx', 'r')
        response = HttpResponse(f, mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=Avian Influenza.xls'
        return response
    else:
        message = "You have no access to this page"    
        return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def patient_registry_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    # fetching all organization recursively of current_user
    all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
    org_id_list = [org.pk for org in all_organizations]

    # this geo_data is the variable for storing all geo location for current_user
    all_geo_id = []
    col_name = []
    json_data = []

    org_type_query = "select * from usermodule_organizations where id = " + str(current_user.organisation_name_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(org_type_query, connection)

    # For CO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 1:
        select_query = "SELECT data_id,date, CASE entry_type WHEN '1' THEN 'New Patient' WHEN '2' THEN 'Follow Up' END AS entry_type, (SELECT NAME  FROM   geo_cluster  WHERE  value = division)                               AS division, (SELECT NAME  FROM   geo_cluster  WHERE  value = district)                               AS district, (SELECT NAME  FROM   geo_cluster  WHERE  value = upazila) AS upazila, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = xunion)                                 AS xunion, village, owner_name, mobile, case species_type WHEN '10' THEN other_species_livestock WHEN '40' THEN other_species_poultry ELSE (select species_name from species where species_id::text = species_type) end as species_type, CASE sex WHEN '1' THEN 'male' WHEN '2' THEN 'Female' WHEN '3' THEN 'Mixed' END AS sex, (select username from auth_user where id = t.username::int) as username FROM  PUBLIC.vw_patient_registry t"
        data = __db_fetch_values_dict(select_query)
        for each1 in data:
                json_data.append(handle_none(each1))
                # each1 contains a json dictionary.
                # each1.items() create (key,value) pair
                for key, value in each1.items():
                    if key not in col_name and key != "data_id":
                        # unique column name insert in col_name list
                        col_name.append(key)
        all_geo_id.append(1)
        return render(request, 'fao_module/patient_registry_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})

    # For ULO/LO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 2:
        for each in org_id_list:
            query = "select geoid from organization_catchment_area where organization_id = " + str(each)
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
            if not df.empty:
                # check for duplicate geoid
                # every time a unique geoid is pushed in all_geo_id
                if df.geoid.tolist()[0] in all_geo_id:
                    continue
                # fetching data from forms_data
                select_query = "SELECT data_id,date, CASE entry_type WHEN '1' THEN 'New Patient' WHEN '2' THEN 'Follow Up' END AS entry_type, (SELECT NAME  FROM   geo_cluster  WHERE  value = division)                               AS division, (SELECT NAME  FROM   geo_cluster  WHERE  value = district)                               AS district, (SELECT NAME  FROM   geo_cluster  WHERE  value = upazila) AS upazila, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = xunion)                                 AS xunion, village, owner_name, mobile, case species_type WHEN '10' THEN other_species_livestock WHEN '40' THEN other_species_poultry ELSE (select species_name from species where species_id::text = species_type) end as species_type, CASE sex WHEN '1' THEN 'male' WHEN '2' THEN 'Female' WHEN '3' THEN 'Mixed' END AS sex, (select username from auth_user where id = t.username::int) as username FROM  PUBLIC.vw_patient_registry t where working_upazila_id = " + str(
                    df.geoid.tolist()[0])
                data = __db_fetch_values_dict(select_query)
                for each1 in data:
                    json_data.append(handle_none(each1))
                    # each1 contains a json dictionary.
                    # each1.items() create (key,value) pair
                    for key, value in each1.items():
                        if key not in col_name and key != "data_id":
                            # unique column name insert in col_name list
                            col_name.append(key)
                all_geo_id.append(df.geoid.tolist()[0])
        return render(request, 'fao_module/patient_registry_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})
    message = "You have no access to this page"    
    return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def xls_report_creator_for_patient_registry(request):
    all_geo_id = request.POST.getlist('all_geo_id')
    if len(all_geo_id):
        if int(all_geo_id[0]) == 1:
            # for CO users
            query = "SELECT form_data_id patient_id,date, owner_name, father_name, CASE entry_type WHEN '1' THEN 'New Patient' WHEN '2' THEN 'Follow Up' END AS entry_type, (SELECT NAME  FROM   geo_cluster  WHERE  value = division) AS division, (SELECT NAME FROM geo_cluster  WHERE  value = district) AS district, (SELECT NAME  FROM   geo_cluster  WHERE  value = upazila)                                AS upazila, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = xunion)  AS xunion, village, mobile, case species_type WHEN '10' THEN other_species_livestock WHEN '40' THEN other_species_poultry ELSE (select species_name from species where species_id::text = species_type) end as species_type, case breed WHEN '1' THEN 'Local' WHEN '2' THEN 'Cross' WHEN '3' THEN 'Exotic' WHEN '4' THEN 'Heading' end as breed, case brought_hospital WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS brought_hospital, case production_type WHEN '1' THEN 'Commercial Broiler' WHEN '2' THEN 'Commercial Layer' WHEN '3' THEN 'Backyard' WHEN '4' THEN 'Recreation' WHEN '5' THEN production_type_other END AS production_type, case age_type_poultry WHEN '1' THEN week || ' weeks' ELSE year || ' years ' || month || ' months ' || day || ' days' END AS age, CASE sex WHEN '1' THEN 'male' WHEN '2' THEN 'Female' WHEN '3' THEN 'Mixed' END AS sex, productive_stage, CASE is_pregnant WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS is_pregnant, body_weight, owner_complain, Replace(clinical_sign_symptom, '@@', ',')                        AS clinical_sign_symptom, Replace(tentative_diagnosis, '@@', ',')  AS tentative_diagnosis, Replace(tratment, '@@', ',')  AS tratment, advice, remarks, (select username from auth_user where id = t.username::int) as username FROM  PUBLIC.vw_patient_registry t"
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
            writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
            df.to_excel(writer, sheet_name='Sheet1', index=False)
            writer.save()
            query = "WITH t AS( SELECT id, (datajson->>'herd_details')::json AS j FROM forms_data WHERE form_name='Patients Registry' AND (datajson->>'herd_details') is NOT NULL), t1 AS ( SELECT t.id, d.KEY, d.value::json AS value FROM t, json_each_text(t.j) AS d) SELECT value->>'patient_id' patient_id, value->>'age_range_type' age_range_type, value->>'age_range_from' adge_range_from, value->>'age_range_to' age_range_to, value->>'age_range_count' age_range_count FROM t1"
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
            df.to_excel(writer, sheet_name='Herd Details', index=False)
            writer.save()
        else:
            # for ULO/LO users
            df = pandas.DataFrame()
            for each in all_geo_id:
                query = "SELECT form_data_id patient_id,date, owner_name, father_name, CASE entry_type WHEN '1' THEN 'New Patient' WHEN '2' THEN 'Follow Up' END AS entry_type, (SELECT NAME  FROM   geo_cluster  WHERE  value = division) AS division, (SELECT NAME FROM geo_cluster  WHERE  value = district) AS district, (SELECT NAME  FROM   geo_cluster  WHERE  value = upazila) AS upazila, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = xunion)  AS xunion, village, mobile, case species_type WHEN '10' THEN other_species_livestock WHEN '40' THEN other_species_poultry ELSE (select species_name from species where species_id::text = species_type) end as species_type, case breed WHEN '1' THEN 'Local' WHEN '2' THEN 'Cross' WHEN '3' THEN 'Exotic' WHEN '4' THEN 'Heading' end as breed, flock, herd, dead, sick, case brought_hospital WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS brought_hospital, case production_type WHEN '1' THEN 'Commercial Broiler' WHEN '2' THEN 'Commercial Layer' WHEN '3' THEN 'Backyard' WHEN '4' THEN 'Recreation' WHEN '5' THEN production_type_other END AS production_type, case age_type_poultry WHEN '1' THEN week || ' weeks' ELSE year || ' years ' || month || ' months ' || day || ' days' END AS age, CASE sex WHEN '1' THEN 'male' WHEN '2' THEN 'Female' WHEN '3' THEN 'Mixed' END AS sex, productive_stage, CASE is_pregnant WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS is_pregnant, body_weight, owner_complain, Replace(clinical_sign_symptom, '@@', ',')                        AS clinical_sign_symptom, Replace(tentative_diagnosis, '@@', ',')  AS tentative_diagnosis, Replace(tratment, '@@', ',')  AS tratment, advice, remarks, (select username from auth_user where id = t.username::int) as username FROM  PUBLIC.vw_patient_registry t where working_upazila_id = " + str(each)
                temp_df = pandas.DataFrame()
                temp_df = pandas.read_sql(query, connection)
                if not temp_df.empty:
                    df = df.append(temp_df, ignore_index=True)
            writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
            df.to_excel(writer, sheet_name='Sheet1', index=False)
            df = pandas.DataFrame()
            for each in all_geo_id:
                query = "WITH t AS( SELECT id, (datajson->>'herd_details')::json AS j FROM forms_data WHERE form_name='Patients Registry' AND (datajson->>'herd_details') is NOT NULL and working_upazila_id = "+str(each)+"), t1 AS ( SELECT t.id, d.KEY, d.value::json AS value FROM t, json_each_text(t.j) AS d) SELECT value->>'patient_id' patient_id, value->>'age_range_type' age_range_type, value->>'age_range_from' adge_range_from, value->>'age_range_to' age_range_to, value->>'age_range_count' age_range_count FROM t1"
                temp_df = pandas.DataFrame()
                temp_df = pandas.read_sql(query, connection)
                if not temp_df.empty:
                    df = df.append(temp_df, ignore_index=True)
            df.to_excel(writer, sheet_name='Herd Details', index=False)
            writer.save()
        f = open('onadata/media/uploaded_files/output.xlsx', 'r')
        response = HttpResponse(f, mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=Patient Registry.xls'
        return response
    else:
        message = "You have no access to this page"    
        return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def postmortem_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    # fetching all organization recursively of current_user
    all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
    org_id_list = [org.pk for org in all_organizations]



    # this geo_data is the variable for storing all geo location for current_user
    all_geo_id = []
    col_name = []
    json_data = []

    org_type_query = "select * from usermodule_organizations where id = " + str(current_user.organisation_name_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(org_type_query, connection)

    # For CO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 1:
        select_query = "SELECT data_id,date, (SELECT NAME FROM   geo_cluster WHERE  value = division) AS division, (SELECT NAME FROM   geo_cluster WHERE  value = district)  AS district,(SELECT NAME FROM   geo_cluster WHERE  value = upazila)   AS upazila,(SELECT NAME FROM   geo_cluster WHERE  value::text = xunion)    AS xunion, address, village, owner_name, mobile, case species_type WHEN '10' THEN other_species_livestock WHEN '40' THEN other_species_poultry ELSE (select species_name from species where species_id::text = species_type) end as species_type, (select username from auth_user where id = t.username::int) as username FROM   PUBLIC.vw_postmortem t"
        data = __db_fetch_values_dict(select_query)
        for each1 in data:
                json_data.append(handle_none(each1))
                # each1 contains a json dictionary.
                # each1.items() create (key,value) pair
                for key, value in each1.items():
                    if key not in col_name and key != "data_id":
                        # unique column name insert in col_name list
                        col_name.append(key)
        all_geo_id.append(1)
        return render(request, 'fao_module/postmortem_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})

    # For ULO/LO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 2:
        for each in org_id_list:
            query = "select geoid from organization_catchment_area where organization_id = " + str(each)
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
            if not df.empty:
                # check for duplicate geoid
                # every time a unique geoid is pushed in all_geo_id
                if df.geoid.tolist()[0] in all_geo_id:
                    continue
                # fetching data from forms_data
                select_query = "SELECT data_id,date, (SELECT NAME FROM   geo_cluster WHERE  value = division) AS division, (SELECT NAME FROM   geo_cluster WHERE  value = district)  AS district,(SELECT NAME FROM   geo_cluster WHERE  value = upazila)   AS upazila,(SELECT NAME FROM   geo_cluster WHERE  value::text = xunion)    AS xunion, address, village, owner_name, mobile, case species_type WHEN '10' THEN other_species_livestock WHEN '40' THEN other_species_poultry ELSE (select species_name from species where species_id::text = species_type) end as species_type, (select username from auth_user where id = t.username::int) as username FROM   PUBLIC.vw_postmortem t where working_upazila_id = " + str(
                    df.geoid.tolist()[0])
                data = __db_fetch_values_dict(select_query)
                for each1 in data:
                    json_data.append(handle_none(each1))
                    # each1 contains a json dictionary.
                    # each1.items() create (key,value) pair
                    for key, value in each1.items():
                        if key not in col_name and key != "data_id":
                            # unique column name insert in col_name list
                            col_name.append(key)
                all_geo_id.append(df.geoid.tolist()[0])
        return render(request, 'fao_module/postmortem_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})
    message = "You have no access to this page"    
    return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def xls_report_creator_for_postmortem(request):
    all_geo_id = request.POST.getlist('all_geo_id')
    if len(all_geo_id):
        if int(all_geo_id[0]) == 1:
            # for CO users
            query = "SELECT date, owner_name, father_name,(SELECT NAME FROM geo_cluster WHERE value = division) AS division, (SELECT NAME FROM geo_cluster WHERE value = district) AS district, (SELECT NAME FROM geo_cluster WHERE value = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, address, village, mobile, sick, dead, case species_type WHEN '10' THEN other_species_livestock WHEN '40' THEN other_species_poultry ELSE (select species_name from species where species_id::text = species_type) end as species_type, number_sample, case sample_type WHEN '1' THEN 'Whole carcass' WHEN '2' THEN 'Live bird' WHEN '3' THEN 'Viscera' WHEN '4' THEN sample_type_other END AS sample_type, sample_history, postmortem_findings, Replace(tentative_diagnosis, '@@', ',') AS tentative_diagnosis, Replace(treatment_treatment, '@@', ',') AS treatment_treatment, Replace(advice_suggestions, '@@', ',') AS advice_suggestions, remarks, (select username from auth_user where id = t.username::int) as username, created_at FROM PUBLIC.vw_postmortem t"
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
        else:
            # for ULO/LO users
            df = pandas.DataFrame()
            for each in all_geo_id:
                query = "SELECT date, owner_name, father_name,(SELECT NAME FROM geo_cluster WHERE value = division) AS division, (SELECT NAME FROM geo_cluster WHERE value = district) AS district, (SELECT NAME FROM geo_cluster WHERE value = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, address, village, mobile, sick, dead, case species_type WHEN '10' THEN other_species_livestock WHEN '40' THEN other_species_poultry ELSE (select species_name from species where species_id::text = species_type) end as species_type, number_sample, case sample_type WHEN '1' THEN 'Whole carcass' WHEN '2' THEN 'Live bird' WHEN '3' THEN 'Viscera' WHEN '4' THEN sample_type_other END AS sample_type, sample_history, postmortem_findings, Replace(tentative_diagnosis, '@@', ',') AS tentative_diagnosis, Replace(treatment_treatment, '@@', ',') AS treatment_treatment, Replace(advice_suggestions, '@@', ',') AS advice_suggestions, remarks, (select username from auth_user where id = t.username::int) as username, created_at FROM PUBLIC.vw_postmortem t where working_upazila_id = " + str(each)
                temp_df = pandas.DataFrame()
                temp_df = pandas.read_sql(query, connection)
                if not temp_df.empty:
                    df = df.append(temp_df, ignore_index=True)
        writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        writer.save()
        f = open('onadata/media/uploaded_files/output.xlsx', 'r')
        response = HttpResponse(f, mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=Postmortem.xls'
        return response
    else:
        message = "You have no access to this page"    
        return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def generic_disease_investigation_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    # fetching all organization recursively of current_user
    all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
    org_id_list = [org.pk for org in all_organizations]

    # this geo_data is the variable for storing all geo location for current_user
    all_geo_id = []
    col_name = []
    json_data = []

    org_type_query = "select * from usermodule_organizations where id = " + str(current_user.organisation_name_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(org_type_query, connection)

    # For CO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 1:
        select_query = "SELECT data_id, investigation_id, farm_id, date_initial_visit,(SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, mouza, village, name_contact_person, mobile_contact_person, case sex WHEN '1' THEN 'Male' WHEN '2' THEN 'Female' END AS sex, assigned_lab, (select username from auth_user where id = t.username::int )as username FROM PUBLIC.vw_generic_disease_investigation t"
        data = __db_fetch_values_dict(select_query)
        for each1 in data:
                json_data.append(handle_none(each1))
                # each1 contains a json dictionary.
                # each1.items() create (key,value) pair
                for key, value in each1.items():
                    if key not in col_name and key != "data_id":
                        # unique column name insert in col_name list
                        col_name.append(key)
        all_geo_id.append(1)
        return render(request, 'fao_module/generic_disease_investigation_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})

    # For ULO/LO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 2:
        for each in org_id_list:
            query = "select geoid from organization_catchment_area where organization_id = " + str(each)
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
            if not df.empty:
                # check for duplicate geoid
                # every time a unique geoid is pushed in all_geo_id
                if df.geoid.tolist()[0] in all_geo_id:
                    continue
                # fetching data from forms_data
                select_query = "SELECT data_id, investigation_id, farm_id, date_initial_visit,(SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, mouza, village, name_contact_person, mobile_contact_person, case sex WHEN '1' THEN 'Male' WHEN '2' THEN 'Female' END AS sex, assigned_lab, (select username from auth_user where id = t.username::int )as username FROM PUBLIC.vw_generic_disease_investigation t where working_upazila_id = " + str(
                    df.geoid.tolist()[0])
                data = __db_fetch_values_dict(select_query)
                for each1 in data:
                    json_data.append(handle_none(each1))
                    # each1 contains a json dictionary.
                    # each1.items() create (key,value) pair
                    for key, value in each1.items():
                        if key not in col_name and key != "data_id":
                            # unique column name insert in col_name list
                            col_name.append(key)
                all_geo_id.append(df.geoid.tolist()[0])
        return render(request, 'fao_module/generic_disease_investigation_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})
    message = "You have no access to this page"    
    return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def xls_report_creator_for_generic_disease_investigation(request):
    all_geo_id = request.POST.getlist('all_geo_id')
    if len(all_geo_id):
        if int(all_geo_id[0]) == 1:
            # for CO users
            query = "SELECT investigation_id, farm_id, date_initial_visit,(SELECT name FROM geo_cluster WHERE value :: text = division) AS division, (SELECT name FROM geo_cluster WHERE value :: text = district) AS district, (SELECT name FROM geo_cluster WHERE value :: text = upazila) AS upazila, (SELECT name FROM geo_cluster WHERE value :: text = xunion) AS xunion, mouza, village, name_contact_person, title_position, mobile_contact_person, CASE sex WHEN '1' THEN 'Male' WHEN '2' THEN 'Female' END AS sex, gps_lattitude, gps_longitude, CASE were_called_investigate_animal WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_called_investigate_animal, CASE meeting_raise_community_awareness_disease WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS meeting_raise_community_awareness_disease, CASE search_sick_dead_animal WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS search_sick_dead_animal, CASE were_sick_dead_animal_found WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_sick_dead_animal_found, date_received_sick_dead_info, estimated_onset, CASE type_production_system_occur WHEN '1' THEN 'Farm ' WHEN '2' THEN 'Household' END AS type_production_system_occur, CASE has_farm_previously_assessed WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS has_farm_previously_assessed, date_farm_previously_assessed, cattle, cattle_dead, cattle_sick, cattle_population, goats, goats_dead, goats_sick, goats_total_population, sheep, sheep_dead, sheep_sick, sheep_population, buffalo, buffalo_dead, buffalo_sick, buffalo_population, horses, horse_dead, horse_sick, horse_population, others_affected_species, other_affected_dead, other_affected_sick, other_affected_population, sick_dead_tested_for_diagnosis, Replace(specimen_type, '@@', ',') AS specimen_type, post_mortem_findings, CASE is_vtm_sample_collected WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS is_vtm_sample_collected, date_vtm_sample_collected, CASE pcr_result WHEN '1' THEN 'Positive' WHEN '2' THEN 'Negative' WHEN '3' THEN 'Test not performed' WHEN '4' THEN 'No lab report received' END AS pcr_result, CASE why_not_vtm WHEN '1' THEN ' No VTM' WHEN '2' THEN 'Not necessary' END AS why_not_vtm, positive_poison, number_poison, positive_bacteria, number_bacteria, positive_virus, number_virus, Replace(initial_control_measure, '@@', ',') AS initial_control_measure, Replace(clinical_symptoms, '@@', ',') AS clinical_symptoms, last_documented_similar_incident_where, last_documented_similar_incident_when, additional_investigation_info, (SELECT username FROM auth_user WHERE id = t.investigator_name1 :: INT) AS investigator_name1, investigator_designation1, investigator_contact_number1, (SELECT username FROM auth_user WHERE id = t.investigator_name2 :: INT) AS investigator_name2, investigator_designation2, investigator_contact_number2, (SELECT username FROM auth_user WHERE id = t.admin_name1 :: INT) AS admin_name1, admin_overnight_date11, admin_overnight_date12, admin_overnight_date13, admin_working_date11, admin_working_date12, admin_working_date13, (SELECT username FROM auth_user WHERE id = t.admin_name2 :: INT) AS admin_name2, admin_overnight_date21, admin_overnight_date22, admin_overnight_date23, admin_working_date21, admin_working_date22, admin_working_date23, (SELECT username FROM auth_user WHERE id = t.acknowledge_by :: INT) AS acknowledge_by, (SELECT username FROM auth_user WHERE id = t.approved_by :: INT) AS approved_by, assigned_lab, (SELECT username FROM auth_user WHERE id = t.username :: INT) AS username, (SELECT username FROM auth_user WHERE id = t.created_at :: INT) AS created_at FROM public.vw_generic_disease_investigation t"
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
        else:
            # for ULO/LO users
            df = pandas.DataFrame()
            for each in all_geo_id:
                query = "SELECT investigation_id, farm_id, date_initial_visit,(SELECT name FROM geo_cluster WHERE value :: text = division) AS division, (SELECT name FROM geo_cluster WHERE value :: text = district) AS district, (SELECT name FROM geo_cluster WHERE value :: text = upazila) AS upazila, (SELECT name FROM geo_cluster WHERE value :: text = xunion) AS xunion, mouza, village, name_contact_person, title_position, mobile_contact_person, CASE sex WHEN '1' THEN 'Male' WHEN '2' THEN 'Female' END AS sex, gps_lattitude, gps_longitude, CASE were_called_investigate_animal WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_called_investigate_animal, CASE meeting_raise_community_awareness_disease WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS meeting_raise_community_awareness_disease, CASE search_sick_dead_animal WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS search_sick_dead_animal, CASE were_sick_dead_animal_found WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_sick_dead_animal_found, date_received_sick_dead_info, estimated_onset, CASE type_production_system_occur WHEN '1' THEN 'Farm ' WHEN '2' THEN 'Household' END AS type_production_system_occur, CASE has_farm_previously_assessed WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS has_farm_previously_assessed, date_farm_previously_assessed, cattle, cattle_dead, cattle_sick, cattle_population, goats, goats_dead, goats_sick, goats_total_population, sheep, sheep_dead, sheep_sick, sheep_population, buffalo, buffalo_dead, buffalo_sick, buffalo_population, horses, horse_dead, horse_sick, horse_population, others_affected_species, other_affected_dead, other_affected_sick, other_affected_population, sick_dead_tested_for_diagnosis, Replace(specimen_type, '@@', ',') AS specimen_type, post_mortem_findings, CASE is_vtm_sample_collected WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS is_vtm_sample_collected, date_vtm_sample_collected, CASE pcr_result WHEN '1' THEN 'Positive' WHEN '2' THEN 'Negative' WHEN '3' THEN 'Test not performed' WHEN '4' THEN 'No lab report received' END AS pcr_result, CASE why_not_vtm WHEN '1' THEN ' No VTM' WHEN '2' THEN 'Not necessary' END AS why_not_vtm, positive_poison, number_poison, positive_bacteria, number_bacteria, positive_virus, number_virus, Replace(initial_control_measure, '@@', ',') AS initial_control_measure, Replace(clinical_symptoms, '@@', ',') AS clinical_symptoms, last_documented_similar_incident_where, last_documented_similar_incident_when, additional_investigation_info, (SELECT username FROM auth_user WHERE id = t.investigator_name1 :: INT) AS investigator_name1, investigator_designation1, investigator_contact_number1, (SELECT username FROM auth_user WHERE id = t.investigator_name2 :: INT) AS investigator_name2, investigator_designation2, investigator_contact_number2, (SELECT username FROM auth_user WHERE id = t.admin_name1 :: INT) AS admin_name1, admin_overnight_date11, admin_overnight_date12, admin_overnight_date13, admin_working_date11, admin_working_date12, admin_working_date13, (SELECT username FROM auth_user WHERE id = t.admin_name2 :: INT) AS admin_name2, admin_overnight_date21, admin_overnight_date22, admin_overnight_date23, admin_working_date21, admin_working_date22, admin_working_date23, (SELECT username FROM auth_user WHERE id = t.acknowledge_by :: INT) AS acknowledge_by, (SELECT username FROM auth_user WHERE id = t.approved_by :: INT) AS approved_by, assigned_lab, (SELECT username FROM auth_user WHERE id = t.username :: INT) AS username, (SELECT username FROM auth_user WHERE id = t.created_at :: INT) AS created_at FROM public.vw_generic_disease_investigation t where working_upazila_id = " + str(each)
                temp_df = pandas.DataFrame()
                temp_df = pandas.read_sql(query, connection)
                if not temp_df.empty:
                    df = df.append(temp_df, ignore_index=True)
        writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        writer.save()
        f = open('onadata/media/uploaded_files/output.xlsx', 'r')
        response = HttpResponse(f, mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=Generic Disease Investigation.xls'
        return response
    else:
        message = "You have no access to this page"    
        return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def avian_influenza_investigation_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    # fetching all organization recursively of current_user
    all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
    org_id_list = [org.pk for org in all_organizations]

    # this geo_data is the variable for storing all geo location for current_user
    all_geo_id = []
    col_name = []
    json_data = []

    org_type_query = "select * from usermodule_organizations where id = " + str(current_user.organisation_name_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(org_type_query, connection)

    # For CO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 1:
        select_query = "SELECT data_id, investigation_id, farm_id, date_completed,(SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, mouza, village, farmer_name, mobile_contact_person, (select username from auth_user where id = t.username::int) username FROM PUBLIC.vw_avian_influenza_investigation t"
        data = __db_fetch_values_dict(select_query)
        for each1 in data:
                json_data.append(handle_none(each1))
                # each1 contains a json dictionary.
                # each1.items() create (key,value) pair
                for key, value in each1.items():
                    if key not in col_name and key != "data_id":
                        # unique column name insert in col_name list
                        col_name.append(key)
        all_geo_id.append(1)
        return render(request, 'fao_module/avian_influenza_investigation_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})

    # For ULO/LO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 2:
        for each in org_id_list:
            query = "select geoid from organization_catchment_area where organization_id = " + str(each)
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
            if not df.empty:
                # check for duplicate geoid
                # every time a unique geoid is pushed in all_geo_id
                if df.geoid.tolist()[0] in all_geo_id:
                    continue
                # fetching data from forms_data
                select_query = "SELECT data_id, investigation_id, farm_id, date_completed,(SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, mouza, village, farmer_name, mobile_contact_person,(select username from auth_user where id = t.username::int) username FROM PUBLIC.vw_avian_influenza_investigation t where working_upazila_id = " + str(
                    df.geoid.tolist()[0])
                data = __db_fetch_values_dict(select_query)
                for each1 in data:
                    json_data.append(handle_none(each1))
                    # each1 contains a json dictionary.
                    # each1.items() create (key,value) pair
                    for key, value in each1.items():
                        if key not in col_name and key != "data_id":
                            # unique column name insert in col_name list
                            col_name.append(key)
                all_geo_id.append(df.geoid.tolist()[0])
        return render(request, 'fao_module/avian_influenza_investigation_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})
    message = "You have no access to this page"    
    return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def xls_report_creator_for_avian_influenza_investigation(request):
    all_geo_id = request.POST.getlist('all_geo_id')
    if len(all_geo_id):
        if int(all_geo_id[0]) == 1:
            # for CO users
            query = "SELECT investigation_id, farm_id, date_completed,(SELECT name FROM geo_cluster WHERE value :: text = division) AS division, (SELECT name FROM geo_cluster WHERE value :: text = district) AS district, (SELECT name FROM geo_cluster WHERE value :: text = upazila) AS upazila, (SELECT name FROM geo_cluster WHERE value :: text = xunion) AS xunion, mouza, village, farmer_name, title_position, mobile_contact_person, CASE sex WHEN '1' THEN 'Male' WHEN '2' THEN 'Female' END AS sex, gps_lattitude, gps_longitude, CASE were_called_investigate_birds WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_called_investigate_birds, CASE meeting_raise_community_avian_influenza WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS meeting_raise_community_avian_influenza, CASE search_sick_dead_birds WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS meeting_raise_community_avian_influenza, CASE were_sick_dead_birds_found WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_sick_dead_birds_found, date_received_sick_dead_info, date_estimated_onset, CASE cases_occur_type_production_system WHEN '1' THEN 'Farm ' WHEN '2' THEN 'Backyard' WHEN '3' THEN 'Wild Bird' END AS cases_occur_type_production_system, CASE has_farm_previously_assessed WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS has_farm_previously_assessed, date_previously_assessed, Replace(clinical_sign_observed, '@@', ',') AS clinical_sign_observed, deshi_chicken, deshi_chicken_dead, deshi_chicken_sick, deshi_chicken_population, sonali_chicken_dead, sonali_chicken_sick, sonali_chicken_total_population, brown_comm_chicken, brown_comm_chicken_dead, brown_comm_chicken_sick, brown_comm_chicken_population, white_comm_chicken, white_comm_chicken_dead, white_comm_chicken_sick, white_comm_chicken_population, ducks, duck_dead, duck_sick, duck_population, others_affected_species, other_affected_dead, other_affected_sick, other_affected_population, CASE birds_production_purpose WHEN '1' THEN 'Egg' WHEN '2' THEN 'Meat' WHEN '3' THEN 'Egg & Meat' WHEN '4' THEN 'Breeder' WHEN '5' THEN 'Sport' WHEN '6' THEN 'Pet' END AS birds_production_purpose, sick_dead_tested_by_rapid_test, CASE used_rapid_test_name WHEN '1' THEN 'Bionote Anigen AIV test' ELSE other_used_rapid_test_name END AS used_rapid_test_name, CASE rapid_test_result WHEN '1' THEN 'Positive' WHEN '2' THEN 'Negative' WHEN '3' THEN 'Not performed' END AS rapid_test_result, CASE vtm_sample_collected WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS vtm_sample_collected, date_vtm_sample_collected, CASE pcr_result WHEN '1' THEN 'Positive' WHEN '2' THEN 'Negative' WHEN '3' THEN 'Test not performed' WHEN '4' THEN 'No lab report received ' END AS pcr_result, CASE why_not_vtm WHEN '1' THEN ' No VTM' WHEN '2' THEN 'Not necessary' END AS why_not_vtm, CASE type_culling_performed WHEN '1' THEN 'Focal culling ( culling of all birds in affected flock)' WHEN '2' THEN 'No culling performed' END AS type_culling_performed, number_birds_culled, why_not_culled, CASE type_compensation_provided WHEN '1' THEN 'Vaccination' WHEN '2' THEN 'Young bird restocking' WHEN '3' THEN 'No compensation' END AS type_compensation_provided, additional_investigation_information, (SELECT username FROM auth_user WHERE id = t.investigator_name1 :: INT) investigator_name1, investigator_designation1, investogator_contact_number1, (SELECT username FROM auth_user WHERE id = t.investigator_name2 :: INT) investigator_name2, investigator_designation2, investigator_contact_number2, (SELECT username FROM auth_user WHERE id = t.admin_name1 :: INT) admin_name1, admin_overnight_date11, admin_overnight_date12, admin_overnight_date13, admin_working_date11, admin_working_date12, admin_working_date13, (SELECT username FROM auth_user WHERE id = t.admin_name2 :: INT) admin_name2, admin_overnight_date21, admin_overnight_date22, admin_overnight_date23, admin_working_date21, admin_working_date22, admin_working_date23, (SELECT username FROM auth_user WHERE id = t.acknowledge_by :: INT) acknowledge_by, (SELECT username FROM auth_user WHERE id = t.approved_by :: INT) approved_by, (SELECT username FROM auth_user WHERE id = t.username :: INT) username, created_at FROM public.vw_avian_influenza_investigation t"
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
        else:
            # for ULO/LO users
            df = pandas.DataFrame()
            for each in all_geo_id:
                query = "SELECT investigation_id, farm_id, date_completed,(SELECT name FROM geo_cluster WHERE value :: text = division) AS division, (SELECT name FROM geo_cluster WHERE value :: text = district) AS district, (SELECT name FROM geo_cluster WHERE value :: text = upazila) AS upazila, (SELECT name FROM geo_cluster WHERE value :: text = xunion) AS xunion, mouza, village, farmer_name, title_position, mobile_contact_person, CASE sex WHEN '1' THEN 'Male' WHEN '2' THEN 'Female' END AS sex, gps_lattitude, gps_longitude, CASE were_called_investigate_birds WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_called_investigate_birds, CASE meeting_raise_community_avian_influenza WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS meeting_raise_community_avian_influenza, CASE search_sick_dead_birds WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS meeting_raise_community_avian_influenza, CASE were_sick_dead_birds_found WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_sick_dead_birds_found, date_received_sick_dead_info, date_estimated_onset, CASE cases_occur_type_production_system WHEN '1' THEN 'Farm ' WHEN '2' THEN 'Backyard' WHEN '3' THEN 'Wild Bird' END AS cases_occur_type_production_system, CASE has_farm_previously_assessed WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS has_farm_previously_assessed, date_previously_assessed, Replace(clinical_sign_observed, '@@', ',') AS clinical_sign_observed, deshi_chicken, deshi_chicken_dead, deshi_chicken_sick, deshi_chicken_population, sonali_chicken_dead, sonali_chicken_sick, sonali_chicken_total_population, brown_comm_chicken, brown_comm_chicken_dead, brown_comm_chicken_sick, brown_comm_chicken_population, white_comm_chicken, white_comm_chicken_dead, white_comm_chicken_sick, white_comm_chicken_population, ducks, duck_dead, duck_sick, duck_population, others_affected_species, other_affected_dead, other_affected_sick, other_affected_population, CASE birds_production_purpose WHEN '1' THEN 'Egg' WHEN '2' THEN 'Meat' WHEN '3' THEN 'Egg & Meat' WHEN '4' THEN 'Breeder' WHEN '5' THEN 'Sport' WHEN '6' THEN 'Pet' END AS birds_production_purpose, sick_dead_tested_by_rapid_test, CASE used_rapid_test_name WHEN '1' THEN 'Bionote Anigen AIV test' ELSE other_used_rapid_test_name END AS used_rapid_test_name, CASE rapid_test_result WHEN '1' THEN 'Positive' WHEN '2' THEN 'Negative' WHEN '3' THEN 'Not performed' END AS rapid_test_result, CASE vtm_sample_collected WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS vtm_sample_collected, date_vtm_sample_collected, CASE pcr_result WHEN '1' THEN 'Positive' WHEN '2' THEN 'Negative' WHEN '3' THEN 'Test not performed' WHEN '4' THEN 'No lab report received ' END AS pcr_result, CASE why_not_vtm WHEN '1' THEN ' No VTM' WHEN '2' THEN 'Not necessary' END AS why_not_vtm, CASE type_culling_performed WHEN '1' THEN 'Focal culling ( culling of all birds in affected flock)' WHEN '2' THEN 'No culling performed' END AS type_culling_performed, number_birds_culled, why_not_culled, CASE type_compensation_provided WHEN '1' THEN 'Vaccination' WHEN '2' THEN 'Young bird restocking' WHEN '3' THEN 'No compensation' END AS type_compensation_provided, additional_investigation_information, (SELECT username FROM auth_user WHERE id = t.investigator_name1 :: INT) investigator_name1, investigator_designation1, investogator_contact_number1, (SELECT username FROM auth_user WHERE id = t.investigator_name2 :: INT) investigator_name2, investigator_designation2, investigator_contact_number2, (SELECT username FROM auth_user WHERE id = t.admin_name1 :: INT) admin_name1, admin_overnight_date11, admin_overnight_date12, admin_overnight_date13, admin_working_date11, admin_working_date12, admin_working_date13, (SELECT username FROM auth_user WHERE id = t.admin_name2 :: INT) admin_name2, admin_overnight_date21, admin_overnight_date22, admin_overnight_date23, admin_working_date21, admin_working_date22, admin_working_date23, (SELECT username FROM auth_user WHERE id = t.acknowledge_by :: INT) acknowledge_by, (SELECT username FROM auth_user WHERE id = t.approved_by :: INT) approved_by, (SELECT username FROM auth_user WHERE id = t.username :: INT) username, created_at FROM public.vw_avian_influenza_investigation t where working_upazila_id = " + str(each)
                temp_df = pandas.DataFrame()
                temp_df = pandas.read_sql(query, connection)
                if not temp_df.empty:
                    df = df.append(temp_df, ignore_index=True)
        writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        writer.save()
        f = open('onadata/media/uploaded_files/output.xlsx', 'r')
        response = HttpResponse(f, mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=Avian Influenza Investigation.xls'
        return response
    else:
        message = "You have no access to this page"    
        return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def sink_surveillance_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    # fetching all organization recursively of current_user
    all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
    org_id_list = [org.pk for org in all_organizations]

    # this geo_data is the variable for storing all geo location for current_user
    all_geo_id = []
    col_name = []
    json_data = []

    org_type_query = "select * from usermodule_organizations where id = " + str(current_user.organisation_name_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(org_type_query, connection)

    # For CO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 1:
        select_query = "SELECT data_id,market_name, ward_number, CASE city_north_or_south WHEN '1' THEN 'DNCC' WHEN '2' THEN 'DSCC' END AS city_corporation, live_bird_market_id, date_sample_collected, sample_collected_by FROM vw_sink_surveillance t"
        data = __db_fetch_values_dict(select_query)
        for each1 in data:
                json_data.append(handle_none(each1))
                # each1 contains a json dictionary.
                # each1.items() create (key,value) pair
                for key, value in each1.items():
                    if key not in col_name and key != "data_id":
                        # unique column name insert in col_name list
                        col_name.append(key)
        all_geo_id.append(1)
        return render(request, 'fao_module/sink_surveillance_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})

    # For ULO/LO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 2:
        for each in org_id_list:
            query = "select geoid from organization_catchment_area where organization_id = " + str(each)
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
            if not df.empty:
                # check for duplicate geoid
                # every time a unique geoid is pushed in all_geo_id
                if df.geoid.tolist()[0] in all_geo_id:
                    continue
                # fetching data from forms_data
                select_query = "SELECT data_id,market_name, ward_number, CASE city_north_or_south WHEN '1' THEN 'DNCC' WHEN '2' THEN 'DSCC' END AS city_corporation, live_bird_market_id, date_sample_collected,sample_collected_by FROM vw_sink_surveillance t where working_upazila_id = " + str(
                    df.geoid.tolist()[0])
                data = __db_fetch_values_dict(select_query)
                for each1 in data:
                    json_data.append(handle_none(each1))
                    # each1 contains a json dictionary.
                    # each1.items() create (key,value) pair
                    for key, value in each1.items():
                        if key not in col_name and key != "data_id":
                            # unique column name insert in col_name list
                            col_name.append(key)
                all_geo_id.append(df.geoid.tolist()[0])
        return render(request, 'fao_module/sink_surveillance_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})
    message = "You have no access to this page"    
    return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def xls_report_creator_for_sink_surveillance(request):
    all_geo_id = request.POST.getlist('all_geo_id')
    if len(all_geo_id):
        if int(all_geo_id[0]) == 1:
            # for CO users
            query = "SELECT market_name, ward_number, CASE city_north_or_south WHEN '1' THEN 'DNCC' WHEN '2' THEN 'DSCC' END AS city_corporation, live_bird_market_id, date_sample_collected, Substr(Replace(area_type, '@@', ','), 1, Length(Replace(area_type, '@@', ',')) - 1) AS area_type, a_area_id, a_lab_identification, a_floor_area, a_cages_birds, a_waste_water, a_waste_bins, a_truck, a_specify_other_name, a_specify_other_number, s_area_id, s_lab_identification, s_table_defeathering, s_bird_meat_holding_tray, s_slautering_boards_area, s_waste_bin, s_waste_water_path, s_defeathering_machine, e_area_id, e_lab_identification, e_display_table, e_chopping_board, e_cloths_wet, e_scales, e_knives_utensils, e_specify_other, e_specify_other_number, remarks,sample_collected_by,(select username from auth_user where id = t.username::int) username FROM vw_sink_surveillance t"
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
        else:
            # for ULO/LO users
            df = pandas.DataFrame()
            for each in all_geo_id:
                query = "SELECT market_name, ward_number, CASE city_north_or_south WHEN '1' THEN 'DNCC' WHEN '2' THEN 'DSCC' END AS city_corporation, live_bird_market_id, date_sample_collected, Substr(Replace(area_type, '@@', ','), 1, Length(Replace(area_type, '@@', ',')) - 1) AS area_type, a_area_id, a_lab_identification, a_floor_area, a_cages_birds, a_waste_water, a_waste_bins, a_truck, a_specify_other_name, a_specify_other_number, s_area_id, s_lab_identification, s_table_defeathering, s_bird_meat_holding_tray, s_slautering_boards_area, s_waste_bin, s_waste_water_path, s_defeathering_machine, e_area_id, e_lab_identification, e_display_table, e_chopping_board, e_cloths_wet, e_scales, e_knives_utensils, e_specify_other, e_specify_other_number, remarks, sample_collected_by,(select username from auth_user where id = t.username::int) username FROM vw_sink_surveillance t where working_upazila_id = " + str(each)
                temp_df = pandas.DataFrame()
                temp_df = pandas.read_sql(query, connection)
                if not temp_df.empty:
                    df = df.append(temp_df, ignore_index=True)
        writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        writer.save()
        f = open('onadata/media/uploaded_files/output.xlsx', 'r')
        response = HttpResponse(f, mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=Sink Surveillance.xls'
        return response
    else:
        message = "You have no access to this page"    
        return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def sink_surveillance_view(request, data_id):
    query = "SELECT market_name, ward_number, CASE city_north_or_south WHEN '1' THEN 'DNCC' WHEN '2' THEN 'DSCC' END AS city_corporation, live_bird_market_id, date_sample_collected, Substr(Replace(area_type, '@@', ','), 1, Length(Replace(area_type, '@@', ',')) - 1) AS area_type, a_area_id, a_lab_identification, a_floor_area, a_cages_birds, a_waste_water, a_waste_bins, a_truck, a_specify_other_name, a_specify_other_number, s_area_id, s_lab_identification, s_table_defeathering, s_bird_meat_holding_tray, s_slautering_boards_area, s_waste_bin, s_waste_water_path, s_defeathering_machine, e_area_id, e_lab_identification, e_display_table, e_chopping_board, e_cloths_wet, e_scales, e_knives_utensils, e_specify_other, e_specify_other_number, remarks, sample_collected_by,(select username from auth_user where id = t.username::int) username FROM vw_sink_surveillance  t where data_id = " + str(
        data_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    data = {}
    data['market_name'] = df.market_name.tolist()[0]
    data['ward_number'] = df.ward_number.tolist()[0]
    data['city_corporation'] = df.city_corporation.tolist()[0]
    data['live_bird_market_id'] = df.live_bird_market_id.tolist()[0]
    data['date_sample_collected'] = df.date_sample_collected.tolist()[0]
    data['a_area_id'] = df.a_area_id.tolist()[0]
    data['s_area_id'] = df.s_area_id.tolist()[0]
    data['e_area_id'] = df.e_area_id.tolist()[0]
    data['a_lab_identification'] = df.a_lab_identification.tolist()[0]
    data['s_lab_identification'] = df.s_lab_identification.tolist()[0]
    data['e_lab_identification'] = df.e_lab_identification.tolist()[0]
    data['a_floor_area'] = df.a_floor_area.tolist()[0]
    data['a_cages_birds'] = df.a_cages_birds.tolist()[0]
    data['a_waste_water'] = df.a_waste_water.tolist()[0]
    data['a_waste_bins'] = df.a_waste_bins.tolist()[0]
    data['a_truck'] = df.a_truck.tolist()[0]
    data['a_specify_other_name'] = df.a_specify_other_name.tolist()[0]
    data['a_specify_other_number'] = df.a_specify_other_number.tolist()[0]
    data['s_table_defeathering'] = df.s_table_defeathering.tolist()[0]
    data['s_bird_meat_holding_tray'] = df.s_bird_meat_holding_tray.tolist()[0]
    data['s_slautering_boards_area'] = df.s_slautering_boards_area.tolist()[0]
    data['s_waste_bin'] = df.s_waste_bin.tolist()[0]
    data['s_waste_water_path'] = df.s_waste_water_path.tolist()[0]
    data['s_defeathering_machine'] = df.s_defeathering_machine.tolist()[0]
    data['e_display_table'] = df.e_display_table.tolist()[0]
    data['e_chopping_board'] = df.e_chopping_board.tolist()[0]
    data['e_cloths_wet'] = df.e_cloths_wet.tolist()[0]
    data['e_scales'] = df.e_scales.tolist()[0]
    data['e_knives_utensils'] = df.e_knives_utensils.tolist()[0]
    data['e_specify_other'] = df.e_specify_other.tolist()[0]
    data['e_specify_other_number'] = df.e_specify_other_number.tolist()[0]
    data['remarks'] = df.remarks.tolist()[0]
    data['sample_collected_by'] = df.sample_collected_by.tolist()[0]
    data = handle_none(data)
    return render(request, 'fao_module/sink_surveillance_view.html',{'data': data})


@login_required
def pathology_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    # fetching all organization recursively of current_user
    all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
    org_id_list = [org.pk for org in all_organizations]

    # this geo_data is the variable for storing all geo location for current_user
    all_geo_id = []
    col_name = []
    json_data = []
    org_type_query = "select * from usermodule_organizations where id = " + str(current_user.organisation_name_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(org_type_query, connection)

    # For CO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 1:
        select_query = "select data_id,date,owner_name,mobile,(SELECT NAME FROM geo_cluster WHERE value = division) AS division,(SELECT NAME FROM geo_cluster WHERE value = district) AS district, (SELECT NAME FROM geo_cluster WHERE value = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, village, case species_type WHEN '10' THEN other_species_livestock WHEN '40' THEN other_species_poultry ELSE (select species_name from species where species_id::text = species_type) end as species_type, (select username from auth_user where id = t.username::int) as username from PUBLIC.vw_pathology t"
        data = __db_fetch_values_dict(select_query)
        for each1 in data:
                json_data.append(handle_none(each1))
                # each1 contains a json dictionary.
                # each1.items() create (key,value) pair
                for key, value in each1.items():
                    if key not in col_name and key != "data_id":
                        # unique column name insert in col_name list
                        col_name.append(key)
        all_geo_id.append(1)
        return render(request, 'fao_module/pathology_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})

    # For ULO/LO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 2:
        for each in org_id_list:
            query = "select geoid from organization_catchment_area where organization_id = " + str(each)
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
            if not df.empty:
                # check for duplicate geoid
                # every time a unique geoid is pushed in all_geo_id
                if df.geoid.tolist()[0] in all_geo_id:
                    continue
                # fetching data from forms_data
                select_query = "select data_id,date,owner_name,mobile,(SELECT NAME FROM geo_cluster WHERE value = division) AS division,(SELECT NAME FROM geo_cluster WHERE value = district) AS district, (SELECT NAME FROM geo_cluster WHERE value = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, village, case species_type WHEN '10' THEN other_species_livestock WHEN '40' THEN other_species_poultry ELSE (select species_name from species where species_id::text = species_type) end as species_type, (select username from auth_user where id = t.username::int) as username from PUBLIC.vw_pathology t where working_upazila_id = " + str(
                    df.geoid.tolist()[0])
                data = __db_fetch_values_dict(select_query)
                for each1 in data:
                    json_data.append(handle_none(each1))
                    # each1 contains a json dictionary.
                    # each1.items() create (key,value) pair
                    for key, value in each1.items():
                        if key not in col_name and key != "data_id":
                            # unique column name insert in col_name list
                            col_name.append(key)
                all_geo_id.append(df.geoid.tolist()[0])
        return render(request, 'fao_module/pathology_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})
    message = "You have no access to this page"    
    return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def xls_report_creator_for_pathology(request):
    all_geo_id = request.POST.getlist('all_geo_id')
    if len(all_geo_id):
        if int(all_geo_id[0]) == 1:
            # for CO users
            query = "SELECT date, owner_name, father_name, mobile,(SELECT NAME FROM geo_cluster WHERE value = division) AS division, (SELECT NAME FROM geo_cluster WHERE value = district) AS district, (SELECT NAME FROM geo_cluster WHERE value = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, village, case species_type WHEN '10' THEN other_species_livestock WHEN '40' THEN other_species_poultry ELSE (select species_name from species where species_id::text = species_type) end as species_type, sample_number, dead, sick, test_performed, sample_details, tratment, advice, remarks, test_result, sample_history, (select username from auth_user where id = t.username::int) as username, created_at FROM PUBLIC.vw_pathology t"
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
        else:
            # for ULO/LO users
            df = pandas.DataFrame()
            for each in all_geo_id:
                query = "SELECT date, owner_name, father_name, mobile,(SELECT NAME FROM geo_cluster WHERE value = division) AS division, (SELECT NAME FROM geo_cluster WHERE value = district) AS district, (SELECT NAME FROM geo_cluster WHERE value = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, village, case species_type WHEN '10' THEN other_species_livestock WHEN '40' THEN other_species_poultry ELSE (select species_name from species where species_id::text = species_type) end as species_type, sample_number, dead, sick, test_performed, sample_details, tratment, advice, remarks, test_result, sample_history, (select username from auth_user where id = t.username::int) as username, created_at FROM PUBLIC.vw_pathology t where working_upazila_id = " + str(each)
                temp_df = pandas.DataFrame()
                temp_df = pandas.read_sql(query, connection)
                if not temp_df.empty:
                    df = df.append(temp_df, ignore_index=True)
        writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        writer.save()
        f = open('onadata/media/uploaded_files/output.xlsx', 'r')
        response = HttpResponse(f, mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=Pathology.xls'
        return response
    else:
        message = "You have no access to this page"    
        return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def ai_lab_result_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    # fetching all organization recursively of current_user
    all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
    org_id_list = [org.pk for org in all_organizations]

    # this geo_data is the variable for storing all geo location for current_user
    all_geo_id = []
    col_name = []
    json_data = []

    org_type_query = "select * from usermodule_organizations where id = " + str(current_user.organisation_name_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(org_type_query, connection)

    # for CO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 1:
        select_query = "with q as(with t as(select distinct on (investigation_id) investigation_id,working_upazila_id from vw_avian_influenza_investigation) select * from t,result_inputs r where t.investigation_id = r.reference_investigation_id) select reference_investigation_id,reference_sample_id,test_set_up_number,date_test_set_up,date_out_put, case result when 1 THEN 'Positive' when 2 THEN 'Negative' when 3 THEN 'Undetermined' end as result, protocol_details, ct_value, result_details,(select username from auth_user where id = t.test_setup_by::int) test_setup_by,(select username from auth_user where id = t.name_result_input_by::int) name_result_input_by from q t"
        data = __db_fetch_values_dict(select_query)
        for each1 in data:
                json_data.append(handle_none(each1))
                # each1 contains a json dictionary.
                # each1.items() create (key,value) pair
                for key, value in each1.items():
                    if key not in col_name and key != "data_id":
                        # unique column name insert in col_name list
                        col_name.append(key)
        all_geo_id.append(1)
        return render(request, 'fao_module/ai_lab_result_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})


    # for LAB users
    if df.organization_type.tolist()[0] is not None and int(df.organization_type.tolist()[0]) == 3:
        # print org_id_list
        for each in org_id_list:
            select_query = "with q as(with t as(select distinct on (investigation_id) investigation_id,working_upazila_id from vw_avian_influenza_investigation) select * from t,result_inputs r where t.investigation_id = r.reference_investigation_id) select reference_investigation_id,reference_sample_id,test_set_up_number,date_test_set_up,date_out_put, case result when 1 THEN 'Positive' when 2 THEN 'Negative' when 3 THEN 'Undetermined' end as result, protocol_details, ct_value, result_details,(select username from auth_user where id = t.test_setup_by::int) test_setup_by,(select username from auth_user where id = t.name_result_input_by::int) name_result_input_by from q t where working_upazila_id = " + str(each)
            data = __db_fetch_values_dict(select_query)
            for each1 in data:
                json_data.append(handle_none(each1))
                # each1 contains a json dictionary.
                # each1.items() create (key,value) pair
                for key, value in each1.items():
                    if key not in col_name and key != "data_id":
                        # unique column name insert in col_name list
                        col_name.append(key)
            all_geo_id.append(each)
        return render(request, 'fao_module/ai_lab_result_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})
    message = "You have no access to this page"    
    return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def xls_report_creator_for_ai_lab_result(request):
    all_geo_id = request.POST.getlist('all_geo_id')
    if len(all_geo_id):
        if int(all_geo_id[0]) == 1:
            query = "with q as(with t as(select distinct on(investigation_id) investigation_id,working_upazila_id from vw_avian_influenza_investigation) select * from t,result_inputs r where t.investigation_id = r.reference_investigation_id) select reference_investigation_id,reference_sample_id,test_set_up_number,date_test_set_up,date_out_put, CASE WHEN test_name = 1 THEN 'RT-PCR' WHEN test_name = 2 THEN other_test_name END AS test_name, CASE rt_pcr_type_test WHEN '1' THEN 'M gene' WHEN '2' THEN 'H' WHEN '3' THEN 'N' END AS rt_pcr_type_test, CASE WHEN rt_pcr_type_test = '2' THEN 'H' || sero_type_h WHEN rt_pcr_type_test = '3' THEN 'N' || sero_type_n WHEN rt_pcr_type_test = '1' THEN 'N/A' WHEN rt_pcr_type_test IS NULL THEN 'N/A' END AS sero_type, rt_pcr_threshold, rt_pcr_control_value_1, rt_pcr_control_value_2, case result when 1 THEN 'Positive' when 2 THEN 'Negative' when 3 THEN 'Undetermined' end as result, protocol_details, ct_value, result_details,(select username from auth_user where id = t.test_setup_by::int) test_setup_by,(select username from auth_user where id = t.name_result_input_by::int) name_result_input_by from q t"
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
            
        else:
            df = pandas.DataFrame()
            for each in all_geo_id:
                query = "with q as(with t as(select distinct on(investigation_id) investigation_id,working_upazila_id from vw_avian_influenza_investigation) select * from t,result_inputs r where t.investigation_id = r.reference_investigation_id) select reference_investigation_id,reference_sample_id,test_set_up_number,date_test_set_up,date_out_put, CASE WHEN test_name = 1 THEN 'RT-PCR' WHEN test_name = 2 THEN other_test_name END AS test_name, CASE rt_pcr_type_test WHEN '1' THEN 'M gene' WHEN '2' THEN 'H' WHEN '3' THEN 'N' END AS rt_pcr_type_test, CASE WHEN rt_pcr_type_test = '2' THEN 'H' || sero_type_h WHEN rt_pcr_type_test = '3' THEN 'N' || sero_type_n WHEN rt_pcr_type_test = '1' THEN 'N/A' WHEN rt_pcr_type_test IS NULL THEN 'N/A' END AS sero_type, rt_pcr_threshold, rt_pcr_control_value_1, rt_pcr_control_value_2, case result when 1 THEN 'Positive' when 2 THEN 'Negative' when 3 THEN 'Undetermined' end as result, protocol_details, ct_value, result_details,(select username from auth_user where id = t.test_setup_by::int) test_setup_by,(select username from auth_user where id = t.name_result_input_by::int) name_result_input_by from q t where working_upazila_id = " + str(each)
                temp_df = pandas.DataFrame()
                temp_df = pandas.read_sql(query, connection)
                if not temp_df.empty:
                    df = df.append(temp_df, ignore_index=True)

    writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
    df.to_excel(writer, sheet_name='Sheet1', index=False)
    writer.save()
    f = open('onadata/media/uploaded_files/output.xlsx', 'r')
    response = HttpResponse(f, mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=AI Lab Result.xls'
    return response


@login_required
def sink_lab_result_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    # fetching all organization recursively of current_user
    all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
    org_id_list = [org.pk for org in all_organizations]

    # this geo_data is the variable for storing all geo location for current_user
    all_geo_id = []
    col_name = []
    json_data = []


    org_type_query = "select * from usermodule_organizations where id = " + str(current_user.organisation_name_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(org_type_query, connection)

    # for CO users
    # print df.organization_type.tolist()[0]
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 1:
        select_query = "with q as(with t as(select distinct ON(live_bird_market_id) live_bird_market_id,working_upazila_id from vw_sink_surveillance) select * from t,result_inputs r where t.live_bird_market_id = r.reference_investigation_id) select reference_investigation_id,reference_sample_id,test_set_up_number,date_test_set_up,date_out_put, case result when 1 THEN 'Positive' when 2 THEN 'Negative' when 3 THEN 'Undetermined' end as result, protocol_details, ct_value, result_details,(select username from auth_user where id = t.test_setup_by::int) test_setup_by,(select username from auth_user where id = t.name_result_input_by::int) name_result_input_by from q t"
        data = __db_fetch_values_dict(select_query)
        for each1 in data:
                json_data.append(handle_none(each1))
                # each1 contains a json dictionary.
                # each1.items() create (key,value) pair
                for key, value in each1.items():
                    if key not in col_name and key != "data_id":
                        # unique column name insert in col_name list
                        col_name.append(key)
        all_geo_id.append(1)
        return render(request, 'fao_module/sink_lab_result_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})


    # for LAB users
    if df.organization_type.tolist()[0] is not None and int(df.organization_type.tolist()[0]) == 3:
        # print org_id_list
        for each in org_id_list:
            select_query = "with q as(with t as(select distinct ON(live_bird_market_id) live_bird_market_id,working_upazila_id from vw_sink_surveillance) select * from t,result_inputs r where t.live_bird_market_id = r.reference_investigation_id) select reference_investigation_id,reference_sample_id,test_set_up_number,date_test_set_up,date_out_put, case result when 1 THEN 'Positive' when 2 THEN 'Negative' when 3 THEN 'Undetermined' end as result, protocol_details, ct_value, result_details,(select username from auth_user where id = t.test_setup_by::int) test_setup_by,(select username from auth_user where id = t.name_result_input_by::int) name_result_input_by from q t where working_upazila_id = " + str(each)
            data = __db_fetch_values_dict(select_query)
            for each1 in data:
                json_data.append(handle_none(each1))
                # each1 contains a json dictionary.
                # each1.items() create (key,value) pair
                for key, value in each1.items():
                    if key not in col_name and key != "data_id":
                        # unique column name insert in col_name list
                        col_name.append(key)
            all_geo_id.append(each)
        return render(request, 'fao_module/sink_lab_result_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})
    message = "You have no access to this page"    
    return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def xls_report_creator_for_sink_lab_result(request):
    
    all_geo_id = request.POST.getlist('all_geo_id')
    if len(all_geo_id):
        if int(all_geo_id[0]) == 1:
            query = "with q as(with t as(select distinct ON(live_bird_market_id) live_bird_market_id,working_upazila_id from vw_sink_surveillance) select * from t,result_inputs r where t.live_bird_market_id = r.reference_investigation_id) select reference_investigation_id,reference_sample_id,test_set_up_number,date_test_set_up,date_out_put, CASE WHEN test_name = 1 THEN 'RT-PCR' WHEN test_name = 2 THEN other_test_name END AS test_name, CASE rt_pcr_type_test WHEN '1' THEN 'M gene' WHEN '2' THEN 'H' WHEN '3' THEN 'N' END AS rt_pcr_type_test, CASE WHEN rt_pcr_type_test = '2' THEN 'H' || sero_type_h WHEN rt_pcr_type_test = '3' THEN 'N' || sero_type_n WHEN rt_pcr_type_test = '1' THEN 'N/A' WHEN rt_pcr_type_test IS NULL THEN 'N/A' END AS sero_type, rt_pcr_threshold, rt_pcr_control_value_1, rt_pcr_control_value_2, case result when 1 THEN 'Positive' when 2 THEN 'Negative' when 3 THEN 'Undetermined' end as result, protocol_details, ct_value, result_details,(select username from auth_user where id = t.test_setup_by::int) test_setup_by,(select username from auth_user where id = t.name_result_input_by::int) name_result_input_by from q t"
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
            
        else:
            df = pandas.DataFrame()
            for each in all_geo_id:
                query = "with q as(with t as(select distinct ON(live_bird_market_id) live_bird_market_id,working_upazila_id from vw_sink_surveillance) select * from t,result_inputs r where t.live_bird_market_id = r.reference_investigation_id) select reference_investigation_id,reference_sample_id,test_set_up_number,date_test_set_up,date_out_put, CASE WHEN test_name = 1 THEN 'RT-PCR' WHEN test_name = 2 THEN other_test_name END AS test_name, CASE rt_pcr_type_test WHEN '1' THEN 'M gene' WHEN '2' THEN 'H' WHEN '3' THEN 'N' END AS rt_pcr_type_test, CASE WHEN rt_pcr_type_test = '2' THEN 'H' || sero_type_h WHEN rt_pcr_type_test = '3' THEN 'N' || sero_type_n WHEN rt_pcr_type_test = '1' THEN 'N/A' WHEN rt_pcr_type_test IS NULL THEN 'N/A' END AS sero_type, rt_pcr_threshold, rt_pcr_control_value_1, rt_pcr_control_value_2, case result when 1 THEN 'Positive' when 2 THEN 'Negative' when 3 THEN 'Undetermined' end as result, protocol_details, ct_value, result_details,(select username from auth_user where id = t.test_setup_by::int) test_setup_by,(select username from auth_user where id = t.name_result_input_by::int) name_result_input_by from q t where working_upazila_id = " + str(each)
                temp_df = pandas.DataFrame()
                temp_df = pandas.read_sql(query, connection)
                if not temp_df.empty:
                    df = df.append(temp_df, ignore_index=True)
    writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
    df.to_excel(writer, sheet_name='Sheet1', index=False)
    writer.save()
    f = open('onadata/media/uploaded_files/output.xlsx', 'r')
    response = HttpResponse(f, mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=Sink Surveillance Lab Result.xls'
    return response


@login_required
def avian_influenza_view(request, data_id):
    query = "SELECT investigation_id, date_sample_collected,(SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, mouza, village, contact_person_name, title_position, contact_person_mobile, CASE sex WHEN '1' THEN 'Male' WHEN '2' THEN 'Female' END AS sex, gps_lattitude, gps_longitude, CASE cases_occur_production_system WHEN '1' THEN 'Farm' WHEN '2' THEN 'Backyard' WHEN '3' THEN other_cases_occur_production_system END AS cases_occur_production_system, CASE has_farm_previously_assessed WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS has_farm_previously_assessed, date_previously_assessed, deshi_chicken_sample_number, deshi_chicken_sample_type_description, deshi_chicken_sample_id, sonali_chicken_sample_number, sonali_chicken_sample_type_description, sonali_chicken_sample_id, brown_comm_chicken_sample_number, brown_comm_chicken_sample_type_description, brown_comm_sample_id, white_comm_chicken_sample_number, white_comm_chicken_sample_type_description, white_comm_sample_id, duck_number_sample, duck_sample_type_description, duck_sample_id, other, other_sample_number, other_sample_type_description, other_sample_id, laboratory_name_sample_sent_to, sample_collected_by_name FROM vw_ai_sample_submission where data_id = " + str(data_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    data = {}
    data['investigation_id'] = df.investigation_id.tolist()[0]
    data['date_sample_collected'] = df.date_sample_collected.tolist()[0]
    data['division'] = df.division.tolist()[0]
    data['district'] = df.district.tolist()[0]
    data['upazila'] = df.upazila.tolist()[0]
    data['xunion'] = df.xunion.tolist()[0]
    data['mouza'] = df.mouza.tolist()[0]
    data['village'] = df.village.tolist()[0]
    data['contact_person_name'] = df.contact_person_name.tolist()[0]
    data['contact_person_mobile'] = df.contact_person_mobile.tolist()[0]
    data['sex'] = df.sex.tolist()[0]
    data['title_position'] = df.title_position.tolist()[0]
    data['gps_lattitude'] = df.gps_lattitude.tolist()[0]
    data['gps_longitude'] = df.gps_longitude.tolist()[0]
    data['cases_occur_production_system'] = df.cases_occur_production_system.tolist()[0]
    data['has_farm_previously_assessed'] = df.has_farm_previously_assessed.tolist()[0]
    data['date_sample_collected'] = df.date_sample_collected.tolist()[0]
    data['sample_collected_by_name'] = df.sample_collected_by_name.tolist()[0]
    data['laboratory_name_sample_sent_to'] = df.laboratory_name_sample_sent_to.tolist()[0]
    data['deshi_chicken_sample_number'] = df.deshi_chicken_sample_number.tolist()[0]
    data['deshi_chicken_sample_type_description'] = df.deshi_chicken_sample_type_description.tolist()[0]
    data['deshi_chicken_sample_id'] = df.deshi_chicken_sample_id.tolist()[0]
    data['sonali_chicken_sample_number'] = df.sonali_chicken_sample_number.tolist()[0]
    data['sonali_chicken_sample_type_description'] = df.sonali_chicken_sample_type_description.tolist()[0]
    data['sonali_chicken_sample_id'] = df.sonali_chicken_sample_id.tolist()[0]
    data['brown_comm_chicken_sample_number'] = df.brown_comm_chicken_sample_number.tolist()[0]
    data['brown_comm_chicken_sample_type_description'] = df.brown_comm_chicken_sample_type_description.tolist()[0]
    data['brown_comm_sample_id'] = df.brown_comm_sample_id.tolist()[0]
    data['white_comm_chicken_sample_number'] = df.white_comm_chicken_sample_number.tolist()[0]
    data['white_comm_chicken_sample_type_description'] = df.white_comm_chicken_sample_type_description.tolist()[0]
    data['white_comm_sample_id'] = df.white_comm_sample_id.tolist()[0]
    data['duck_number_sample'] = df.duck_number_sample.tolist()[0]
    data['duck_sample_type_description'] = df.duck_sample_type_description.tolist()[0]
    data['duck_sample_id'] = df.duck_sample_id.tolist()[0]
    data['other_sample_number'] = df.other_sample_number.tolist()[0]
    data['other_sample_type_description'] = df.other_sample_type_description.tolist()[0]
    data['other_sample_id'] = df.other_sample_id.tolist()[0]
    data['duck_sample_type_description'] = df.duck_sample_type_description.tolist()[0]
    data['duck_sample_type_description'] = df.duck_sample_type_description.tolist()[0]
    data = handle_none(data)
    return render(request, 'fao_module/avian_influenza_view.html',{'data': data})

@login_required
def avian_influenza_investigation_view(request, data_id):
    query = "SELECT investigation_id, farm_id, date_completed,(SELECT name FROM geo_cluster WHERE value :: text = division) AS division, (SELECT name FROM geo_cluster WHERE value :: text = district) AS district, (SELECT name FROM geo_cluster WHERE value :: text = upazila) AS upazila, (SELECT name FROM geo_cluster WHERE value :: text = xunion) AS xunion, mouza, village, farmer_name, title_position, mobile_contact_person, CASE sex WHEN '1' THEN 'Male' WHEN '2' THEN 'Female' END AS sex, gps_lattitude, gps_longitude, CASE were_called_investigate_birds WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_called_investigate_birds, CASE meeting_raise_community_avian_influenza WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS meeting_raise_community_avian_influenza, CASE search_sick_dead_birds WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS search_sick_dead_birds, CASE were_sick_dead_birds_found WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_sick_dead_birds_found, date_received_sick_dead_info, date_estimated_onset, CASE cases_occur_type_production_system WHEN '1' THEN 'Farm' WHEN '2' THEN 'Backyard' WHEN '3' THEN 'Wild Bird' END AS cases_occur_type_production_system, CASE has_farm_previously_assessed WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS has_farm_previously_assessed, date_previously_assessed, Replace(clinical_sign_observed, '@@', ',') AS clinical_sign_observed, deshi_chicken, deshi_chicken_dead, deshi_chicken_sick, deshi_chicken_population, sonali_chicken_dead, sonali_chicken_sick, sonali_chicken_total_population, brown_comm_chicken, brown_comm_chicken_dead, brown_comm_chicken_sick, brown_comm_chicken_population, white_comm_chicken, white_comm_chicken_dead, white_comm_chicken_sick, white_comm_chicken_population, ducks, duck_dead, duck_sick, duck_population, others_affected_species, other_affected_dead, other_affected_sick, other_affected_population, CASE birds_production_purpose WHEN '1' THEN 'Egg' WHEN '2' THEN 'Meat' WHEN '3' THEN 'Egg & Meat' WHEN '4' THEN 'Breeder' WHEN '5' THEN 'Sport' WHEN '6' THEN 'Pet' END AS birds_production_purpose, sick_dead_tested_by_rapid_test, CASE used_rapid_test_name WHEN '1' THEN 'Bionote Anigen AIV test' ELSE other_used_rapid_test_name END AS used_rapid_test_name, CASE rapid_test_result WHEN '1' THEN 'Positive' WHEN '2' THEN 'Negative' WHEN '3' THEN 'Not performed' END AS rapid_test_result, CASE vtm_sample_collected WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS vtm_sample_collected, date_vtm_sample_collected, CASE pcr_result WHEN '1' THEN 'Positive' WHEN '2' THEN 'Negative' WHEN '3' THEN 'Test not performed' WHEN '4' THEN 'No lab report received' END AS pcr_result, CASE why_not_vtm WHEN '1' THEN 'No VTM' WHEN '2' THEN 'Not necessary' END AS why_not_vtm, CASE type_culling_performed WHEN '1' THEN 'Focal culling ( culling of all birds in affected flock)' WHEN '2' THEN 'No culling performed' END AS type_culling_performed, number_birds_culled, why_not_culled, CASE type_compensation_provided WHEN '1' THEN 'Vaccination' WHEN '2' THEN 'Young bird restocking' WHEN '3' THEN 'No compensation' END AS type_compensation_provided, additional_investigation_information,(select username from auth_user where id = t.investigator_name1::int) as investigator_name1, investigator_designation1, investogator_contact_number1,(select username from auth_user where id = t.investigator_name2::int) as investigator_name2 , investigator_designation2, investigator_contact_number2,(select username from auth_user where id = t.admin_name1::int )as admin_name1,admin_working_date11, admin_working_date12, admin_working_date13, admin_overnight_date11, admin_overnight_date12, admin_overnight_date13, (select username from auth_user where id = t.admin_name2::int )as admin_name2,admin_working_date21, admin_working_date22, admin_working_date23, admin_overnight_date21, admin_overnight_date22, admin_overnight_date23, (select username from auth_user where id = t.acknowledge_by::int) as acknowledge_by, (select username from auth_user where id = t.approved_by::int) as approved_by, (select username from auth_user where id = t.username::int) as username, created_at FROM public.vw_avian_influenza_investigation t where data_id = " + str(data_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    data = {}
    data['investigation_id'] = df.investigation_id.tolist()[0]
    data['farm_id'] = df.farm_id.tolist()[0]
    data['date_completed'] = df.date_completed.tolist()[0]
    data['division'] = df.division.tolist()[0]
    data['district'] = df.district.tolist()[0]
    data['upazila'] = df.upazila.tolist()[0]
    data['mouza'] = df.mouza.tolist()[0]
    data['xunion'] = df.xunion.tolist()[0]
    data['village'] = df.village.tolist()[0]
    data['farmer_name'] = df.farmer_name.tolist()[0]
    data['title_position'] = df.title_position.tolist()[0]
    data['mobile_contact_person'] = df.mobile_contact_person.tolist()[0]
    data['sex'] = df.sex.tolist()[0]
    data['gps_lattitude'] = df.gps_lattitude.tolist()[0]
    data['gps_longitude'] = df.gps_longitude.tolist()[0]
    data['were_called_investigate_birds'] = df.were_called_investigate_birds.tolist()[0]
    data['meeting_raise_community_avian_influenza'] = df.meeting_raise_community_avian_influenza.tolist()[0]
    data['search_sick_dead_birds'] = df.search_sick_dead_birds.tolist()[0]
    data['were_sick_dead_birds_found'] = df.were_sick_dead_birds_found.tolist()[0]
    data['date_received_sick_dead_info'] = df.date_received_sick_dead_info.tolist()[0]
    data['date_estimated_onset'] = df.date_estimated_onset.tolist()[0]
    data['cases_occur_type_production_system'] = df.cases_occur_type_production_system.tolist()[0]
    data['has_farm_previously_assessed'] = df.has_farm_previously_assessed.tolist()[0]
    data['date_previously_assessed'] = df.date_previously_assessed.tolist()[0]
    data['clinical_sign_observed'] = df.clinical_sign_observed.tolist()[0]
    data['deshi_chicken'] = df.deshi_chicken.tolist()[0]
    data['deshi_chicken_dead'] = df.deshi_chicken_dead.tolist()[0]
    data['deshi_chicken_sick'] = df.deshi_chicken_sick.tolist()[0]
    data['deshi_chicken_population'] = df.deshi_chicken_population.tolist()[0]
    data['sonali_chicken_dead'] = df.sonali_chicken_dead.tolist()[0]
    data['sonali_chicken_sick'] = df.sonali_chicken_sick.tolist()[0]
    data['sonali_chicken_total_population'] = df.sonali_chicken_total_population.tolist()[0]
    data['brown_comm_chicken_dead'] = df.brown_comm_chicken_dead.tolist()[0]
    data['brown_comm_chicken_sick'] = df.brown_comm_chicken_sick.tolist()[0]
    data['brown_comm_chicken_population'] = df.brown_comm_chicken_population.tolist()[0]
    data['white_comm_chicken_dead'] = df.white_comm_chicken_dead.tolist()[0]
    data['white_comm_chicken_sick'] = df.white_comm_chicken_sick.tolist()[0]
    data['white_comm_chicken_population'] = df.white_comm_chicken_population.tolist()[0]
    data['duck_dead'] = df.duck_dead.tolist()[0]
    data['duck_sick'] = df.white_comm_chicken_population.tolist()[0]
    data['duck_population'] = df.white_comm_chicken_population.tolist()[0]
    data['other_affected_dead'] = df.other_affected_dead.tolist()[0]
    data['other_affected_sick'] = df.other_affected_sick.tolist()[0]
    data['other_affected_population'] = df.other_affected_population.tolist()[0]
    data['sick_dead_tested_by_rapid_test'] = df.sick_dead_tested_by_rapid_test.tolist()[0]
    data['used_rapid_test_name'] = df.used_rapid_test_name.tolist()[0]
    data['rapid_test_result'] = df.rapid_test_result.tolist()[0]
    data['vtm_sample_collected'] = df.vtm_sample_collected.tolist()[0]
    data['date_vtm_sample_collected'] = df.date_vtm_sample_collected.tolist()[0]
    data['pcr_result'] = df.pcr_result.tolist()[0]
    data['why_not_vtm'] = df.why_not_vtm.tolist()[0]
    data['type_culling_performed'] = df.type_culling_performed.tolist()[0]
    data['number_birds_culled'] = df.number_birds_culled.tolist()[0]
    data['why_not_culled'] = df.why_not_culled.tolist()[0]
    data['additional_investigation_information'] = df.additional_investigation_information.tolist()[0]
    data['investigator_name1'] = df.investigator_name1.tolist()[0]
    data['investigator_designation1'] = df.investigator_designation1.tolist()[0]
    data['investogator_contact_number1'] = df.investogator_contact_number1.tolist()[0]
    data['investigator_name2'] = df.investigator_name2.tolist()[0]
    data['investigator_designation2'] = df.investigator_designation2.tolist()[0]
    data['investigator_contact_number2'] = df.investigator_contact_number2.tolist()[0]
    data['admin_name1'] = df.admin_name1.tolist()[0]
    data['admin_working_date11'] = df.admin_working_date11.tolist()[0]
    data['admin_working_date12'] = df.admin_working_date12.tolist()[0]
    data['admin_working_date13'] = df.admin_working_date13.tolist()[0]
    data['admin_overnight_date11'] = df.admin_overnight_date11.tolist()[0]
    data['admin_overnight_date12'] = df.admin_overnight_date12.tolist()[0]
    data['admin_overnight_date13'] = df.admin_overnight_date13.tolist()[0]
    data['admin_name2'] = df.admin_name2.tolist()[0]
    data['admin_working_date21'] = df.admin_working_date21.tolist()[0]
    data['admin_working_date22'] = df.admin_working_date22.tolist()[0]
    data['admin_working_date23'] = df.admin_working_date23.tolist()[0]
    data['admin_overnight_date21'] = df.admin_overnight_date21.tolist()[0]
    data['admin_overnight_date22'] = df.admin_overnight_date22.tolist()[0]
    data['admin_overnight_date23'] = df.admin_overnight_date23.tolist()[0]
    data['acknowledge_by'] = df.acknowledge_by.tolist()[0]
    data['approved_by'] = df.approved_by.tolist()[0]
    data = handle_none(data)
    return render(request, 'fao_module/avian_influenza_investigation_view.html',{'data': data})

@login_required
def generic_disease_investigation_view(request, data_id):
    query = "SELECT investigation_id, farm_id, date_initial_visit,(SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, mouza, village, name_contact_person, title_position, mobile_contact_person, case sex WHEN '1' THEN 'Male' WHEN '2' THEN 'Female' END AS sex, gps_lattitude, gps_longitude, case were_called_investigate_animal WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_called_investigate_animal, case meeting_raise_community_awareness_disease WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS meeting_raise_community_awareness_disease, case search_sick_dead_animal WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS search_sick_dead_animal, case were_sick_dead_animal_found WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_sick_dead_animal_found, date_received_sick_dead_info, estimated_onset, case type_production_system_occur WHEN '1' THEN 'Farm ' WHEN '2' THEN 'Household' END AS type_production_system_occur, case has_farm_previously_assessed WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS has_farm_previously_assessed, date_farm_previously_assessed, cattle, cattle_dead, cattle_sick, cattle_population, goats, goats_dead, goats_sick, goats_total_population, sheep, sheep_dead, sheep_sick, sheep_population, buffalo, buffalo_dead, buffalo_sick, buffalo_population, horses, horse_dead, horse_sick, horse_population, others_affected_species, other_affected_dead, other_affected_sick, other_affected_population, sick_dead_tested_for_diagnosis, Replace(specimen_type, '@@', ',') AS specimen_type, post_mortem_findings, case is_vtm_sample_collected WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS is_vtm_sample_collected, date_vtm_sample_collected, case pcr_result WHEN '1' THEN 'Positive' WHEN '2' THEN 'Negative' WHEN '3' THEN 'Test not performed' WHEN '4' THEN 'No lab report received' END AS pcr_result, case why_not_vtm WHEN '1' THEN ' No VTM' WHEN '2' THEN 'Not necessary' END AS why_not_vtm, positive_poison, number_poison, positive_bacteria, number_bacteria, positive_virus, number_virus, Replace(initial_control_measure, '@@', ',') AS initial_control_measure, Replace(clinical_symptoms, '@@', ',') AS clinical_symptoms, last_documented_similar_incident_where, last_documented_similar_incident_when, additional_investigation_info,(select username from auth_user where id = t.investigator_name1::int )as investigator_name1, investigator_designation1, investigator_contact_number1,(select username from auth_user where id = t.investigator_name2::int )as investigator_name2, investigator_designation2, investigator_contact_number2,(select username from auth_user where id = t.admin_name1::int )as admin_name1,admin_working_date11, admin_working_date12, admin_working_date13, admin_overnight_date11, admin_overnight_date12, admin_overnight_date13, (select username from auth_user where id = t.admin_name2::int )as admin_name2,admin_working_date21, admin_working_date22, admin_working_date23, admin_overnight_date21, admin_overnight_date22, admin_overnight_date23, (select username from auth_user where id = t.acknowledge_by::int )as acknowledge_by ,(select username from auth_user where id = t.approved_by::int )as approved_by , assigned_lab,(select username from auth_user where id = t.username::int )as username,(select username from auth_user where id = t.created_at::int )as created_at FROM PUBLIC.vw_generic_disease_investigation t where data_id = " + str(data_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    data = {}
    data['investigation_id'] = df.investigation_id.tolist()[0]
    data['farm_id'] = df.farm_id.tolist()[0]
    data['date_initial_visit'] = df.date_initial_visit.tolist()[0]
    data['division'] = df.division.tolist()[0]
    data['district'] = df.district.tolist()[0]
    data['upazila'] = df.upazila.tolist()[0]
    data['mouza'] = df.mouza.tolist()[0]
    data['xunion'] = df.xunion.tolist()[0]
    data['village'] = df.village.tolist()[0]
    data['name_contact_person'] = df.name_contact_person.tolist()[0]
    data['title_position'] = df.title_position.tolist()[0]
    data['mobile_contact_person'] = df.mobile_contact_person.tolist()[0]
    data['sex'] = df.sex.tolist()[0]
    data['gps_lattitude'] = df.gps_lattitude.tolist()[0]
    data['gps_longitude'] = df.gps_longitude.tolist()[0]
    data['were_called_investigate_animal'] = df.were_called_investigate_animal.tolist()[0]
    data['meeting_raise_community_awareness_disease'] = df.meeting_raise_community_awareness_disease.tolist()[0]
    data['search_sick_dead_animal'] = df.search_sick_dead_animal.tolist()[0]
    data['were_sick_dead_animal_found'] = df.were_sick_dead_animal_found.tolist()[0]
    data['date_received_sick_dead_info'] = df.date_received_sick_dead_info.tolist()[0]
    data['estimated_onset'] = df.estimated_onset.tolist()[0]
    data['type_production_system_occur'] = df.type_production_system_occur.tolist()[0]
    data['has_farm_previously_assessed'] = df.has_farm_previously_assessed.tolist()[0]
    data['date_farm_previously_assessed'] = df.date_farm_previously_assessed.tolist()[0]
    data['cattle_dead'] = df.cattle_dead.tolist()[0]
    data['cattle_sick'] = df.cattle_sick.tolist()[0]
    data['cattle_population'] = df.cattle_population.tolist()[0]
    data['goats_dead'] = df.goats_dead.tolist()[0]
    data['goats_sick'] = df.goats_sick.tolist()[0]
    data['goats_total_population'] = df.goats_total_population.tolist()[0]
    data['sheep_dead'] = df.sheep_dead.tolist()[0]
    data['sheep_sick'] = df.sheep_sick.tolist()[0]
    data['sheep_population'] = df.sheep_population.tolist()[0]
    data['buffalo_dead'] = df.buffalo_dead.tolist()[0]
    data['buffalo_sick'] = df.buffalo_sick.tolist()[0]
    data['buffalo_population'] = df.buffalo_population.tolist()[0]
    data['horse_dead'] = df.horse_dead.tolist()[0]
    data['horse_sick'] = df.horse_sick.tolist()[0]
    data['horse_population'] = df.horse_population.tolist()[0]
    data['other_affected_dead'] = df.other_affected_dead.tolist()[0]
    data['other_affected_sick'] = df.other_affected_sick.tolist()[0]
    data['other_affected_population'] = df.other_affected_population.tolist()[0]
    data['sick_dead_tested_for_diagnosis'] = df.sick_dead_tested_for_diagnosis.tolist()[0]
    if df.specimen_type.tolist()[0] is not None:
        data['specimen_type'] = df.specimen_type.tolist()[0].split(',')
    else:
        data['specimen_type'] = None
    data['post_mortem_findings'] = df.post_mortem_findings.tolist()[0]
    data['is_vtm_sample_collected'] = df.is_vtm_sample_collected.tolist()[0]
    data['date_vtm_sample_collected'] = df.date_vtm_sample_collected.tolist()[0]
    data['pcr_result'] = df.pcr_result.tolist()[0]
    data['why_not_vtm'] = df.why_not_vtm.tolist()[0]
    data['positive_poison'] = df.positive_poison.tolist()[0]
    data['number_poison'] = df.number_poison.tolist()[0]
    data['positive_bacteria'] = df.positive_bacteria.tolist()[0]
    data['number_bacteria'] = df.number_bacteria.tolist()[0]
    data['positive_virus'] = df.positive_virus.tolist()[0]
    data['number_virus'] = df.number_virus.tolist()[0]
    if df.initial_control_measure.tolist()[0] is not None:
        data['initial_control_measure'] = df.initial_control_measure.tolist()[0].split(',')
    else:
        data['initial_control_measure'] = None
    data['clinical_symptoms'] = df.clinical_symptoms.tolist()[0]
    data['last_documented_similar_incident_where'] = df.last_documented_similar_incident_where.tolist()[0]
    data['last_documented_similar_incident_when'] = df.last_documented_similar_incident_when.tolist()[0]
    data['additional_investigation_info'] = df.additional_investigation_info.tolist()[0]
    data['investigator_name1'] = df.investigator_name1.tolist()[0]
    data['investigator_designation1'] = df.investigator_designation1.tolist()[0]
    data['investigator_contact_number1'] = df.investigator_contact_number1.tolist()[0]
    data['investigator_name2'] = df.investigator_name2.tolist()[0]
    data['investigator_designation2'] = df.investigator_designation2.tolist()[0]
    data['investigator_contact_number2'] = df.investigator_contact_number2.tolist()[0]
    data['admin_name1'] = df.admin_name1.tolist()[0]
    data['admin_working_date11'] = df.admin_working_date11.tolist()[0]
    data['admin_working_date12'] = df.admin_working_date12.tolist()[0]
    data['admin_working_date13'] = df.admin_working_date13.tolist()[0]
    data['admin_overnight_date11'] = df.admin_overnight_date11.tolist()[0]
    data['admin_overnight_date12'] = df.admin_overnight_date12.tolist()[0]
    data['admin_overnight_date13'] = df.admin_overnight_date13.tolist()[0]
    data['admin_name2'] = df.admin_name2.tolist()[0]
    data['admin_working_date21'] = df.admin_working_date21.tolist()[0]
    data['admin_working_date22'] = df.admin_working_date22.tolist()[0]
    data['admin_working_date23'] = df.admin_working_date23.tolist()[0]
    data['admin_overnight_date21'] = df.admin_overnight_date21.tolist()[0]
    data['admin_overnight_date22'] = df.admin_overnight_date22.tolist()[0]
    data['admin_overnight_date23'] = df.admin_overnight_date23.tolist()[0]
    data['acknowledge_by'] = df.acknowledge_by.tolist()[0]
    data['approved_by'] = df.approved_by.tolist()[0]
    data = handle_none(data)
    return render(request, 'fao_module/generic_disease_investigation_view.html',{'data': data})


@login_required
def farm_assessment_view(request, data_id):
    query = "SELECT farm_id, CASE report_type WHEN '1' THEN 'First Assessment Report' WHEN '2' THEN 'Follow-up Report' END AS report_type, date_initial_visit,(SELECT name FROM geo_cluster WHERE value :: text = division) AS division, (SELECT name FROM geo_cluster WHERE value :: text = district) AS district, (SELECT name FROM geo_cluster WHERE value :: text = upazila) AS upazila, (SELECT name FROM geo_cluster WHERE value :: text = xunion) AS xunion, mouza, village, address, owner_name, mobile_owner, CASE farm_ownership_type WHEN '4' THEN 'Rental' WHEN '3' THEN 'Personal contract' WHEN '2' THEN 'Independent' WHEN '1' THEN 'Corporate contract' END AS farm_ownership_type, CASE type_person_interviewed WHEN '1' THEN 'Owner' WHEN '2' THEN 'Farm manager' WHEN '3' THEN 'Farm worker' WHEN '4' THEN 'Dealer' END AS type_person_interviewed, gps_lattitude, gps_longitude, Replace(type_species, '@@', ',') AS type_species, Replace(type_chicken, '@@', ',') AS type_chicken, standing_population_birds, maximum_farm_capacity_birds, CASE birds_production_purpose WHEN '1' THEN 'Egg' WHEN '2' THEN 'Meat' WHEN '3' THEN 'Egg & Meat' WHEN '4' THEN 'Breeder' WHEN '5' THEN 'Sport' WHEN '6' THEN 'Pet' END AS birds_production_purpose, CASE age_arrival_farm WHEN '1' THEN 'DOC' WHEN '2' THEN 'Pullet' WHEN '3' THEN 'Adult' END AS age_arrival_farm, CASE previously_avian_influenza_investigate WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS previously_avian_influenza_investigate, date_previously_avian_influenza_investigate, vaccine1_ai_vaccination_used, CASE schedule_vaccine1 WHEN '1' THEN 'Age basis:' WHEN '2' THEN 'Calendar basis' WHEN '3' THEN 'After outbreak' WHEN '4' THEN 'No schedule (farmer doesn''t know)' END AS schedule_vaccine1, Replace(schedule_vaccine1_before_production, '@@', ',') AS schedule_vaccine1_before_production, Replace(schedule_vaccine1_after_production, '@@', ',') AS schedule_vaccine1_after_production, date1_last3_ai_vaccination1, date2_last3_ai_vaccination1, date3_last3_ai_vaccination1, vaccine2_ai_vaccination_used, CASE schedule_vaccine2 WHEN '1' THEN 'Age basis:' WHEN '2' THEN 'Calendar basis' WHEN '3' THEN 'After outbreak' WHEN '4' THEN 'No schedule (farmer doesn''t know)' END AS schedule_vaccine2, Replace(schedule_vaccine2_before_production, '@@', ',') AS schedule_vaccine2_before_production, Replace(schedule_vaccine2_after_production, '@@', ',') AS schedule_vaccine2_after_production, date1_last3_ai_vaccination2, date2_last3_ai_vaccination2, date3_last3_ai_vaccination2, CASE vaccination_given_by WHEN '1' THEN 'Outside vaccinator' WHEN '2' THEN 'Farm Staff' WHEN '3' THEN 'Both' END AS vaccination_given_by, Replace(vaccine_means_verification, '@@', ',') AS vaccine_means_verification, CASE outside_worker_do_not_enter_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS outside_worker_do_not_enter_farm, CASE only_workers_approved_visitor_enter_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS only_workers_approved_visitor_enter_farm, CASE no_manure_collector_enter_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS no_manure_collector_enter_farm, CASE fenced_duck_chicken_proof WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS fenced_duck_chicken_proof, CASE dead_birds_disposed_safely WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS dead_birds_disposed_safely, CASE sign_posted WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS sign_posted, CASE no_vehical_in_out_production_area WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS no_vehical_in_out_production_area, CASE only_workers_enter_production_area WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS only_workers_enter_production_area, CASE visitors_enter_production_if_approve_manager WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS visitors_enter_production_if_approve_manager, CASE access_control_loading_production_sign_posted WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS access_control_loading_production_sign_posted, CASE footwear_left_outside WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS footwear_left_outside, CASE change_clothes_entering_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS change_clothes_entering_farm, CASE uses_dedicated_footwear WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS uses_dedicated_footwear, CASE shower_entering_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS shower_entering_farm, CASE returning_materials_cleaned WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS returning_materials_cleaned, CASE returning_materials_disinfect WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS returning_materials_disinfect, CASE dead_bird_management_practice WHEN '1' THEN 'buried' WHEN '2' THEN 'river' WHEN '3' THEN 'rubbish pit' WHEN '4' THEN 'pond' WHEN '5' THEN 'open place/bush' WHEN '6' THEN 'rubbish container' WHEN '7' THEN 'food/feed' END AS dead_bird_management_practice, Replace(farm_entrance_means_verification, '@@', ',') AS farm_entrance_means_verification, antibacterial_usages_product1, CASE antibacterial_usage_salesman_product1 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Upazila Vet Hosp' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END AS antibacterial_usage_salesman_product1, CASE antibacterial_usage_prevention_product1 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END AS antibacterial_usage_prevention_product1, CASE antibacterial_usage_drinking_water_product1 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END AS antibacterial_usage_drinking_water_product1, CASE antibacterial_frequency_product1 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' WHEN '7' THEN '3 Times a Day' END AS antibacterial_frequency_product1, antibacterial_usages_product2, CASE antibacterial_usage_salesman_product2 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Upazila Vet Hosp' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END AS antibacterial_usage_salesman_product2, CASE antibacterial_usage_prevention_product2 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END AS antibacterial_usage_prevention_product2, CASE antibacterial_usage_drinking_water_product2 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END AS antibacterial_usage_drinking_water_product2, CASE antibacterial_frequency_product2 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' WHEN '7' THEN '3 Times a Day' END AS antibacterial_frequency_product2, antibacterial_usages_product3, CASE antibacterial_usage_salesman_product3 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Upazila Vet Hosp' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END AS antibacterial_usage_salesman_product3, CASE antibacterial_usage_prevention_product3 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END antibacterial_usage_prevention_product3, CASE antibacterial_usage_drinking_water_product3 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END AS antibacterial_usage_drinking_water_product3, CASE antibacterial_frequency_product3 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' WHEN '7' THEN '3 Times a Day' END AS antibacterial_frequency_product3, antibacterial_usages_product4, CASE antibacterial_usage_salesman_product4 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Upazila Vet Hosp' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END AS antibacterial_usage_salesman_product4, CASE antibacterial_usage_prevention_product4 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END AS antibacterial_usage_prevention_product4, CASE antibacterial_usage_drinking_water_product4 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END AS antibacterial_usage_drinking_water_product4, CASE antibacterial_frequency_product4 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' WHEN '7' THEN '3 Times a Day' END AS antibacterial_frequency_product4, antibacterial_usages_product5, CASE antibacterial_usage_salesman_product5 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Upazila Vet Hosp' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END AS antibacterial_usage_salesman_product5, CASE antibacterial_usage_prevention_product5 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END AS antibacterial_usage_prevention_product5, CASE antibacterial_usage_drinking_water_product5 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END AS antibacterial_usage_drinking_water_product5, CASE antibacterial_frequency_product5 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' WHEN '7' THEN '3 Times a Day' END AS antibacterial_frequency_product5, farmer_concern, image, (SELECT username FROM auth_user WHERE id = t.field_staff1 :: INT) AS field_staff1, (SELECT username FROM auth_user WHERE id = t.field_staff2 :: INT) AS field_staff2, (SELECT username FROM auth_user WHERE id = t.ackknowlwdge_by :: INT) AS ackknowlwdge_by, (SELECT username FROM auth_user WHERE id = t.approved_by :: INT) AS approved_by FROM vw_farm_assessment t where data_id = " + str(data_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    data = {}
    data['farm_id'] = df.farm_id.tolist()[0]
    data['report_type'] = df.report_type.tolist()[0]
    data['date_initial_visit'] = df.date_initial_visit.tolist()[0]
    data['division'] = df.division.tolist()[0]
    data['district'] = df.district.tolist()[0]
    data['upazila'] = df.upazila.tolist()[0]
    data['mouza'] = df.mouza.tolist()[0]
    data['xunion'] = df.xunion.tolist()[0]
    data['village'] = df.village.tolist()[0]
    data['address'] = df.address.tolist()[0]
    data['owner_name'] = df.owner_name.tolist()[0]
    data['mobile_owner'] = df.mobile_owner.tolist()[0]
    data['farm_ownership_type'] = df.farm_ownership_type.tolist()[0]
    data['type_person_interviewed'] = df.type_person_interviewed.tolist()[0]
    data['gps_lattitude'] = df.gps_lattitude.tolist()[0]
    data['gps_longitude'] = df.gps_longitude.tolist()[0]
    if df.type_species.tolist()[0] is not None:
        data['type_species'] = df.type_species.tolist()[0].split(',')
    else:
        data['type_species'] = None
    if df.type_chicken.tolist()[0] is not None:
        data['type_chicken'] = df.type_chicken.tolist()[0].split(',')
    else:
        data['type_chicken'] = None
    data['standing_population_birds'] = df.standing_population_birds.tolist()[0]
    data['maximum_farm_capacity_birds'] = df.maximum_farm_capacity_birds.tolist()[0]
    data['birds_production_purpose'] = df.birds_production_purpose.tolist()[0]
    data['age_arrival_farm'] = df.age_arrival_farm.tolist()[0]
    data['previously_avian_influenza_investigate'] = df.previously_avian_influenza_investigate.tolist()[0]
    data['date_previously_avian_influenza_investigate'] = df.date_previously_avian_influenza_investigate.tolist()[0]
    data['vaccine1_ai_vaccination_used'] = df.vaccine1_ai_vaccination_used.tolist()[0]
    data['schedule_vaccine1'] = df.schedule_vaccine1.tolist()[0]
    if df.schedule_vaccine1_before_production.tolist()[0] is not None:
        data['schedule_vaccine1_before_production'] = df.schedule_vaccine1_before_production.tolist()[0].split(',')
    else:
        data['schedule_vaccine1_before_production'] = None
    data['schedule_vaccine1_after_production'] = df.schedule_vaccine1_after_production.tolist()[0]
    data['date1_last3_ai_vaccination1'] = df.date1_last3_ai_vaccination1.tolist()[0]
    data['date2_last3_ai_vaccination1'] = df.date2_last3_ai_vaccination1.tolist()[0]
    data['date3_last3_ai_vaccination1'] = df.date3_last3_ai_vaccination1.tolist()[0]
    data['vaccine2_ai_vaccination_used'] = df.vaccine2_ai_vaccination_used.tolist()[0]
    data['schedule_vaccine2'] = df.schedule_vaccine2.tolist()[0]
    if df.schedule_vaccine2_before_production.tolist()[0] is not None:
        data['schedule_vaccine2_before_production'] = df.schedule_vaccine2_before_production.tolist()[0].split(',')
    else:
        data['schedule_vaccine2_before_production'] = None
    if df.schedule_vaccine2_after_production.tolist()[0] is not None:
        data['schedule_vaccine2_after_production'] = df.schedule_vaccine2_after_production.tolist()[0].split(',')
    else:
        data['schedule_vaccine2_after_production'] = None
    data['date1_last3_ai_vaccination2'] = df.date1_last3_ai_vaccination2.tolist()[0]
    data['date2_last3_ai_vaccination2'] = df.date2_last3_ai_vaccination2.tolist()[0]
    data['date3_last3_ai_vaccination2'] = df.date3_last3_ai_vaccination2.tolist()[0]
    data['vaccination_given_by'] = df.vaccination_given_by.tolist()[0]
    data['vaccine_means_verification'] = df.vaccine_means_verification.tolist()[0]
    data['outside_worker_do_not_enter_farm'] = df.outside_worker_do_not_enter_farm.tolist()[0]
    data['only_workers_approved_visitor_enter_farm'] = df.only_workers_approved_visitor_enter_farm.tolist()[0]
    data['no_manure_collector_enter_farm'] = df.no_manure_collector_enter_farm.tolist()[0]
    data['fenced_duck_chicken_proof'] = df.fenced_duck_chicken_proof.tolist()[0]
    data['dead_birds_disposed_safely'] = df.dead_birds_disposed_safely.tolist()[0]
    data['sign_posted'] = df.sign_posted.tolist()[0]
    data['no_vehical_in_out_production_area'] = df.no_vehical_in_out_production_area.tolist()[0]
    data['only_workers_enter_production_area'] = df.only_workers_enter_production_area.tolist()[0]
    data['visitors_enter_production_if_approve_manager'] = df.visitors_enter_production_if_approve_manager.tolist()[0]
    data['access_control_loading_production_sign_posted'] = df.access_control_loading_production_sign_posted.tolist()[0]
    data['footwear_left_outside'] = df.footwear_left_outside.tolist()[0]
    data['change_clothes_entering_farm'] = df.change_clothes_entering_farm.tolist()[0]
    data['uses_dedicated_footwear'] = df.uses_dedicated_footwear.tolist()[0]
    data['shower_entering_farm'] = df.shower_entering_farm.tolist()[0]
    data['returning_materials_cleaned'] = df.returning_materials_cleaned.tolist()[0]
    data['returning_materials_disinfect'] = df.returning_materials_disinfect.tolist()[0]
    data['dead_bird_management_practice'] = df.dead_bird_management_practice.tolist()[0]
    if df.farm_entrance_means_verification.tolist()[0] is not None:
        data['farm_entrance_means_verification'] = df.farm_entrance_means_verification.tolist()[0].split(',')
    else:
        data['farm_entrance_means_verification'] = None
    data['antibacterial_usages_product1'] = df.antibacterial_usages_product1.tolist()[0]
    data['antibacterial_usage_salesman_product1'] = df.antibacterial_usage_salesman_product1.tolist()[0]
    data['antibacterial_usage_prevention_product1'] = df.antibacterial_usage_prevention_product1.tolist()[0]
    data['antibacterial_usage_drinking_water_product1'] = df.antibacterial_usage_drinking_water_product1.tolist()[0]
    data['antibacterial_frequency_product1'] = df.antibacterial_frequency_product1.tolist()[0]
    data['antibacterial_usages_product2'] = df.antibacterial_usages_product2.tolist()[0]
    data['antibacterial_usages_product3'] = df.antibacterial_usages_product3.tolist()[0]
    data['antibacterial_usages_product4'] = df.antibacterial_usages_product4.tolist()[0]
    data['antibacterial_usages_product5'] = df.antibacterial_usages_product5.tolist()[0]
    data['antibacterial_usage_salesman_product2'] = df.antibacterial_usage_salesman_product2.tolist()[0]
    data['antibacterial_usage_prevention_product2'] = df.antibacterial_usage_prevention_product2.tolist()[0]
    data['antibacterial_usage_drinking_water_product2'] = df.antibacterial_usage_drinking_water_product2.tolist()[0]
    data['antibacterial_frequency_product2'] = df.antibacterial_frequency_product2.tolist()[0]
    data['antibacterial_usage_salesman_product3'] = df.antibacterial_usage_salesman_product3.tolist()[0]
    data['antibacterial_usage_prevention_product3'] = df.antibacterial_usage_prevention_product3.tolist()[0]
    data['antibacterial_usage_drinking_water_product3'] = df.antibacterial_usage_drinking_water_product3.tolist()[0]
    data['antibacterial_frequency_product3'] = df.antibacterial_frequency_product3.tolist()[0]
    data['antibacterial_usage_salesman_product4'] = df.antibacterial_usage_salesman_product4.tolist()[0]
    data['antibacterial_usage_prevention_product4'] = df.antibacterial_usage_prevention_product4.tolist()[0]
    data['antibacterial_usage_drinking_water_product4'] = df.antibacterial_usage_drinking_water_product4.tolist()[0]
    data['antibacterial_frequency_product4'] = df.antibacterial_frequency_product4.tolist()[0]
    data['antibacterial_usage_salesman_product5'] = df.antibacterial_usage_salesman_product5.tolist()[0]
    data['antibacterial_usage_prevention_product5'] = df.antibacterial_usage_prevention_product5.tolist()[0]
    data['antibacterial_usage_drinking_water_product5'] = df.antibacterial_usage_drinking_water_product5.tolist()[0]
    data['antibacterial_frequency_product5'] = df.antibacterial_frequency_product5.tolist()[0]
    data['farmer_concern'] = df.farmer_concern.tolist()[0]
    data['image'] = df.image.tolist()[0]
    data['field_staff1'] = df.field_staff1.tolist()[0]
    data['field_staff2'] = df.field_staff2.tolist()[0]
    data['ackknowlwdge_by'] = df.ackknowlwdge_by.tolist()[0]
    data['approved_by'] = df.approved_by.tolist()[0]
    data = handle_none(data)
    return render(request, 'fao_module/farm_assessment_view.html',{'data': data})



@login_required
def patient_registry_view(request,data_id):
    query = "SELECT date, owner_name, father_name, CASE entry_type WHEN '1' THEN 'New Patient' WHEN '2' THEN 'Follow Up' END AS entry_type, (SELECT NAME  FROM   geo_cluster  WHERE  value = division) AS division, (SELECT NAME FROM geo_cluster  WHERE  value = district) AS district, (SELECT NAME  FROM   geo_cluster  WHERE  value = upazila)                                AS upazila, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = xunion)  AS xunion, village, mobile, case species_type WHEN '10' THEN other_species_livestock WHEN '40' THEN other_species_poultry ELSE (select species_name from species where species_id::text = species_type) end as species_type, case breed WHEN '1' THEN 'Local' WHEN '2' THEN 'Cross' WHEN '3' THEN 'Exotic' WHEN '4' THEN 'Heading' end as breed, flock, herd, dead, sick, case brought_hospital WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS brought_hospital, case production_type WHEN '1' THEN 'Commercial Broiler' WHEN '2' THEN 'Commercial Layer' WHEN '3' THEN 'Backyard' WHEN '4' THEN 'Recreation' WHEN '5' THEN production_type_other END AS production_type, case age_type_poultry WHEN '1' THEN week || ' weeks' ELSE year || ' years ' || month || ' months ' || day || ' days' END AS age, CASE sex WHEN '1' THEN 'male' WHEN '2' THEN 'Female' WHEN '3' THEN 'Mixed' END AS sex, productive_stage, CASE is_pregnant WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS is_pregnant, body_weight, owner_complain, Replace(clinical_sign_symptom, '@@', ',')                        AS clinical_sign_symptom, Replace(tentative_diagnosis, '@@', ',')  AS tentative_diagnosis, Replace(tratment, '@@', ',')  AS tratment, advice, remarks, (select username from auth_user where id = t.username::int) as username FROM  PUBLIC.vw_patient_registry t where data_id = " +str(data_id)
    data = __db_fetch_values_dict(query)
    return render(request,'fao_module/patient_registry_view.html',{'data':json.dumps(data)})


@login_required
def postmortem_view(request,data_id):
    query = "SELECT date, owner_name, father_name,(SELECT NAME FROM geo_cluster WHERE value = division) AS division, (SELECT NAME FROM geo_cluster WHERE value = district) AS district, (SELECT NAME FROM geo_cluster WHERE value = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, address, village, mobile, sick, dead, case species_type WHEN '10' THEN other_species_livestock WHEN '40' THEN other_species_poultry ELSE (select species_name from species where species_id::text = species_type) end as species_type, number_sample, case sample_type WHEN '1' THEN 'Whole carcass' WHEN '2' THEN 'Live bird' WHEN '3' THEN 'Viscera' WHEN '4' THEN sample_type_other END AS sample_type, sample_history, postmortem_findings, Replace(tentative_diagnosis, '@@', ',') AS tentative_diagnosis, Replace(treatment_treatment, '@@', ',') AS treatment_treatment, Replace(advice_suggestions, '@@', ',') AS advice_suggestions, remarks, (select username from auth_user where id = t.username::int) as username, created_at FROM PUBLIC.vw_postmortem t where data_id = " +str(data_id)
    data = __db_fetch_values_dict(query)
    return render(request,'fao_module/postmortem_view.html',{'data':json.dumps(data)})


@login_required
def pathology_view(request,data_id):
    query = "SELECT date, owner_name, father_name, mobile,(SELECT NAME FROM geo_cluster WHERE value = division) AS division, (SELECT NAME FROM geo_cluster WHERE value = district) AS district, (SELECT NAME FROM geo_cluster WHERE value = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, village, case species_type WHEN '10' THEN other_species_livestock WHEN '40' THEN other_species_poultry ELSE (select species_name from species where species_id::text = species_type) end as species_type, sample_number, dead, sick, test_performed, sample_details, tratment, advice, remarks, test_result, sample_history, (select username from auth_user where id = t.username::int) as username, created_at FROM PUBLIC.vw_pathology t where data_id = " +str(data_id)
    data = __db_fetch_values_dict(query)
    return render(request,'fao_module/pathology_view.html',{'data':json.dumps(data)})



@login_required
def home_page(request):
    # print "START"
    # print datetime.datetime.now()
    content_affected = []
    content_mortality = []
    khulna_file = open("onadata/media/all_geojson/Khulna_div.geojson", 'r')
    khulna_content = khulna_file.read()
    khulna_file.close()
    chittagong_file = open("onadata/media/all_geojson/Chittagong_div.geojson", 'r')
    chittagong_content = chittagong_file.read()
    khulna_file.close()
    
    percentage_affected = []
    percentage_mortality = []
    query = "with t as( SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'Patients Registry'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'Postmortem'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'pathology'::text)) select vwunion.division,vwunion.division_id, sum(sick::int) total_sick FROM vwunion left outer join t on t.union_id::int = vwunion.union_id where division_id = 20 group by vwunion.division,vwunion.division_id having sum(sick::int) is not null"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    if not df.empty:
        percentage_affected.append(df.total_sick.tolist()[0])
        content_affected.append(chittagong_content)
    query = "with t as( SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'Patients Registry'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'Postmortem'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'pathology'::text)) select vwunion.division,vwunion.division_id, sum(sick::int) total_sick FROM vwunion left outer join t on t.union_id::int = vwunion.union_id where division_id = 40 group by vwunion.division,vwunion.division_id having sum(sick::int) is not null"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    if not df.empty:
        percentage_affected.append(df.total_sick.tolist()[0])
        content_affected.append(khulna_content)
    json_content_affected = json.dumps({'content_affected': content_affected})
    
    query = "with t as( SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'Patients Registry'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'Postmortem'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'pathology'::text)) select vwunion.division,vwunion.division_id, sum(dead::int) total_dead FROM vwunion left outer join t on t.union_id::int = vwunion.union_id where division_id = 20 group by vwunion.division,vwunion.division_id having sum(dead::int) is not null"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    if not df.empty:  
        percentage_mortality.append(df.total_dead.tolist()[0])
        content_mortality.append(chittagong_content)
    query = "with t as( SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'Patients Registry'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'Postmortem'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'pathology'::text)) select vwunion.division,vwunion.division_id, sum(dead::int) total_dead FROM vwunion left outer join t on t.union_id::int = vwunion.union_id where division_id = 40 group by vwunion.division,vwunion.division_id having sum(dead::int) is not null"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    if not df.empty:  
        percentage_mortality.append(df.total_dead.tolist()[0])
        content_mortality.append(khulna_content)
    json_content_mortality = json.dumps({'content_mortality': content_mortality})

    count_fetch_query_affected = "with t as( SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'Patients Registry'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'Postmortem'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'pathology'::text)), minimum as ( select vwunion.union_id, sum(sick::int) total_sick FROM vwunion left outer join t on t.union_id::int = vwunion.union_id group by vwunion.union_id having sum(sick::int) is not null ), maximum as ( select vwunion.division_id, sum(sick::int) total_sick FROM vwunion left outer join t on t.union_id::int = vwunion.union_id group by vwunion.division_id having sum(sick::int) is not null ) select min(minimum.total_sick) min_sick,max(maximum.total_sick) max_sick from minimum,maximum"
    df = pandas.DataFrame()
    df = pandas.read_sql(count_fetch_query_affected, connection)
    min_affected = 0
    max_affected = 0
    if df.min_sick.tolist()[0] is not None or df.min_sick.tolist()[0] is not None:
        min_affected = df.min_sick.tolist()[0]
        max_affected = df.max_sick.tolist()[0]

    count_fetch_query_mortality = "with t as( SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'Patients Registry'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'Postmortem'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'pathology'::text)), minimum as ( select vwunion.union_id, sum(dead::int) total_dead FROM vwunion left outer join t on t.union_id::int = vwunion.union_id group by vwunion.union_id having sum(dead::int) is not null ), maximum as ( select vwunion.division_id, sum(dead::int) total_dead FROM vwunion left outer join t on t.union_id::int = vwunion.union_id group by vwunion.division_id having sum(dead::int) is not null ) select min(minimum.total_dead) min_dead,max(maximum.total_dead) max_dead from minimum,maximum"
    df = pandas.DataFrame()
    df = pandas.read_sql(count_fetch_query_mortality, connection)
    min_mortality = 0
    max_mortality = 0
    if df.min_dead.tolist()[0] is not None or df.max_dead.tolist()[0] is not None:
        min_mortality = df.min_dead.tolist()[0]
        max_mortality = df.max_dead.tolist()[0]

    return render(request,'fao_module/home_page.html',{'json_content_mortality': json_content_mortality,'json_content_affected': json_content_affected, 'percentage_affected': percentage_affected,'percentage_mortality':percentage_mortality,'min_affected':min_affected,'max_affected':max_affected,'min_mortality':min_mortality,'max_mortality':max_mortality})


def handle_none(dictionary):
    for key,value in dictionary.items():
        if value is None:
            dictionary[key] = " "
    return dictionary


def handle_nan(dictionary):
    for key,value in dictionary.items():
        if value == "nan":
            dictionary[key] = " "
    return dictionary


def set_nan_to_space(var):
    if var == "nan":
        var = " "
    return var


@login_required
def affected_area_mortaility(request):
    content = []
    khulna_file = open("onadata/media/all_geojson/Khulna_div.geojson", 'r')
    khulna_content = khulna_file.read()
    khulna_file.close()
    chittagong_file = open("onadata/media/all_geojson/Chittagong_div.geojson", 'r')
    chittagong_content = chittagong_file.read()
    khulna_file.close()
    content.append(khulna_content)
    content.append(chittagong_content)
    json_content = json.dumps({'content': content})
    percentage = []
    query = "select * from geo_cluster where loc_type = 1"
    df = pandas.read_sql(query, connection)
    division = df.value.tolist()
    for each in division:
        query = "WITH q AS(WITH recursive children AS( WITH t AS(WITH p AS ( SELECT gc.value, (case coalesce(vpr.dead,'') when '' then '0' else (coalesce(vpr.dead,'0')) end) as dead, gc.parent FROM geo_cluster gc LEFT JOIN vw_patient_registry vpr ON vpr.xunion::int = gc.value WHERE gc.loc_type IN (1,2,3,4) UNION ALL SELECT gc.value, (case coalesce(vps.dead,'') when '' then '0' else (coalesce(vps.dead,'0')) end) as dead, gc.parent FROM geo_cluster gc LEFT JOIN vw_postmortem vps ON vps.xunion::int = gc.value WHERE gc.loc_type IN (1,2,3,4) UNION ALL SELECT gc.value, (case coalesce(vpt.dead,'') when '' then '0' else (coalesce(vpt.dead,'0')) end) as dead, gc.parent FROM geo_cluster gc LEFT JOIN vw_pathology vpt ON vpt.xunion::int = gc.value WHERE gc.loc_type IN (1,2,3,4)) SELECT value, sum(dead::int) AS dead, parent FROM p GROUP BY value, parent) SELECT value, dead, parent FROM t UNION ALL SELECT t.value, children.dead, t.parent FROM children JOIN t ON children.parent = t.value) SELECT value, sum(dead) AS total_dead FROM children GROUP BY value ORDER BY value) SELECT value AS geoid, total_dead FROM q WHERE total_dead != 0 and value = " + str(each)
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        if df.empty:
            continue
        percentage.append(df.total_dead.tolist()[0])
    return render(request, 'fao_module/affected_area_mortality.html',
                  {'id': id, 'json_content': json_content, 'percentage': percentage})

@login_required
def json_data_fetch_mortaility(request):
    location_type = request.POST.get('loc_type')
    id = request.POST.get('id')
    children_list = []
    percentage = []
    content = []
    if location_type == '2':
        query = "with t as( SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'Patients Registry'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'Postmortem'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'pathology'::text)) select vwunion.division,vwunion.district_id, sum(dead::int) total_dead FROM vwunion left outer join t on t.union_id::int = vwunion.union_id where division_id = "+str(id)+" and vwunion.district_id = any (select geoid from organization_catchment_area_geojson) group by vwunion.division,vwunion.district_id having sum(dead::int) is not null"
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        children_list = df.district_id.tolist()
        percentage = df.total_dead.tolist()
        # print df
    elif location_type == '3':
        query = "with t as( SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'Patients Registry'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'Postmortem'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'pathology'::text)) select vwunion.upazilla,vwunion.upazilla_id, sum(dead::int) total_dead FROM vwunion left outer join t on t.union_id::int = vwunion.union_id where district_id = "+str(id)+" and vwunion.upazilla_id = any (select geoid from organization_catchment_area_geojson) group by vwunion.upazilla,vwunion.upazilla_id having sum(dead::int) is not null"
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        children_list = df.upazilla_id.tolist()
        percentage = df.total_dead.tolist()
    elif location_type == '4':
        query = "with t as( SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'Patients Registry'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'Postmortem'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'dead' dead FROM forms_data WHERE (form_name = 'pathology'::text)) select vwunion.union_name,vwunion.union_id, sum(dead::int) total_dead FROM vwunion left outer join t on t.union_id::int = vwunion.union_id where upazilla_id = "+str(id)+" and vwunion.union_id = any (select geoid from organization_catchment_area_geojson) group by vwunion.union_name,vwunion.union_id having sum(dead::int) is not null"     
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        children_list = df.union_id.tolist()
        percentage = df.total_dead.tolist()
    for each in children_list:
        query = "select geojson_file_path from organization_catchment_area_geojson where geoid = " + str(each)
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        if df.empty:
            continue
        path = df.geojson_file_path.tolist()[0]
        file = open(path, 'r')
        file_content = file.read()
        file.close()
        content.append(file_content)
    return HttpResponse(json.dumps({'content': content, 'percentage': percentage}))


@login_required
def affected_area_affect(request):
    content = []
    khulna_file = open("onadata/media/all_geojson/Khulna_div.geojson", 'r')
    khulna_content = khulna_file.read()
    khulna_file.close()
    chittagong_file = open("onadata/media/all_geojson/Chittagong_div.geojson", 'r')
    chittagong_content = chittagong_file.read()
    khulna_file.close()
    content.append(khulna_content)
    content.append(chittagong_content)
    json_content = json.dumps({'content': content})
    percentage = []
    query = "select * from geo_cluster where loc_type = 1"
    df = pandas.read_sql(query, connection)
    division = df.value.tolist()
    for each in division:
        query = "with q as(WITH RECURSIVE children AS( with t as (with p as(select gc.value,vpr.sick,gc.parent from geo_cluster gc left join vw_patient_registry vpr on vpr.xunion::int = gc.value where gc.loc_type in (1,2,3,4) union all select gc.value,vps.sick,gc.parent from geo_cluster gc left join vw_postmortem vps on vps.xunion::int = gc.value where gc.loc_type in (1,2,3,4) union all select gc.value,vpt.sick,gc.parent from geo_cluster gc left join vw_pathology vpt on vpt.xunion::int = gc.value where gc.loc_type in (1,2,3,4)) select value,sum(sick::int) as sick,parent from p group by value,parent) SELECT value, sick, parent FROM t UNION ALL SELECT t.value, children.sick, t.parent FROM children JOIN t ON children.parent = t.value) SELECT value, sum(sick) as total_sick FROM children GROUP BY value ORDER BY value) select value as geoid,total_sick from q where total_sick is not null and value = " + str(each)
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        if df.empty:
            continue
        percentage.append(df.total_sick.tolist()[0])
        if each == 20:
            content.append(chittagong_content)
        if each == 40:
            content.append(khulna_content)
    json_content = json.dumps({'content': content})    
    return render(request, 'fao_module/affected_area_affect.html',
                  {'id': id, 'json_content': json_content, 'percentage': percentage})


@login_required
def json_data_fetch_affect(request):
    location_type = request.POST.get('loc_type')
    id = request.POST.get('id')
    children_list = []
    percentage = []
    content = []
    if location_type == '2':
        query = "with t as( SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'Patients Registry'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'Postmortem'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'pathology'::text)) select vwunion.division,vwunion.district_id, sum(sick::int) total_sick FROM vwunion left outer join t on t.union_id::int = vwunion.union_id where division_id = "+str(id)+" and vwunion.district_id = any (select geoid from organization_catchment_area_geojson) group by vwunion.division,vwunion.district_id having sum(sick::int) is not null"
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        children_list = df.district_id.tolist()
        percentage = df.total_sick.tolist()
        # print df
    elif location_type == '3':
        query = "with t as( SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'Patients Registry'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'Postmortem'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'pathology'::text)) select vwunion.upazilla,vwunion.upazilla_id, sum(sick::int) total_sick FROM vwunion left outer join t on t.union_id::int = vwunion.union_id where district_id = "+str(id)+" and vwunion.upazilla_id = any (select geoid from organization_catchment_area_geojson) group by vwunion.upazilla,vwunion.upazilla_id having sum(sick::int) is not null"
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        children_list = df.upazilla_id.tolist()
        percentage = df.total_sick.tolist()
    elif location_type == '4':
        query = "with t as( SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'Patients Registry'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'Postmortem'::text) union all SELECT datajson->>'xunion' union_id,datajson ->> 'sick' sick FROM forms_data WHERE (form_name = 'pathology'::text)) select vwunion.union_name,vwunion.union_id, sum(sick::int) total_sick FROM vwunion left outer join t on t.union_id::int = vwunion.union_id where upazilla_id = "+str(id)+" and vwunion.union_id = any (select geoid from organization_catchment_area_geojson) group by vwunion.union_name,vwunion.union_id having sum(sick::int) is not null"     
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        children_list = df.union_id.tolist()
        percentage = df.total_sick.tolist()
    for each in children_list:
        query = "select geojson_file_path from organization_catchment_area_geojson where geoid = " + str(each)
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        if df.empty:
            continue
        path = df.geojson_file_path.tolist()[0]
        file = open(path, 'r')
        file_content = file.read()
        file.close()
        content.append(file_content)
    return HttpResponse(json.dumps({'content': content, 'percentage': percentage}))



@login_required
def livebird_markets_list(request):
    query = "select id,market_id, market_name, ward_number, city_corp, assigned_officer from livebird_markets"
    result = __db_fetch_values_dict(query)
    livebird_markets_list = []
    for each in result:
        livebird_markets_list.append(handle_nan(json.loads(json.dumps(each))))
    return render(request, 'fao_module/livebird_markets_list.html', {
        'livebird_markets_list': json.dumps(livebird_markets_list)
    })


@login_required
def add_livebird_markets_list_file_form(request):
    return render(request, 'fao_module/add_livebird_markets_list_file_form.html')

@login_required
def insert_livebird_markets_list_file_form(request):
    if request.POST:
        myfile = request.FILES['livebird_markets_list_file_name']
        url = "onadata/media/uploaded_files/"
        fs = FileSystemStorage(location=url)
        myfile.name = str(datetime.datetime.now()) + "_" + str(myfile.name)
        filename = fs.save(myfile.name, myfile)
        full_file_path = "onadata/media/uploaded_files/" + myfile.name
        df = pandas.DataFrame()
        xlsx = pandas.ExcelFile(full_file_path)
        df = xlsx.parse(0)
        for each in df.index:
            if str(df.loc[each]['LBM_ID']) != "nan" and str(df.loc[each]['Ward No']) != "nan" and str(df.loc[each]['Mkt Name']) != "nan" and str(df.loc[each]['Assigned Oficer']) != "nan" and str(df.loc[each]['Name of City Corporation']) != "nan":
                try:
                    insert_query = "INSERT INTO public.livebird_markets (market_id, market_name, ward_number, city_corp, assigned_officer)VALUES('" + str(
                        df.loc[each]['LBM_ID']) + "', '" + str(
                        df.loc[each]['Mkt Name']).replace("'", "''") + "', " + str(
                        df.loc[each]['Ward No']) + ", '" + str(
                        df.loc[each]['Name of City Corporation']).replace("'", "''") + "', '" + str(
                        df.loc[each]['Assigned Oficer']).replace("'", "''") + "')"
                    __db_commit_query(insert_query)
                except:
                    continue
        messages.success(request,'<i class="fa fa-check-circle"></i> Live Bird Markets List File has been uploaded successfully!',
                         extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/livebird_markets_list/")


@login_required
def insert_livebird_markets_list_form(request):
    if request.POST:
        insert_query = "INSERT INTO public.livebird_markets (market_id, market_name, ward_number, city_corp, assigned_officer)VALUES('" + str(
            request.POST.get('market_id')) + "', '" + str(
            request.POST.get('market_name')).replace("'", "''") + "', " + str(
            request.POST.get('ward_number')) + ", '" + str(
            request.POST.get('city_corp')).replace("'", "''") + "', '" + str(
            request.POST.get('assigned_officer')).replace("'", "''") + "')"
        __db_commit_query(insert_query)
        messages.success(request, '<i class="fa fa-check-circle"></i> New Live Bird Markets Info has been added successfully!',
                         extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/livebird_markets_list/")


@login_required
def edit_livebird_markets_list_form(request, livebird_markets_id):
    query = "select id,market_id, market_name, ward_number, city_corp, assigned_officer from livebird_markets where  id = " + str(livebird_markets_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    market_id = set_nan_to_space(df.market_id.tolist()[0])
    market_name = set_nan_to_space(df.market_name.tolist()[0])
    ward_number = set_nan_to_space(df.ward_number.tolist()[0])
    city_corp = set_nan_to_space(df.city_corp.tolist()[0])
    assigned_officer = set_nan_to_space(df.assigned_officer.tolist()[0])
    return render(request, 'fao_module/edit_livebird_markets_list_form.html',
                  {'livebird_markets_id': livebird_markets_id, 'market_id': market_id,
                   'market_name': market_name,
                   'ward_number': ward_number,
                   'city_corp': city_corp,
                   'assigned_officer': assigned_officer})


@login_required
def update_livebird_markets_form(request):
    if request.POST:
        update_query = "UPDATE public.livebird_markets SET market_id='" + str( request.POST.get('market_id')) + "', market_name='" + str( request.POST.get('market_name')).replace("'", "''") + "', ward_number= " + str( request.POST.get('ward_number')) + ", city_corp='" + str( request.POST.get('city_corp')).replace("'", "''") + "', assigned_officer='" + str( request.POST.get('assigned_officer')).replace("'", "''") + "',updated_at = now() where id=" + str(request.POST.get('livebird_markets_id'))
        __db_commit_query(update_query)
        messages.success(request, '<i class="fa fa-check-circle"></i> Live Bird Markets Info has been updated successfully!',
                         extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/livebird_markets_list/")


@login_required
def delete_livebird_markets_list_form(request, livebird_markets_id):
    delete_query = "delete from livebird_markets where id = " + str(livebird_markets_id)
    __db_commit_query(delete_query)
    messages.success(request, '<i class="fa fa-check-circle"></i> Live Bird Markets Info has been deleted successfully!',
                     extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/fao_module/livebird_markets_list/")


def export_all(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    # fetching all organization recursively of current_user
    all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
    org_id_list = [org.pk for org in all_organizations]
    org_type_query = "select * from usermodule_organizations where id = " + str(current_user.organisation_name_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(org_type_query, connection)
    if df.organization_type.tolist()[0] is not None and int(df.organization_type.tolist()[0]) == 1:
        query = "SELECT farm_id, CASE report_type WHEN '1' THEN 'First Assessment Report' WHEN '2' THEN 'Follow-up Report' END  AS report_type, date_initial_visit, (SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila)  AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion)  AS xunion, mouza, village, address, owner_name, mobile_owner, CASE farm_ownership_type WHEN '4' THEN 'Rental' WHEN '3' THEN 'Personal contract' WHEN '2' THEN 'Independent' WHEN '1' THEN 'Corporate contract' END  AS farm_ownership_type, CASE type_person_interviewed WHEN '1' THEN 'Owner' WHEN '2' THEN 'Farm manager' WHEN '3' THEN 'Farm worker' WHEN '4' THEN 'Dealer' END  AS type_person_interviewed, gps_lattitude, gps_longitude, Replace(type_species, '@@', ',')  AS type_species, Replace(type_chicken, '@@', ',')  AS type_chicken, standing_population_birds, maximum_farm_capacity_birds, CASE birds_production_purpose WHEN '1' THEN 'Egg' WHEN '2' THEN 'Meat' WHEN '3' THEN 'Egg & Meat' WHEN '4' THEN 'Breeder' WHEN '5' THEN 'Sport' WHEN '6' THEN 'Pet' END  AS birds_production_purpose, CASE age_arrival_farm WHEN '1' THEN 'DOC' WHEN '2' THEN 'Pullet' WHEN '3' THEN 'Adult' END  AS age_arrival_farm, CASE previously_avian_influenza_investigate WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS previously_avian_influenza_investigate, date_previously_avian_influenza_investigate, vaccine1_ai_vaccination_used, CASE schedule_vaccine1 WHEN '1' THEN 'Age basis:' WHEN '2' THEN 'Calendar basis' WHEN '3' THEN 'After outbreak' WHEN '4' THEN 'No schedule (farmer doesn''t know)' END  AS schedule_vaccine1, Replace(schedule_vaccine1_before_production, '@@', ',') AS schedule_vaccine1_before_production, Replace(schedule_vaccine1_after_production, '@@', ',') AS schedule_vaccine1_after_production, date1_last3_ai_vaccination1, date2_last3_ai_vaccination1, date3_last3_ai_vaccination1, vaccine2_ai_vaccination_used, CASE schedule_vaccine2 WHEN '1' THEN 'Age basis:' WHEN '2' THEN 'Calendar basis' WHEN '3' THEN 'After outbreak' WHEN '4' THEN 'No schedule (farmer doesn''t know)' END  AS schedule_vaccine2, Replace(schedule_vaccine2_before_production, '@@', ',') AS schedule_vaccine2_before_production, Replace(schedule_vaccine2_after_production, '@@', ',') AS schedule_vaccine2_after_production, date1_last3_ai_vaccination2, date2_last3_ai_vaccination2, date3_last3_ai_vaccination2, CASE vaccination_given_by WHEN '1' THEN 'Outside vaccinator' WHEN '2' THEN 'Farm Staff' WHEN '3' THEN 'Both' END  AS vaccination_given_by, CASE vaccine_means_verification WHEN '1' THEN 'Vaccination record' WHEN '2' THEN 'Semi-structure interview' END  AS vaccine_means_verification, CASE outside_worker_do_not_enter_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS outside_worker_do_not_enter_farm, CASE only_workers_approved_visitor_enter_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS only_workers_approved_visitor_enter_farm, CASE no_manure_collector_enter_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS no_manure_collector_enter_farm, CASE fenced_duck_chicken_proof WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS fenced_duck_chicken_proof, CASE dead_birds_disposed_safely WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS dead_birds_disposed_safely, CASE sign_posted WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS sign_posted, CASE no_vehical_in_out_production_area WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS no_vehical_in_out_production_area, CASE only_workers_enter_production_area WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS only_workers_enter_production_area, CASE visitors_enter_production_if_approve_manager WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS visitors_enter_production_if_approve_manager, CASE access_control_loading_production_sign_posted WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS access_control_loading_production_sign_posted, CASE footwear_left_outside WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS footwear_left_outside, CASE change_clothes_entering_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS change_clothes_entering_farm, CASE uses_dedicated_footwear WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS uses_dedicated_footwear, CASE shower_entering_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS shower_entering_farm, CASE returning_materials_cleaned WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS returning_materials_cleaned, CASE returning_materials_disinfect WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END  AS returning_materials_disinfect, CASE dead_bird_management_practice WHEN '1' THEN 'buried' WHEN '2' THEN 'river' WHEN '3' THEN 'rubbish pit' WHEN '4' THEN 'pond' WHEN '5' THEN 'open place/bush' WHEN '6' THEN 'rubbish container' WHEN '7' THEN 'food/feed' END  AS dead_bird_management_practice, Replace(farm_entrance_means_verification, '@@', ',') AS farm_entrance_means_verification, antibacterial_usages_product1, CASE antibacterial_usage_salesman_product1 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Govt' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END  AS antibacterial_usage_salesman_product1, CASE antibacterial_usage_prevention_product1 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END  AS antibacterial_usage_prevention_product1, CASE antibacterial_usage_drinking_water_product1 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END  AS antibacterial_usage_drinking_water_product1, CASE antibacterial_frequency_product1 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' END  AS antibacterial_frequency_product1, antibacterial_usages_product2, CASE antibacterial_usage_salesman_product2 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Govt' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END  AS antibacterial_usage_salesman_product2, CASE antibacterial_usage_prevention_product2 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END  AS antibacterial_usage_prevention_product2, CASE antibacterial_usage_drinking_water_product2 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END  AS antibacterial_usage_drinking_water_product2, CASE antibacterial_frequency_product2 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' END  AS antibacterial_frequency_product2, antibacterial_usages_product3, CASE antibacterial_usage_salesman_product3 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Govt' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END  AS antibacterial_usage_salesman_product3, CASE antibacterial_usage_prevention_product3 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END antibacterial_usage_prevention_product3, CASE antibacterial_usage_drinking_water_product3 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END  AS antibacterial_usage_drinking_water_product3, CASE antibacterial_frequency_product3 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' END  AS antibacterial_frequency_product3, antibacterial_usages_product4, CASE antibacterial_usage_salesman_product4 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Govt' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END  AS antibacterial_usage_salesman_product4, CASE antibacterial_usage_prevention_product4 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END  AS antibacterial_usage_prevention_product4, CASE antibacterial_usage_drinking_water_product4 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END  AS antibacterial_usage_drinking_water_product4, CASE antibacterial_frequency_product4 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' END  AS antibacterial_frequency_product4, antibacterial_usages_product5, CASE antibacterial_usage_salesman_product5 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Govt' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END  AS antibacterial_usage_salesman_product5, CASE antibacterial_usage_prevention_product5 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END  AS antibacterial_usage_prevention_product5, CASE antibacterial_usage_drinking_water_product5 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END  AS antibacterial_usage_drinking_water_product5, CASE antibacterial_frequency_product5 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' END  AS antibacterial_frequency_product5, farmer_concern, image, field_staff1, field_staff2, ackknowlwdge_by, approved_by FROM vw_farm_assessment"
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
        df.to_excel(writer, sheet_name='Farm Assessment', index=False)
        query = "SELECT investigation_id, farm_id, date_completed,(SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, mouza, village, farmer_name, title_position, mobile_contact_person, case sex WHEN '1' THEN 'Male' WHEN '2' THEN 'Female' END AS sex, gps_lattitude, gps_longitude, case were_called_investigate_birds WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_called_investigate_birds, case meeting_raise_community_avian_influenza WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS meeting_raise_community_avian_influenza, case search_sick_dead_birds WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS meeting_raise_community_avian_influenza, case were_sick_dead_birds_found WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_sick_dead_birds_found, date_received_sick_dead_info, date_estimated_onset, case cases_occur_type_production_system WHEN '1' THEN 'Farm ' WHEN '2' THEN 'Backyard' WHEN '3' THEN 'Wild Bird' END AS cases_occur_type_production_system, case has_farm_previously_assessed WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS has_farm_previously_assessed, date_previously_assessed, Replace(clinical_sign_observed, '@@', ',') AS clinical_sign_observed, deshi_chicken, deshi_chicken_dead, deshi_chicken_sick, deshi_chicken_population, sonali_chicken_dead, sonali_chicken_sick, sonali_chicken_total_population, brown_comm_chicken, brown_comm_chicken_dead, brown_comm_chicken_sick, brown_comm_chicken_population, white_comm_chicken, white_comm_chicken_dead, white_comm_chicken_sick, white_comm_chicken_population, ducks, duck_dead, duck_sick, duck_population, others_affected_species, other_affected_dead, other_affected_sick, other_affected_population, case birds_production_purpose WHEN '1' THEN 'Egg' WHEN '2' THEN 'Meat' WHEN '3' THEN 'Egg & Meat' WHEN '4' THEN 'Breeder' WHEN '5' THEN 'Sport' WHEN '6' THEN 'Pet' END as birds_production_purpose, sick_dead_tested_by_rapid_test, case used_rapid_test_name WHEN '1' THEN 'Bionote Anigen AIV test' ELSE other_used_rapid_test_name END AS used_rapid_test_name, case rapid_test_result WHEN '1' THEN 'Positive' WHEN '2' THEN 'Negative' WHEN '3' THEN 'Not performed' END AS rapid_test_result, case vtm_sample_collected WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS vtm_sample_collected, date_vtm_sample_collected, case pcr_result WHEN '1' THEN 'Positive' WHEN '2' THEN 'Negative' WHEN '3' THEN 'Test not performed' WHEN '4' THEN 'No lab report received ' END AS pcr_result, case why_not_vtm WHEN '1' THEN ' No VTM' WHEN '2' THEN 'Not necessary' END AS why_not_vtm, case type_culling_performed WHEN '1' THEN 'Focal culling ( culling of all birds in affected flock)' WHEN '2' THEN 'No culling performed' END AS type_culling_performed, number_birds_culled, why_not_culled, case type_compensation_provided WHEN '1' THEN 'Vaccination' WHEN '2' THEN 'Young bird restocking' WHEN '3' THEN 'No compensation' END AS type_compensation_provided, additional_investigation_information, investigator_name1, investigator_designation1, investogator_contact_number1, investigator_name2, investigator_designation2, investigator_contact_number2, admin_name1, admin_working_date11,admin_working_date12,admin_working_date13, admin_overnight_date11,admin_overnight_date12,admin_overnight_date13,admin_name2, admin_working_date21,admin_working_date22,admin_working_date23, admin_overnight_date21,admin_overnight_date22,admin_overnight_date23 acknowledge_by, approved_by, username, created_at FROM PUBLIC.vw_avian_influenza_investigation"
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        df.to_excel(writer, sheet_name='Avian Influenza Investigation', index=False)
        query = "SELECT investigation_id, date_sample_collected, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = division) AS division, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = district) AS district, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = upazila)  AS upazila, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = xunion)   AS xunion, mouza, village, contact_person_name, contact_person_mobile, laboratory_name_sample_sent_to, sample_collected_by_name FROM  vw_ai_sample_submission"
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        df.to_excel(writer, sheet_name='AI Sample Submission', index=False)
        writer.save()
        f = open('onadata/media/uploaded_files/output.xlsx', 'r')
        response = HttpResponse(f, mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=Hierarchical Forms Data.xls'
        return response
    elif df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 2:
        df = pandas.DataFrame()
        for each in org_id_list:
            query = "SELECT farm_id, CASE report_type WHEN '1' THEN 'First Assessment Report' WHEN '2' THEN 'Follow-up Report' END AS report_type, date_initial_visit,(SELECT name FROM geo_cluster WHERE value :: text = division) AS division, (SELECT name FROM geo_cluster WHERE value :: text = district) AS district, (SELECT name FROM geo_cluster WHERE value :: text = upazila) AS upazila, (SELECT name FROM geo_cluster WHERE value :: text = xunion) AS xunion, mouza, village, address, owner_name, mobile_owner, CASE farm_ownership_type WHEN '4' THEN 'Rental' WHEN '3' THEN 'Personal contract' WHEN '2' THEN 'Independent' WHEN '1' THEN 'Corporate contract' END AS farm_ownership_type, CASE type_person_interviewed WHEN '1' THEN 'Owner' WHEN '2' THEN 'Farm manager' WHEN '3' THEN 'Farm worker' WHEN '4' THEN 'Dealer' END AS type_person_interviewed, gps_lattitude, gps_longitude, Replace(type_species, '@@', ',') AS type_species, Replace(type_chicken, '@@', ',') AS type_chicken, standing_population_birds, maximum_farm_capacity_birds, CASE birds_production_purpose WHEN '1' THEN 'Egg' WHEN '2' THEN 'Meat' WHEN '3' THEN 'Egg & Meat' WHEN '4' THEN 'Breeder' WHEN '5' THEN 'Sport' WHEN '6' THEN 'Pet' END AS birds_production_purpose, CASE age_arrival_farm WHEN '1' THEN 'DOC' WHEN '2' THEN 'Pullet' WHEN '3' THEN 'Adult' END AS age_arrival_farm, CASE previously_avian_influenza_investigate WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS previously_avian_influenza_investigate, date_previously_avian_influenza_investigate, vaccine1_ai_vaccination_used, CASE schedule_vaccine1 WHEN '1' THEN 'Age basis:' WHEN '2' THEN 'Calendar basis' WHEN '3' THEN 'After outbreak' WHEN '4' THEN 'No schedule (farmer doesn''t know)' END AS schedule_vaccine1, Replace(schedule_vaccine1_before_production, '@@', ',') AS schedule_vaccine1_before_production, Replace(schedule_vaccine1_after_production, '@@', ',') AS schedule_vaccine1_after_production, date1_last3_ai_vaccination1, date2_last3_ai_vaccination1, date3_last3_ai_vaccination1, vaccine2_ai_vaccination_used, CASE schedule_vaccine2 WHEN '1' THEN 'Age basis:' WHEN '2' THEN 'Calendar basis' WHEN '3' THEN 'After outbreak' WHEN '4' THEN 'No schedule (farmer doesn''t know)' END AS schedule_vaccine2, Replace(schedule_vaccine2_before_production, '@@', ',') AS schedule_vaccine2_before_production, Replace(schedule_vaccine2_after_production, '@@', ',') AS schedule_vaccine2_after_production, date1_last3_ai_vaccination2, date2_last3_ai_vaccination2, date3_last3_ai_vaccination2, CASE vaccination_given_by WHEN '1' THEN 'Outside vaccinator' WHEN '2' THEN 'Farm Staff' WHEN '3' THEN 'Both' END AS vaccination_given_by, Replace(vaccine_means_verification, '@@', ',') AS vaccine_means_verification, CASE outside_worker_do_not_enter_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS outside_worker_do_not_enter_farm, CASE only_workers_approved_visitor_enter_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS only_workers_approved_visitor_enter_farm, CASE no_manure_collector_enter_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS no_manure_collector_enter_farm, CASE fenced_duck_chicken_proof WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS fenced_duck_chicken_proof, CASE dead_birds_disposed_safely WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS dead_birds_disposed_safely, CASE sign_posted WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS sign_posted, CASE no_vehical_in_out_production_area WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS no_vehical_in_out_production_area, CASE only_workers_enter_production_area WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS only_workers_enter_production_area, CASE visitors_enter_production_if_approve_manager WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS visitors_enter_production_if_approve_manager, CASE access_control_loading_production_sign_posted WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS access_control_loading_production_sign_posted, CASE footwear_left_outside WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS footwear_left_outside, CASE change_clothes_entering_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS change_clothes_entering_farm, CASE uses_dedicated_footwear WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS uses_dedicated_footwear, CASE shower_entering_farm WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS shower_entering_farm, CASE returning_materials_cleaned WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS returning_materials_cleaned, CASE returning_materials_disinfect WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS returning_materials_disinfect, CASE dead_bird_management_practice WHEN '1' THEN 'buried' WHEN '2' THEN 'river' WHEN '3' THEN 'rubbish pit' WHEN '4' THEN 'pond' WHEN '5' THEN 'open place/bush' WHEN '6' THEN 'rubbish container' WHEN '7' THEN 'food/feed' END AS dead_bird_management_practice, Replace(farm_entrance_means_verification, '@@', ',') AS farm_entrance_means_verification, antibacterial_usages_product1, CASE antibacterial_usage_salesman_product1 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Upazila Vet Hosp' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END AS antibacterial_usage_salesman_product1, CASE antibacterial_usage_prevention_product1 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END AS antibacterial_usage_prevention_product1, CASE antibacterial_usage_drinking_water_product1 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END AS antibacterial_usage_drinking_water_product1, CASE antibacterial_frequency_product1 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' WHEN '7' THEN '3 Times a Day' END AS antibacterial_frequency_product1, antibacterial_usages_product2, CASE antibacterial_usage_salesman_product2 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Upazila Vet Hosp' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END AS antibacterial_usage_salesman_product2, CASE antibacterial_usage_prevention_product2 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END AS antibacterial_usage_prevention_product2, CASE antibacterial_usage_drinking_water_product2 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END AS antibacterial_usage_drinking_water_product2, CASE antibacterial_frequency_product2 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' WHEN '7' THEN '3 Times a Day' END AS antibacterial_frequency_product2, antibacterial_usages_product3, CASE antibacterial_usage_salesman_product3 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Upazila Vet Hosp' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END AS antibacterial_usage_salesman_product3, CASE antibacterial_usage_prevention_product3 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END antibacterial_usage_prevention_product3, CASE antibacterial_usage_drinking_water_product3 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END AS antibacterial_usage_drinking_water_product3, CASE antibacterial_frequency_product3 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' WHEN '7' THEN '3 Times a Day' END AS antibacterial_frequency_product3, antibacterial_usages_product4, CASE antibacterial_usage_salesman_product4 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Upazila Vet Hosp' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END AS antibacterial_usage_salesman_product4, CASE antibacterial_usage_prevention_product4 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END AS antibacterial_usage_prevention_product4, CASE antibacterial_usage_drinking_water_product4 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END AS antibacterial_usage_drinking_water_product4, CASE antibacterial_frequency_product4 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' WHEN '7' THEN '3 Times a Day' END AS antibacterial_frequency_product4, antibacterial_usages_product5, CASE antibacterial_usage_salesman_product5 WHEN '1' THEN 'Salesman' WHEN '2' THEN 'Upazila Vet Hosp' WHEN '3' THEN 'Market' WHEN '4' THEN 'Dealer' WHEN '5' THEN 'Vet' WHEN '6' THEN 'Quack' END AS antibacterial_usage_salesman_product5, CASE antibacterial_usage_prevention_product5 WHEN '1' THEN 'Infection/sick' WHEN '2' THEN 'Prevention' WHEN '3' THEN 'Faster growth/more eggs' END AS antibacterial_usage_prevention_product5, CASE antibacterial_usage_drinking_water_product5 WHEN '1' THEN 'Drinking water' WHEN '2' THEN 'Feed' WHEN '3' THEN 'Injection' END AS antibacterial_usage_drinking_water_product5, CASE antibacterial_frequency_product5 WHEN '1' THEN 'Twice a day' WHEN '2' THEN 'Once a day' WHEN '3' THEN 'Once a week' WHEN '4' THEN 'Once a month' WHEN '5' THEN 'After illness' WHEN '6' THEN 'Before winter' WHEN '7' THEN '3 Times a Day' END AS antibacterial_frequency_product5, farmer_concern, image, field_staff1, field_staff2, ackknowlwdge_by, approved_by FROM vw_farm_assessment where working_upazila_id = " + str(
                each)
            temp_df = pandas.DataFrame()
            temp_df = pandas.read_sql(query, connection)
            if not temp_df.empty:
                df = df.append(temp_df, ignore_index=True)
        writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
        df.to_excel(writer, sheet_name='Farm Assessment', index=False)
        df = pandas.DataFrame()
        for each in org_id_list:
            query = "SELECT investigation_id, farm_id, date_completed,(SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, mouza, village, farmer_name, title_position, mobile_contact_person, case sex WHEN '1' THEN 'Male' WHEN '2' THEN 'Female' END AS sex, gps_lattitude, gps_longitude, case were_called_investigate_birds WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_called_investigate_birds, case meeting_raise_community_avian_influenza WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS meeting_raise_community_avian_influenza, case search_sick_dead_birds WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS meeting_raise_community_avian_influenza, case were_sick_dead_birds_found WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS were_sick_dead_birds_found, date_received_sick_dead_info, date_estimated_onset, case cases_occur_type_production_system WHEN '1' THEN 'Farm ' WHEN '2' THEN 'Backyard' WHEN '3' THEN 'Wild Bird' END AS cases_occur_type_production_system, case has_farm_previously_assessed WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS has_farm_previously_assessed, date_previously_assessed, Replace(clinical_sign_observed, '@@', ',') AS clinical_sign_observed, deshi_chicken, deshi_chicken_dead, deshi_chicken_sick, deshi_chicken_population, sonali_chicken_dead, sonali_chicken_sick, sonali_chicken_total_population, brown_comm_chicken, brown_comm_chicken_dead, brown_comm_chicken_sick, brown_comm_chicken_population, white_comm_chicken, white_comm_chicken_dead, white_comm_chicken_sick, white_comm_chicken_population, ducks, duck_dead, duck_sick, duck_population, others_affected_species, other_affected_dead, other_affected_sick, other_affected_population, case birds_production_purpose WHEN '1' THEN 'Egg' WHEN '2' THEN 'Meat' WHEN '3' THEN 'Egg & Meat' WHEN '4' THEN 'Breeder' WHEN '5' THEN 'Sport' WHEN '6' THEN 'Pet' END as birds_production_purpose, sick_dead_tested_by_rapid_test, case used_rapid_test_name WHEN '1' THEN 'Bionote Anigen AIV test' ELSE other_used_rapid_test_name END AS used_rapid_test_name, case rapid_test_result WHEN '1' THEN 'Positive' WHEN '2' THEN 'Negative' WHEN '3' THEN 'Not performed' END AS rapid_test_result, case vtm_sample_collected WHEN '1' THEN 'Yes' WHEN '2' THEN 'No' END AS vtm_sample_collected, date_vtm_sample_collected, case pcr_result WHEN '1' THEN 'Positive' WHEN '2' THEN 'Negative' WHEN '3' THEN 'Test not performed' WHEN '4' THEN 'No lab report received ' END AS pcr_result, case why_not_vtm WHEN '1' THEN ' No VTM' WHEN '2' THEN 'Not necessary' END AS why_not_vtm, case type_culling_performed WHEN '1' THEN 'Focal culling ( culling of all birds in affected flock)' WHEN '2' THEN 'No culling performed' END AS type_culling_performed, number_birds_culled, why_not_culled, case type_compensation_provided WHEN '1' THEN 'Vaccination' WHEN '2' THEN 'Young bird restocking' WHEN '3' THEN 'No compensation' END AS type_compensation_provided, additional_investigation_information, investigator_name1, investigator_designation1, investogator_contact_number1, investigator_name2, investigator_designation2, investigator_contact_number2, admin_name1, admin_working_date11,admin_working_date12,admin_working_date13, admin_overnight_date11,admin_overnight_date12,admin_overnight_date13, admin_name2, admin_working_date21,admin_working_date22,admin_working_date23, admin_overnight_date21,admin_overnight_date22,admin_overnight_date23, acknowledge_by, approved_by, username, created_at FROM PUBLIC.vw_avian_influenza_investigation where working_upazila_id = " + str(
                each)
            temp_df = pandas.DataFrame()
            temp_df = pandas.read_sql(query, connection)
            if not temp_df.empty:
                df = df.append(temp_df, ignore_index=True)
        writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
        df.to_excel(writer, sheet_name='Avian Influenza Investigation', index=False)
        df = pandas.DataFrame()
        for each in org_id_list:
            query = "SELECT investigation_id, date_sample_collected, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = division) AS division, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = district) AS district, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = upazila)  AS upazila, (SELECT NAME  FROM   geo_cluster  WHERE  value::text = xunion)   AS xunion, mouza, village, contact_person_name, contact_person_mobile, laboratory_name_sample_sent_to, sample_collected_by_name FROM  vw_ai_sample_submission where working_upazila_id = " + str(
                each)
            temp_df = pandas.DataFrame()
            temp_df = pandas.read_sql(query, connection)
            if not temp_df.empty:
                df = df.append(temp_df, ignore_index=True)
        writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
        df.to_excel(writer, sheet_name='AI Sample Submission', index=False)
        writer.save()
        f = open('onadata/media/uploaded_files/output.xlsx', 'r')
        response = HttpResponse(f, mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename= Hierarchical Forms Data.xls'
        return response
    else:
        message = "You have no access to this page"
        return render(request, 'fao_module/error_404.html', {'message': message})


@login_required
def participatory_livestock_assessment_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    # fetching all organization recursively of current_user
    all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
    org_id_list = [org.pk for org in all_organizations]

    # this geo_data is the variable for storing all geo location for current_user
    all_geo_id = []
    col_name = []
    json_data = []

    org_type_query = "select * from usermodule_organizations where id = " + str(current_user.organisation_name_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(org_type_query, connection)

    # For CO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 1:
        select_query = "select pla_id, visit_date,(SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, village, focal_person, mobile from vw_participatory_assessment"
        data = __db_fetch_values_dict(select_query)
        for each1 in data:
                json_data.append(handle_none(each1))
                # each1 contains a json dictionary.
                # each1.items() create (key,value) pair
                for key, value in each1.items():
                    if key not in col_name and key != "data_id":
                        # unique column name insert in col_name list
                        col_name.append(key)
        all_geo_id.append(1)
        return render(request, 'fao_module/participatory_livestock_assessment_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})

    # For ULO/LO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 2:
        for each in org_id_list:
            query = "select geoid from organization_catchment_area where organization_id = " + str(each)
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
            if not df.empty:
                # check for duplicate geoid
                # every time a unique geoid is pushed in all_geo_id
                if df.geoid.tolist()[0] in all_geo_id:
                    continue
                # fetching data from forms_data
                select_query = "select pla_id, visit_date,(SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, village, focal_person, mobile from vw_participatory_assessment where working_upazila_id = " + str(
                    df.geoid.tolist()[0])
                data = __db_fetch_values_dict(select_query)
                for each1 in data:
                    json_data.append(handle_none(each1))
                    # each1 contains a json dictionary.
                    # each1.items() create (key,value) pair
                    for key, value in each1.items():
                        if key not in col_name and key != "data_id":
                            # unique column name insert in col_name list
                            col_name.append(key)
                all_geo_id.append(df.geoid.tolist()[0])
        return render(request, 'fao_module/participatory_livestock_assessment_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})
    message = "You have no access to this page"    
    return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def xls_report_creator_for_participatory_livestock_assessment(request):
    all_geo_id = request.POST.getlist('all_geo_id')
    if len(all_geo_id):
        if int(all_geo_id[0]) == 1:
            # for CO users
            query = "select data_id, pla_id, visit_date,(SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, mouza, village, focal_person, mobile, adult_female, adult_male, children, latitude, longitude, Replace(animal_reared, '@@', ',') AS animal_reared, animal_reared_other, rank1_species_number, rank1_species_percent, rank1_species_economic_importance, rank2_species_number, rank2_species_percent, rank2_species_economic_importance, rank3_species_number, rank3_species_percent, rank3_species_economic_importance, rank4_species_number, rank4_species_percent, rank4_species_economic_importance, rank5_species_number, rank5_species_percent, rank5_species_economic_importance, Replace(disscussion_species, '@@', ',') AS disscussion_species, disscussion_species_other, species_disease_rank1, species_disease_rank2, species_disease_rank3, species_disease_rank4, species_disease_rank5, rank_disease_type1, rank_disease_type2, rank_disease_type3, rank_disease_type4, rank_disease_type5, rank1_summer_disease_type_poultry, rank1_rainy_disease_type_poultry, rank1_winter_disease_type_poultry, rank2_summer_disease_type_poultry, rank2_rainy_disease_type_poultry, rank2_winter_disease_type_poultry, rank3_summer_disease_type_poultry, rank3_rainy_disease_type_poultry, rank3_winter_disease_type_poultry, rank4_summer_disease_type_poultry, rank4_rainy_disease_type_poultry, rank4_winter_disease_type_poultry, rank5_summer_disease_type_poultry, rank5_rainy_disease_type_poultry, rank5_winter_disease_type_poultry, Replace(do_when_bird_sick, '@@', ',') AS do_when_bird_sick, do_when_bird_sick_other, Replace(do_when_bird_dead, '@@', ',') AS do_when_bird_dead, do_when_bird_dead_other, unusual_surprising_info, problem1_identified, problem1_action_needed, problem1_action_taken, problem2_identified, problem2_action_needed, problem2_action_taken, problem3_identified, problem3_action_needed, problem3_action_taken,(select username from auth_user where id = t.name1::int) name1,(select username from auth_user where id = t.name2::int) name2,(select username from auth_user where id = t.acknowledge_name::int) acknowledge_name,(select username from auth_user where id = t.approved_name::int) approved_name,(select username from auth_user where id = t.username::int) username from vw_participatory_assessment t"
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
        else:
            # for ULO/LO users
            df = pandas.DataFrame()
            for each in all_geo_id:
                query = "select data_id, pla_id, visit_date,(SELECT NAME FROM geo_cluster WHERE value::text = division) AS division, (SELECT NAME FROM geo_cluster WHERE value::text = district) AS district, (SELECT NAME FROM geo_cluster WHERE value::text = upazila) AS upazila, (SELECT NAME FROM geo_cluster WHERE value::text = xunion) AS xunion, mouza, village, focal_person, mobile, adult_female, adult_male, children, latitude, longitude, Replace(animal_reared, '@@', ',') AS animal_reared, animal_reared_other, rank1_species_number, rank1_species_percent, rank1_species_economic_importance, rank2_species_number, rank2_species_percent, rank2_species_economic_importance, rank3_species_number, rank3_species_percent, rank3_species_economic_importance, rank4_species_number, rank4_species_percent, rank4_species_economic_importance, rank5_species_number, rank5_species_percent, rank5_species_economic_importance, Replace(disscussion_species, '@@', ',') AS disscussion_species, disscussion_species_other, species_disease_rank1, species_disease_rank2, species_disease_rank3, species_disease_rank4, species_disease_rank5, rank_disease_type1, rank_disease_type2, rank_disease_type3, rank_disease_type4, rank_disease_type5, rank1_summer_disease_type_poultry, rank1_rainy_disease_type_poultry, rank1_winter_disease_type_poultry, rank2_summer_disease_type_poultry, rank2_rainy_disease_type_poultry, rank2_winter_disease_type_poultry, rank3_summer_disease_type_poultry, rank3_rainy_disease_type_poultry, rank3_winter_disease_type_poultry, rank4_summer_disease_type_poultry, rank4_rainy_disease_type_poultry, rank4_winter_disease_type_poultry, rank5_summer_disease_type_poultry, rank5_rainy_disease_type_poultry, rank5_winter_disease_type_poultry, Replace(do_when_bird_sick, '@@', ',') AS do_when_bird_sick, do_when_bird_sick_other, Replace(do_when_bird_dead, '@@', ',') AS do_when_bird_dead, do_when_bird_dead_other, unusual_surprising_info, problem1_identified, problem1_action_needed, problem1_action_taken, problem2_identified, problem2_action_needed, problem2_action_taken, problem3_identified, problem3_action_needed, problem3_action_taken,(select username from auth_user where id = t.name1::int) name1,(select username from auth_user where id = t.name2::int) name2,(select username from auth_user where id = t.acknowledge_name::int) acknowledge_name,(select username from auth_user where id = t.approved_name::int) approved_name,(select username from auth_user where id = t.username::int) username from vw_participatory_assessment t where working_upazila_id = " + str(each)
                temp_df = pandas.DataFrame()
                temp_df = pandas.read_sql(query, connection)
                if not temp_df.empty:
                    df = df.append(temp_df, ignore_index=True)
        writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        writer.save()
        f = open('onadata/media/uploaded_files/output.xlsx', 'r')
        response = HttpResponse(f, mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=Participatory Livestock Assessment.xls'
        return response
    else:
        message = "You have no access to this page"    
        return render(request, 'fao_module/error_404.html',{'message':message})







@login_required
def submission_count_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    # fetching all organization recursively of current_user
    all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
    org_id_list = [org.pk for org in all_organizations]
    # this geo_data is the variable for storing all geo location for current_user
    all_geo_id = []
    col_name = []
    json_data = []

    org_type_query = "select * from usermodule_organizations where id = " + str(current_user.organisation_name_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(org_type_query, connection)

    # For CO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 1:
        select_query = "WITH t AS(SELECT DISTINCT form_name, (SELECT Count(*) FROM forms_data WHERE form_name = 'Patients Registry' AND Date_trunc('day', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM forms_data WHERE form_name = 'Patients Registry' AND Date_trunc('month', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM forms_data WHERE form_name = 'Patients Registry' AND Date_trunc('year', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'Patients Registry' AND Extract(year FROM To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM forms_data WHERE form_name = 'Patients Registry') as total FROM forms_data WHERE form_name = 'Patients Registry' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM forms_data WHERE form_name = 'pathology' AND Date_trunc('day', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM forms_data WHERE form_name = 'pathology' AND Date_trunc('month', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM forms_data WHERE form_name = 'pathology' AND Date_trunc('year', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'pathology' AND Extract(year FROM To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM forms_data WHERE form_name = 'pathology') as total FROM forms_data WHERE form_name = 'pathology' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM forms_data WHERE form_name = 'Postmortem' AND Date_trunc('day', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM forms_data WHERE form_name = 'Postmortem' AND Date_trunc('month', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM forms_data WHERE form_name = 'Postmortem' AND Date_trunc('year', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'Postmortem' AND Extract(year FROM To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM forms_data WHERE form_name = 'Postmortem') as total FROM forms_data WHERE form_name = 'Postmortem' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM forms_data WHERE form_name = 'Farm Assessment Monitoring' AND Date_trunc('day', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM forms_data WHERE form_name = 'Farm Assessment Monitoring' AND Date_trunc('month', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM forms_data WHERE form_name = 'Farm Assessment Monitoring' AND Date_trunc('year', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'Farm Assessment Monitoring' AND Extract(year FROM To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM forms_data WHERE form_name = 'Farm Assessment Monitoring') as total FROM forms_data WHERE form_name = 'Farm Assessment Monitoring' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM forms_data WHERE form_name = 'Participatory Livestock Assessment' AND Date_trunc('day', To_date( datajson ->> 'visit_date' , 'YYYY/MM/DD')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM forms_data WHERE form_name = 'Participatory Livestock Assessment' AND Date_trunc('month', To_date( datajson ->> 'visit_date', 'YYYY/MM/DD')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM forms_data WHERE form_name = 'Participatory Livestock Assessment' AND Date_trunc('year', To_date( datajson ->> 'visit_date' , 'YYYY/MM/DD')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'Participatory Livestock Assessment' AND Extract(year FROM To_date( datajson ->> 'visit_date' , 'YYYY/MM/DD')) = Extract( year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM forms_data WHERE form_name = 'Participatory Livestock Assessment') as total FROM forms_data WHERE form_name = 'Participatory Livestock Assessment' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Sample' AND Date_trunc('day', To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Sample' AND Date_trunc('month', To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Sample' AND Date_trunc('year', To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Sample' AND Extract(year FROM To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Sample') as total FROM forms_data WHERE form_name = 'Avian Influenza Sample' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM forms_data WHERE form_name = 'Generic Disease Investigation' AND Date_trunc('day', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM forms_data WHERE form_name = 'Generic Disease Investigation' AND Date_trunc('month', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM forms_data WHERE form_name = 'Generic Disease Investigation' AND Date_trunc('year', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'Generic Disease Investigation' AND Extract(year FROM To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM forms_data WHERE form_name = 'Generic Disease Investigation') as total FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Investigation' AND Date_trunc('day', To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Investigation' AND Date_trunc('month', To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Investigation' AND Date_trunc('year', To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Investigation' AND Extract(year FROM To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Investigation') as total FROM forms_data WHERE form_name = 'Avian Influenza Investigation') SELECT form_name, COALESCE(cday, 0) cday, COALESCE(cmonth, 0) cmonth, COALESCE(cyear, 0) cyear, COALESCE(last_yr, 0) last_yr, COALESCE(total, 0) total FROM t"
        data = __db_fetch_values_dict(select_query)
        for each1 in data:
                # print each1
                json_data.append(handle_none(each1))
                # each1 contains a json dictionary.
                # each1.items() create (key,value) pair
                for key, value in each1.items():
                    if key not in col_name and key != "data_id":
                        # unique column name insert in col_name list
                        col_name.append(key)
        all_geo_id.append(1)
        return render(request, 'fao_module/submission_count_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})

    # For ULO/LO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 2:
        for each in org_id_list:
            query = "select geoid from organization_catchment_area where organization_id = " + str(each)
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
            if not df.empty:
                # check for duplicate geoid
                # every time a unique geoid is pushed in all_geo_id
                if df.geoid.tolist()[0] in all_geo_id:
                    continue
                # fetching data from forms_data
                # select_query = "WITH m AS(WITH t AS (SELECT DISTINCT form_name, working_upazila_id, (SELECT Count(*) FROM forms_data WHERE form_name = 'Patients Registry' AND Date_trunc('day', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM forms_data WHERE form_name = 'Patients Registry' AND Date_trunc('month', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM forms_data WHERE form_name = 'Patients Registry' AND Date_trunc('year', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'Patients Registry' AND Extract(year FROM To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr , (SELECT Count(*) FROM forms_data WHERE form_name = 'Patients Registry') AS total FROM forms_data WHERE form_name = 'Patients Registry' UNION ALL SELECT DISTINCT form_name, working_upazila_id, (SELECT Count(*) FROM forms_data WHERE form_name = 'pathology' AND Date_trunc('day', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM forms_data WHERE form_name = 'pathology' AND Date_trunc('month', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM forms_data WHERE form_name = 'pathology' AND Date_trunc('year', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'pathology' AND Extract(year FROM To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM forms_data WHERE form_name = 'pathology') AS total FROM forms_data WHERE form_name = 'pathology' UNION ALL SELECT DISTINCT form_name, working_upazila_id, (SELECT Count(*) FROM forms_data WHERE form_name = 'Postmortem' AND Date_trunc('day', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM forms_data WHERE form_name = 'Postmortem' AND Date_trunc('month', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM forms_data WHERE form_name = 'Postmortem' AND Date_trunc('year', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'Postmortem' AND Extract(year FROM To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM forms_data WHERE form_name = 'Postmortem') AS total FROM forms_data WHERE form_name = 'Postmortem' UNION ALL SELECT DISTINCT form_name, working_upazila_id, (SELECT Count(*) FROM forms_data WHERE form_name = 'Farm Assessment Monitoring' AND Date_trunc('day', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM forms_data WHERE form_name = 'Farm Assessment Monitoring' AND Date_trunc('month', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM forms_data WHERE form_name = 'Farm Assessment Monitoring' AND Date_trunc('year', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'Farm Assessment Monitoring' AND Extract(year FROM To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr , (SELECT Count(*) FROM forms_data WHERE form_name = 'Farm Assessment Monitoring') AS total FROM forms_data WHERE form_name = 'Farm Assessment Monitoring' UNION ALL SELECT DISTINCT form_name, working_upazila_id, (SELECT Count(*) FROM forms_data WHERE form_name = 'Participatory Livestock Assessment' AND Date_trunc('day', To_date( datajson ->> 'visit_date' , 'YYYY/MM/DD')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM forms_data WHERE form_name = 'Participatory Livestock Assessment' AND Date_trunc('month', To_date( datajson ->> 'visit_date', 'YYYY/MM/DD')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM forms_data WHERE form_name = 'Participatory Livestock Assessment' AND Date_trunc('year', To_date( datajson ->> 'visit_date' , 'YYYY/MM/DD')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'Participatory Livestock Assessment' AND Extract(year FROM To_date( datajson ->> 'visit_date' , 'YYYY/MM/DD')) = Extract( year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM forms_data WHERE form_name = 'Participatory Livestock Assessment') AS total FROM forms_data WHERE form_name = 'Participatory Livestock Assessment' UNION ALL SELECT DISTINCT form_name, working_upazila_id, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Sample' AND Date_trunc('day', To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Sample' AND Date_trunc('month', To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE ) GROUP BY form_name) AS cmonth , (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Sample' AND Date_trunc('year', To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Sample' AND Extract(year FROM To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Sample') AS total FROM forms_data WHERE form_name = 'Avian Influenza Sample' UNION ALL SELECT DISTINCT form_name, working_upazila_id, (SELECT Count(*) FROM forms_data WHERE form_name = 'Generic Disease Investigation' AND Date_trunc('day', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday , (SELECT Count(*) FROM forms_data WHERE form_name = 'Generic Disease Investigation' AND Date_trunc('month', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM forms_data WHERE form_name = 'Generic Disease Investigation' AND Date_trunc('year', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'Generic Disease Investigation' AND Extract(year FROM To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr , (SELECT Count(*) FROM forms_data WHERE form_name = 'Generic Disease Investigation' ) AS total FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT DISTINCT form_name, working_upazila_id, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Investigation' AND Date_trunc('day', To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday , (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Investigation' AND Date_trunc('month', To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Investigation' AND Date_trunc('year', To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Investigation' AND Extract(year FROM To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr , (SELECT Count(*) FROM forms_data WHERE form_name = 'Avian Influenza Investigation' ) AS total FROM forms_data WHERE form_name = 'Avian Influenza Investigation') SELECT form_name, working_upazila_id, COALESCE(cday, 0) cday, COALESCE(cmonth, 0) cmonth, COALESCE(cyear, 0) cyear, COALESCE(last_yr, 0) last_yr, COALESCE(total, 0) total FROM t) select distinct form_name, m.cday,m.cmonth,m.cyear,m.last_yr,m.total from m  where working_upazila_id = "+str(df.geoid.tolist()[0])
                select_query = "WITH m as(select * from forms_data where working_upazila_id::int ="+str(df.geoid.tolist()[0])+"), t AS (SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'Patients Registry' AND Date_trunc('day', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM m WHERE form_name = 'Patients Registry' AND Date_trunc('month', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM m WHERE form_name = 'Patients Registry' AND Date_trunc('year', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'Patients Registry' AND Extract(year FROM To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM m WHERE form_name = 'Patients Registry') AS total FROM m WHERE form_name = 'Patients Registry' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'pathology' AND Date_trunc('day', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM m WHERE form_name = 'pathology' AND Date_trunc('month', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM m WHERE form_name = 'pathology' AND Date_trunc('year', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'pathology' AND Extract(year FROM To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM m WHERE form_name = 'pathology') AS total FROM m WHERE form_name = 'pathology' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'Postmortem' AND Date_trunc('day', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM m WHERE form_name = 'Postmortem' AND Date_trunc('month', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM m WHERE form_name = 'Postmortem' AND Date_trunc('year', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'Postmortem' AND Extract(year FROM To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM m WHERE form_name = 'Postmortem') AS total FROM m WHERE form_name = 'Postmortem' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'Farm Assessment Monitoring' AND Date_trunc('day', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM m WHERE form_name = 'Farm Assessment Monitoring' AND Date_trunc('month', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM m WHERE form_name = 'Farm Assessment Monitoring' AND Date_trunc('year', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'Farm Assessment Monitoring' AND Extract(year FROM To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr , (SELECT Count(*) FROM m WHERE form_name = 'Farm Assessment Monitoring') AS total FROM m WHERE form_name = 'Farm Assessment Monitoring' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'Participatory Livestock Assessment' AND Date_trunc('day', To_date( datajson ->> 'visit_date' , 'YYYY/MM/DD')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM m WHERE form_name = 'Participatory Livestock Assessment' AND Date_trunc('month', To_date( datajson ->> 'visit_date', 'YYYY/MM/DD') ) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM m WHERE form_name = 'Participatory Livestock Assessment' AND Date_trunc('year', To_date( datajson ->> 'visit_date' , 'YYYY/MM/DD')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'Participatory Livestock Assessment' AND Extract(year FROM To_date( datajson ->> 'visit_date' , 'YYYY/MM/DD')) = Extract( year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM m WHERE form_name = 'Participatory Livestock Assessment') AS total FROM m WHERE form_name = 'Participatory Livestock Assessment' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Sample' AND Date_trunc('day', To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Sample' AND Date_trunc('month', To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth , (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Sample' AND Date_trunc('year', To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Sample' AND Extract(year FROM To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Sample') AS total FROM m WHERE form_name = 'Avian Influenza Sample' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'Generic Disease Investigation' AND Date_trunc('day', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday , (SELECT Count(*) FROM m WHERE form_name = 'Generic Disease Investigation' AND Date_trunc('month', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM m WHERE form_name = 'Generic Disease Investigation' AND Date_trunc('year', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'Generic Disease Investigation' AND Extract(year FROM To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr , (SELECT Count(*) FROM m WHERE form_name = 'Generic Disease Investigation') AS total FROM m WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Investigation' AND Date_trunc('day', To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday , (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Investigation' AND Date_trunc('month', To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Investigation' AND Date_trunc('year', To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Investigation' AND Extract(year FROM To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr , (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Investigation') AS total FROM m WHERE form_name = 'Avian Influenza Investigation') SELECT form_name, COALESCE(cday, 0) cday, COALESCE(cmonth, 0) cmonth, COALESCE(cyear, 0) cyear, COALESCE(last_yr, 0) last_yr, COALESCE(total, 0) total FROM t"
                data = __db_fetch_values_dict(select_query)
                for each1 in data:
                    json_data.append(handle_none(each1))
                    # each1 contains a json dictionary.
                    # each1.items() create (key,value) pair
                    for key, value in each1.items():
                        if key not in col_name and key != "data_id":
                            # unique column name insert in col_name list
                            col_name.append(key)
                all_geo_id.append(df.geoid.tolist()[0])
        return render(request, 'fao_module/submission_count_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})
    message = "You have no access to this page"    
    return render(request, 'fao_module/error_404.html',{'message':message})


@login_required
def getCountData(request):
    division = request.POST.get('division')
    district = request.POST.get('district')
    upazilla = request.POST.get('upazilla')
    all_geo_id = request.POST.get('all_geo_id')

    filter_query = ""

    if division != "" or district !="" or upazilla != "":    
        if upazilla !="":
            filter_query += "where working_upazila_id::int = "+str(upazilla)
        else:
            if district != "":
                filter_query += "where working_upazila_id::int in (select value from geo_cluster where parent = "+str(district)+")"
            else:
                if division != "":
                    filter_query += "where working_upazila_id::int in (select value from geo_cluster where parent in (select value from geo_cluster where parent = "+str(division)+"))"   

    query = "WITH m as(select * from forms_data "+str(filter_query)+"), t AS (SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'Patients Registry' AND Date_trunc('day', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM m WHERE form_name = 'Patients Registry' AND Date_trunc('month', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM m WHERE form_name = 'Patients Registry' AND Date_trunc('year', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'Patients Registry' AND Extract(year FROM To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM m WHERE form_name = 'Patients Registry') AS total FROM m WHERE form_name = 'Patients Registry' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'pathology' AND Date_trunc('day', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM m WHERE form_name = 'pathology' AND Date_trunc('month', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM m WHERE form_name = 'pathology' AND Date_trunc('year', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'pathology' AND Extract(year FROM To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM m WHERE form_name = 'pathology') AS total FROM m WHERE form_name = 'pathology' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'Postmortem' AND Date_trunc('day', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM m WHERE form_name = 'Postmortem' AND Date_trunc('month', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM m WHERE form_name = 'Postmortem' AND Date_trunc('year', To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'Postmortem' AND Extract(year FROM To_date( datajson ->> 'date', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM m WHERE form_name = 'Postmortem') AS total FROM m WHERE form_name = 'Postmortem' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'Farm Assessment Monitoring' AND Date_trunc('day', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM m WHERE form_name = 'Farm Assessment Monitoring' AND Date_trunc('month', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM m WHERE form_name = 'Farm Assessment Monitoring' AND Date_trunc('year', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'Farm Assessment Monitoring' AND Extract(year FROM To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr , (SELECT Count(*) FROM m WHERE form_name = 'Farm Assessment Monitoring') AS total FROM m WHERE form_name = 'Farm Assessment Monitoring' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'Participatory Livestock Assessment' AND Date_trunc('day', To_date( datajson ->> 'visit_date' , 'YYYY/MM/DD')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM m WHERE form_name = 'Participatory Livestock Assessment' AND Date_trunc('month', To_date( datajson ->> 'visit_date', 'YYYY/MM/DD') ) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM m WHERE form_name = 'Participatory Livestock Assessment' AND Date_trunc('year', To_date( datajson ->> 'visit_date' , 'YYYY/MM/DD')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'Participatory Livestock Assessment' AND Extract(year FROM To_date( datajson ->> 'visit_date' , 'YYYY/MM/DD')) = Extract( year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM m WHERE form_name = 'Participatory Livestock Assessment') AS total FROM m WHERE form_name = 'Participatory Livestock Assessment' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Sample' AND Date_trunc('day', To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday, (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Sample' AND Date_trunc('month', To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth , (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Sample' AND Date_trunc('year', To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Sample' AND Extract(year FROM To_date( datajson ->> 'date_sample_collected', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr, (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Sample') AS total FROM m WHERE form_name = 'Avian Influenza Sample' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'Generic Disease Investigation' AND Date_trunc('day', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday , (SELECT Count(*) FROM m WHERE form_name = 'Generic Disease Investigation' AND Date_trunc('month', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM m WHERE form_name = 'Generic Disease Investigation' AND Date_trunc('year', To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'Generic Disease Investigation' AND Extract(year FROM To_date( datajson ->> 'date_initial_visit', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr , (SELECT Count(*) FROM m WHERE form_name = 'Generic Disease Investigation') AS total FROM m WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT DISTINCT form_name, (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Investigation' AND Date_trunc('day', To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Date_trunc('day', CURRENT_DATE) GROUP BY form_name) AS cday , (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Investigation' AND Date_trunc('month', To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Date_trunc('month', CURRENT_DATE) GROUP BY form_name) AS cmonth, (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Investigation' AND Date_trunc('year', To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Date_trunc('year', CURRENT_DATE) GROUP BY form_name) AS cyear, (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Investigation' AND Extract(year FROM To_date( datajson ->> 'date_completed', 'DD-MM-YYYY')) = Extract(year FROM CURRENT_DATE) - 1 GROUP BY form_name) AS last_yr , (SELECT Count(*) FROM m WHERE form_name = 'Avian Influenza Investigation') AS total FROM m WHERE form_name = 'Avian Influenza Investigation') SELECT form_name, COALESCE(cday, 0) cday, COALESCE(cmonth, 0) cmonth, COALESCE(cyear, 0) cyear, COALESCE(last_yr, 0) last_yr, COALESCE(total, 0) total FROM t "
    test_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return HttpResponse(json.dumps({'test_list':test_list}))


@login_required
def hr_engagement_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    # fetching all organization recursively of current_user
    all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
    org_id_list = [org.pk for org in all_organizations]

    # this geo_data is the variable for storing all geo location for current_user
    all_geo_id = []
    col_name = []
    json_data = []

    org_type_query = "select * from usermodule_organizations where id = " + str(current_user.organisation_name_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(org_type_query, connection)

    # query for filtering options
    all_query = "WITH m AS(WITH t AS (SELECT datajson ->> 'date_initial_visit' AS working_date, datajson ->> 'field_staff1' AS field_staff, working_upazila_id FROM forms_data WHERE form_name = 'Farm Assessment Monitoring' UNION ALL SELECT datajson ->> 'date_initial_visit' AS working_date, datajson ->> 'field_staff2' AS field_staff, working_upazila_id FROM forms_data WHERE form_name = 'Farm Assessment Monitoring') SELECT DISTINCT field_staff, working_date, NULL AS working_night, 'Farm Assessment Monitoring' AS activity, working_upazila_id FROM t UNION ALL ( WITH t AS (SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date11' AS working_date, datajson ->> 'admin_overnight_date11' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date12' AS working_date, datajson ->> 'admin_overnight_date12' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date13' AS working_date, datajson ->> 'admin_overnight_date13' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date21' AS working_date, datajson ->> 'admin_overnight_date21' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date22' AS working_date, datajson ->> 'admin_overnight_date22' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date23' AS working_date, datajson ->> 'admin_overnight_date23' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation') SELECT DISTINCT field_staff, working_date, working_night, 'Avian Influenza Investigation' AS activity, working_upazila_id FROM t WHERE working_date IS NOT NULL) UNION ALL ( WITH t AS (SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date11' AS working_date, datajson ->> 'admin_overnight_date11' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date12' AS working_date, datajson ->> 'admin_overnight_date12' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date13' AS working_date, datajson ->> 'admin_overnight_date13' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date21' AS working_date, datajson ->> 'admin_overnight_date21' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date22' AS working_date, datajson ->> 'admin_overnight_date22' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date23' AS working_date, datajson ->> 'admin_overnight_date23' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation') SELECT DISTINCT field_staff, To_char(working_date :: DATE, 'DD-MM-YYYY') AS working_date , To_char(working_night :: DATE, 'DD-MM-YYYY') AS working_night, 'Generic Disease Investigation' AS activity , working_upazila_id FROM t WHERE working_date IS NOT NULL) UNION ALL ( WITH t AS (SELECT datajson ->> 'name1' AS field_staff, datajson ->> 'visit_date' AS working_date, working_upazila_id FROM forms_data WHERE form_name = 'Participatory Livestock Assessment' UNION ALL SELECT datajson ->> 'name2' AS field_staff, datajson ->> 'visit_date' AS working_date, working_upazila_id FROM forms_data WHERE form_name = 'Participatory Livestock Assessment') SELECT DISTINCT field_staff, To_char(working_date :: DATE, 'DD-MM-YYYY') AS working_date , NULL AS working_night, 'Participatory Livestock Assessment' AS activity, working_upazila_id FROM t)) SELECT (SELECT first_name ||' ' ||last_name FROM auth_user WHERE id :: text = m.field_staff) AS username, (SELECT (SELECT organization FROM usermodule_organizations WHERE id = organisation_name_id) AS organization FROM usermodule_usermoduleprofile WHERE user_id :: text = m.field_staff) AS office, Count(distinct m.working_date) AS number_of_days, Count(distinct m.working_night) AS number_of_nights FROM m GROUP BY m.field_staff"
    df1= pandas.read_sql(all_query,connection)
    users = df1.username.unique().tolist()
    offices = df1.office.unique().tolist()

    # For CO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 1:
        select_query = "WITH m AS(WITH t AS (SELECT datajson ->> 'date_initial_visit' AS working_date, datajson ->> 'field_staff1' AS field_staff, working_upazila_id FROM forms_data WHERE form_name = 'Farm Assessment Monitoring' UNION ALL SELECT datajson ->> 'date_initial_visit' AS working_date, datajson ->> 'field_staff2' AS field_staff, working_upazila_id FROM forms_data WHERE form_name = 'Farm Assessment Monitoring') SELECT DISTINCT field_staff, working_date, NULL AS working_night, 'Farm Assessment Monitoring' AS activity, working_upazila_id FROM t UNION ALL ( WITH t AS (SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date11' AS working_date, datajson ->> 'admin_overnight_date11' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date12' AS working_date, datajson ->> 'admin_overnight_date12' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date13' AS working_date, datajson ->> 'admin_overnight_date13' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date21' AS working_date, datajson ->> 'admin_overnight_date21' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date22' AS working_date, datajson ->> 'admin_overnight_date22' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date23' AS working_date, datajson ->> 'admin_overnight_date23' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation') SELECT DISTINCT field_staff, working_date, working_night, 'Avian Influenza Investigation' AS activity, working_upazila_id FROM t WHERE working_date IS NOT NULL) UNION ALL ( WITH t AS (SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date11' AS working_date, datajson ->> 'admin_overnight_date11' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date12' AS working_date, datajson ->> 'admin_overnight_date12' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date13' AS working_date, datajson ->> 'admin_overnight_date13' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date21' AS working_date, datajson ->> 'admin_overnight_date21' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date22' AS working_date, datajson ->> 'admin_overnight_date22' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date23' AS working_date, datajson ->> 'admin_overnight_date23' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation') SELECT DISTINCT field_staff, To_char(working_date :: DATE, 'DD-MM-YYYY') AS working_date , To_char(working_night :: DATE, 'DD-MM-YYYY') AS working_night, 'Generic Disease Investigation' AS activity , working_upazila_id FROM t WHERE working_date IS NOT NULL) UNION ALL ( WITH t AS (SELECT datajson ->> 'name1' AS field_staff, datajson ->> 'visit_date' AS working_date, working_upazila_id FROM forms_data WHERE form_name = 'Participatory Livestock Assessment' UNION ALL SELECT datajson ->> 'name2' AS field_staff, datajson ->> 'visit_date' AS working_date, working_upazila_id FROM forms_data WHERE form_name = 'Participatory Livestock Assessment') SELECT DISTINCT field_staff, To_char(working_date :: DATE, 'DD-MM-YYYY') AS working_date , NULL AS working_night, 'Participatory Livestock Assessment' AS activity, working_upazila_id FROM t)) SELECT (SELECT first_name ||' '||last_name FROM auth_user WHERE id :: text = m.field_staff) AS username, (SELECT (SELECT organization FROM usermodule_organizations WHERE id = organisation_name_id) AS organization FROM usermodule_usermoduleprofile WHERE user_id :: text = m.field_staff) AS office, Count(distinct m.working_date) AS number_of_days, Count(distinct m.working_night) AS number_of_nights FROM m GROUP BY m.field_staff"
        data = __db_fetch_values_dict(select_query)
        for each1 in data:
                json_data.append(handle_none(each1))
                # each1 contains a json dictionary.
                # each1.items() create (key,value) pair
                for key, value in each1.items():
                    if key not in col_name and key != "data_id":
                        # unique column name insert in col_name list
                        col_name.append(key)
        all_geo_id.append(1)
        return render(request, 'fao_module/hr_engagement_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id,'users':users,'offices':offices})

    # For ULO/LO users
    if df.organization_type.tolist()[0] is not None and  int(df.organization_type.tolist()[0]) == 2:
        for each in org_id_list:
            query = "select geoid from organization_catchment_area where organization_id = " + str(each)
            df = pandas.DataFrame()
            df = pandas.read_sql(query, connection)
            if not df.empty:
                # check for duplicate geoid
                # every time a unique geoid is pushed in all_geo_id
                if df.geoid.tolist()[0] in all_geo_id:
                    continue
                # fetching data from forms_data
                select_query = "WITH m AS(WITH t AS (SELECT datajson ->> 'date_initial_visit' AS working_date, datajson ->> 'field_staff1' AS field_staff ,working_upazila_id FROM forms_data WHERE form_name = 'Farm Assessment Monitoring' UNION ALL SELECT datajson ->> 'date_initial_visit' AS working_date, datajson ->> 'field_staff2' AS field_staff ,working_upazila_id FROM forms_data WHERE form_name = 'Farm Assessment Monitoring') SELECT DISTINCT field_staff, working_date , NULL AS working_night, 'Farm Assessment Monitoring' AS activity ,working_upazila_id FROM t UNION ALL ( WITH t AS (SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date11' AS working_date, datajson ->> 'admin_overnight_date11' AS working_night,working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date12' AS working_date, datajson ->> 'admin_overnight_date12' AS working_night ,working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date13' AS working_date, datajson ->> 'admin_overnight_date13' AS working_night ,working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date21' AS working_date, datajson ->> 'admin_overnight_date21' AS working_night ,working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date22' AS working_date, datajson ->> 'admin_overnight_date22' AS working_night ,working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date23' AS working_date, datajson ->> 'admin_overnight_date23' AS working_night ,working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation') SELECT DISTINCT field_staff, working_date, working_night, 'Avian Influenza Investigation' AS activity,working_upazila_id FROM t WHERE working_date IS NOT NULL) UNION ALL ( WITH t AS (SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date11' AS working_date, datajson ->> 'admin_overnight_date11' AS working_night ,working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date12' AS working_date, datajson ->> 'admin_overnight_date12' AS working_night ,working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date13' AS working_date, datajson ->> 'admin_overnight_date13' AS working_night ,working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date21' AS working_date, datajson ->> 'admin_overnight_date21' AS working_night ,working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date22' AS working_date, datajson ->> 'admin_overnight_date22' AS working_night ,working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date23' AS working_date, datajson ->> 'admin_overnight_date23' AS working_night ,working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation') SELECT DISTINCT field_staff, To_char(working_date :: DATE, 'DD-MM-YYYY') AS working_date , To_char(working_night :: DATE, 'DD-MM-YYYY') AS working_night, 'Generic Disease Investigation' AS activity ,working_upazila_id FROM t WHERE working_date IS NOT NULL) UNION ALL ( WITH t AS (SELECT datajson ->> 'name1' AS field_staff, datajson ->> 'visit_date' AS working_date ,working_upazila_id FROM forms_data WHERE form_name = 'Participatory Livestock Assessment' UNION ALL SELECT datajson ->> 'name2' AS field_staff, datajson ->> 'visit_date' AS working_date ,working_upazila_id FROM forms_data WHERE form_name = 'Participatory Livestock Assessment') SELECT DISTINCT field_staff, To_char(working_date :: DATE, 'DD-MM-YYYY') AS working_date , NULL AS working_night, 'Participatory Livestock Assessment' AS activity ,working_upazila_id FROM t)) SELECT (SELECT first_name||' '||last_name FROM auth_user WHERE id :: text = m.field_staff) AS username, (SELECT (SELECT organization FROM usermodule_organizations WHERE id = organisation_name_id) AS organization FROM usermodule_usermoduleprofile WHERE user_id :: text = m.field_staff) AS office, Count(distinct m.working_date) AS number_of_days, Count(distinct m.working_night) AS number_of_nights FROM m where working_upazila_id = " + str(df.geoid.tolist()[0])+" GROUP BY m.field_staff"
                data = __db_fetch_values_dict(select_query)
                for each1 in data:
                    json_data.append(handle_none(each1))
                    # each1 contains a json dictionary.
                    # each1.items() create (key,value) pair
                    for key, value in each1.items():
                        if key not in col_name and key != "data_id":
                            # unique column name insert in col_name list
                            col_name.append(key)
                all_geo_id.append(df.geoid.tolist()[0])
        return render(request, 'fao_module/hr_engagement_list.html',{'col_name': col_name, 'json_data': json_data, 'all_geo_id': all_geo_id})
    message = "You have no access to this page"    
    return render(request, 'fao_module/error_404.html',{'message':message})



@login_required
def getHRData(request):
    user = request.POST.get('user')
    office = request.POST.get('office')
    

    filter_query = ""

    

    if user != "" or office !="":
        filter_query = " where "
        if user != "" and office !="":
            filter_query += " username = '"+str(user)+"' and "
        elif user != "":
            filter_query += " username = '"+str(user)+"' "
        if office !="":
            filter_query += " office = '"+str(office)+"' "
        

    query = "with s as(WITH m AS (WITH t AS (SELECT datajson ->> 'date_initial_visit' AS working_date, datajson ->> 'field_staff1' AS field_staff, working_upazila_id FROM forms_data WHERE form_name = 'Farm Assessment Monitoring' UNION ALL SELECT datajson ->> 'date_initial_visit' AS working_date, datajson ->> 'field_staff2' AS field_staff, working_upazila_id FROM forms_data WHERE form_name = 'Farm Assessment Monitoring') SELECT DISTINCT field_staff, working_date, NULL AS working_night, 'Farm Assessment Monitoring' AS activity, working_upazila_id FROM t UNION ALL ( WITH t AS (SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date11' AS working_date, datajson ->> 'admin_overnight_date11' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date12' AS working_date, datajson ->> 'admin_overnight_date12' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date13' AS working_date, datajson ->> 'admin_overnight_date13' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date21' AS working_date, datajson ->> 'admin_overnight_date21' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date22' AS working_date, datajson ->> 'admin_overnight_date22' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date23' AS working_date, datajson ->> 'admin_overnight_date23' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Avian Influenza Investigation') SELECT DISTINCT field_staff, working_date, working_night, 'Avian Influenza Investigation' AS activity, working_upazila_id FROM t WHERE working_date IS NOT NULL) UNION ALL ( WITH t AS (SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date11' AS working_date, datajson ->> 'admin_overnight_date11' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date12' AS working_date, datajson ->> 'admin_overnight_date12' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name1' AS field_staff, datajson ->> 'admin_working_date13' AS working_date, datajson ->> 'admin_overnight_date13' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date21' AS working_date, datajson ->> 'admin_overnight_date21' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date22' AS working_date, datajson ->> 'admin_overnight_date22' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation' UNION ALL SELECT datajson ->> 'investigator_name2' AS field_staff, datajson ->> 'admin_working_date23' AS working_date, datajson ->> 'admin_overnight_date23' AS working_night, working_upazila_id FROM forms_data WHERE form_name = 'Generic Disease Investigation') SELECT DISTINCT field_staff, To_char(working_date :: DATE, 'DD-MM-YYYY') AS working_date , To_char(working_night :: DATE, 'DD-MM-YYYY') AS working_night, 'Generic Disease Investigation' AS activity , working_upazila_id FROM t WHERE working_date IS NOT NULL) UNION ALL ( WITH t AS (SELECT datajson ->> 'name1' AS field_staff, datajson ->> 'visit_date' AS working_date, working_upazila_id FROM forms_data WHERE form_name = 'Participatory Livestock Assessment' UNION ALL SELECT datajson ->> 'name2' AS field_staff, datajson ->> 'visit_date' AS working_date, working_upazila_id FROM forms_data WHERE form_name = 'Participatory Livestock Assessment') SELECT DISTINCT field_staff, To_char(working_date :: DATE, 'DD-MM-YYYY') AS working_date , NULL AS working_night, 'Participatory Livestock Assessment' AS activity, working_upazila_id FROM t)) SELECT (SELECT first_name ||' ' ||last_name FROM auth_user WHERE id :: text = m.field_staff) AS username, (SELECT (SELECT organization FROM usermodule_organizations WHERE id = organisation_name_id) AS organization FROM usermodule_usermoduleprofile WHERE user_id :: text = m.field_staff) AS office, Count(distinct m.working_date) AS number_of_days, Count(distinct m.working_night) AS number_of_nights FROM m GROUP BY m.field_staff) select * from s "+str(filter_query)
    print(query)
    test_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return HttpResponse(json.dumps({'test_list':test_list}))


#########################################################################
#########################################################################
#########################################################################
