from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
import os

from restaurant import Orders, unavailable_food, add_order, remove_order, print_receipt

load_dotenv()

app = Flask(__name__)
app.secret_key = 'acid-treats-secret-key'

db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT')
db_name = os.environ.get('DB_NAME')

app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from models import db, Order, MenuItem, User
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
    menu_items = MenuItem.query.filter_by(available=True).all()
    return render_template('menu.html', menu_items=menu_items)


@app.route('/add_order', methods=['POST'])
def add():
    food = request.form['food']
    quantity = int(request.form['quantity'])
    notes = request.form.get('notes', '').strip()
    add_order(food, quantity, notes)
    return redirect('/')

@app.route('/cart')
@login_required
def cart():
    import restaurant
    return render_template('cart.html', ordered_food=restaurant.Ordered_food, total=restaurant.total_amount_ordered)


@app.route('/remove_order', methods=['POST'])
def remove():
    item = request.form['item']
    parts = item.split()
    quantity= int(parts[0])
    food = parts[1]
    remove_order(food, int(quantity))
    return redirect('/cart')

@app.route('/checkout')
@login_required
def checkout():
    import restaurant
    if not restaurant.Ordered_food:
        return redirect('/')

    return render_template('checkout.html', ordered_food=restaurant.Ordered_food, total=restaurant.total_amount_ordered, delivery_fee=1000)

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    import restaurant
    order_type = request.form.get('order_type', 'Pickup')

    items_string = "; ".join(restaurant.Ordered_food)

    DELIVERY_FEE = 1000

    total = restaurant.total_amount_ordered
    if order_type == 'Delivery':
        total += DELIVERY_FEE

    new_order = Order(
        items=items_string,
        total=total,
        order_type=order_type,
        user_id=current_user.id if current_user.is_authenticated else None
    )
    db.session.add(new_order)
    db.session.commit()

    restaurant.Ordered_food.clear()
    restaurant.total_amount_ordered = 0
    return render_template('order_confirmed.html', order_type=order_type)

@app.route('/history')
@login_required
def history():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('history.html', orders=orders)


@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        return redirect('/')

    menu_items = MenuItem.query.all()
    return render_template('admin.html', menu_items=menu_items)


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

@app.route('/admin/toggle/<int:item_id>', methods=['POST'])
@login_required
def toggle_item(item_id):
    if not current_user.is_admin:
        return redirect('/')

    item = MenuItem.query.get(item_id)
    item.available = not item.available
    db.session.commit()
    return redirect('/admin')


@app.route('/admin/add', methods=['POST'])
@login_required
def add_item():
    if not current_user.is_admin:
        return redirect('/')

    name = request.form['name']
    price = request.form['price']

    new_item = MenuItem(name=name, price=price, available=True)
    db.session.add(new_item)
    db.session.commit()
    return redirect('/admin')


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
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

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)

