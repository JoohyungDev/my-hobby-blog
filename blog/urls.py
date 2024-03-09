from django.urls import path
from . import views

urlpatterns = [
    path("", views.PostList.as_view(), name="post_list"),
    path("<int:pk>/", views.PostDetail.as_view()),
    path("category/<str:slug>/", views.category_page),
    path("tag/<str:slug>/", views.tag_page),
    path("create_post/", views.PostCreate.as_view()),
    path("update_post/<int:pk>", views.PostUpdate.as_view()),
    path("delete_post/<int:pk>", views.PostDelete.as_view(), name="post_delete"),
    path("search/<str:q>/", views.PostSearch.as_view()),
]
