from django import template
import os

register = template.Library()

@register.filter
def split(value, arg):
    """
    Split a string by the specified delimiter
    Usage: {{ value|split:"/" }}
    """
    return value.split(arg)

@register.filter
def filename(value):
    """Returns the filename from a file path"""
    return os.path.basename(value)

@register.filter
def get_file_extension(filename):
    return os.path.splitext(filename)[1][1:].upper()