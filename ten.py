import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workshop_core.settings')
django.setup()

from django.contrib.auth.models import User

# Thay đổi thông tin bạn muốn ở đây
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print("Đã tạo tài khoản Admin thành công!")