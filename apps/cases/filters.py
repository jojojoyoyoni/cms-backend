import django_filters
from django.db.models import Q
from .models import Case

class CaseFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_search', label='Search')
    
    class Meta:
        model = Case
        fields = ['status', 'priority']    # NO 'case' here!

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value) | 
            Q(case_number__icontains=value) | 
            Q(description__icontains=value)
        )