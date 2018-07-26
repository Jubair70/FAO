from django.conf.urls import patterns, include, url
from django.contrib import admin
from onadata.apps.hhmodule import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^add_household/$', views.add_household, name='add_household'),
    url(r'^show_household/$', views.show_household, name='show_household'),
    url(r'^edit_household/(?P<household_id>\d+)/$', views.edit_household, name='edit_household')
)
