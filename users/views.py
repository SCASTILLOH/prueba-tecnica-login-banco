from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from .models import *
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.utils import timezone
from django.db.models.functions import Coalesce
from django.db.models import Sum
from .forms import LoginForm
from datetime import datetime
from .utils import format_number


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            rut = form.cleaned_data['rut']
            password = form.cleaned_data['password']

            user = authenticate(request, rut=rut, password=password)

            if user and user.estado == 'bloqueado':
                messages.error(
                    request, f'Usuario bloqueado, contacte a su administrador')
                return render(request, 'login.html', {'form': form})

            if user is not None:
                login(request, user)
                user.estado = 'activo'
                user.intentos_fallidos = 0
                user.save()
                return redirect('/')
            else:
                try:
                    user = UserAccount.objects.get(rut=rut)

                    user.intentos_fallidos += 1
                    if user.intentos_fallidos >= 3:
                        user.estado = 'bloqueado'
                        messages.error(
                            request, f'Demasiados intentos fallidos, contacte a su administrador')
                    else:
                        messages.error(
                            request, f'Los datos ingresados no son correctos. Recuerda que al tercer intento fallido tu clave será bloqueada. Por favor intenta nuevamente.')
                    user.save()
                except UserAccount.DoesNotExist:
                    messages.error(request, 'El usuario no existe')

            print('user data: ', UserAccount.objects.filter(rut=rut).values())
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


@login_required(login_url='/login/')
def home_view(request):

    user_data = UserAccount.objects.filter(rut=request.user.rut).first()

    total_abonos_sin_ret = Abonos.objects.filter(cuenta=user_data, retencion=False).aggregate(
        total=Coalesce(Sum('monto'), 0))['total']

    total_abonos_con_ret = Abonos.objects.filter(cuenta=user_data, retencion=True).aggregate(
        total=Coalesce(Sum('monto'), 0))['total']

    total_cargos = Cargos.objects.filter(cuenta=user_data).aggregate(
        total=Coalesce(Sum('monto'), 0))['total']

    total_abonos = total_abonos_sin_ret + total_abonos_con_ret

    saldo_inicial = user_data.saldo_inicial

    fecha_actual = datetime.now()
    fecha_formateada = fecha_actual.strftime("%d/%m/%Y %H:%Mhrs")

    context = {
        'user': user_data,
        'fecha': fecha_formateada,
        'total_abonos': format_number(total_abonos),
        'total_abonos_con_ret': format_number(total_abonos_con_ret),
        'total_cargos': format_number(total_cargos),
        'saldo_linea_credito': format_number(user_data.saldo_linea_credito),
        'saldo_disponible': format_number(user_data.saldo_disponible),
        'saldo_contable': format_number(user_data.saldo_contable),
        'sobregirado': bool(user_data.saldo_disponible < 0),
    }

    return render(request, 'home.html', context)


def logout_view(request):
    logout(request)
    return redirect('login')
