from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class TaskURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.new_group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Тестовое описание группы'
        )
        cls.user = User.objects.create_user(username='TestUser')
        Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.new_group
        )
        cls.user_for_post = User.objects.create_user(username='UserForPost')
        cls.post_for_test = Post.objects.create(
            text='Тестовый пост для проверки редактирования',
            author=cls.user_for_post
        )
        cls.templates_urls = {
            ('/', 'no_auth'): ('posts/index.html',
                               None),
            ('/group/test_group/', 'no_auth'): ('posts/group_list.html',
                                                None),
            ('/profile/TestUser/', 'no_auth'): ('posts/profile.html',
                                                None),
            ('/posts/1/', 'no_auth'): ('posts/post_detail.html',
                                       None),
            ('/posts/{}/edit/', 'auth'): ('posts/create_post.html',
                                          '/auth/login/'),
            ('/create/', 'auth'): ('posts/create_post.html',
                                   '/auth/login/')
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls_for_guest(self):
        for url, condition in self.templates_urls.keys():
            if condition == 'no_auth':
                with self.subTest(adress=url):
                    response = self.guest_client.get(url)
                    self.assertEqual(response.status_code, 200)
            if condition == 'auth':
                with self.subTest(adress=url):
                    response = self.guest_client.get(url.format('1'))
                    redirect = self.templates_urls[url, condition][1]
                    self.assertRedirects(response,
                                         f'{redirect}?next={url.format("1")}')

    def test_urls_for_auth(self):
        for url, condition in self.templates_urls.keys():
            if condition == 'auth':
                with self.subTest(adress=url):
                    if url == '/posts/{}/edit/':
                        for post in Post.objects.all():
                            index = post.pk
                            response = self.authorized_client.get(
                                url.format(index)
                            )
                            if self.user.username == post.author.username:
                                self.assertEqual(response.status_code, 200)
                            else:
                                self.assertRedirects(
                                    response, f'/posts/{index}/'
                                )
                    else:
                        response = self.authorized_client.get(url)
                        self.assertEqual(response.status_code, 200)

    def test_urls_templates(self):
        for url, template in self.templates_urls.items():
            address = url[0].format('1')
            with self.subTest(adress=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template[0])

    def test_404(self):
        response = self.guest_client.get('/no_page/')
        self.assertEqual(response.status_code, 404)
