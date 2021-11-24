from time import sleep

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django import forms

from ..models import Group, Post

User = get_user_model()


class TaskPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.new_group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Тестовое описание группы'
        )
        cls.one_post_group = Group.objects.create(
            title='Группа одного поста',
            slug='one_post_group',
            description='Тестовое описание группы'
        )
        cls.user = User.objects.create_user(username='TestUser')
        for i in range(14):
            Post.objects.create(
                text=f'Тестовый пост {i}',
                author=cls.user,
                group=cls.new_group
            )
            sleep(0.05)
        cls.templates_pages = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': 'test_group'}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': 'TestUser'}): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': '1'}): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': '1'}): 'posts/create_post.html'
        }

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_templates(self):
        for page, template in self.templates_pages.items():
            with self.subTest(reverse_name=page):
                response = self.authorized_client.get(page)
                self.assertTemplateUsed(response, template)

    def test_homepage(self):
        page = list(self.templates_pages.keys())[0]

        response = self.authorized_client.get(page)
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        post_author_0 = first_object.author.username
        post_group_0 = first_object.group.title
        self.assertEqual(post_text_0, 'Тестовый пост 13')
        self.assertEqual(post_author_0, 'TestUser')
        self.assertEqual(post_group_0, 'Тестовая группа')
        self.assertEqual(len(response.context['page_obj']), 10)

        response = self.authorized_client.get(page + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 4)

    def test_group_posts(self):
        page = list(self.templates_pages.keys())[1]

        response = self.authorized_client.get(page)
        self.assertEqual(response.context.get('group').title,
                         'Тестовая группа')
        self.assertEqual(response.context.get('group').description,
                         'Тестовое описание группы')
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        post_author_0 = first_object.author.username
        post_group_0 = first_object.group.title
        self.assertEqual(post_text_0, 'Тестовый пост 13')
        self.assertEqual(post_author_0, 'TestUser')
        self.assertEqual(post_group_0, 'Тестовая группа')
        self.assertEqual(len(response.context['page_obj']), 10)

        response = self.authorized_client.get(page + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 4)

    def test_profile(self):
        page = list(self.templates_pages.keys())[2]

        response = self.authorized_client.get(page)
        self.assertEqual(response.context.get('author').username, 'TestUser')
        self.assertEqual(response.context.get('amount'), 14)
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        post_author_0 = first_object.author.username
        post_group_0 = first_object.group.title
        self.assertEqual(post_text_0, 'Тестовый пост 13')
        self.assertEqual(post_author_0, 'TestUser')
        self.assertEqual(post_group_0, 'Тестовая группа')
        self.assertEqual(len(response.context['page_obj']), 10)

        response = self.authorized_client.get(page + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 4)

    def test_post_detail(self):
        page = list(self.templates_pages.keys())[3]

        response = self.authorized_client.get(page)
        self.assertEqual(response.context.get('post').text, 'Тестовый пост 0')
        self.assertEqual(response.context.get('post').author.username,
                         'TestUser')
        self.assertEqual(response.context.get('post').group.title,
                         'Тестовая группа')
        self.assertEqual(response.context.get('amount'), 14)
        self.assertTrue(response.context.get('correct_user'))

    def test_create_post(self):
        page = list(self.templates_pages.keys())[4]

        response = self.authorized_client.get(page)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_edit_post(self):
        page = list(self.templates_pages.keys())[5]

        response = self.authorized_client.get(page)
        self.assertEqual(response.context.get('post').text, 'Тестовый пост 0')
        self.assertTrue(response.context.get('is_edit'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_new_post_entity_check(self):
        new_post = Post.objects.create(
            text='Совсем новый пост',
            author=self.user,
            group=self.one_post_group
        )

        response = self.authorized_client.get(reverse('posts:index'))
        objects = response.context['page_obj']
        self.assertTrue(new_post in objects)

        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'one_post_group'})
        )
        objects = response.context['page_obj']
        self.assertTrue(new_post in objects)

        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test_group'})
        )
        objects = response.context['page_obj']
        self.assertFalse(new_post in objects)

        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'TestUser'})
        )
        objects = response.context['page_obj']
        self.assertTrue(new_post in objects)
