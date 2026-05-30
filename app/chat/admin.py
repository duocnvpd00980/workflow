# chat/admin.py

from django.contrib import admin

from .models import (
    Conversation,
    ConversationMemory,
    Message,
)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "title",
        "is_archived",
        "last_message_at",
        "created_at",
    )

    list_filter = (
        "is_archived",
        "created_at",
    )

    search_fields = (
        "title",
        "user__email",
        "user__username",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "last_message_at",
    )

    ordering = ("-last_message_at",)

    fieldsets = (
        (
            "Conversation",
            {
                "fields": (
                    "id",
                    "user",
                    "title",
                    "system_prompt",
                    "is_archived",
                )
            },
        ),
        (
            "Metadata",
            {"fields": ("metadata",)},
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "last_message_at",
                )
            },
        ),
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation",
        "role",
        "status",
        "short_content",
        "created_at",
    )

    list_filter = (
        "role",
        "status",
        "created_at",
    )

    search_fields = (
        "content",
        "html",
        "conversation__title",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("created_at",)

    fieldsets = (
        (
            "Message",
            {
                "fields": (
                    "id",
                    "conversation",
                    "role",
                    "status",
                    "content",
                    "html",
                )
            },
        ),
        (
            "AI",
            {
                "fields": (
                    "node_name",
                    "model_name",
                    "token_input",
                    "token_output",
                )
            },
        ),
        (
            "Error",
            {"fields": ("error_message",)},
        ),
        (
            "Metadata",
            {"fields": ("metadata",)},
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def short_content(self, obj):
        return obj.content[:80]

    short_content.short_description = "Content"


@admin.register(ConversationMemory)
class ConversationMemoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation",
        "key",
        "created_at",
    )

    search_fields = ("key",)

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
