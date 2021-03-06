from flask import request, redirect, url_for, render_template, flash
from ...helpers import admin_required
from ... import db
from ...forms import PostForm, CategoryForm
from ...models import Post, Tag, Category, Settings
from sqlalchemy import or_
from . import admin


@admin.route('/blog')
@admin_required
def blog():
    posts_count = Post.query.filter_by(_type='article').count()
    cates_count = Category.query.count()
    tags_count = Tag.query.count()
    sets = Settings.query.get(1)
    return render_template('admin/blog.html',
                           title='博客管理',
                           sets=sets,
                           posts_count=posts_count,
                           cates_count=cates_count,
                           tags_count=tags_count)


# below is about post
@admin.route('/blog/post', methods=['GET', 'POST'])
@admin_required
def new_post():
    form = PostForm()

    if form.validate_on_submit():
        p = Post()
        category_id = request.form.get('category', 1)
        cate = Category.query.get(category_id)
        tags = form.tags.data.strip()
        if form.publish.data:
            Post.publish(
                post=p,
                title=form.title.data,
                content=form.content.data,
                public=form.publicity.data,
                commendable=form.commendable.data,
                category=cate,
                tags=tags
            )
            return redirect(url_for('blog.post', post_link=p.link))
        elif form.save.data:
            Post.save(
                post=p,
                title=form.title.data,
                content=form.content.data,
                public=form.publicity.data,
                commendable=form.commendable.data,
                category=cate,
                tags=tags
            )
            return redirect(url_for('admin.edit_post', post_link=p.link, post_version="main"))
    cates = Category.query.filter_by(_level=0).order_by(Category._order.asc()).all()
    return render_template("admin/new_post.html",
                           form=form,
                           title='书写文章',
                           categories=cates)


@admin.route('/blog/post/<path:post_link>/<post_version>', methods=['GET', 'POST'])
@admin_required
def edit_post(post_link, post_version):
    """post_version用于获取文章的版本
       'main' 表示获取已发布的文章或者未发布的新文章本身
       'draft' 表示获取已发布文章的修改稿
    """
    p = Post.query.filter_by(_link=post_link).order_by(Post._publish_date.asc()).first()
    form = PostForm()
    form.post_id.data = p.id

    if post_version == "draft":
        old_p = p
        p = p.draft
        if p is None:
            return redirect(url_for('admin.edit_post', post_link=old_p.link, post_version='main'))
    elif post_version != "main":
        return redirect(url_for("admin.edit_post", post_link=p.link, post_version="main"))

    if form.validate_on_submit():
        category_id = request.form.get('category', 1)
        new_cate = Category.query.get(category_id)
        tags = form.tags.data.strip()

        if form.save.data:
            Post.save(post=p,
                      category=new_cate,
                      tags=tags,
                      title=form.title.data,
                      content=form.content.data,
                      commendable=form.commendable.data,
                      public=form.publicity.data)
            return redirect(url_for('admin.edit_post', post_link=p.link, post_version='draft'))

        elif form.publish.data:
            Post.publish(post=p,
                         category=new_cate,
                         tags=tags,
                         title=form.title.data,
                         content=form.content.data,
                         commendable=form.commendable.data,
                         public=form.publicity.data)
            return redirect(url_for('blog.post', post_link=p.link))

    form.title.data = p.title
    form.content.data = p.content
    form.tags.data = p._tags if p._tags else None
    form.commendable.data = p.commendable
    form.publicity.data = p.public
    cates = Category.query.filter_by(_level=0).order_by(Category._order.asc()).all()
    return render_template("admin/new_post.html",
                           form=form, post=p,
                           categories=cates,
                           title="编辑文章")


