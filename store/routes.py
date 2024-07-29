#from crypt import methods
from flask_socketio import SocketIO, send, emit, join_room, leave_room
import re
from select import select
from flask import Flask, render_template, url_for, request, redirect, flash, Response, session
from flask_session import Session
from store import app, db, socketio
from store.models import Messages, Notification, User, Tools, Reviews, Flags, Address, Img, BorrowHistory, Chat
from store.forms import RegistrationForm, ReviewForm, ToolForm, EditToolForm, ProfileForm, MessagesForm, SearchForm, LoginForm, FlagForm, RentToolForm, ResetPassword, ChangePassword, ToolConditionForm
from flask_login import login_user, logout_user, login_required, current_user
from store.email import send_mail
from store.authentication import generate_confirmation_token, verify_confirmation_token
from werkzeug.utils import secure_filename
import base64
from post_codes.process_postcodes import postcodes
import requests
import googlemaps
import json
import random
from sqlalchemy import desc, or_


@socketio.on('join', namespace='/chat')
def join(data):
    other_user_id = data['other_user']
    chat = Chat.query.filter(Chat.user_1==current_user.id, Chat.user_2==other_user_id).first()
    chat2 = Chat.query.filter(Chat.user_1==other_user_id, Chat.user_2==current_user.id).first()

    if chat!=None:
        room = chat.room

    elif chat2!=None:
        room = chat2.room


    name = User.query.get_or_404(current_user.id).name
    join_room(room)
    emit('status', {'msg':  name + ' has entered the room.'}, room=room)

@socketio.on('text', namespace='/chat')
def text(message):
    other_user = User.query.get_or_404(message['other_user'])
    chat = Chat.query.filter(Chat.user_1==current_user.id, Chat.user_2==other_user.id).first()
    chat2 = Chat.query.filter(Chat.user_1==other_user.id, Chat.user_2==current_user.id).first()
    if chat!=None:
        room = chat.room

    elif chat2!=None:
        room = chat2.room

    username = User.query.get_or_404(current_user.id).name
    emit('message', {'msg': username + ': ' + message['msg']}, room=room)
    message = Messages(from_user=current_user.id, to_user=other_user.id, contents=message['msg'])


    subject = "New Message from " + current_user.name
    content = "You have a new message from "+current_user.name+"."
    notif = Notification(user_id=other_user.id, subject=subject, content=content)

    db.session.add(message)
    db.session.commit()
    db.session.add(notif)
    db.session.commit()


@app.route('/private_chat/<int:user_id>', methods=['POST', 'GET'])
@login_required
def private_chat(user_id):
    count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()

    messages=[]
    user1 = User.query.get_or_404(user_id)
    user2 = User.query.get_or_404(current_user.id)

    prev_messages = Messages.query.filter(or_(Messages.to_user==current_user.id, Messages.from_user==current_user.id)).distinct().order_by(Messages.datetime)

    for msg in prev_messages:
        if msg.from_user == user1.id or msg.to_user == user1.id:
            user_name = User.query.get_or_404(msg.from_user).name
            messages.append(user_name+': '+msg.contents)

    #session.clear()

    return render_template('private_chat.html', session=session, other_user=user1, current_user=user2, messages=messages, count=count)

@app.route('/create_room/<int:user_id>')
@login_required
def create_room(user_id):

    chat = Chat.query.filter(Chat.user_1==current_user.id, Chat.user_2==user_id).first()
    chat2 = Chat.query.filter(Chat.user_1==user_id, Chat.user_2==current_user.id).first()

    if chat!=None or chat2!=None:
        return redirect(url_for('chats'))

    username = User.query.get_or_404(current_user.id).name
    other_username = User.query.get_or_404(user_id).name
    room = username+other_username

    session['username'] = username
    session['room'] = room
    #session.clear()
    chat_init = Chat(user_1 = current_user.id, user_2 = user_id, room = room)
    db.session.add(chat_init)
    db.session.commit()
    return redirect(url_for('chats'))

@app.route('/chats')
@login_required
def chats():
    count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()
    user_info = []
    chat_users = Chat.query.filter(or_(Chat.user_1 == current_user.id, Chat.user_2 == current_user.id))

    for chat_user in chat_users:
        if chat_user.user_2==current_user.id and chat_user.user_1 not in user_info:
            user_info.append(chat_user.user_1)

        elif chat_user.user_1==current_user.id and chat_user.user_2 not in user_info:
            user_info.append(chat_user.user_2)

    users = User.query.filter(User.id.in_(user_info))

    return render_template('chats.html', chat_users=users, count=count)

@app.before_request
def before_request():
    if current_user.is_authenticated \
        and not current_user.confirmed \
        and request.endpoint in ['post_tool', 'edit_tool', 'rent_tool', 'post_review', 'flag_tool', 'borrow', 'rent_info', 'accept_request', 'return_tool', 'tool_returned', 'send_reminder', 'borrow_history', 'confirm_return', 'deny_reminder', 'customer_condition', 'owner_condition']:

        return redirect(url_for('unconfirmed'))


@app.route('/unconfirmed', methods=['POST', 'GET'])
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('home'))
    return render_template('auth/unconfirmed.html')


@app.route('/resend-confirmation', methods=['POST', 'GET'])
def resend_confirmation_email():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('home'))
    token = generate_confirmation_token(current_user.id)
    flash("A new confirmation link has been sent to your email")
    send_mail(current_user.email, 'Confirm your account', '/mail/confirmation_mail', user=current_user, token=token)
    notif = Notification(user_id=current_user.id, subject='Confirm your acccount', content='Please refer to your email to confirm your account')
    db.session.add(notif)
    db.session.commit()
    return redirect(url_for('unconfirmed'))


