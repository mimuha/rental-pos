from django import template

register = template.Library()


@register.filter
def any_url_contains(models, path):
    for model in models:
        url = model.get('admin_url', '')
        if url and url in path:
            return True
    return False