@admin.route('/blog/posts', methods=['GET', 'POST'])
@admin_required
def manage_posts():
    category = request.args.get('category')
    status = request.args.get('status')
    publicity = request.args.get('publicity')
    commendable = request.args.get('commendable')
    tag = request.args.get('tag')
    query = Post.query.filter_by(_main_id=None)
    if category:
        category = Category.query.filter_by(_name=category).first()
        if category:
            query = query.filter(or_(Post._category.like(category.link),
                                     Post._category.like(category.link + '/%')))
    if tag:
        if tag == ',':
            query = query.filter(or_((Post._tags == ''),
                                     Post._tags == None))
        else:
            query = query.filter(or_(Post._tags.like(tag + ',%'),
                                     Post._tags.like('%,' + tag),
                                     Post._tags.like(tag),
                                     Post._tags.like('%,' + tag + ',%')))
    if publicity:
        if publicity == 'True':
            query = query.filter_by(_public=True)
        elif publicity == 'False':
            query = query.filter_by(_public=False)
    if commendable:
        if commendable == 'On':
            query = query.filter_by(_commendable=True)
        elif commendable == 'Off':
            query = query.filter_by(_commendable=False)
    if status:
        if status == 'Article':
            query = query.filter_by(_type='article', draft=None)
        elif status == 'Draft':
            query = query.filter_by(_type='draft')
        elif status == 'Saved':
            query = query.filter(Post.draft != None)

    query = query.order_by(Post._publish_date.desc())
    if query.count() <= 10:
        posts = query.all()
        pagination = None
    else:
        page = request.args.get('page', 1, type=int)
        pagination = query.paginate(
            page=page, error_out=False, per_page=10
        )
        posts = pagination.items
    categories = Category.query.filter_by(_level=0).all()
    tags = Tag.query.all()
    return render_template('admin/post.html',
                           title='管理文章',
                           posts=posts, tags=tags,
                           categories=categories,
                           pagination=pagination,
                           )


@admin.route('/blog/post-display', methods=['GET', 'POST'])
@admin_required
def manage_display_style():
    sets = Settings.query.get(1)
    sets.show_abstract = not sets.show_abstract
    return redirect(url_for('admin.blog'))


# below is about comment
@admin.route('/blog/comment', methods=['GET', 'POST'])
@admin_required
def manage_comment():
    sets = Settings.query.get(1)
    sets.enable_post_comment = not sets.enable_post_comment
    return redirect(url_for('admin.blog'))


# below is about category
@admin.route('/blog/new-category', methods=['GET', 'POST'])
@admin_required
def new_category():
    form = CategoryForm()
    if form.validate_on_submit():
        if '/' in form.name.data:
            flash('分类名中不能包含"/"')
            return redirect(url_for('admin.new_category'))
        name = form.name.data
        order = form.order.data
        try:
            parent_id = request.form.get('parent')
            parent = Category.query.get(parent_id)
        except KeyError:
            parent = None
        cate = Category(name=name, order=order)
        cate.parent = parent
        db.session.add(cate)
        if parent:
            return redirect(url_for('admin.manage_category', category_link=cate.parent.link))
        else:
            return redirect(url_for('admin.manage_categories'))
    categories = Category.query.filter_by(_level=0).all()
    return render_template('admin/new_category.html',
                           title='新建分类',
                           form=form,
                           categories=categories)


@admin.route('/blog/edit-category/<path:category_link>', methods=['GET', 'POST'])
@admin_required
def edit_category(category_link):
    form = CategoryForm()
    cate = Category.query.filter_by(_link=category_link).first()
    form.cate_id.data = cate.id
    if form.validate_on_submit():
        name = form.name.data
        order = form.order.data
        try:
            parent_id = request.form.get('parent')
            parent = Category.query.get(parent_id)
        except KeyError:
            parent = None
        cate.name = name
        cate.order = order
        cate.parent = parent
        if parent:
            return redirect(url_for('admin.manage_category', category_link=cate.parent.link))
        else:
            return redirect(url_for('admin.manage_categories'))
    form.name.data = cate.name
    form.order.data = cate.order
    categories = Category.query.filter_by(_level=0).all()
    return render_template('admin/new_category.html',
                           title='编辑分类',
                           form=form,
                           category=cate,
                           categories=categories)


@admin.route('/blog/category', methods=['GET', 'POST'])
@admin_required
def manage_categories():
    categories = Category.query.filter_by(_level=0).order_by(Category._order.asc()).all()
    return render_template('admin/category.html',
                           title='管理分类',
                           categories=categories)


@admin.route('/blog/category/<path:category_link>', methods=['GET', 'POST'])
@admin_required
def manage_category(category_link):
    category = Category.query.filter_by(_link=category_link).first()
    categories = category.children.order_by(Category._order.asc()).all()
    return render_template('admin/category.html',
                           title='管理分类',
                           category=category,
                           categories=categories)


# below is about tag
@admin.route('/blog/tag', methods=['GET', 'POST'])
@admin_required
def manage_tags():
    query = Tag.query
    if query.count() <= 15:
        tags = query.all()
        pagination = None
    else:
        page = request.args.get('page', 1, int)
        pagination = query.paginate(page=page, per_page=15, error_out=False)
        tags = pagination.items
    return render_template('admin/tag.html',
                           title='管理标签',
                           pagination=pagination,
                           tags=tags)
