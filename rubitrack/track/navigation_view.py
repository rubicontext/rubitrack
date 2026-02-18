from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def navigation_view(request):
    """
    Display a navigation page with links to all main features
    """
    return render(request, 'track/navigation.html')
