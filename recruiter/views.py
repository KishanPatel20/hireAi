from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db.models import Count
from .models import RecruiterProfile, Department, ActiveRole, Workflow, ConversationTurn
from .serializers import *

class IsRecruiter(permissions.BasePermission):
    def has_permission(self, request, view):
        return hasattr(request.user, 'recruiterprofile')

class IsOwnerOfDepartment(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.recruiter == request.user.recruiterprofile

class IsOwnerOfActiveRole(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.recruiter == request.user.recruiterprofile

class IsOwnerOfWorkflow(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.recruiter == request.user.recruiterprofile

class RecruiterProfileViewSet(viewsets.ModelViewSet):
    serializer_class = RecruiterProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]

    def get_queryset(self):
        return RecruiterProfile.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get', 'patch', 'post'])
    def me(self, request):
        if request.method == 'GET':
            profile = get_object_or_404(RecruiterProfile, user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        elif request.method == 'PATCH':
            profile = get_object_or_404(RecruiterProfile, user=request.user)
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        elif request.method == 'POST':
            # Only allow creation if profile does not exist
            if RecruiterProfile.objects.filter(user=request.user).exists():
                return Response({'error': 'Profile already exists for this user.'}, status=status.HTTP_400_BAD_REQUEST)
            data = request.data.copy()
            data['user'] = request.user.id
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def dashboard_overview(self, request):
        profile = get_object_or_404(RecruiterProfile, user=request.user)
        
        # Get counts for dashboard
        departments_count = Department.objects.filter(recruiter=profile).count()
        active_roles_count = ActiveRole.objects.filter(recruiter=profile).count()
        workflows_count = Workflow.objects.filter(recruiter=profile).count()
        
        return Response({
            'departments_count': departments_count,
            'active_roles_count': active_roles_count,
            'workflows_count': workflows_count,
            'profile': self.get_serializer(profile).data
        })

class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsRecruiter, IsOwnerOfDepartment]

    def get_queryset(self):
        return Department.objects.filter(recruiter=self.request.user.recruiterprofile)

    def perform_create(self, serializer):
        serializer.save(recruiter=self.request.user.recruiterprofile)

class ActiveRoleViewSet(viewsets.ModelViewSet):
    serializer_class = ActiveRoleSerializer
    permission_classes = [permissions.IsAuthenticated, IsRecruiter, IsOwnerOfActiveRole]

    def get_queryset(self):
        return ActiveRole.objects.filter(recruiter=self.request.user.recruiterprofile)

    def perform_create(self, serializer):
        serializer.save(recruiter=self.request.user.recruiterprofile)

class WorkflowViewSet(viewsets.ModelViewSet):
    serializer_class = WorkflowSerializer
    permission_classes = [permissions.IsAuthenticated, IsRecruiter, IsOwnerOfWorkflow]

    def get_queryset(self):
        return Workflow.objects.filter(recruiter=self.request.user.recruiterprofile)

    @action(detail=True, methods=['post'])
    def chat(self, request, pk=None):
        workflow = self.get_object()
        serializer = ConversationTurnSerializer(
            data=request.data,
            context={'workflow_id': pk}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def chat_history(self, request, pk=None):
        workflow = self.get_object()
        conversation_turns = workflow.conversationturn_set.all()
        serializer = ConversationTurnSerializer(conversation_turns, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def create_from_chat(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            workflow = serializer.save(recruiter=request.user.recruiterprofile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class RecruiterRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RecruiterRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'user': UserSerializer(user).data,
            'message': 'Recruiter registered successfully'
        }, status=status.HTTP_201_CREATED)

class RecruiterLoginView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RecruiterLoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        
        if user and hasattr(user, 'recruiterprofile'):
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data
            })
        return Response(
            {'error': 'Invalid credentials or user is not a recruiter'},
            status=status.HTTP_401_UNAUTHORIZED
        )

class RecruiterProfileView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    serializer_class = RecruiterProfileSerializer

    def get_object(self):
        return get_object_or_404(RecruiterProfile, user=self.request.user)

class RecruiterProfileUpdateView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    serializer_class = RecruiterProfileUpdateSerializer

    def get_object(self):
        return get_object_or_404(RecruiterProfile, user=self.request.user)

class ChangePasswordView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    serializer_class = ChangePasswordSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = self.get_object()
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'error': 'Invalid old password'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Delete the old token and create a new one
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        
        return Response({
            'message': 'Password updated successfully',
            'token': token.key
        })
