#!/usr/bin/env python3
from models import Category, User, CategoryItem, Base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.orm.exc import UnmappedInstanceError
from sqlalchemy import create_engine, asc
from sqlalchemy.ext.declarative import declarative_base
from flask import session as login_session
import random
import string
from flask_httpauth import HTTPBasicAuth
import requests
from flask import make_response
import json
import httplib2
from oauth2client.client import FlowExchangeError
from oauth2client.client import flow_from_clientsecrets
from flask import Flask, render_template, jsonify
from flask import request, redirect, url_for, abort, flash, g
auth = HTTPBasicAuth()
engine = create_engine('sqlite:///catalog.db',
                       connect_args={'check_same_thread': False})

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item Catalog Application"


def CreateUser(login_session):
    newUSer = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUSer)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except FlowExchangeError:
        return None

# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)
    # return "The current session state is %s" % login_session['state']


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = CreateUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '  # noqa
    flash("you are now logged in as %s" % login_session['username'])
    print("done!")
    return output


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print('Access Token is None')
        response = make_response(json.dumps(
            'Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print('In gdisconnect access token is %s', access_token)
    print('User name is: ')
    print(login_session['username'])
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']  # noqa
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print('result is ')
    print(result)
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        allcategory = session.query(Category).all()
        return render_template('publicCategory.html', categories=allcategory)
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/categoryJson/', methods=['GET'])
def showAllCategoriesJson():
    allcategory = session.query(Category).all()
    return jsonify(Categories=[p.serialize for p in allcategory])


@app.route('/', methods=['GET'])
@app.route('/category/')
def showAllCategories():
    allcategory = session.query(Category).all()
    if 'username' not in login_session:
        return render_template('publicCategory.html', categories=allcategory)
    else:
        return render_template('categories.html', categories=allcategory)


@app.route('/category/new/', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newCategory = Category(category_name=request.form['name'],
                               user_id=login_session['user_id'])
        session.add(newCategory)
        flash('New Category %s Successfully Created' %
              newCategory.category_name)
        session.commit()
        return redirect(url_for('showAllCategories'))
    else:
        return render_template('newcategory.html')


@app.route('/category/<int:category_id>/', methods=['GET', 'POST'])
def showCategoryItems(category_id):
    selected_category = session.query(Category).filter_by(
        category_id=category_id).first()
    allcategoryItems = session.query(
        CategoryItem).filter_by(item_id=category_id).all()
    creator = getUserInfo(selected_category.user_id)
    if ('username' not in login_session or
            creator.id != login_session['user_id']):
        return render_template(
            'publicCategoryItem.html',
            categoryitems=allcategoryItems,
            category_name=selected_category.category_name,
            category_id=selected_category.category_id,
            creator=creator)
    else:
        return render_template(
            'categoryItems.html',
            categoryitems=allcategoryItems,
            category_name=selected_category.category_name,
            category_id=selected_category.category_id,
            creator=creator)


@app.route('/category/<int:category_id>/new/', methods=['GET', 'POST'])
def addnewitem(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    selected_category = session.query(
        Category).filter_by(category_id=category_id).one()
    if selected_category.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to add new item. Please create your own cateory in order to proceed.');}</script><body onload='myFunction()''>"  # noqa

    if request.method == 'POST':
        newCategoryItem = CategoryItem(
            title=request.form['title'],
            description=request.form['description'],
            item_id=category_id,
            user_id=login_session['user_id'])
        session.add(newCategoryItem)
        session.commit()
        flash('New category Item:%s Successfully Created' %
              (newCategoryItem.title))
        return redirect(
            url_for(
                'showCategoryItems',
                category_id=selected_category.category_id))
    else:
        return render_template(
            'newcategoryitem.html',
            category_id=selected_category.category_id,
            category_name=selected_category.category_name)


@app.route('/category/<int:category_id>/edit/', methods=['GET', 'POST'])
def editCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    editcategory = session.query(Category).filter_by(
        category_id=category_id).one()
    if editcategory.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this category. Please create your own cateory in order to edit.');}</script><body onload='myFunction()''>"  # noqa
    if request.method == 'POST':
        if request.form['name']:
            editcategory.category_name = request.form['name']
            flash('Category Successfully Edited %s' %
                  editcategory.category_name)
            return redirect(
                url_for(
                    'showCategoryItems',
                    category_id=editcategory.category_id))
    else:
        return render_template('editcategory.html', category=editcategory)


@app.route('/category/<int:category_id>/delete/', methods=['GET', 'POST'])
def deleteCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    deletecategory = session.query(Category).filter_by(
        category_id=category_id).first()
    if deletecategory.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to delete this category. Please create your own cateory in order to delete.');}</script><body onload='myFunction()''>"  # noqa
    if request.method == 'POST':
        session.delete(deletecategory)
        session.query(CategoryItem).filter_by(item_id=category_id).delete()
        flash('%s Successfully Deleted' % deletecategory.category_name)
        session.commit()
        return redirect(url_for('showAllCategories'))
    else:
        return render_template('deletecategory.html', category=deletecategory)


@app.route('/category/<int:category_id>/<int:id>/', methods=['GET', 'POST'])
def showItemDetails(category_id, id):
    selectedItem = session.query(CategoryItem).filter_by(id=id).one()
    selectedCategory = session.query(Category).filter_by(
        category_id=category_id).one()
    if request.method == 'POST':
        if 'username' not in login_session:
            return redirect('/login')
        if request.form['title']:
            selectedItem.title = request.form['title']
        if request.form['description']:
            selectedItem.description = request.form['description']
        return redirect(
            url_for(
                'showCategoryItems',
                category_id=selectedCategory.category_id))
    else:
        return render_template(
            'viewcategoryitemdetails.html',
            category=selectedCategory,
            category_item=selectedItem)


@app.route(
    '/category/<int:category_id>/<int:id>/delete/',
    methods=[
        'GET',
        'POST'])
def deleteCategoryItem(category_id, id):
    if 'username' not in login_session:
        return redirect('/login')
    deletecategoryItem = session.query(CategoryItem).filter_by(id=id).one()
    session.delete(deletecategoryItem)
    session.commit()
    return redirect(url_for('showAllCategories'))


@app.route(
    '/category/<int:category_id>/<int:id>/edit/',
    methods=[
        'GET',
        'POST'])
def editCategoryItem(category_id, id):
    selected_category = session.query(Category).filter_by(
        category_id=category_id).first()
    selected_categoryItem = session.query(CategoryItem).filter_by(id=id).one()
    if request.method == 'POST':
        selected_categoryItem.title = request.form['title']
        selected_categoryItem.description = request.form['description']
        flash('Item Successfully Edited')
        return redirect(url_for('showCategoryItems', category_id=category_id))
    else:
        return render_template(
            'editCategoryItem.html',
            categoryitems=selected_categoryItem,
            category_name=selected_category.category_name,
            category_id=selected_category.category_id)


if __name__ == '__main__':
    app.secret_key = 'uLPC3gTecbulKeeQNrO7asVx'
    app.run(host='0.0.0.0', port=8000)
