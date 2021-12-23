import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms
from time import sleep

from ..models import CommentModel, Group, Post
from yatube.settings import POST_PAGINATOR

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
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
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.new_posts = {}
        for i in range(14):
            cls.new_posts[i + 1] = Post.objects.create(
                text=f'Тестовый пост {i + 1}',
                author=cls.user,
                group=cls.new_group,
                image=uploaded
            )
            sleep(0.05)
        cls.templates_pages = {
            reverse('posts:index'):
                'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': cls.new_group.slug}):
                'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': cls.user.username}):
                'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': list(cls.new_posts.keys())[0]}):
                'posts/post_detail.html',
            reverse('posts:post_create'):
                'posts/create_post.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': list(cls.new_posts.keys())[0]}):
                'posts/create_post.html'
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_templates(self):
        for page, template in self.templates_pages.items():
            with self.subTest(reverse_name=page):
                response = self.authorized_client.get(page)
                self.assertTemplateUsed(response, template)

    def paginator_page1_test(self, page):
        response = self.authorized_client.get(page)
        first_object = response.context['page_obj'][0]
        post_pk_0 = first_object.pk
        post_text_0 = first_object.text
        post_author_0 = first_object.author.username
        post_group_0 = first_object.group.title
        post_image_0 = first_object.image
        last_post = len(self.new_posts)
        self.assertEqual(post_pk_0, self.new_posts[last_post].pk)
        self.assertEqual(post_text_0, self.new_posts[last_post].text)
        self.assertEqual(post_author_0,
                         self.new_posts[last_post].author.username)
        self.assertEqual(post_group_0, self.new_posts[last_post].group.title)
        self.assertEqual(post_image_0, self.new_posts[last_post].image)
        self.assertEqual(len(response.context['page_obj']), POST_PAGINATOR)
        return response

    def paginator_page2_test(self, page):
        response = self.authorized_client.get(page + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 4)

    def test_homepage(self):
        page = list(self.templates_pages.keys())[0]
        self.paginator_page1_test(page)
        self.paginator_page2_test(page)

    def test_cache(self):
        page = list(self.templates_pages.keys())[0]
        response = self.authorized_client.get(page)
        content_before = response.content
        post = Post.objects.latest('pub_date')
        post.delete()
        response = self.authorized_client.get(page)
        content_now = response.content
        self.assertEqual(content_before, content_now)
        sleep(21)
        response = self.authorized_client.get(page)
        content_now = response.content
        self.assertNotEqual(content_before, content_now)

    def test_group_posts(self):
        page = list(self.templates_pages.keys())[1]

        response = self.paginator_page1_test(page)
        self.assertEqual(response.context.get('group').title,
                         self.new_group.title)
        self.assertEqual(response.context.get('group').description,
                         self.new_group.description)

        self.paginator_page2_test(page)

    def test_profile(self):
        page = list(self.templates_pages.keys())[2]

        response = self.paginator_page1_test(page)
        self.assertEqual(response.context.get('author').username,
                         self.user.username)
        self.assertEqual(response.context.get('amount'), 14)

        self.paginator_page2_test(page)

    def test_post_detail(self):
        page = list(self.templates_pages.keys())[3]

        response = self.authorized_client.get(page)
        first_post = self.new_posts[list(self.new_posts.keys())[0]]
        self.assertEqual(response.context.get('post').text,
                         first_post.text)
        self.assertEqual(response.context.get('post').author.username,
                         first_post.author.username)
        self.assertEqual(response.context.get('post').group.title,
                         first_post.group.title)
        self.assertEqual(response.context.get('post').image,
                         first_post.image)
        self.assertEqual(response.context.get('amount'),
                         len(self.new_posts))
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
        first_post = self.new_posts[list(self.new_posts.keys())[0]]
        self.assertEqual(response.context.get('post').text, first_post.text)
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
            reverse('posts:group_list',
                    kwargs={'slug': self.one_post_group.slug})
        )
        objects = response.context['page_obj']
        self.assertTrue(new_post in objects)

        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.new_group.slug})
        )
        objects = response.context['page_obj']
        self.assertFalse(new_post in objects)

        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        objects = response.context['page_obj']
        self.assertTrue(new_post in objects)

    def test_comment_in_post(self):
        post = self.new_posts.get(1)
        page = list(self.templates_pages.keys())[3]
        new_comment = CommentModel.objects.create(
            text='random',
            post=post,
            author=self.user
        )
        response = self.authorized_client.get(page)
        self.assertTrue(
            new_comment in response.context.get('post').comments.all()
        )

