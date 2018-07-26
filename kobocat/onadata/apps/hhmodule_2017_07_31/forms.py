from django import forms
from onadata.apps.hhmodule.models import *
from django.forms.models import inlineformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div,Layout
#from django.forms.models import inlineformset_factory

class MyColFormHelper(FormHelper):
    form_tag = False
    disable_csrf = True

#************************LogFrame Entry Forms***************************

class HouseholdForm(forms.ModelForm):
    hh_status = forms.ModelChoiceField(label='Status', required=True,queryset=HhStatus.objects.all(),to_field_name='id', empty_label="Select Status")
    geo_ward = forms.ModelChoiceField(label='Ward', required=True, queryset=GeoWard.objects.all(),
                                       to_field_name='id', empty_label="Select")
    hh_use_asset_grant = forms.ModelChoiceField(label='Use Asset Grant', required=True, queryset=HhUseAssetGrant.objects.all(),
                                       to_field_name='id', empty_label="Select")

    class Meta:
        model = Household
        #exclude = ('id',)

    def __init__(self, *args, **kwargs):
        super(HouseholdForm, self).__init__(*args, **kwargs)
        self.helper = MyColFormHelper()
        self.helper.layout = Layout(
            Div(
                Div('hh_status', css_class='controls col-md-4'),
                Div('geo_ward', css_class='controls col-md-2'),
                Div('hh_use_asset_grant', css_class='controls col-md-6'),
                Div('holding_no', css_class='controls col-md-2'),
                Div('hh_member_number', css_class='controls col-md-2'),
                Div('hh_serial', css_class='controls col-md-2'),
                Div('hh_id', css_class='controls col-md-3'),
                Div('hh_phone', css_class='controls col-md-3'),
                css_class=''),
        )


class HhMemberForm(forms.ModelForm):
    highest_education_level = forms.ModelChoiceField(label='Highest Education Level', required=True, queryset=HighestEducationLevel.objects.all(),
                                       to_field_name='id', empty_label="Select Status")
    occupation = forms.ModelChoiceField(label='Occupation', required=True, queryset=Occupation.objects.all(),
                                       to_field_name='id', empty_label="Select Status")
    member_relationship = forms.ModelChoiceField(label='Relationship', required=True, queryset=MemberRelationship.objects.all(),
                                       to_field_name='id', empty_label="Select Status")
    member_status = forms.ModelChoiceField(label='Member Status', required=True, queryset=MemberStatus.objects.all(),
                                       to_field_name='id', empty_label="Select Status")

    #household = forms.CharField(widget=forms.HiddenInput(), required=False)
    class Meta:
        model = HhMember
        exclude = ('household',)

    def __init__(self, *args, **kwargs):
        super(HhMemberForm, self).__init__(*args, **kwargs)
        self.helper = MyColFormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Div('highest_education_level', css_class='controls col-md-4'),
                Div('occupation', css_class='controls col-md-4'),
                Div('member_relationship', css_class='controls col-md-4'),
                Div('member_status', css_class='controls col-md-6'),
                Div('name', css_class='controls  col-md-3'),
                Div('age', css_class='controls  col-md-3'),
                Div('gender', css_class='controls  col-md-2'),
                Div('member_id', css_class='controls  col-md-3'),
                Div('disability', css_class='controls  col-md-2'),
                Div('regular_attendence', css_class='controls  col-md-2'),
                Div('profile_photo', css_class='controls  col-md-3'),
                Div('mobile_no', css_class='controls  col-md-3'),
                Div('work_for_cash', css_class='controls  col-md-2'),
                css_class=''),
        )

HouseholdMemberFormSet = inlineformset_factory(Household, HhMember, form=HhMemberForm, extra=1)
#HhMemberFormSet = inlineformset_factory(Household, HhMemberForm, form=HhMemberForm, extra=1)