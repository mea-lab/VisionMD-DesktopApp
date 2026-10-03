"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.http import JsonResponse, FileResponse
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path
from django.views.decorators.cache import never_cache
from app.views.get_stream_media import get_stream_media

@never_cache
def frontend_index(request):
    """Read the current build entry point, bypassing Django's template cache.

    Cached HTML can reference an obsolete player bundle after a local update.
    Hashed JS/CSS assets may remain cached; this small entry point must not.
    """
    return FileResponse(open(settings.BASE_DIR / 'dist' / 'index.html', 'rb'), content_type='text/html')

urlpatterns = [
    path('api/', include('app.urls')),
    path('admin/', admin.site.urls),
    path('media/<path:path>', get_stream_media),
]


urlpatterns += [
    re_path(r'^.*$', frontend_index),
]