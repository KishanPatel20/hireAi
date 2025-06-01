from rest_framework.permissions import BasePermission

class IsRecruiter(BasePermission):
    def has_permission(self, request, view):
        return hasattr(request.user, 'recruiterprofile')

class IsOwnerOfDepartment(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.recruiter.user == request.user

class IsOwnerOfActiveRole(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.recruiter.user == request.user

class IsOwnerOfWorkflow(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.recruiter.user == request.user