@app.route("/")
@app.route("/home")
def home():

    if current_user.is_authenticated:
        count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()

        maxTools = Tools.query.filter(Tools.availibility==True, Tools.user_id!=current_user.id).count()
        tools=[]
        owners=[]
        distances=[]
        random_tools_id=[]

        if maxTools <= 10:
            tools=Tools.query.filter(Tools.availibility==True, Tools.user_id!=current_user.id)


        else:
            tools_id = [x.id for x in Tools.query.filter(Tools.availibility==True, Tools.user_id!=current_user.id).all()]

            for i in range(10):
                random_number = random.randint(0, len(tools_id)-1)
                random_tools_id.append(tools_id[random_number])
                del tools_id[random_number]

            tools = Tools.query.filter(Tools.id.in_(random_tools_id))

        current_user_address = Address.query.filter(Address.user_id == current_user.id).first()


            #Get coordinates of current user
        api_key = ''
        gmaps = googlemaps.Client(key=api_key)

        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        endpoint = f"{base_url}?address={current_user_address.postcode}&key={api_key}"          #Might change and add the coords to the databse
        r = requests.get(endpoint)

        results = r.json()['results'][0]
        lat = results['geometry']['location']['lat']
        lng = results['geometry']['location']['lng']

        average_rating=[]

        for eachTool in tools:
            tool_owner = User.query.get(eachTool.user_id)
            owners.append(tool_owner)

            #Get distance between user and tool
            address=Address.query.filter(Address.user_id == eachTool.user_id).first()
            lat2 = address.latitude
            lng2 = address.longitude
            dist = gmaps.distance_matrix((lat, lng), (lat2, lng2), mode='driving')['rows'][0]['elements'][0]['distance']['value']
            dist/=1000
            distances.append(dist)

            tool_owners_tools = [x.id for x in Tools.query.filter(Tools.user_id == tool_owner.id).all()]

            reviews=Reviews.query.filter(Reviews.tool_id.in_(tool_owners_tools))

            if reviews.count() > 0:

                sum_rating = 0
                for i in reviews:
                    sum_rating+=i.rating
                average_rating.append(sum_rating / reviews.count())

            else:
                average_rating.append(-1)


    # If user is not authenticated
    else:
        count = 0
        maxTools = Tools.query.filter(Tools.availibility==True).count()

        tools=[]
        owners=[]
        random_tools_id=[]

        if maxTools <= 10:
            tools=Tools.query.filter(Tools.availibility==True)


        else:
            tools_id = [x.id for x in Tools.query.filter(Tools.availibility==True).all()]

            for i in range(10):
                random_number = random.randint(0, len(tools_id)-1)
                random_tools_id.append(tools_id[random_number])
                del tools_id[random_number]

            tools = Tools.query.filter(Tools.id.in_(random_tools_id))

        average_rating=[]

        for eachTool in tools:
            tool_owner = User.query.get(eachTool.user_id)
            owners.append(tool_owner)

            tool_owners_tools = [x.id for x in Tools.query.filter(Tools.user_id == tool_owner.id).all()]

            reviews=Reviews.query.filter(Reviews.tool_id.in_(tool_owners_tools))

            if reviews.count() > 0:

                sum_rating = 0
                for i in reviews:
                    sum_rating+=i.rating
                average_rating.append(sum_rating / reviews.count())

            else:
                average_rating.append(-1)

        distances=[]


    return render_template("home.html", tools_owners_distances_avRating=zip(tools, owners, distances, average_rating), tools=tools, distances=distances, tools_owners_avRating=zip(tools, owners, average_rating), count=count)

@app.route("/sort_by", methods=['GET','POST'])
def sort_by():
    select = request.form.get('sort')
    if select == "nameAZ":
        sort_items = Tools.query.order_by(Tools.title).all()
    return redirect('/borrow', tools=sort_items)


@app.route("/profile")
@login_required
def profile():
    count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()
    has_tools = False
    tools = Tools.query.filter(Tools.user_id == current_user.id).all()
    if len(tools):
        has_tools = True
    user = User.query.get_or_404(current_user.id)
    address=Address.query.filter(current_user.id == Address.user_id).first()
    if address.city:
        has_city = True
    else:
        has_city = False
    return render_template('profile.html', tools=tools, user=user, address=address, tool_status=has_tools, count=count, has_city=has_city)

# @app.route("/messages/")
# @login_required
# def messages():
#     to_chats = []
#     sent_messages = Messages.query.filter(Messages.to_user == current_user.id)
#     for message in sent_messages:
#         to_chats.append([message, User.query.get(message.from_user).name])
#
#
#     from_chats = []
#     received_messages = Messages.query.filter(Messages.from_user == current_user.id)
#     for message in received_messages:
#         from_chats.append([message, User.query.get(message.to_user).name])
#
#     return render_template('messages.html', to_chats=to_chats, from_chats=from_chats)

@app.route("/notifications/")
@login_required
def notifications():
    notifications = Notification.query.filter(Notification.user_id == current_user.id).order_by(Notification.id.desc())
    count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()

    pageData = render_template('notifications.html', notifications=notifications, count=count)

    for notification in notifications:
        notification.seen=True
    db.session.commit()
    return pageData

# @login_required
# @app.route('/sendmessage/<int:user_id>', methods=['GET', 'POST'])
# def send_message(user_id):
#     form = MessagesForm()
#     if form.validate_on_submit():
#         from_user = current_user.id
#         to_user = user_id
#         message_content = form.message.data
#
#         message = Messages(from_user=from_user, to_user=to_user, contents=message_content)
#         subject = "Message from " + User.query.get(from_user).name
#         notif = Notification(user_id=user_id, subject=subject, content=message_content)
#         db.session.add(notif)
#         db.session.add(message)
#         db.session.commit()
#
#         flash('Message sent')
#         return redirect(url_for('messages'))
#
#     return render_template('sendmessage.html', form=form)


