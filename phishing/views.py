from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required

@login_required(login_url=reverse_lazy('login'))
def monitoreo(request):
    context = {}
    return render(request, 'monitoreo.html', context)
