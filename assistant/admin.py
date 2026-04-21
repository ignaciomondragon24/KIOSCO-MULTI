"""
Admin configuration for the Assistant app.
"""
from django.contrib import admin
from .models import Conversation, Message, AssistantSettings, QueryLog


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['created_at', 'tokens_used']
    fields = ['role', 'content', 'created_at', 'tokens_used']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at', 'user']
    search_fields = ['title', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'role', 'short_content', 'created_at', 'tokens_used']
    list_filter = ['role', 'created_at']
    search_fields = ['content']
    readonly_fields = ['created_at']
    
    def short_content(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    short_content.short_description = 'Contenido'


@admin.register(AssistantSettings)
class AssistantSettingsAdmin(admin.ModelAdmin):
    list_display = ['id', 'model', 'is_enabled', 'max_tokens', 'temperature', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not AssistantSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'short_query', 'was_successful', 'tokens_used', 'response_time_ms', 'created_at']
    list_filter = ['was_successful', 'created_at', 'user']
    search_fields = ['query', 'user__username']
    readonly_fields = ['created_at']
    
    def short_query(self, obj):
        return obj.query[:80] + '...' if len(obj.query) > 80 else obj.query
    short_query.short_description = 'Consulta'
