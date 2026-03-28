
from rest_framework import serializers
from .models import Unit, Partner, Product
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = '__all__'

class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source='unit.name', read_only=True)

    class Meta:
        model = Product
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255)
    password = serializers.CharField(max_length=128, write_only=True)
    
    def validate(self, data):
        from django.contrib.auth import authenticate
        user = authenticate(username=data['username'], password=data['password'])
        if user is None:
            raise serializers.ValidationError("Tên đăng nhập hoặc mật khẩu không đúng")
        data['user'] = user
        return data

class RegisterSerializer(serializers.ModelSerializer):
    # Thêm trường email nếu hệ thống của bạn cần, nếu không có thể bỏ qua
    email = serializers.EmailField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'email')
        # Đảm bảo password chỉ được ghi, không bao giờ trả về trong response
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Sử dụng create_user để mật khẩu được băm (hash) an toàn
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user