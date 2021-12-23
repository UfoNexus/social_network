from django.contrib import admin

from .models import CommentModel, Group, Post


class CommentInline(admin.TabularInline):
    model = CommentModel
    extra = 0


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'text',
        'pub_date',
        'author',
        'group'
    )
    list_editable = ('group',)
    search_fields = ('text',)
    list_filter = ('author', 'pub_date', 'group')
    inlines = (CommentInline,)
    empty_value_display = '-пусто-'


class PostInline(admin.TabularInline):
    model = Post
    extra = 0


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'title',
        'slug',
        'description'
    )
    search_fields = ('title', 'description')
    sortable_by = ('title',)
    inlines = (PostInline,)


@admin.register(CommentModel)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'text',
        'post',
        'author'
    )
    search_fields = ('text',)
    list_filter = ('post', 'author', 'created')
