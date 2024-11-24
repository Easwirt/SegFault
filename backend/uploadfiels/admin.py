from django.contrib import admin
from django.utils.html import format_html
from django.template.defaultfilters import filesizeformat
from .models import UserUpload


@admin.register(UserUpload)
class UserUploadAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'user_info', 'formatted_file_size',
                    'uploaded_at', 'file_download')
    list_filter = ('uploaded_at', 'user')
    search_fields = ('original_filename', 'user__username', 'user__email')
    readonly_fields = ('uploaded_at', 'file_size')
    date_hierarchy = 'uploaded_at'

    def user_info(self, obj):
        return format_html(
            '<span title="Email: {}">{}</span>',
            obj.user.email,
            obj.user.username
        )

    user_info.short_description = 'User'
    user_info.admin_order_field = 'user__username'

    def formatted_file_size(self, obj):
        return filesizeformat(obj.file_size)

    formatted_file_size.short_description = 'File Size'
    formatted_file_size.admin_order_field = 'file_size'

    def file_download(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">Download</a>',
                obj.file.url
            )
        return '-'

    file_download.short_description = 'Download'