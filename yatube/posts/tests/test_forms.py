import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.new_groups = {}
        for i in range(2):
            index = i + 1
            cls.new_groups[index] = Group.objects.create(
                title=f'Тестовая группа {index}',
                slug=f'test_group{index}',
                description=f'Тестовое описание группы {index}'
            )
        cls.user = User.objects.create_user(username='TestUser')
        cls.new_post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post_auth(self):
        posts_count = Post.objects.count()
        required_group = self.new_groups[list(self.new_groups.keys())[0]]
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
        form_data = {
            'text': 'Тестовый текст из формы',
            'group': required_group.pk,
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response,
                             reverse('posts:profile',
                                     kwargs={'username': self.user.username})
                             )
        posts_amount = Post.objects.count()
        new_post = list(Post.objects.order_by('-pk'))[0]
        self.assertEqual(posts_amount, posts_count + 1)
        self.assertTrue(Post.objects.filter(
            pk=new_post.pk, image=f'posts/{uploaded.name}'
        ).exists())
        self.assertEqual(new_post.text, form_data['text'])
        self.assertEqual(new_post.group.pk, form_data['group'])

    def test_edit_post_auth(self):
        required_group = self.new_groups[list(self.new_groups.keys())[1]]
        form_data = {
            'text': 'Новый текст для поста',
            'group': required_group.pk
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.new_post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response,
                             reverse('posts:post_detail',
                                     kwargs={'post_id': self.new_post.pk})
                             )
        edited_post = Post.objects.get(pk=self.new_post.pk)
        self.assertEqual(edited_post.text, form_data['text'])
        self.assertEqual(edited_post.group.pk, form_data['group'])

    def test_create_post_guest(self):
        posts_count = Post.objects.count()
        required_group = self.new_groups[list(self.new_groups.keys())[0]]
        form_data = {
            'text': 'Тестовый текст из формы',
            'group': required_group.pk
        }
        response = self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response,
                             f'{reverse("users:login")}?next='
                             f'{reverse("posts:post_create")}'
                             )
        posts_amount = Post.objects.count()
        self.assertEqual(posts_amount, posts_count)

    def test_edit_post_guest(self):
        required_group = self.new_groups[list(self.new_groups.keys())[1]]
        form_data = {
            'text': 'Новый текст для поста',
            'group': required_group.pk
        }
        response = self.client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.new_post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, '{}?next={}'.format(
            reverse("users:login"),
            reverse("posts:post_edit", kwargs={"post_id": self.new_post.pk})
        ))
        edited_post = Post.objects.get(pk=self.new_post.pk)
        self.assertNotEqual(edited_post.text, form_data['text'])
        self.assertNotEqual(edited_post.group, required_group)