@app.route("/post_tool", methods=['GET', 'POST'])
@login_required
def post_tool():

    count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()

    form = ToolForm()

    if form.validate_on_submit():
        tool = Tools(title=form.title.data, description=form.description.data,
            deposit=form.deposit.data, tool_category=form.tool_category.data, user_id=current_user.id)

        db.session.add(tool)
        address = Address(address_line_1=form.location.data, user_id=current_user.id)

        if Address.query.filter(current_user.id == Address.user_id).first():
            address=Address.query.filter(current_user.id == Address.user_id).first()
            address.address_line_1 = form.location.data

            #Get coords of user through address
        api_key = 'AIzaSyDyrFnIprNCQ3-sChnwRq74w8Df0K-SmXs'

        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        endpoint = f"{base_url}?address={address.address_line_1}&key={api_key}"
        r = requests.get(endpoint)

        results = r.json()['results'][0]
        lat = results['geometry']['location']['lat']
        lng = results['geometry']['location']['lng']
        address.latitude = lat
        address.longitude = lng


        db.session.add(address)
        db.session.commit()
        if form.images.data:
            #Gets the image and puts it into img table
            for pic in form.images.data:
                filename = secure_filename(pic.filename)
                encoded_img = base64.b64encode(pic.read())
                image = Img(img=encoded_img, mimetype=pic.mimetype, name=filename)
                image.tool_id = tool.id
                db.session.add(image)
                db.session.commit()
                # tool.image_id = image.id

        flash('Tool Posted')
        return redirect(url_for('post_tool'))

    return render_template('post_tool.html', title='Post Tool', form=form, count=count)


@app.route("/edit_tool/<int:tool_id>", methods=['GET', 'POST'])
@login_required
def edit_tool(tool_id):
    tool = Tools.query.get_or_404(tool_id)

    if tool.user_id != current_user.id:
        flash("You do not have permission to access this page!")
        return redirect(url_for('home'))

    count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()

    form = EditToolForm()

    if form.validate_on_submit():

        # form.populate_obj(tool)

        # check see if the user uploaded any new image(s)
        if form.images.data:
            for pic in form.images.data:
                if not isinstance(pic, str):
                    filename = secure_filename(pic.filename)
                    encoded_img = base64.b64encode(pic.read())
                    image = Img(img = encoded_img, mimetype=pic.mimetype, name=filename)
                    image.tool_id = tool.id
                    db.session.add(image)
                    db.session.commit()

        # update the tool with the edited info:
        address = Address.query.filter(tool.user_id == Address.user_id).first()


        if form.title.data:
            tool.title = form.title.data

        if form.description.data:
            tool.description = form.description.data

        if form.deposit.data:
            tool.deposit = form.deposit.data

        if form.location.data:
            address.address_line_1 = form.location.data
            #Get the coords of the new address
            api_key = 'AIzaSyDyrFnIprNCQ3-sChnwRq74w8Df0K-SmXs'

            base_url = "https://maps.googleapis.com/maps/api/geocode/json"
            endpoint = f"{base_url}?address={address.address_line_1}&key={api_key}"
            r = requests.get(endpoint)

            results = r.json()['results'][0]
            lat = results['geometry']['location']['lat']
            lng = results['geometry']['location']['lng']
            address.latitude = lat
            address.longitude = lng

        db.session.add(tool)
        db.session.add(address)
        db.session.commit()

        # tool.image_id = image_id
        # db.session.commit()
        flash('Tool Edited')
        return redirect(url_for('edit_tool', tool_id=tool_id))

    return render_template('edit_tool.html', form=form, tool=tool, count=count)


@app.route("/tool/<int:tool_id>")
@login_required
def tool(tool_id):
    count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()

    tool = Tools.query.get_or_404(tool_id)
    reviews=Reviews.query.filter(Reviews.tool_id == tool_id)
    average_rating = -1
    users = []
    for review in reviews:
        users.append(User.query.get_or_404(review.user_id))

    has_reviews = False
    if reviews.count():
       has_reviews = True

    if reviews.count()>=5:
        sum_rating=0
        for i in reviews:
            sum_rating+=i.rating
        average_rating = sum_rating / reviews.count()

    return render_template("tool.html", title=tool.title, tool=tool, users_reviews=zip(users, reviews), average_rating=average_rating, has_reviews=has_reviews, count=count)


