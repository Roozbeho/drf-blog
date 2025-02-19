import logging

from django.conf import settings
from django.urls import resolve
from django.contrib.contenttypes.models import ContentType
from rest_framework.exceptions import ValidationError
from django.contrib.auth.models import AnonymousUser

from .models import ActivityLog

class ActivityLogMixin:
    log_message = None

    def _get_action_type(self, request):
        return self.action_type_mapper().get(f"{request.method.upper()}")
    
    def _build_log_messsage(self, request):
        return f'\
            User: {self._get_user_mixin(request)} \
            -- Action Type: {self._get_action_type(request)} \
            -- Path: {request.path} \
            -- Path Name: {resolve(request.path_info).url_name}'
    
    def get_log_message(self, request):
        return self.log_message or self._build_log_messsage(request)
    
    @staticmethod
    def action_type_mapper():
        return {
            'GET': ActivityLog.Activity_Type.READ,
            'RETRIEVE': ActivityLog.Activity_Type.READ,
            'POST': ActivityLog.Activity_Type.CREATE,
            'PUT': ActivityLog.Activity_Type.UPDATE,
            'PATCH': ActivityLog.Activity_Type.UPDATE,
            'DELETE': ActivityLog.Activity_Type.DELETE
        }
    
    @staticmethod
    def _get_user_mixin(request):
        return request.user if request.user.is_authenticated else AnonymousUser()
    
    def _get_content_type(self, data):
        try:
            data['content_type'] = ContentType.objects.get_for_model(self.get_queryset().model)
        except (AttributeError, ValidationError):
            data['content_type'] = None
        except AssertionError:
            pass
        return data
    
    def _get_object_id(self, data):
        try:
            data['object_id'] = self.get_object().pk
        except:
            pass
        return data
    
    def _write_log(self, request, response):
        user = self._get_user_mixin(request)

        if user:
            logging.info('Logging... ')
            data = {
                'user': request.user,
                'action_type': self._get_action_type(request),
                'status': (
                    ActivityLog.Action_Status.SUCCESS
                    if response.status_code < 400
                    else ActivityLog.Action_Status.FAILED
                    ),
                'remarks': self.get_log_message(request),
                }
            data = self._get_content_type(data)
            data = self._get_object_id(data)
            ActivityLog.objects.create(**data)
    
    def finalize_response(self, request, *args, **kwargs):
        response = super().finalize_response(request, *args, **kwargs)
        print(response)
        self._write_log(request, response)
        return response
    
