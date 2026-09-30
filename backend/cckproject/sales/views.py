from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from users.permisions import HasCompany
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.template.loader import render_to_string
from django.db.models import Prefetch
from django.http import HttpResponse
from weasyprint import HTML
import traceback
from rest_framework.exceptions import ValidationError

from .models import Sale, SaleItem, StockMovement, Payment, Customer
from .serializers import (
    CreateSaleSerializer, SaleSerializer, StockMovementSerializer,
    SaleItemReadSerializer, UpdateSerializer, PaymentInputSerializer, 
    PaymentSerializer, CustomerSerializer, SaleWithPaymentsSerializer
)
from users.authentication import CustomJWTAuthentication
from .services import SaleService, ReceiptCreateService


class CreateSaleView(ModelViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CreateSaleSerializer

    def get_queryset(self):
        return Sale.objects.filter(company=self.request.user.company).all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        sale = SaleService.create_sale(data=serializer.validated_data, company=request.user.company)
        
        response =  Response(
            SaleSerializer(sale).data,
            status=status.HTTP_201_CREATED
        )
        print("response data:", response.data)
        return response

    @action(detail=True, methods=['post'], url_path='pay')
    def pay(self, request, pk=None):
       
        sale = self.get_object()
        uuid = request.META.get('HTTP_X_UUID')
        
        payment = PaymentInputSerializer(data=request.data)
        payment.is_valid(raise_exception=True)
      
        result = SaleService.complete_payment(data=payment.validated_data, instance=sale, key=uuid)
        
        return Response(PaymentSerializer(result).data)

    @action(detail=True, methods=["post"], url_path="receipt")
    def receipt(self, request, pk=None):
        sale = self.get_object()

        uuid = request.headers.get("X-UUID")
        print("before payment", uuid)
        payment = sale.payments.order_by("-created_at").first()
        print("payment", payment)
        if payment is None:
            receipt = ReceiptCreateService.generate_no_payment_receipt(sale=sale, key=uuid)
            print("receipt", receipt)
        else:
            receipt = ReceiptCreateService.generate_receipt(
                sale=sale,
                payment=payment,
                key=uuid,
            )

        context = {
            "company": sale.company,
            "sale": sale,
            "customer": sale.customer,
            "receipt": receipt,

            "items": sale.sale_items.select_related(
                "variant",
                "variant__product",
            ).all(),

            "subtotal": sale.total_amount,
            "amount_paid": sale.total_payment,
            "outstanding": sale.outstanding_amount,
        }
        print("context", context)
        if payment is not None:
            context["payment"] = payment

        try:
            html = render_to_string(
                "receipts/sales_receipts.html",
                context,
            )
            print("html generated", html)
            pdf = HTML(
                string=html,
                base_url=request.build_absolute_uri("/"),
            ).write_pdf()

        except Exception as e:
            print("RECEIPT PDF ERROR:", repr(e))
    
            traceback.print_exc()
            return Response(
                {"detail": "Receipt PDF could not be generated!"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response = HttpResponse(
            pdf,
            content_type="application/pdf",
        )

        response["Content-Disposition"] = (
            'attachment; filename="sales_receipt.pdf"'
        )

        return response


class ListSaleView(ModelViewSet):
    permission_classes = [IsAuthenticated,HasCompany]
    queryset = Sale.objects.select_related("customer").prefetch_related("sale_items").all()
    serializer_class = SaleSerializer

    def get_queryset(self):
        param = self.request.query_params.get('status')
        if param:
            return super().get_queryset().filter(company=self.request.user.company, sale_status=param).exclude(sale_items__isnull=True).distinct()
        
        return super().get_queryset().filter(company=self.request.user.company).exclude(sale_items__isnull=True).distinct()

class DeleteSaleView(ModelViewSet):
    permission_classes = [IsAuthenticated,HasCompany]
    queryset = SaleItem.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(sale__company=self.request.user.company)

    def destroy(self, request, *args, **kwargs):
        sale_item = self.get_object()         
        SaleService.delete_item(item_id=sale_item.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PatchSaleView(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = SaleItem.objects.all()
    serializer_class = SaleItemReadSerializer
    
    def get_queryset(self):
        return super().get_queryset().filter(sale__company=self.request.user.company)
    
    def perform_update(self, serializer):
        SaleService.partial_update(instance=serializer.instance, data=serializer.validated_data)


class UpdateSaleView(ModelViewSet):
    permission_classes = [IsAuthenticated,HasCompany]
    queryset = Sale.objects.all()
    serializer_class = UpdateSerializer

    def get_queryset(self):
        return super().get_queryset().filter(company=self.request.user.company)
    
    def perform_create(self, serializer):
        SaleService.full_create(data=serializer.validated_data, company=self.request.user.company)
  

class StockMovementView(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = StockMovement.objects.select_related("variant", "variant__product")
    serializer_class = StockMovementSerializer

    def get_queryset(self):
        return super().get_queryset().filter(variant__product__category__company=self.request.user.company)
    

class CustomerView(ModelViewSet):
    permission_classes = [IsAuthenticated, HasCompany]
    serializer_class = CustomerSerializer
    
    def get_queryset(self):
        status = self.request.query_params.get("status")
        customer_id = self.kwargs.get("pk")

        sales_queryset = Sale.objects.all()

        if status:
            sales_queryset = sales_queryset.filter(
                sale_status=status
            )

        queryset = (
            Customer.objects
            .filter(company=self.request.user.company)
            .prefetch_related(
                Prefetch(
                    "sales",
                    queryset=sales_queryset,
                )
            )
        )

        if customer_id:
            queryset = queryset.filter(pk=customer_id)

        return queryset

class PaymentView(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SaleWithPaymentsSerializer

    def get_queryset(self):
        print("sale with refunds")
        return Sale.objects.filter(
            company=self.request.user.company
        ).prefetch_related("refunds")

    