@app.route("/borrow", methods = ['GET','POST'])
def borrow():

    form = SearchForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:

            tools = Tools.query.filter(Tools.availibility==True, Tools.user_id!=current_user.id)
        else:
            tools = Tools.query.filter(Tools.availibility==True)

        toolsSearched_ids=[]
        searchTerm = form.search.data
        for tool in tools:
            if searchTerm.lower() in tool.title.lower():
                toolsSearched_ids.append(tool.id)
        return redirect(url_for('searched', searchedTools=json.dumps(toolsSearched_ids)))

    select = request.form.get('sort')
    toolCat = request.form.get('filter')
    if current_user.is_authenticated:

        if select == "nameAZ":
            tools=Tools.query.filter(Tools.availibility==True, Tools.user_id!=current_user.id).order_by(Tools.title)

            if toolCat is not None:
                tools=Tools.query.filter(Tools.availibility==True, Tools.tool_category==toolCat, Tools.user_id!=current_user.id).order_by(Tools.title)

            flash("Tools sorted by name A-Z")

        elif select == "nameZA":
            tools=Tools.query.filter(Tools.availibility==True, Tools.user_id!=current_user.id).order_by(Tools.title.desc())

            if toolCat is not None:
                tools=Tools.query.filter(Tools.availibility==True, Tools.tool_category==toolCat, Tools.user_id!=current_user.id).order_by(Tools.title.desc())
            flash("Tools sorted by name Z-A")

        elif select == "priceAsc":
            tools=Tools.query.filter(Tools.availibility==True, Tools.user_id!=current_user.id).order_by(Tools.deposit)

            if toolCat is not None:
                tools=Tools.query.filter(Tools.availibility==True, Tools.tool_category==toolCat, Tools.user_id!=current_user.id).order_by(Tools.deposit)
            flash("Sorted Tools by price from Lowest - Highest")

        elif select == "priceDesc":
            tools=Tools.query.filter(Tools.availibility==True, Tools.user_id!=current_user.id).order_by(Tools.deposit.desc())

            if toolCat is not None:
                tools=Tools.query.filter(Tools.availibility==True, Tools.tool_category==toolCat, Tools.user_id!=current_user.id).order_by(Tools.deposit.desc())
            flash("Sorted Tools by price from Highest - Lowest")

        else:
            tools = Tools.query.filter(Tools.availibility==True, Tools.user_id!=current_user.id)

            if toolCat is not None:
                tools = Tools.query.filter(Tools.availibility==True, Tools.tool_category==toolCat, Tools.user_id!=current_user.id)

        count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()

        distances=[]
        owners=[]
        toolNames=[]
        toolIDs = []
        current_user_address = Address.query.filter(Address.user_id == current_user.id).first()


            #Get coordinates of current user
        api_key = 'AIzaSyDyrFnIprNCQ3-sChnwRq74w8Df0K-SmXs'
        gmaps = googlemaps.Client(key=api_key)

        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        endpoint = f"{base_url}?address={current_user_address.postcode}&key={api_key}"          #Might change and add the coords to the databse
        r = requests.get(endpoint)

        results = r.json()['results'][0]
        lat = results['geometry']['location']['lat']
        lng = results['geometry']['location']['lng']

        average_rating=[]

        for eachTool in tools:
            tool_owner = User.query.get(eachTool.user_id)
            owners.append(tool_owner)
            toolNames.append(eachTool.title)
            toolIDs.append(eachTool.id)

            #get distance between current user's location and every tool owners
            address=Address.query.filter(Address.user_id == eachTool.user_id).first()
            lat2 = address.latitude
            lng2 = address.longitude
            dist = gmaps.distance_matrix((lat, lng), (lat2, lng2), mode='driving')['rows'][0]['elements'][0]['distance']['value']
            dist/=1000
            distances.append(dist)

            tool_owners_tools = [x.id for x in Tools.query.filter(Tools.user_id == tool_owner.id).all()]

            reviews=Reviews.query.filter(Reviews.tool_id.in_(tool_owners_tools))

            if reviews.count() > 0:

                sum_rating = 0
                for i in reviews:
                    sum_rating+=i.rating
                average_rating.append(sum_rating / reviews.count())

            else:
                average_rating.append(-1)

        if select == "distanceAsc":
            if toolCat is not None:
                toolIDs = [x for _, x in sorted(zip(distances, toolIDs))]
                distances = sorted(distances)
                tools = Tools.query.filter(Tools.id.in_(toolIDs))
                tool_map = {t.id: t for t in tools}
                tools = [tool_map[n] for n in toolIDs]


            else:
                toolIDs = [x for _, x in sorted(zip(distances, toolIDs))]
                distances = sorted(distances)
                tools = Tools.query.filter(Tools.id.in_(toolIDs))
                tool_map = {t.id: t for t in tools}
                tools = [tool_map[n] for n in toolIDs]

            flash("Sorted Tools by Distance (Closest First)")


    # If user is not authenticated
    else:
        if select == "nameAZ":
            tools=Tools.query.filter(Tools.availibility==True).order_by(Tools.title)

            if toolCat is not None:
                tools=Tools.query.filter(Tools.availibility==True, Tools.tool_category==toolCat).order_by(Tools.title)

            flash("Tools sorted by name A-Z")

        elif select == "nameZA":
            tools=Tools.query.filter(Tools.availibility==True).order_by(Tools.title.desc())

            if toolCat is not None:
                tools=Tools.query.filter(Tools.availibility==True, Tools.tool_category==toolCat).order_by(Tools.title.desc())
            flash("Tools sorted by name Z-A")

        elif select == "priceAsc":
            tools=Tools.query.filter(Tools.availibility==True).order_by(Tools.deposit)

            if toolCat is not None:
                tools=Tools.query.filter(Tools.availibility==True, Tools.tool_category==toolCat).order_by(Tools.deposit)
            flash("Sorted Tools by price from Lowest - Highest")

        elif select == "priceDesc":
            tools=Tools.query.filter(Tools.availibility==True).order_by(Tools.deposit.desc())

            if toolCat is not None:
                tools=Tools.query.filter(Tools.availibility==True, Tools.tool_category==toolCat).order_by(Tools.deposit.desc())
            flash("Sorted Tools by price from Highest - Lowest")

        elif select == 'distanceAsc':
            tools = Tools.query.filter(Tools.availibility==True)

            if toolCat is not None:
                tools = Tools.query.filter(Tools.availibility==True, Tools.tool_category==toolCat)

            flash('You need an account for this option!')

        else:
            tools = Tools.query.filter(Tools.availibility==True)

            if toolCat is not None:
                tools = Tools.query.filter(Tools.availibility==True, Tools.tool_category==toolCat)

        distances=[]
        owners=[]
        toolNames=[]
        count=0
        average_rating=[]

        for eachTool in tools:
            tool_owner = User.query.get(eachTool.user_id)
            owners.append(tool_owner)
            toolNames.append(eachTool.title)

            tool_owners_tools = [x.id for x in Tools.query.filter(Tools.user_id == tool_owner.id).all()]

            reviews=Reviews.query.filter(Reviews.tool_id.in_(tool_owners_tools))

            if reviews.count() > 0:

                sum_rating = 0
                for i in reviews:
                    sum_rating+=i.rating
                average_rating.append(sum_rating / reviews.count())

            else:
                average_rating.append(-1)


    return render_template('borrow.html', tools_owners_distances_avRating=zip(tools, owners, distances, average_rating), tools=tools, distances=distances, tools_owners_avRating=zip(tools, owners, average_rating), count=count, toolNames=toolNames, form=form, title='Tools', active='home')


