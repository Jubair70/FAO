import pytz
import sys
from datetime import datetime

from django.conf import settings
from django.http import Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.models import User

from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import authenticate
from django.contrib.contenttypes.models import ContentType

from onadata.apps.api.tools import get_media_file_response
from onadata.apps.logger.models.xform import XForm
from onadata.apps.main.models.meta_data import MetaData
from onadata.apps.main.models.user_profile import UserProfile
from onadata.libs import filters
from onadata.libs.authentication import DigestAuthentication
from onadata.libs.renderers.renderers import MediaFileContentNegotiation
from onadata.libs.renderers.renderers import XFormListRenderer
from onadata.libs.renderers.renderers import XFormManifestRenderer
from onadata.libs.serializers.xform_serializer import XFormListSerializer
from onadata.libs.serializers.xform_serializer import XFormManifestSerializer
from onadata.apps.usermodule.models import UserModuleProfile
from onadata.apps.scheduling.models.geo_location_psu import GeoPsu
from django.core import serializers
from django.http import HttpResponse
import json


# 10,000,000 bytes
DEFAULT_CONTENT_LENGTH = getattr(settings, 'DEFAULT_CONTENT_LENGTH', 10000000)


class XFormListApi(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (DigestAuthentication,)
    content_negotiation_class = MediaFileContentNegotiation
    filter_backends = (filters.XFormListObjectPermissionFilter,)
    queryset = XForm.objects.filter(downloadable=True)
    permission_classes = (permissions.AllowAny,)
    renderer_classes = (XFormListRenderer,)
    serializer_class = XFormListSerializer
    template_name = 'api/xformsList.xml'

    def get_openrosa_headers(self):
        tz = pytz.timezone(settings.TIME_ZONE)
        dt = datetime.now(tz).strftime('%a, %d %b %Y %H:%M:%S %Z')

        return {
            'Date': dt,
            'X-OpenRosa-Version': '1.0',
            'X-OpenRosa-Accept-Content-Length': DEFAULT_CONTENT_LENGTH
        }

    def mobile_login(self, request, *args, **kwargs):        
        username = self.kwargs.get('username')
        #username = request.GET.get('username', '')
        password = request.GET.get('password', '')
        print username
        print password
        users = authenticate(username=username, password=password)
        if users is not None:
            return HttpResponse(json.dumps(self.mobile_login_response(username, password)),
                                content_type="application/json", status=200)
        else:
            return Response(password, headers=self.get_openrosa_headers(), status=401)
    def mobile_login_response(self, username, password):
        _psu_list = []
        user = get_object_or_404(User, username=username.lower())
        user_module_profile = UserModuleProfile.objects.get(user=user)
        #psu = user_module_profile.psu;
        #_psu_list.append(psu.name)
        # for psu in psus:
        #   psuList.append(psu)
        return {
            'username': username,
            'password': password,
            'role': 'Enumerator',
            #'PSU': _psu_list
        }
        # return dict(role='', PSU=psu)


    def get_renderers(self):
        if self.action and self.action == 'manifest':
            return [XFormManifestRenderer()]

        return super(XFormListApi, self).get_renderers()

    def filter_queryset(self, queryset):
        username = self.kwargs.get('username')
        #print '7777777777777777777777777777777777777777777777777777'
        #print username        
        formlist_user = get_object_or_404(User, username=username)
        content_user = get_object_or_404(User, username=username)
        if username is None and self.request.user.is_anonymous():
            # raises a permission denied exception, forces authentication
            self.permission_denied(self.request)

        if username is not None:
            profile = get_object_or_404(
                UserProfile, user__username=username.lower())

            if profile.require_auth and self.request.user.is_anonymous():
                # raises a permission denied exception, forces authentication
                self.permission_denied(self.request)
            else:
                xfct = ContentType.objects.get(app_label='logger', model='xform')
                xfs = content_user.userobjectpermission_set.filter(content_type=xfct)
                shared_forms_pks = list(set([xf.object_pk for xf in xfs]))
                queryset =  XForm.objects.filter(
                        pk__in=shared_forms_pks).select_related('user')  

                #print xforms              
                #queryset = queryset.filter(user=profile.user)

        if not self.request.user.is_anonymous():
            queryset = super(XFormListApi, self).filter_queryset(queryset)
        #print queryset
        return queryset

    def list(self, request, *args, **kwargs):
        self.object_list = self.filter_queryset(self.get_queryset())

        serializer = self.get_serializer(self.object_list, many=True)

        return Response(serializer.data, headers=self.get_openrosa_headers())

    def retrieve(self, request, *args, **kwargs):
        self.object = self.get_object()

        return Response(self.object.xml, headers=self.get_openrosa_headers())

    @action(methods=['GET'])
    def manifest(self, request, *args, **kwargs):
        self.object = self.get_object()
        object_list = MetaData.objects.filter(data_type='media',
                                              xform=self.object)
        context = self.get_serializer_context()
        serializer = XFormManifestSerializer(object_list, many=True,
                                             context=context)

        return Response(serializer.data, headers=self.get_openrosa_headers())

    @action(methods=['GET'])
    def media(self, request, *args, **kwargs):
        self.object = self.get_object()
        pk = kwargs.get('metadata')

        if not pk:
            raise Http404()

        meta_obj = get_object_or_404(
            MetaData, data_type='media', xform=self.object, pk=pk)

        return get_media_file_response(meta_obj)
