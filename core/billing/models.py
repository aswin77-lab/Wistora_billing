from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.db.models import Sum

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('accountant', 'Accountant'),
    )
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='accountant')

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Customer(models.Model):
    TYPE_CHOICES = (
        ('student', 'STUDENT'), 
        ('client', 'CLIENT')
    )
    customer_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='student')
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    course_or_service = models.CharField(max_length=255)
    fees = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    college_name = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.full_name


class Invoice(models.Model):
    STATUS_CHOICES = (
        ('UNPAID', 'UNPAID'),
        ('PARTIAL', 'PARTIALLY PAID'),
        ('PAID', 'PAID'),
    )
    
    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
    issue_date = models.DateField(default=timezone.now)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_applied = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='UNPAID')

    def save(self, *args, **kwargs):
        # 1. Automatically generate the custom sequential invoice number if not set
        if not self.invoice_number:
            year = timezone.now().year
            last_inv = Invoice.objects.filter(invoice_number__contains=f"INV-{year}").order_by('-id').first()
            if last_inv:
                try:
                    last_num = int(last_inv.invoice_number.split('-')[-1])
                    new_num = str(last_num + 1).zfill(3)
                except (ValueError, IndexError):
                    new_num = "001"
            else:
                new_num = "001"
            self.invoice_number = f"INV-{year}-{new_num}"
            
        super().save(*args, **kwargs)

    def update_status(self):
        """
        Forces a non-cached query lookup from the database to aggregate all payments 
        associated with this invoice instance, transitioning ledger states safely.
        """
        # Clear prefetch memory layers if present to bypass local variable reuse
        if hasattr(self, '_prefetched_objects_cache'):
            self._prefetched_objects_cache.clear()

        # Query straight from the base database engine manager using our explicit primary key
        db_aggregation = Invoice.objects.get(pk=self.pk).payments.aggregate(total=Sum('amount'))
        total_paid = db_aggregation['total'] or 0.00
        
        # Cast fields safely to float values for bulletproof mathematical checks
        current_paid = float(total_paid)
        target_total = float(self.grand_total)

        if current_paid >= target_total:
            self.status = 'PAID'
        elif current_paid > 0:
            self.status = 'PARTIAL'
        else:
            self.status = 'UNPAID'
            
        # Write ONLY the status flag instantly to prevent recursive loops on standard save signals
        self.save(update_fields=['status'])

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.full_name} (₹{self.grand_total})"


class Payment(models.Model):
    receipt_id = models.CharField(max_length=50, unique=True, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, default='UPI')
    payment_date = models.DateField(default=timezone.now)

    def save(self, *args, **kwargs):
        # 1. Automatically generate receipt tracking sequences sequentially
        if not self.receipt_id:
            last_pay = Payment.objects.order_by('-id').first()
            if last_pay and last_pay.receipt_id:
                try:
                    new_id = int(last_pay.receipt_id.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    new_id = 1
            else:
                new_id = 1
            self.receipt_id = f"PAY-{str(new_id).zfill(3)}"
            
        super().save(*args, **kwargs)