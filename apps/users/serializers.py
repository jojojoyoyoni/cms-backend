from rest_framework import serializers
from .models import User, Organization, Department

class OrganizationSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()
    case_count = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ['id', 'name', 'logo', 'logo_url', 'description', 'website','contact_email', 'contact_phone', 'address', 'country', 'is_active', 'created_at', 'user_count', 'case_count']
        read_only_fields = ['created_at', 'user_count', 'case_count', 'logo_url']

    def get_user_count(self, obj):
        return obj.users.count()

    def get_case_count(self, obj):
        return obj.cases.count()

    def get_logo_url(self, obj):
        request = self.context.get('request')
        if request and obj.logo:
            return request.build_absolute_uri(obj.logo.url)
        return None
    
class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'organization', 'department']
        depth = 1

class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role', 'organization', 'department']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user