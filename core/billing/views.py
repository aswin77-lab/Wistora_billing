import csv
import os
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, Http404
from .models import Customer, Invoice, Payment, User


def ensure_default_admin_user():
    if User.objects.exists():
        return

    username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
    email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@wistora.local')
    password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123')

    user = User.objects.create_user(username=username, email=email, password=password, role='admin')
    user.is_staff = True
    user.is_superuser = True
    user.save()


def login_view(request):
    ensure_default_admin_user()

    if request.method == 'POST':
        username = request.POST.get('username') or request.POST.get('email') or ''
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')

        form = AuthenticationForm(request, data=request.POST)
        form.add_error(None, 'Invalid username or password.')
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


@login_required
def dashboard_view(request):
    # 1. Base Summary Cards Computations
    revenue_agg = Payment.objects.aggregate(total=Sum('amount'))['total']
    total_revenue = revenue_agg if revenue_agg is not None else 0.00

    total_invoiced = Invoice.objects.aggregate(total=Sum('grand_total'))['total'] or 0.00
    total_paid = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0.00
    outstanding_dues = max(0.00, float(total_invoiced) - float(total_paid))

    # 2. Dynamic 6-Month Timeline Query Engine
    today = datetime.today()
    six_months_ago = today - timedelta(days=180)
    
    # Query database and group payment sums by month using payment_date
    monthly_data = (
        Payment.objects.filter(payment_date__gte=six_months_ago)
        .annotate(month=TruncMonth('payment_date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )

    # Convert database result to a swift lookup dictionary map
    revenue_map = {item['month'].strftime('%b'): float(item['total'] or 0) for item in monthly_data}

    # Generate chronologically sequenced baseline dataset for the last 6 months
    chart_data = []
    for i in range(5, -1, -1):
        check_date = today - timedelta(days=i*30)
        m_name = check_date.strftime('%b')  # e.g., 'Jan', 'Feb', 'Mar'
        chart_data.append({
            'month': m_name,
            'amount': revenue_map.get(m_name, 0.00)
        })

    # Track maximum layout ceiling to dynamically calculate relative percentages
    max_amount = max([d['amount'] for d in chart_data]) if chart_data else 0
    
    # Apply rendering heights dynamically (with a 5% baseline minimum so empty metrics stay visible)
    for data in chart_data:
        if max_amount > 0:
            data['height'] = int(5 + (data['amount'] / max_amount) * 90)
        else:
            data['height'] = 5

    context = {
        'total_revenue': "{:.2f}".format(float(total_revenue)),
        'outstanding_dues': "{:.2f}".format(float(outstanding_dues)),
        'student_count': Customer.objects.filter(customer_type='student').count(),
        'pending_count': Invoice.objects.exclude(status='PAID').count(),
        'recent_activities': Invoice.objects.select_related('customer').order_by('-id')[:5],
        'chart_data': chart_data
    }
    return render(request, 'dashboard.html', context)


@login_required
def customers_view(request):
    # Role-based access control check
    if request.user.role != 'admin':
        return redirect('dashboard')
        
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # --- ACTION: CREATE CUSTOMER ---
        if action == 'create_customer':
            customer_type = request.POST.get('customer_type')
            
            Customer.objects.create(
                customer_type=customer_type,
                full_name=request.POST.get('full_name'),
                email=request.POST.get('email'),
                phone_number=request.POST.get('phone_number'),
                course_or_service=request.POST.get('course_or_service'),
                fees=request.POST.get('fees'),
                # Read these fields only if the input entity type is a student
                college_name=request.POST.get('college_name') if customer_type == 'student' else None,
                address=request.POST.get('address') if customer_type == 'student' else None
            )
            return redirect('customers')
            
        # --- ACTION: UPDATE CUSTOMER ---
        elif action == 'update_customer':
            customer_id = request.POST.get('customer_id')
            customer = get_object_or_404(Customer, id=customer_id)
            
            customer.full_name = request.POST.get('full_name')
            customer.email = request.POST.get('email')
            customer.phone_number = request.POST.get('phone_number')
            customer.course_or_service = request.POST.get('course_or_service')
            customer.fees = request.POST.get('fees')
            
            # Conditionally update extra details if the loaded entity is a student
            if customer.customer_type == 'student':
                customer.college_name = request.POST.get('college_name')
                customer.address = request.POST.get('address')
                
            customer.save()
            return redirect('customers')

    # Fetch complete customer dataset ordered by latest registration index
    customers = Customer.objects.all().order_by('-id')
    return render(request, 'customers.html', {'customers': customers})


@login_required
def invoices_view(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
        
    if request.method == 'POST' and request.POST.get('action') == 'create_invoice':
        customer = Customer.objects.get(id=int(request.POST.get('customer_id')))
        discount = float(request.POST.get('discount_applied') or 0)
        
        # TAX REMOVED: Grand total matches base fees minus the applied discount exactly
        grand_total = max(0, float(customer.fees) - discount)

        Invoice.objects.create(
            customer=customer,
            discount_applied=discount,
            tax_amount=0.00,
            grand_total=grand_total,
            status='UNPAID'
        )
        return redirect('invoices')

    invoices = Invoice.objects.select_related('customer').all().order_by('-id')
    customers = Customer.objects.all()
    return render(request, 'invoices.html', {'invoices': invoices, 'customers': customers})


@login_required
def payments_view(request):
    if request.method == 'POST':
        invoice_id = int(request.POST.get('invoice_id'))
        invoice = Invoice.objects.get(id=invoice_id)
        amount_paid = float(request.POST.get('amount') or 0)

        Payment.objects.create(
            invoice=invoice,
            amount=amount_paid,
            method=request.POST.get('method', 'UPI')
        )
        
        invoice.refresh_from_db()
        invoice.update_status()
            
        return redirect('payments')

    payments = Payment.objects.select_related('invoice__customer').all().order_by('-id')
    open_invoices = Invoice.objects.exclude(status='PAID').select_related('customer').order_by('-id')
    
    context = {
        'payments': payments,
        'open_invoices': open_invoices
    }
    return render(request, 'payments.html', context)


@login_required
def reports_view(request):
    action = request.GET.get('action')
    invoice_id = request.GET.get('invoice_id')
    payment_id = request.GET.get('payment_id')
    target_month = request.GET.get('month')  # format expected: 'YYYY-MM'

    # Build filtered queryset based on selected calendar limits
    payments_set = Payment.objects.select_related('invoice__customer').all().order_by('-id')
    if target_month:
        try:
            parsed_date = datetime.strptime(target_month, '%Y-%m')
            payments_set = payments_set.filter(
                payment_date__year=parsed_date.year, 
                payment_date__month=parsed_date.month
            )
        except ValueError:
            pass

    # --- 1. ACTION: Audit Trace Trail Preview ---
    if action == 'audit_trail' and invoice_id:
        try:
            target_invoice = Invoice.objects.select_related('customer').get(id=int(invoice_id))
            history_logs = Payment.objects.filter(invoice=target_invoice).order_by('payment_date')
            
            context = {
                'invoice': target_invoice,
                'history_logs': history_logs
            }
            return render(request, 'audit_trail_popup.html', context)
        except (Invoice.DoesNotExist, ValueError):
            raise Http404("Target invoice logging vector missing from database records.")

    # --- 2. ACTION: Export CSV Ledger (Includes College and Address parameters) ---
    if action == 'export_csv':
        response = HttpResponse(content_type='text/csv')
        filename = f"billing_ledger_{target_month}.csv" if target_month else "billing_master_ledger.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Payment ID', 'Invoice ID', 'Payer/Customer Name', 'Classification Type',
            'College Name', 'Physical Address', 'Total Invoiced (₹)', 'Amount Collected (₹)', 
            'Pending Amount (₹)', 'Payment Method', 'Transaction Date'
        ])
        
        for p in payments_set:
            customer = p.invoice.customer
            grand_total = float(p.invoice.grand_total or 0.00)
            
            # Extract student properties safely; substitute fallback placeholder if corporate client
            college_name = customer.college_name if customer.customer_type == 'student' and customer.college_name else "N/A"
            physical_address = customer.address if customer.customer_type == 'student' and customer.address else "N/A"
            
            # Dynamic lookups for aggregated historical payments per structural ledger
            total_paid_agg = Payment.objects.filter(invoice=p.invoice).aggregate(total=Sum('amount'))['total'] or 0.00
            pending_amount = max(0.00, grand_total - float(total_paid_agg))

            writer.writerow([
                p.id,
                p.invoice.id,
                customer.full_name,
                customer.get_customer_type_display(),
                college_name,
                physical_address,
                f"{grand_total:.2f}",
                f"{float(p.amount):.2f}",
                f"{pending_amount:.2f}",
                p.method,
                p.payment_date.strftime('%Y-%m-%d %H:%M')
            ])
        return response

    # --- 3. ACTION: Print / Download Frame Layout Sheet PDF ---
    if action == 'print_pdf':
        payment_aggregation = payments_set.aggregate(total=Sum('amount'))
        net_collection = payment_aggregation['total'] if payment_aggregation['total'] is not None else 0.00
        
        total_invoiced = Invoice.objects.aggregate(total=Sum('grand_total'))['total'] or 0.00
        outstanding_dues = max(0.00, float(total_invoiced) - float(net_collection))

        context = {
            'payments': payments_set,
            'net_collection': "{:.2f}".format(float(net_collection)),
            'outstanding_dues': "{:.2f}".format(float(outstanding_dues)),
            'print_mode': True
        }
        
        response = render(request, 'reports_print_frame.html', context)
        if request.GET.get('download') == 'true':
            filename = f"financial_report_{target_month}.html" if target_month else "financial_master_report.html"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    # --- 4. NEW ACTION: Print Individual Payment Bill/Receipt Voucher ---
    if action == 'print_receipt':
        if not payment_id:
            raise Http404("Missing identification parameter.")
            
        target_payment = get_object_or_404(
            Payment.objects.select_related('invoice__customer'), 
            id=int(payment_id)
        )
        
        # Calculate balance details dynamically for this specific person invoice status
        grand_total = float(target_payment.invoice.grand_total or 0.00)
        total_paid_agg = Payment.objects.filter(invoice=target_payment.invoice).aggregate(total=Sum('amount'))['total'] or 0.00
        pending_amount = max(0.00, grand_total - float(total_paid_agg))

        context = {
            'payment': target_payment,
            'pending_amount': "{:.2f}".format(pending_amount),
            'grand_total': "{:.2f}".format(grand_total),
        }
        return render(request, 'receipt_print_frame.html', context)

    # --- Baseline GET Request Handling & Dynamic Filter Collections ---
    available_months = (
        Payment.objects.annotate(month_slice=TruncMonth('payment_date'))
        .values_list('month_slice', flat=True)
        .distinct()
        .order_by('-month_slice')
    )
    month_options = [m.strftime('%Y-%m') for m in available_months if m]

    payment_aggregation = payments_set.aggregate(total=Sum('amount'))
    net_collection = payment_aggregation['total'] if payment_aggregation['total'] is not None else 0.00

    total_invoiced = Invoice.objects.aggregate(total=Sum('grand_total'))['total'] or 0.00
    outstanding_dues = max(0.00, float(total_invoiced) - float(net_collection))

    context = {
        'net_collection': "{:.2f}".format(float(net_collection)),
        'outstanding_dues': "{:.2f}".format(float(outstanding_dues)),
        'payments': payments_set,
        'month_options': month_options,
        'selected_month': target_month or ''
    }
    return render(request, 'reports.html', context)


def logout_view(request):
    logout(request)
    return redirect('login')