@app.route("/searched/<searchedTools>", methods = ['GET','POST'])
def searched(searchedTools):
    form = SearchForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:

            tools = Tools.query.filter(Tools.availibility==True, Tools.user_id!=current_user.id)
        else:
            tools=Tools.query.filter(Tools.availibility==True)

        toolsSearched_ids=[]
        searchTerm = form.search.data
        for tool in tools:
            if searchTerm.lower() in tool.title.lower():
                toolsSearched_ids.append(tool.id)

        return redirect(url_for('searched', searchedTools=json.dumps(toolsSearched_ids)))

    toolsIDs = json.loads(searchedTools)
    tools = Tools.query.filter(Tools.id.in_(toolsIDs))

    if current_user.is_authenticated:

        count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()

        distances=[]
        owners=[]
        toolNames=[]
        current_user_address = Address.query.filter(Address.user_id == current_user.id).first()


            #Get coordinates of current user
        api_key = 'AIzaSyDyrFnIprNCQ3-sChnwRq74w8Df0K-SmXs'
        gmaps = googlemaps.Client(key=api_key)

        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        endpoint = f"{base_url}?address={current_user_address.postcode}&key={api_key}"          #Might change and add the coords to the databse
        r = requests.get(endpoint)

        results = r.json()['results'][0]
        lat = results['geometry']['location']['lat']
        lng = results['geometry']['location']['lng']

        average_rating=[]

        for eachTool in tools:
            tool_owner = User.query.get(eachTool.user_id)
            owners.append(tool_owner)

            #get distance between current user's location and every tool owners
            address=Address.query.filter(Address.user_id == eachTool.user_id).first()
            lat2 = address.latitude
            lng2 = address.longitude
            dist = gmaps.distance_matrix((lat, lng), (lat2, lng2), mode='driving')['rows'][0]['elements'][0]['distance']['value']
            dist/=1000
            distances.append(dist)

            tool_owners_tools = [x.id for x in Tools.query.filter(Tools.user_id == tool_owner.id).all()]

            reviews=Reviews.query.filter(Reviews.tool_id.in_(tool_owners_tools))

            if reviews.count() > 0:

                sum_rating = 0
                for i in reviews:
                    sum_rating+=i.rating
                average_rating.append(sum_rating / reviews.count())

            else:
                average_rating.append(-1)

        allTools = Tools.query.filter(Tools.availibility==True, Tools.user_id!=current_user.id)

        for everyTool in allTools:
            toolNames.append(everyTool.title)


    # If user is not authenticated
    else:

        distances=[]
        owners=[]
        toolNames=[]
        count=0
        average_rating=[]

        for eachTool in tools:
            tool_owner = User.query.get(eachTool.user_id)
            owners.append(tool_owner)

            tool_owners_tools = [x.id for x in Tools.query.filter(Tools.user_id == tool_owner.id).all()]

            reviews=Reviews.query.filter(Reviews.tool_id.in_(tool_owners_tools))

            if reviews.count() > 0:

                sum_rating = 0
                for i in reviews:
                    sum_rating+=i.rating
                average_rating.append(sum_rating / reviews.count())

            else:
                average_rating.append(-1)

        allTools = Tools.query.filter(Tools.availibility==True)

        for everyTool in allTools:
            toolNames.append(everyTool.title)

    return render_template('search.html', tools_owners_distances_avRating=zip(tools, owners, distances, average_rating), tools=tools, distances=distances, tools_owners_avRating=zip(tools, owners, average_rating), count=count, toolNames=toolNames, form=form)

@app.route("/edit_profile", methods = ['GET','POST'])
@login_required
def edit_profile():
    count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()

    user = current_user
    form = ProfileForm()

    address = Address.query.filter(Address.user_id == user.id).first()
    if form.validate_on_submit():
        if form.image.data:
            pic = form.image.data
            filename = secure_filename(pic.filename)
            encoded_img = base64.b64encode(pic.read())
            if user.image:
                # the user already has an image - instead of making another one, replace this to save space on the DB
                user.image.img=encoded_img
                user.image.mimetype=pic.mimetype
                user.image.name=filename
                db.session.add(user)
                db.session.commit()

            else:
            # if the user doesn't have a profile pic already, create a new one and assign it to the user
                image = Img(img=encoded_img, mimetype=pic.mimetype, name=filename)
                image.user_id = user.id
                db.session.add(image)
                db.session.commit()
            flash("Your profile picture has been updated successfully!")

        if form.description.data:
            user.description = form.description.data
            flash("Your profile description has been updated successfully!")

        if form.email.data:
            user.email = form.email.data
            user.confirmed = False
            confirmation_token = generate_confirmation_token(user.id)
            send_mail(user.email, 'Confirm your account', '/mail/confirmation_mail', user=user, token=confirmation_token)
            notif = Notification(user_id=current_user.id, subject='Your email has been updated succesfully!', content='We have sent you a confirmation email to this new email address.')
            db.session.add(notif)
            db.session.commit()
            flash("Your email has been updated successfully! We have sent you a confirmation email to this new email address.")

        if form.name.data:
            user.name = form.name.data
            flash("Your name has been updated successfully!")

        if form.address_line_1.data:
            address.address_line_1 = form.address_line_1.data
            flash('Your address has been updated successfully ')

        if form.city.data:
            address.city = form.city.data
            flash('Your city has been updated successfully')


        db.session.add(user)

        db.session.commit()

        return redirect(url_for('profile'))

    return render_template('edit_profile.html', form=form, count=count)


@app.route("/post_review/<int:tool_id>", methods=['GET', 'POST'])
@login_required
def post_review(tool_id):
    count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()

    toolID = tool_id

    if BorrowHistory.query.filter(BorrowHistory.user_id == current_user.id, BorrowHistory.tool_id == toolID).count() > 0:

        form = ReviewForm()

        if form.validate_on_submit():
            review = Reviews(rating = form.rating.data, written_review = form.written.data, user_id = current_user.id, tool_id = toolID)
            db.session.add(review)
            db.session.commit()
            flash('Review Posted')
            return redirect(url_for('post_review', tool_id=toolID))

        return render_template('review.html', form=form, count=count)

    else:
        flash("You cannot review a tool you haven't borrowed!")
        return redirect(url_for('tool', tool_id=toolID))

