import simplejson
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.db.models import Count,Q
from django.http import ( HttpResponseRedirect, HttpResponse)
from django.shortcuts import render_to_response, get_object_or_404, render
from django.forms.formsets import formset_factory
from onadata.apps.hhmodule.forms import HouseholdForm, HhMemberForm
from django.db.models import ProtectedError
from django.db import connection
from onadata.apps.hhmodule.models import *
import json
from django.forms.models import inlineformset_factory
from collections import OrderedDict
# *************************** Household (hh) Module *****************************************


def index(request):
    current_user = request.user
    print "Hello!!"
    householdForm = HouseholdForm()
    #hhMemberFormSet = formset_factory(HhMemberForm)

    hhMemberFormSet = formset_factory(HhMemberForm, extra=3)
    hhmember_formset = hhMemberFormSet()

    context = {
        'household_form': householdForm,
        'hhMember_formSet': hhmember_formset
    }
    return render(request,'hhmodule/index.html',context)


"""
Prepare json of given query for data table
@persia
"""
def getDatatable(query):
    data_list = []
    col_names = []
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = cursor.fetchall();
    col_names = [i[0] for i in cursor.description]
    col_names.append('Action')
    for eachval in fetchVal:
        #delete_button = '<a class="delete-program-item tooltips" data-placement="top" href="#" data-original-title="Delete Program"  onclick="delete_program('+ str(eachval[0]) +')"><i class="fa fa-2x fa-trash-o"></i></a>'
        delete_button = ''
        edit_button = '<a class="tooltips" data-placement="top" data-original-title="Edit Program" href="#" onclick="edit_entity('+str(eachval[0]) +');"><i class="fa fa-2x fa-pencil-square-o"></i></a>' + ' ' + delete_button
        eachval = eachval + (edit_button,)
        data_list.append(list(eachval))
    return json.dumps({'col_name': col_names, 'data': data_list})


"""
Prepare Message for Ajax request message
@persia
"""
def getAjaxMessage(type, message):
    data = {}
    data['type'] = type
    data['messages'] = message
    return data



"""
Add Household Information
Parent (household)-child (household members) relation, Django Formset implementation
@persia
"""
def add_household(request):
    current_user = request.user
    householdForm = HouseholdForm()
    hhMemberFormSet = inlineformset_factory(Household, HhMember, form=HhMemberForm, extra=1)
    #hhMemberFormSet = formset_factory(HhMemberForm)
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        householdForm = HouseholdForm(data=request.POST)
        hhMemberFormSet=hhMemberFormSet(data=request.POST)
        if householdForm.is_valid() and hhMemberFormSet.is_valid():
            # Save user info
            household_instance=householdForm.save()
            # Now save the data for each form in the formset
            for member_form in hhMemberFormSet:
                member_form_instance=member_form.save(commit=False)
                member_form_instance.household=household_instance;
                member_form.save()
        data = getAjaxMessage("success","<i class='fa fa-check-circle'> </i> New Household -" + household_instance.holding_no + " has been created successfully")
        return HttpResponse(simplejson.dumps(data), content_type="application/json")
    elif request.is_ajax():
        householdForm = HouseholdForm()
        return render(request, 'hhmodule/add_household_form.html', {'household_form': householdForm, 'hhMember_formSet': hhMemberFormSet})
    context = {
        'household_form': householdForm,
        'hhMember_formSet': hhMemberFormSet
    }
    return render(request,'hhmodule/index.html',context)



