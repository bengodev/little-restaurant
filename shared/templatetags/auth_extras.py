from django import template


register = template.Library()


@register.filter()
def has_group(user, group_name):
    """Return True if the user is in the specified group."""
    return user.groups.filter(name=group_name).exists()


@register.filter()
def has_any_groups(user, group_names):
    """Check if user belongs to any of the given groups (comma-separated)."""
    if not user.is_authenticated:
        return False
    group_list = [name.strip() for name in group_names.split(',')]
    return user.groups.filter(name__in=group_list).exists()


@register.filter
def is_admin(user):
    """Check if user is superuser or in Admin group"""
    if not user.is_authenticated:
        return False
    return user.is_superuser or has_group(user, 'Admins')


'''
Uses example:

{% if user|has_group:"Editors" %}

{% if user|has_any_groups:"Admins,Editors,Managers" %}

{% if user|is_admin %}
'''
