from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from flask_mail import Mail, Message
import secrets
from datetime import datetime, timedelta
import os
import requests

load_dotenv()

app = Flask(__name__)
app.secret_key = 'acid-treats-secret-key'

app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

mail = Mail(app)

db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT')
db_name = os.environ.get('DB_NAME')
PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')

app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from models import db, Order, MenuItem, User, ContactMessage, CartItem, PromoCode
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

    if MenuItem.query.count() == 0:
        starter_menu = {
            'Rice': 500,
            'Beans': 300,
            'Pasta': 200,
            'Pizza': 15000,
            'Sharwama': 3000
        }
        for name, price in starter_menu.items():
            db.session.add(MenuItem(name=name, price=price))
        db.session.commit()




@app.route('/')
def home():
    selected_category = request.args.get('category')
    if selected_category:
        menu_items = MenuItem.query.filter_by(available=True, category=selected_category).all()
    else:
        menu_items = MenuItem.query.filter_by(available=True).all()
    popular_items = MenuItem.query.filter_by(available=True).order_by(MenuItem.order_count.desc()).limit(3).all()
    return render_template('menu.html', menu_items=menu_items, popular_items=popular_items, selected_category=selected_category)

@app.route('/add_order', methods=['POST'])
@login_required
def add():
    food = request.form['food']
    quantity = int(request.form['quantity'])
    notes = request.form.get('notes', '').strip()

    existing = CartItem.query.filter_by(user_id=current_user.id, food=food, notes=notes).first()
    if existing:
        existing.quantity += quantity
    else:
        new_item = CartItem(user_id=current_user.id, food=food, quantity=quantity, notes=notes)
        db.session.add(new_item)

    item = MenuItem.query.filter_by(name=food).first()
    if item:
        item.order_count = (item.order_count or 0) + quantity

    db.session.commit()
    return redirect('/')

@app.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(
        (MenuItem.query.filter_by(name=item.food).first().price or 0) * item.quantity
        for item in cart_items
    )
    return render_template('cart.html', ordered_food=cart_items, total=total)


@app.route('/remove_order', methods=['POST'])
@login_required
def remove():
    item_id = int(request.form['item_id'])
    cart_item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
    return redirect('/cart')

@app.route('/checkout')
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return redirect('/')

    total = sum(
        (MenuItem.query.filter_by(name=item.food).first().price or 0) * item.quantity
        for item in cart_items
    )
    return render_template('checkout.html', ordered_food=cart_items, total=total)

@app.route('/initialize_payment', methods=['POST'])
@login_required
def initialize_payment():
    order_type = request.form.get('order_type', 'Pickup')

    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return redirect('/cart')

    DELIVERY_FEE = 1000
    total = sum(
        (MenuItem.query.filter_by(name=item.food).first().price or 0) * item.quantity
        for item in cart_items
    )
    if order_type == 'Delivery':
        total += DELIVERY_FEE

    promo_code_input = request.form.get('promo_code', '').strip().upper()
    discount_applied = 0

    if promo_code_input:
        promo = PromoCode.query.filter_by(code=promo_code_input, active=True).first()
        if promo:
            if promo.discount_type == 'percent':
                discount_applied = total * promo.discount_value / 100
            else:
                discount_applied = promo.discount_value
            total = max(total - discount_applied, 0)

    amount_kobo = int(total * 100)  # Paystack uses kobo, not naira

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "email": current_user.email,
        "amount": amount_kobo,
        "callback_url": url_for('verify_payment', _external=True),
        "metadata": {
            "order_type": order_type,
            "user_id": current_user.id
        }
    }

    response = requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers)
    res_data = response.json()

    if res_data.get('status'):
        return redirect(res_data['data']['authorization_url'])
    else:
        return "Payment initialization failed. Please try again.", 400


@app.route('/verify_payment')
@login_required
def verify_payment():
    reference = request.args.get('reference')
    if not reference:
        return "Missing payment reference.", 400

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
    }
    response = requests.get(f"https://api.paystack.co/transaction/verify/{reference}", headers=headers)
    res_data = response.json()

    if res_data.get('status') and res_data['data']['status'] == 'success':
        order_type = res_data['data']['metadata'].get('order_type', 'Pickup')

        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            return render_template('order_confirmed.html', order_type=order_type)

        items_string = "; ".join(
            f"{item.quantity} {item.food}" + (f" ({item.notes})" if item.notes else "")
            for item in cart_items
        )
        total = res_data['data']['amount'] / 100  # convert back from kobo

        new_order = Order(
            items=items_string,
            total=total,
            order_type=order_type,
            user_id=current_user.id
        )
        db.session.add(new_order)

        for item in cart_items:
            db.session.delete(item)

        db.session.commit()

        return render_template('order_confirmed.html', order_type=order_type)
    else:
        return "Payment verification failed. Please contact support.", 400


