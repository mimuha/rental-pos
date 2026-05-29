from django import template

register = template.Library()


@register.filter
def has_delete_model_permission(user, opts):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if not opts:
        return False
    return user.has_perm(f"{opts.app_label}.delete_{opts.model_name}")

