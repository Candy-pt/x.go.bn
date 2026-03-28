from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Sum, Case, When, F, DecimalField, Value
from django.utils import timezone
from datetime import datetime
from .models import Batch, InventoryTransaction
from django.db import transaction
from django.db.models.functions import Coalesce 
from .serializers import BatchSerializer, InventoryTransactionSerializer

class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all().order_by('-import_date')
    serializer_class = BatchSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['batch_code', 'product__name', 'supplier__name', 'note']
    ordering_fields = ['import_date', 'batch_code']
    ordering = ['-import_date']
    
   
    @action(detail=False, methods=['get'])
    def stock_report(self, request):
        queryset = Batch.objects.select_related('product', 'product__unit', 'supplier')

        p_type = request.query_params.get('product_type')
        if p_type:
            queryset = queryset.filter(product__product_type=p_type)

        batches = queryset.annotate(
            total_import=Coalesce(Sum(
                Case(When(transactions__transaction_type='IMPORT', then='transactions__quantity'), default=0, output_field=DecimalField())
            ), Value(0, output_field=DecimalField())),
            
            total_export=Coalesce(Sum(
                Case(When(transactions__transaction_type='EXPORT', then='transactions__quantity'), default=0, output_field=DecimalField())
            ), Value(0, output_field=DecimalField())),
            
            db_current_stock=F('total_import') - F('total_export')
        ).filter(db_current_stock__gt=0.01).order_by('import_date')  

        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        start = (page - 1) * page_size
        end = start + page_size

        paginated = batches[start:end]

        data = [
            {
                'id': b.id,
                'batch_code': b.batch_code,
                'product_name': b.product.name,
                'unit_name': b.product.unit.name,
                'supplier_name': b.supplier.name,               
                'current_stock': float(b.db_current_stock), 
                'import_date': b.import_date,
                'product_type': b.product.product_type
            }
            for b in paginated
        ]

        return Response({
            'results': data,
            'total': batches.count(),
            'page': page,
            'page_size': page_size
        })


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = InventoryTransaction.objects.select_related('batch', 'batch__product').all().order_by('-date')
    serializer_class = InventoryTransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    
    search_fields = ['batch__batch_code', 'batch__product__name', 'note', 'created_by__username']
    ordering_fields = ['date', 'quantity', 'transaction_type']
    ordering = ['-date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 1. Lấy các tham số 
        transaction_type = self.request.query_params.get('transaction_type')
        batch_id = self.request.query_params.get('batch')
        search_product = self.request.query_params.get('product') 
        start_date = self.request.query_params.get('start_date')  
        end_date = self.request.query_params.get('end_date')     
        
        # 2. Xử lý Lọc theo Loại và Batch 
        if transaction_type and transaction_type != 'Tất cả':
            queryset = queryset.filter(transaction_type=transaction_type)
        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)
            
        # 3. Xử lý Lọc theo Tên Sản Phẩm 
        # icontains: Tìm kiếm gần đúng, không phân biệt hoa/thường 
        if search_product:
            queryset = queryset.filter(batch__product__name__icontains=search_product)
            
        if start_date:
            try:
                queryset = queryset.filter(date__gte=start_date)
            except ValueError:
                pass 

        if end_date:
            try:
                end_datetime_str = f"{end_date} 23:59:59"
                end_datetime = datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M:%S")
                end_datetime_aware = timezone.make_aware(end_datetime) if timezone.is_naive(end_datetime) else end_datetime
                
                queryset = queryset.filter(date__lte=end_datetime_aware)
            except (ValueError, TypeError):
                pass

        return queryset
    
    def perform_create(self, serializer):
        user = getattr(self.request, 'user', None)
        with transaction.atomic():
            if user and getattr(user, 'is_authenticated', False):
                serializer.save(created_by=user)
            else:
                serializer.save()