@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    order_type = request.form.get('order_type', 'Pickup')

    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return redirect('/cart')

    items_string = "; ".join(
        f"{item.quantity} {item.food}" + (f" ({item.notes})" if item.notes else "")
        for item in cart_items
    )

    DELIVERY_FEE = 1000
    total = sum(
        (MenuItem.query.filter_by(name=item.food).first().price or 0) * item.quantity
        for item in cart_items
    )
    if order_type == 'Delivery':
        total += DELIVERY_FEE

    new_order = Order(
        items=items_string,
        total=total,
        order_type=order_type,
        user_id=current_user.id
    )
    db.session.add(new_order)

    for item in cart_items:
        db.session.delete(item)

    db.session.commit()

    return render_template('order_confirmed.html', order_type=order_type)


@app.route('/history')
@login_required
def history():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('history.html', orders=orders)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()

        existing = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing:
            return render_template('profile.html', error="That email is already in use by another account.")

        current_user.full_name = full_name
        current_user.email = email
        current_user.phone = phone
        db.session.commit()

        return render_template('profile.html', success="Profile updated successfully.")

    return render_template('profile.html')

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        return redirect('/')

    menu_items = MenuItem.query.all()
    orders = Order.query.order_by(Order.id.desc()).all()

    total_revenue = db.session.query(db.func.sum(Order.total)).scalar() or 0
    total_orders = Order.query.count()
    top_items = MenuItem.query.order_by(MenuItem.order_count.desc()).limit(5).all()

    return render_template('admin.html', menu_items=menu_items, orders=orders,
                            total_revenue=total_revenue, total_orders=total_orders, top_items=top_items)


@app.route('/admin/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    if not current_user.is_admin:
        return redirect('/')

    item = MenuItem.query.get(item_id)

    if request.method == 'POST':
        item.name = request.form['name']
        item.price = request.form['price']
        db.session.commit()
        return redirect('/admin')

    return render_template('edit_item.html', item=item)

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    item = MenuItem.query.get_or_404(item_id)
    return render_template('item_detail.html', item=item)

@app.route('/admin/toggle/<int:item_id>', methods=['POST'])
@login_required
def toggle_item(item_id):
    if not current_user.is_admin:
        return redirect('/')

    item = MenuItem.query.get(item_id)
    item.available = not item.available
    db.session.commit()
    return redirect('/admin')



from werkzeug.utils import secure_filename

@app.route('/admin/add', methods=['POST'])
@login_required
def admin_add():
    if not current_user.is_admin:
        return redirect('/')

    name = request.form['name']
    price = int(request.form['price'])
    category = request.form['category']

    image_url = None
    file = request.files.get('image')
    if file and file.filename:
        filename = secure_filename(file.filename)
        filepath = os.path.join('static', 'images', filename)
        file.save(filepath)
        image_url = f'/static/images/{filename}'

    new_item = MenuItem(name=name, price=price, category=category, image_url=image_url)
    db.session.add(new_item)
    db.session.commit()
    return redirect('/admin')


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        new_message = ContactMessage(name=name, email=email, message=message)
        db.session.add(new_message)
        db.session.commit()

        return render_template('contact.html', success=True)

    return render_template('contact.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('signup.html', error="Username already taken")

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            return render_template('signup.html', error="Email already registered")

        new_user = User(username=username, full_name=full_name, email=email, phone=phone)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect('/')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect('/')
        else:
            return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']

        user = User.query.filter_by(username=username, email=email).first()
        if not user:
            return render_template('forgot_password.html', error="No account matches that username and email.")

        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()

        reset_link = url_for('reset_password', token=token, _external=True)

        msg = Message('Reset Your Password - ACiD\'S TREATS',
                       sender=os.environ.get('MAIL_USERNAME'),
                       recipients=[email])
        msg.body = f"Hi {user.full_name},\n\nClick the link below to reset your password. This link expires in 1 hour.\n\n{reset_link}\n\nIf you didn't request this, ignore this email."
        mail.send(msg)

        return render_template('forgot_password.html', success=True)

    return render_template('forgot_password.html')

@app.route('/admin/order/<int:order_id>/status', methods=['POST'])
@login_required
def update_order_status(order_id):
    if not current_user.is_admin:
        return redirect(url_for('home'))
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    valid_statuses = ['Pending', 'Preparing', 'Out for Delivery', 'Delivered']
    if new_status in valid_statuses:
        order.status = new_status
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()

    if not user or user.reset_token_expiry < datetime.utcnow():
        return render_template('forgot_password.html', error="That reset link is invalid or has expired.")

    if request.method == 'POST':
        new_password = request.form['new_password']
        user.set_password(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        return redirect('/login')

    return render_template('reset_password.html', token=token)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)