"""
Edit Household Information
Parent (household)-child (household members) relation, Django Formset implementation
@:param household id in Household table
@ persia
"""
def edit_household(request, household_id):
    HOUSEHOLD_EDIT_ID = Household.objects.filter(hh_id=household_id).first().id

    if request.method == 'GET':
        household_form_instance = Household.objects.filter(id=HOUSEHOLD_EDIT_ID).first()
        household_form = HouseholdForm(instance=household_form_instance)

        #hhMembers= HhMember.objects.filter(household_id=HOUSEHOLD_EDIT_ID).values('age', 'disability', 'gender', 'highest_education_level', 'household', 'id', 'member_id', 'member_relationship', 'member_status', 'mobile_no', 'name', 'occupation', 'profile_photo', 'regular_attendence', 'work_for_cash')
        hhMembers= HhMember.objects.filter(household_id=HOUSEHOLD_EDIT_ID)
        hhMembers =hhMembers.values('age', 'disability', 'gender',
                                    'highest_education_level',
                                    'household', 'id', 'member_id',
                                    'member_relationship',
                                    'member_status', 'mobile_no', 'name',
                                    'occupation', 'profile_photo',
                                    'regular_attendence',
                                    'work_for_cash')

        hhMembers_count = hhMembers.count()
        if hhMembers_count==0:
            hhMembers_count=1
        HouseholdMemberFormSet = inlineformset_factory(Household, HhMember, form=HhMemberForm, extra=hhMembers_count)
        hhMember_formset = HouseholdMemberFormSet(initial=hhMembers)
    if request.method == 'POST':
        #Household Form
        household_form_instance = Household.objects.filter(id=HOUSEHOLD_EDIT_ID).first()
        household_form = HouseholdForm(data=request.POST, instance=household_form_instance)
        print "Before submit"
        #HH Member Formset
        HouseholdMemberFormSet = inlineformset_factory(Household, HhMember, form=HhMemberForm)
        hhMember_formset = HouseholdMemberFormSet(request.POST, request.FILES, instance=household_form_instance)
        if household_form.is_valid():
            print "HH  submit"
            household_instance=household_form.save(commit=False)
            hhMember_formset = HouseholdMemberFormSet(request.POST,request.FILES ,instance=household_instance)
            if hhMember_formset.is_valid():
                # Now save the data for each form in the formset
                for instance in hhMember_formset:
                    instance_data_dict = instance.cleaned_data
                    hhmember_each_form = instance.save(commit=False);
                    if instance_data_dict.get('id') is not None:
                        hh_member_original_instance = HhMember.objects.filter(id=instance_data_dict.get('id').id).first()
                        hhmember_each_form.id=hh_member_original_instance.id;
                    if instance_data_dict.get('DELETE')==False:
                        hhmember_each_form.save()
                    else: hhmember_each_form.delete()

                household_form.save()
            else :
                #data = getAjaxMessage("danger", "<i class='fa fa-check-circle'> </i> Household -" + household_instance.holding_no + " has been edited successfully")
                #return HttpResponse(simplejson.dumps(data), content_type="application/json")
                return render(request,'hhmodule/add_household_form.html', {'household_form': household_form, 'hhMember_formSet': hhMember_formset, 'HOUSEHOLD_EDIT_ID': HOUSEHOLD_EDIT_ID}, status=500)
        else :
            return render(request, 'hhmodule/add_household_form.html',
                          {'household_form': household_form, 'hhMember_formSet': hhMember_formset,
                           'HOUSEHOLD_EDIT_ID': HOUSEHOLD_EDIT_ID}, status=500)
        #household_form = HouseholdForm()
        #hhMember_formset = formset_factory(HhMemberForm)
        print "After submit"
        data = getAjaxMessage("success", "<i class='fa fa-check-circle'> </i> Household -" + household_instance.holding_no + " has been edited successfully")
        return HttpResponse(simplejson.dumps(data), content_type="application/json")
    return render(request,'hhmodule/add_household_form.html',{'household_form': household_form, 'hhMember_formSet': hhMember_formset, 'HOUSEHOLD_EDIT_ID': HOUSEHOLD_EDIT_ID})



def show_household(request):
    datajson = getDatatable(
        'SELECT id, (select name from geo_ward where id=geo_ward_id) as Ward, (select name from hh_use_asset_grant where id=hh_use_asset_grant_id) as User_Grant, hh_status_id, holding_no, hh_member_number, hh_serial, hh_id FROM public.household ')

    return HttpResponse(datajson, content_type='application/json')


################# shahin #######################
@login_required
def cupDashboard(request):
    ward_list_query = "select id,name from geo_ward"
    ward_list_data = json.dumps(__db_fetch_values_dict(ward_list_query))
    hh_list_query = "SELECT hh.id, hh.hh_id, (select name from hh_member where member_id = hhm.member_id LIMIT 1) as hhhead_name, hh.holding_no,(SELECT NAME FROM PUBLIC.geo_ward WHERE id = hh.geo_ward_id) AS ward, hh.hh_phone, (SELECT NAME FROM PUBLIC.hh_status WHERE id = hh.hh_status_id) AS hh_status FROM PUBLIC.household hh LEFT JOIN PUBLIC.hh_member hhm ON hhm.household_id = hh.id WHERE hhm.member_relationship_id = 1"
    hh_list_data = json.dumps(__db_fetch_values_dict(hh_list_query))
    return render(request, "cup/cup_dashbaord.html", { 'hh_list_data' : hh_list_data, 'ward_list_data':ward_list_data })