@app.route("/flag/<int:tool_id>", methods=['GET', 'POST'])
@login_required
def flag_tool(tool_id):
    count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()

    form = FlagForm()
    toolID = tool_id
    if form.validate_on_submit():
        categories=''
        counter=0
        for i in form.category.data:
            if counter==0:
                categories=i
            elif counter==len(form.category.data)-1:
                categories = categories+' and '+i
            else:
                categories = categories+', '+i
            counter+=1

        flag = Flags(category = categories, user_id = current_user.id, tool_id = toolID)
        db.session.add(flag)
        db.session.commit()
        flash('Flag Received')
        user=User.query.get_or_404(current_user.id)
        tool=Tools.query.get_or_404(toolID)
        send_mail(app.config['ADMIN_MAIL'], 'User just flagged a post', '/mail/flagging_mail', user=user, tool=tool, flag=flag)
        return redirect(url_for('flag_tool', tool_id = toolID))

    return render_template('flag.html', form=form, count=count)


@app.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('home'))
    key = verify_confirmation_token(token)

    if key:
        if key.get('confirm') == current_user.id:
            current_user.confirmed = True
            db.session.add(current_user)
            db.session.commit()
            flash('You have successfully confirmed your account. Thanks!')
        else:
            flash('The confirmation link is either invalid or has expired!')
        return redirect(url_for('home'))



