from rest_framework import serializers
from django.contrib.auth.models import User
from .models import RecruiterProfile, Department, ActiveRole, Workflow, ConversationTurn

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')

class RecruiterLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class RecruiterRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    company_name = serializers.CharField(write_only=True, required=True)
    phone_number = serializers.CharField(write_only=True, required=False, allow_null=True)
    bio = serializers.CharField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'first_name', 'last_name', 'company_name', 'phone_number', 'bio')
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': True},
            'password': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False}
        }

    def validate(self, data):
        if not data.get('company_name'):
            raise serializers.ValidationError({'company_name': 'This field is required.'})
        return data

    def create(self, validated_data):
        company_name = validated_data.pop('company_name')
        phone_number = validated_data.pop('phone_number', None)
        bio = validated_data.pop('bio', None)
        
        # Create user
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        
        # Create recruiter profile
        RecruiterProfile.objects.create(
            user=user,
            company_name=company_name,
            phone_number=phone_number,
            bio=bio
        )
        
        return user

class RecruiterProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = RecruiterProfile
        fields = (
            'id', 'user', 'company_name', 'phone_number', 'bio',
            'industry', 'website', 'company_size', 'founded', 'headquarters', 'company_description',
            'job_title', 'years_of_experience', 'linkedin_profile',
            'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')

class RecruiterProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    email = serializers.EmailField(source='user.email', required=False)

    class Meta:
        model = RecruiterProfile
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'bio', 'company_name')
        extra_kwargs = {
            'phone_number': {'required': False},
            'bio': {'required': False},
            'company_name': {'required': False}
        }

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user

        # Update user fields
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ('id', 'name', 'description', 'head_count', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['recruiter'] = self.context['request'].user.recruiterprofile
        return super().create(validated_data)

class ActiveRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActiveRole
        fields = ('id', 'title', 'department', 'level', 'status', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['recruiter'] = self.context['request'].user.recruiterprofile
        return super().create(validated_data)

class ConversationTurnSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationTurn
        fields = ('id', 'sender', 'message_content', 'timestamp')
        read_only_fields = ('timestamp',)

    def create(self, validated_data):
        workflow_id = self.context.get('workflow_id')
        if not workflow_id:
            raise serializers.ValidationError({'workflow': 'Workflow ID is required'})
        
        try:
            workflow = Workflow.objects.get(id=workflow_id)
            validated_data['workflow'] = workflow
            return super().create(validated_data)
        except Workflow.DoesNotExist:
            raise serializers.ValidationError({'workflow': 'Workflow not found'})

class WorkflowSerializer(serializers.ModelSerializer):
    conversation_turns = ConversationTurnSerializer(many=True, read_only=True)

    class Meta:
        model = Workflow
        fields = ('id', 'name', 'initial_user_request', 
                 'system_response_summary', 'conversation_turns', 
                 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['recruiter'] = self.context['request'].user.recruiterprofile
        return super().create(validated_data)