def filter_hh_list(request):
    where_clause = ''
    hh_id = request.POST.get('f_hh_id')
    hh_head_name = request.POST.get('f_hh_head_name')
    hh_ward = request.POST.get('f_hh_ward')
    hh_mobile = request.POST.get('f_hh_mobile')

    if hh_id is not None and hh_id != '':
        where_clause += " AND t.hh_id = '"+str(hh_id)+"'"
    if hh_head_name is not None and hh_head_name != '':
        where_clause += " AND t.hhhead_name = '"+str(hh_head_name)+"'"
    if hh_ward is not None:
        where_clause += " AND t.geo_ward_id = "+str(hh_ward)
    if hh_mobile is not None and hh_mobile != '':
        where_clause += " AND t.hh_phone = '"+str(hh_mobile)+"'"


    hh_list_filter_qry = "with t as(SELECT hh.id, hh.hh_id, (SELECT name FROM hh_member WHERE member_id = hhm.member_id LIMIT 1) AS hhhead_name, hh.holding_no, (SELECT name FROM public.geo_ward WHERE id = hh.geo_ward_id) AS ward,hh.geo_ward_id, hh.hh_phone, (SELECT name FROM public.hh_status WHERE id = hh.hh_status_id) AS hh_status FROM public.household hh LEFT JOIN public.hh_member hhm ON hhm.household_id = hh.id WHERE hhm.member_relationship_id = 1) select * from t where 1 = 1 " + str(where_clause)
    print hh_list_filter_qry
    hh_list_filter_data = json.dumps(__db_fetch_values_dict(hh_list_filter_qry))

    return HttpResponse(json.dumps(hh_list_filter_data))




def getHHProfile(request):
    profile_id = request.POST.get('profile_id')
    baseline_id_qry = "select id from logger_instance where deleted_at is null  and xform_id=333 and ('0' || (json->>'hh_id')::text)= '"+str(profile_id)+"'"
    instance_id = __db_fetch_single_value(baseline_id_qry)
    profile_query = "SELECT hh.id, hh.hh_id, (select name from hh_member where member_id = hhm.member_id LIMIT 1) as hhhead_name, hh.holding_no,(SELECT name FROM public.hh_use_asset_grant where id = hh.hh_use_asset_grant_id) as hh_use_asset_name,(SELECT name FROM public.geo_ward WHERE id = hh.geo_ward_id) AS ward, hh.hh_phone, (SELECT name FROM public.hh_status WHERE id = hh.hh_status_id) AS hh_status FROM public.household hh LEFT JOIN public.hh_member hhm ON hhm.household_id = hh.id WHERE hhm.member_relationship_id = 1 AND hh_id = '"+profile_id+"' LIMIT 1"
    profile_data = json.dumps(__db_fetch_values_dict(profile_query))
    return HttpResponse(json.dumps(profile_data+'@@@@@'+str(instance_id)))


def getMemberLsit(request):
    profile_id = request.POST.get('profile_id')
    mem_list_query = "SELECT name, age, CASE WHEN(gender = 1) THEN 'Male' WHEN (gender = 2) THEN 'Female' END AS gender, (SELECT name FROM public.highest_education_level where id = highest_education_level_id) as highest_education_level, (SELECT name FROM public.occupation where id = occupation_id) as occupation, CASE WHEN (disability = 0) THEN 'No' WHEN (disability = 1) THEN 'Yes' END AS disability, (SELECT name FROM public.member_status where id = member_status_id) as member_status FROM hh_member WHERE household_id = (SELECT id FROM public.household WHERE hh_id = '"+str(profile_id)+"' LIMIT 1) "
    mem_list_data = json.dumps(__db_fetch_values_dict(mem_list_query))
    return HttpResponse(json.dumps(mem_list_data))


def getSnapshotData(request):
    profile_id = request.POST.get('profile_id')
    snapshot_query = "select id,respondent_name,visit_date::text,visit_type, (select username from auth_user where id = user_id) as sender from vssnapshotlist where hh_id = '"+str(profile_id)+"'"
    snapshot_data = json.dumps(__db_fetch_values_dict(snapshot_query))
    return HttpResponse(json.dumps(snapshot_data))


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


def dictfetchall(cursor):
    desc = cursor.description
    return [
        OrderedDict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()]