@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user)
            return redirect(request.args.get('next') or url_for('home'))
        flash('Incorrect login details!')
        return redirect(url_for('login'))

    return render_template('/auth/login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()

    if form.validate_on_submit():

        user = User(name=form.name.data, email=form.email.data,
                    password=form.password.data, age=form.age.data)
        db.session.add(user)
        db.session.commit()

        default_image = Img.query.get(125)
        default_image_user_specific = Img(img=default_image.img, mimetype=default_image.mimetype, name=default_image.name)
        default_image_user_specific.user_id = user.id
        db.session.add(default_image_user_specific)
        db.session.commit()

        address = Address(postcode=form.postcode.data, user_id=user.id)
        db.session.add(address)
        db.session.commit()
        send_mail(app.config['ADMIN_MAIL'], 'New User joined the platform', '/mail/registration_mail', user=user)
        confirmation_token = generate_confirmation_token(user.id)
        send_mail(user.email, 'Confirm your account', '/mail/confirmation_mail', user=user, token=confirmation_token)
        flash('A confirmation email has been sent to your email!')
        return redirect(url_for('login'))
    return render_template('/auth/register.html', form=form, postcodes=postcodes())


@app.route('/reset_password', methods=['GET', 'POST'])
def forgotten_password():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = ResetPassword()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user:
            reset_token = generate_confirmation_token(user.email)
            send_mail(user.email, 'Reset your password', '/mail/reset_password', user=user, token=reset_token)
            notif = Notification(user_id=user.id, subject='Your password has been reset', content='We have sent you a confirmation email.')
            db.session.add(notif)
            db.session.commit()
            flash("We've sent a password reset link to your email!")
        else:
            flash("There isn't any account associated to the email address provided!")

        return redirect(url_for('forgotten_password'))

    return render_template('/auth/forgot_password.html', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    key = verify_confirmation_token(token)
    if not key:
        flash("Your reset link has either expired or is not valid!")
        flash("Try reseting your password again")
        return redirect(url_for('reset_password'))

    form = ChangePassword()
    if form.validate_on_submit():
        user = User.query.filter_by(email=key.get('confirm')).first()
        user.password = form.password.data
        db.session.add(user)
        db.session.commit()
        flash("Your password has been successfully updated!")
        return redirect(url_for('login'))
    return render_template('/auth/reset_password.html', form=form)


@app.route("/rent_info/<int:tool_id>/<int:customer_id>/<token>", methods=['GET', 'POST'])
@login_required
def rent_info(tool_id, customer_id, token):
    key = verify_confirmation_token(token)
    if not key:
        flash("The link is either invalid or has expired!")
        return redirect(url_for('home'))

    elif (key['confirm'][1] != current_user.id):
        flash("You don't have permission to access this link! Only the owner of the tool can access this page!")
        return redirect(url_for('home'))
    else:
        tool = Tools.query.get_or_404(tool_id)
        customer = User.query.get_or_404(customer_id)

    return render_template('/rent_info.html', tool=tool, customer=customer)


@app.route("/accept_request/<int:tool_id>/<int:customer_id>")
@login_required
def accept_request(tool_id, customer_id):
    confirmation_token = generate_confirmation_token([customer_id, tool_id])
    customer = User.query.get_or_404(customer_id)
    tool = Tools.query.get_or_404(tool_id)
    send_mail(customer.email, 'Your Tool Request Has Been Accepted!', '/mail/tool_accepted', token=confirmation_token, tool=tool, customer=customer)
    notif = Notification(user_id=customer.id, subject='Your Tool Request Has Been Accepted!', content='You are now able to pick up and use the tool you requested. Check your emails to pay your deposit.')
    db.session.add(notif)
    db.session.commit()

    flash("An email will be sent to the user to pay the deposit amount required for borrowing your tool.")
    return(redirect(url_for('home')))

@app.route("/deny_request/<int:tool_id>/<int:customer_id>")
@login_required
def deny_request(tool_id, customer_id):
    tool = Tools.query.get_or_404(tool_id)
    tool.availibility = True
    db.session.add(tool)
    db.session.commit()

    confirmation_token = generate_confirmation_token(customer_id)
    customer = User.query.get_or_404(customer_id)
    send_mail(customer.email, 'Your Tool Request Has Been Denied', '/mail/tool_denied', customer=customer, tool=tool, token=confirmation_token)
    notif = Notification(user_id=customer.id, subject='Your Tool Request Has Been Denied', content='We regret to inform you that you have been denied use of the tool you selected.')
    db.session.add(notif)
    db.session.commit()

    flash("This tool will be made available again. A confirmation email has been sent to the user wanting to borrow the tool.")
    return(redirect(url_for('home')))


@app.route("/rent_tool/<token>", methods=['GET', 'POST'])
@login_required
def rent_tool(token):
    count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()

    key = verify_confirmation_token(token)
    if not key:
        flash("Link either invalid or has expired!")
        return redirect(url_for('home'))

    elif (key['confirm'][0] != current_user.id):
        flash("You don't have permission to access this link!")
        return redirect(url_for('home'))
    else:
        form = RentToolForm()
        tool = Tools.query.get_or_404(key['confirm'][1])
        deposit = tool.deposit

        if form.validate_on_submit():
            # create a borrow history entry in the database:
            borrow_history_element = BorrowHistory(user_id=current_user.id, tool_id=tool.id, deposit_paid=tool.deposit)
            db.session.add(borrow_history_element)
            db.session.commit()
            return redirect(url_for('successfully_rented', user_id=current_user.id, tool_id=tool.id))

    return render_template("payment_form.html", form=form, deposit=deposit, count=count)


@app.route('/deposit_received/<int:user_id>/<int:tool_id>')
@login_required
def successfully_rented(user_id, tool_id):
    count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()

    if user_id != current_user.id:
        flash("You cannot access this page!")
        return redirect(url_for('home'))

    # check to see whether the user has even borrowed this particular tool:
    tool_borrowed_status = False

    tool = Tools.query.get_or_404(tool_id)
    for x in current_user.borrowed_tools:
        if x.tool_id == tool_id:
            tool_borrowed_status = True

    if not tool_borrowed_status:
        flash("Invalid link!")
        return redirect(url_for('home'))

    return render_template("successful_deposit.html", tool=tool, count=count, owner=tool.user_id)


@app.route('/borrow_history')
@login_required
def borrow_history():
    count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()
    borrow_history_elements = current_user.borrowed_tools
    hist_elements_a = []
    hist_elements_p = []
    borrowed_tools_a = [];
    borrowed_owners_a = [];
    borrow_date_a = []
    customer_a = []
    borrowed_tools_p = [];
    borrowed_owners_p = [];
    borrow_date_p = []
    customer_p = []
    active_tool_list = []
    previous_tool_list = []
    user_has_borrowed = False
    if len(borrow_history_elements):
        user_has_borrowed = True
        for x in borrow_history_elements:
            if x.active_status == True:
                hist_elements_a.append(x)
                borrowed_tools_a.append(Tools.query.get_or_404(x.tool_id))
                tool = Tools.query.get_or_404(x.tool_id)
                customer_a.append(User.query.get_or_404(x.user_id))
                borrowed_owners_a.append(User.query.get_or_404(tool.user_id))
                borrow_date_a.append(x.date.date())
            elif x.active_status == False:
                hist_elements_p.append(x)
                borrowed_tools_p.append(Tools.query.get_or_404(x.tool_id))
                tool = Tools.query.get_or_404(x.tool_id)
                customer_p.append(User.query.get_or_404(x.user_id))
                borrowed_owners_p.append(User.query.get_or_404(tool.user_id))
                borrow_date_p.append(x.date.date())
    if len(hist_elements_a) > 0 and len(hist_elements_p) > 0:
        return render_template('borrow_history.html', user=current_user, active_tools_details=zip(hist_elements_a, borrowed_tools_a, borrowed_owners_a, borrow_date_a, customer_a), previous_tools_details=zip(hist_elements_p, borrowed_tools_p, borrowed_owners_p, borrow_date_p, customer_p), borrow_status=user_has_borrowed, count=count)
    if len(hist_elements_a) > 0:
        return render_template('borrow_history.html', user=current_user, active_tools_details=zip(hist_elements_a, borrowed_tools_a, borrowed_owners_a, borrow_date_a, customer_a), borrow_status=user_has_borrowed, count=count)
    if len(hist_elements_p) > 0:
        return render_template('borrow_history.html', user=current_user, previous_tools_details=zip(hist_elements_p, borrowed_tools_p, borrowed_owners_p, borrow_date_p, customer_p), borrow_status=user_has_borrowed, count=count)

    return render_template('borrow_history.html', user=current_user, borrow_status=user_has_borrowed, count=count)

@app.route("/return_tool/<int:tool_id>/<int:user_id>/<int:customer_id>")
@login_required
def return_tool(tool_id, user_id, customer_id):
    owner = User.query.get_or_404(user_id)
    customer = User.query.get_or_404(customer_id)
    tool = Tools.query.get_or_404(tool_id)
    confirmation_token = generate_confirmation_token([owner.id, customer.id, tool.id])
    send_mail(owner.email, 'Has your tool been returned?', '/mail/owner_returned', owner=owner, tool=tool, customer=customer, token=confirmation_token)
    notif = Notification(user_id=owner.id, subject='Has your tool been returned?', content='Please refer to your email to confirm when your tool has been returned correctly.')
    db.session.add(notif)
    db.session.commit()
    flash("The owner of the tool has been sent an email to check that they have received the tool. Please wait for them to confirm.")

    return redirect(url_for('home'))


@app.route("/tool_returned/<token>", methods=['GET', 'POST'])
@login_required
def tool_returned(token):
    key = verify_confirmation_token(token)
    if not key:
        flash("The link is either invalid or has expired!")
        return redirect(url_for('home'))
    elif (key['confirm'][0] != current_user.id):
        flash("You don't have permission to access this link!")
        return redirect(url_for('home'))
    else:
        tool = Tools.query.get_or_404(key['confirm'][2])
        customer = User.query.get_or_404(key['confirm'][1])

    return render_template('/tool_returned.html', tool=tool, customer=customer, owner_id=current_user.id)

@app.route("/confirm_return/<int:tool_id>/<int:customer_id>")
@login_required
def confirm_return(tool_id, customer_id):

    customer = User.query.get_or_404(customer_id)
    notif = Notification(user_id=current_user.id, subject='Tool return confirmation', content='You have confirmed the tool has been returned. The tool will now be put back up as available on our website!')
    db.session.add(notif)
    db.session.commit()

    flash("You have confirmed the tool has been returned. The tool will now be put back up as available on our wesbite!")
    return redirect(url_for('owner_condition', customer_id=customer_id, tool_id=tool_id))

@app.route("/owner_condition/<int:customer_id>/<int:tool_id>/<int:owner_id>", methods=['GET', 'POST'])
@login_required
def owner_condition(customer_id, tool_id, owner_id):

    if current_user.id != owner_id:
        flash("You don't have permission to access this page!")
        return redirect(url_for('home'))

    count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()

    form = ToolConditionForm()

    owner = User.query.get_or_404(current_user.id)
    tool = Tools.query.get_or_404(tool_id)
    customer = User.query.get_or_404(customer_id)
    if form.validate_on_submit():
        rating = form.condition.data
        owner_note = form.notes.data
        confirmation_token = generate_confirmation_token([owner_id, customer_id, tool_id, rating, owner_note])
        send_mail(customer.email, 'Tool condition rating', '/mail/customer_condition', token=confirmation_token, customer=customer, tool=tool, owner=owner)
        notif = Notification(user_id=customer.id, subject='Please rate the tool!', content='Please rate the condition of the tool you just returned to receive your deposit. Check your email.')
        db.session.add(notif)
        db.session.commit()
        flash("Thank you for rating the tool's condition. Once the customer has rated the condition of the tool, the deposit will be returned.")
        return redirect(url_for('home'))

    return render_template('/owner_condition.html', form=form, count=count)

@app.route("/customer_condition/<token>", methods=['GET','POST'])
@login_required
def customer_condition(token):
    count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()

    key = verify_confirmation_token(token)

    if not key:
        flash("The link has either expired or is invalid!")
        return redirect(url_for('home'))
    elif (key['confirm'][1] != current_user.id):
        flash("You don't have permission to access this link!")
        return redirect(url_for('home'))
    else:
        form = ToolConditionForm()
        rating = key['confirm'][3]
        tool = Tools.query.get_or_404(key['confirm'][2])
        owner_notes = key['confirm'][4]
        if owner_notes:
            has_notes = True
        else:
            has_notes = False
        if form.validate_on_submit():
            tool = Tools.query.get_or_404(key['confirm'][2])
            tool.availibility = True
            db.session.add(tool)
            db.session.commit()

            tool_borrowed = BorrowHistory.query.filter_by(tool_id=key['confirm'][2])
            active_tool = tool_borrowed.filter_by(active_status=True).first()
            deposit_return = active_tool.deposit_paid
            depos = active_tool.deposit_paid
            deposit_status = True
            if rating == ("given" or "cosmetic"):
                deposit_return = (depos) * 0.97
                reason = "Only 3% fee taken by the website as the owner was satisfied with the condition of the returned tool."
            elif rating == "partial":
                deposit_return = (depos) * 0.47
                reason = "50% of deposit taken as the tool was partially functional when returned!"
            elif rating == "broken":
                reason = "The tool was returned in a broken condition!"
                deposit_return = 0
                deposit_status = False
            deposit_return = "{:.2f}".format(deposit_return)

            history = BorrowHistory.query.filter_by(tool_id=key['confirm'][2])
            tool_hist = history.filter_by(active_status=True).first()
            # history = User.query.filter_by(email=form.email.data).first()

            tool_hist.active_status = False
            db.session.add(tool)
            db.session.commit()

            send_mail(current_user.email, 'Thank you!', '/mail/deposit_return',  deposit_return=deposit_return,
                      customer=current_user, tool=tool, depos=depos, reason=reason, status=deposit_status,
                      notes=owner_notes, has_notes=has_notes)
            flash("Thank you for reviewing the tool. Your deposit should be returned within the next 5-10 working days. We have sent you an email containing more detail!")
            return redirect(url_for('home'))

    return render_template('/owner_condition.html', form=form, count=count)

@app.route("/deny_return/<int:tool_id>/<int:customer_id>")
@login_required
def deny_return(tool_id, customer_id):
    tool = Tools.query.get_or_404(tool_id)
    customer = User.query.get_or_404(customer_id)
    send_mail(customer.email, 'Tool return reminder', '/mail/deny_returned', customer=customer, tool=tool)
    notif = Notification(user_id=customer.id, subject='Tool return reminder', content='An email has been sent to the user with your tool.')
    db.session.add(notif)
    db.session.commit()

    flash("An email has been sent to the user with your tool. Check you notification ")
    return redirect(url_for('home'))

@app.route("/request_tool/<int:tool_id>")
@login_required
def request_tool(tool_id):
    tool = Tools.query.get_or_404(tool_id)
    if tool.availibility:
        tool.availibility = False
        db.session.add(tool)
        db.session.commit()

        tool = Tools.query.get_or_404(tool_id)
        user = User.query.get_or_404(current_user.id)
        owner = User.query.get_or_404(tool.user_id)

        confirmation_token = generate_confirmation_token([current_user.id, owner.id])
        send_mail(owner.email, 'Tool request', '/mail/tool_request', user=user, owner=owner, tool=tool, token=confirmation_token)
        notif = Notification(user_id=owner.id, subject='Tool request', content='A user has requested to borrow your tool. Please check your email.')
        db.session.add(notif)
        db.session.commit()
        flash("A request email has been sent to the owner. Please wait for them to respond.")
    else:
        flash("This tool is not currently available! You can either wait or look for other similar tools.")
    return redirect(url_for('tool', tool_id = tool_id))


@app.route('/userprofile/<int:owner_id>')
def user_profile(owner_id):
    user = User.query.get_or_404(owner_id)
    has_tools = False
    tools = Tools.query.filter(Tools.user_id == owner_id).all()
    if len(tools):
        has_tools = True
    return render_template('user_profile.html', user=user, has_tools=has_tools, tools=tools)


@app.route('/remove_image/<int:img_id>')
@login_required
def remove_image(img_id):

    toolID = Img.query.get_or_404(img_id).tool_id
    Img.query.filter(Img.id == img_id).delete()
    db.session.commit()

    return redirect(url_for('edit_tool', tool_id=toolID))

@app.route('/terms')
def terms():
    if current_user.is_authenticated:
        count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()
    else:
        count = None;
    return render_template('terms.html', count=count)


@app.route('/privacy-policy')
def privacy_policy():
    if current_user.is_authenticated:
        count = Notification.query.filter(Notification.user_id == current_user.id).filter(Notification.seen == False).count()
    else:
        count = None;

    return render_template('privacy.html', count=count)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))
